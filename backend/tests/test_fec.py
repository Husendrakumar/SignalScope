import os
import json
import random
import pytest
from fastapi.testclient import TestClient
from app.main import app
from scripts.generate_test_signals import generate_test_signals
from app.signal_processing.fec import (
    convolutional_encode,
    viterbi_decode,
    try_viterbi_decoders
)


@pytest.fixture(scope="module", autouse=True)
def setup_test_signals():
    generate_test_signals()


def test_encoder_decoder_roundtrip():
    """
    Proves viterbi_decode is the exact mathematical inverse of convolutional_encode
    across deterministic, alternating, non-repeating, and pseudo-random payloads.
    """
    rng = random.Random(42)
    test_patterns = [
        "10110010",
        "1010101010101010",
        "1100110011001100",
        "".join(rng.choice(["0", "1"]) for _ in range(256)),
    ]

    for pattern in test_patterns:
        encoded = convolutional_encode(pattern, k=3, g1=7, g2=5, flush=True)
        # Encoded length is (len(pattern) + 2) * 2
        assert len(encoded) == (len(pattern) + 2) * 2

        decoded = viterbi_decode(encoded, k=3, g1=7, g2=5, trim_flush=True)
        assert decoded == pattern, f"Roundtrip failed for pattern: {pattern[:16]}..."


def test_error_correction_capability():
    """
    Demonstrates actual Forward Error Correction:
    Injects bit flips into the encoded bitstream and verifies that Viterbi decoding
    corrects the errors, achieving BER before Viterbi > 0 and BER after Viterbi = 0.
    """
    rng = random.Random(777)
    original_payload = "".join(rng.choice(["0", "1"]) for _ in range(128))

    encoded = convolutional_encode(original_payload, k=3, g1=7, g2=5, flush=True)
    encoded_list = list(encoded)

    # Inject bit errors (flip 2 bits at positions 10 and 50)
    flip_indices = [10, 50]
    for idx in flip_indices:
        encoded_list[idx] = '1' if encoded_list[idx] == '0' else '0'

    corrupted_encoded = "".join(encoded_list)

    # Compute raw BER before Viterbi
    raw_errors = len(flip_indices)
    raw_ber = raw_errors / len(encoded)
    assert raw_ber > 0.0

    # Run Viterbi decoding
    decoded_payload = viterbi_decode(corrupted_encoded, k=3, g1=7, g2=5, trim_flush=True)
    assert len(decoded_payload) == len(original_payload)

    # Compute payload BER after Viterbi
    payload_errors = sum(1 for i in range(len(original_payload)) if decoded_payload[i] != original_payload[i])
    payload_ber = payload_errors / len(original_payload)

    assert payload_ber == 0.0, f"Viterbi failed to correct errors, got {payload_errors} errors ({payload_ber*100:.2f}% BER)"


def test_invalid_fec_parameters():
    with pytest.raises(ValueError):
        convolutional_encode("1010", k=7, g1=171, g2=133)  # Unsupported K

    with pytest.raises(ValueError):
        viterbi_decode("10101", k=3, g1=7, g2=5)  # Odd bit count for Rate 1/2

    with pytest.raises(ValueError):
        convolutional_encode("10201", k=3, g1=7, g2=5)  # Non-binary character '2'


def test_try_viterbi_decoders_candidates():
    rng = random.Random(888)
    orig_bits = "".join(rng.choice(["0", "1"]) for _ in range(128))
    encoded = convolutional_encode(orig_bits, k=3, g1=7, g2=5, flush=True)

    res = try_viterbi_decoders(encoded, ground_truth=orig_bits)
    assert res["input_bit_count"] == len(encoded)
    assert res["selected_configuration"]["rate"] == "1/2"
    assert res["selected_configuration"]["constraint_length"] == 3
    assert res["selected_configuration"]["status"] == "VALIDATED"
    assert res["decoded_bits"] == orig_bits


def test_end_to_end_fec_fsk_pipeline():
    """
    End-to-End Pipeline Test for Part 10A:
    test_fec_fsk -> FSK Demodulator -> Viterbi Decoder -> Original Payload (100% Accuracy)
    """
    client = TestClient(app)

    json_path = os.path.join("test_data", "test_fec_fsk.json")
    assert os.path.exists(json_path)
    with open(json_path, "r") as f:
        gt_meta = json.load(f)

    expected_original_bits = gt_meta["original_bits"]
    k = gt_meta["constraint_length"]
    g1 = gt_meta["g1_octal"]
    g2 = gt_meta["g2_octal"]

    test_files = [
        ("test_fec_fsk.wav", "audio/wav", "WAV"),
        ("test_fec_fsk.iq", "application/octet-stream", "IQ"),
    ]

    for filename, mime_type, fmt in test_files:
        file_path = os.path.join("test_data", filename)
        assert os.path.exists(file_path)

        with open(file_path, "rb") as f:
            res_up = client.post("/api/files/upload", files={"file": (filename, f, mime_type)})
        assert res_up.status_code == 200
        signal_id = res_up.json()["signal_id"]

        # Run API endpoint POST /api/fec/viterbi/{signal_id}?constraint_length=3&g1=7&g2=5
        res_fec = client.post(f"/api/fec/viterbi/{signal_id}?constraint_length={k}&g1={g1}&g2={g2}")
        assert res_fec.status_code == 200, f"API failed for {filename}: {res_fec.text}"
        data = res_fec.json()

        assert data["signal_id"] == signal_id
        assert data["format"] == fmt
        assert data["output_bit_count"] == len(expected_original_bits)

        decoded_bits = data["decoded_bits"]
        assert len(decoded_bits) == len(expected_original_bits)

        # Measure payload bit error rate
        err_count = sum(1 for i in range(len(decoded_bits)) if decoded_bits[i] != expected_original_bits[i])
        ber = err_count / len(expected_original_bits)

        assert ber == 0.0, f"Expected 100% recovery accuracy for {filename}, got BER = {ber*100:.2f}% ({err_count} errors)"


def test_fec_invalid_signal_id():
    client = TestClient(app)
    res = client.post("/api/fec/viterbi/nonexistent-signal-id-9999")
    assert res.status_code == 404
    assert res.json() == {"detail": "Signal session not found or expired. Please upload the signal file again."}
