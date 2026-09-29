import os
import json
import random
import pytest
from fastapi.testclient import TestClient
from app.main import app
from scripts.generate_test_signals import generate_test_signals
from app.signal_processing.fec import (
    reed_solomon_encode,
    reed_solomon_decode,
    try_reed_solomon_decoders,
    bits_to_bytes,
    bytes_to_bits
)


@pytest.fixture(scope="module", autouse=True)
def setup_test_signals():
    generate_test_signals()


def test_rs_round_trip():
    """
    Proves reed_solomon_decode is the exact mathematical inverse of reed_solomon_encode
    across deterministic zero, ones, sequential, pseudo-random, and shortened payloads.
    """
    rng = random.Random(42)
    test_payloads = [
        bytes([0] * 223),  # All zeros
        bytes([0xFF] * 223),  # All ones
        bytes(i % 256 for i in range(223)),  # Sequential bytes
        bytes(rng.randint(0, 255) for _ in range(223)),  # Deterministic pseudo-random
        bytes(rng.randint(0, 255) for _ in range(100)),  # Shortened payload (< 223 bytes)
    ]

    for payload in test_payloads:
        payload_bits = bytes_to_bits(payload)
        encoded_bits = reed_solomon_encode(payload_bits, n=255, k=223)
        decoded_bits, info = reed_solomon_decode(encoded_bits, n=255, k=223)

        assert decoded_bits == payload_bits, "RS round trip failed for bitstream payload"
        decoded_payload = bits_to_bytes(decoded_bits)
        assert decoded_payload == payload, "RS round trip failed for byte payload"
        assert info["corrected_symbol_count"] == 0


def test_rs_error_correction_1_symbol():
    rng = random.Random(101)
    payload = bytes(rng.randint(0, 255) for _ in range(223))
    encoded = bytearray(reed_solomon_encode(payload, n=255, k=223))

    # Inject 1 symbol error (corrupt byte index 10)
    encoded[10] ^= 0xFF

    decoded, info = reed_solomon_decode(bytes(encoded), n=255, k=223)
    assert decoded == payload
    assert info["corrected_symbol_count"] == 1


def test_rs_error_correction_4_symbols():
    rng = random.Random(202)
    payload = bytes(rng.randint(0, 255) for _ in range(223))
    encoded = bytearray(reed_solomon_encode(payload, n=255, k=223))

    # Inject 4 symbol errors
    for idx in [5, 25, 45, 65]:
        encoded[idx] ^= 0xAA

    decoded, info = reed_solomon_decode(bytes(encoded), n=255, k=223)
    assert decoded == payload
    assert info["corrected_symbol_count"] == 4


def test_rs_error_correction_8_symbols():
    rng = random.Random(303)
    payload = bytes(rng.randint(0, 255) for _ in range(223))
    encoded = bytearray(reed_solomon_encode(payload, n=255, k=223))

    # Inject 8 symbol errors
    for idx in range(0, 80, 10):
        encoded[idx] ^= 0x55

    decoded, info = reed_solomon_decode(bytes(encoded), n=255, k=223)
    assert decoded == payload
    assert info["corrected_symbol_count"] == 8


def test_rs_error_correction_16_symbols():
    """
    Tests maximum error correction capability: 16 symbol errors per RS(255,223) codeword.
    """
    rng = random.Random(404)
    payload = bytes(rng.randint(0, 255) for _ in range(223))
    encoded = bytearray(reed_solomon_encode(payload, n=255, k=223))

    # Inject 16 symbol errors
    for idx in range(0, 160, 10):
        encoded[idx] ^= 0x0F

    decoded, info = reed_solomon_decode(bytes(encoded), n=255, k=223)
    assert decoded == payload
    assert info["corrected_symbol_count"] == 16


def test_rs_beyond_capacity_17_symbols():
    """
    Tests behavior when symbol errors (17 errors) exceed correction capacity (16 errors).
    Must raise ValueError and not falsely claim successful recovery.
    """
    rng = random.Random(505)
    payload = bytes(rng.randint(0, 255) for _ in range(223))
    encoded = bytearray(reed_solomon_encode(payload, n=255, k=223))

    # Inject 17 symbol errors
    for idx in range(0, 170, 10):
        encoded[idx] ^= 0xF0

    with pytest.raises(ValueError) as exc_info:
        reed_solomon_decode(bytes(encoded), n=255, k=223)

    assert "too many symbol errors" in str(exc_info.value).lower() or "decoding failed" in str(exc_info.value).lower()


def test_try_reed_solomon_decoders_candidates():
    rng = random.Random(606)
    payload = bytes(rng.randint(0, 255) for _ in range(223))
    payload_bits = bytes_to_bits(payload)
    encoded_bits = reed_solomon_encode(payload_bits, n=255, k=223)

    res = try_reed_solomon_decoders(encoded_bits, ground_truth=payload_bits)
    assert res["fec_type"] == "REED_SOLOMON"
    assert res["n"] == 255
    assert res["k"] == 223
    assert res["selected_configuration"]["status"] == "VALIDATED"
    assert res["decoded_bits"] == payload_bits


def test_end_to_end_rs_fsk_pipeline():
    """
    End-to-End Pipeline Test for Part 10B:
    test_rs_fsk -> FSK Demodulator -> Reed-Solomon Decoder -> Original Payload (100% Accuracy)
    """
    client = TestClient(app)

    json_path = os.path.join("test_data", "test_rs_fsk.json")
    assert os.path.exists(json_path)
    with open(json_path, "r") as f:
        gt_meta = json.load(f)

    expected_original_bits = gt_meta["original_bits"]
    n = gt_meta["n"]
    k = gt_meta["k"]

    test_files = [
        ("test_rs_fsk.wav", "audio/wav", "WAV"),
        ("test_rs_fsk.iq", "application/octet-stream", "IQ"),
    ]

    for filename, mime_type, fmt in test_files:
        file_path = os.path.join("test_data", filename)
        assert os.path.exists(file_path)

        with open(file_path, "rb") as f:
            res_up = client.post("/api/files/upload", files={"file": (filename, f, mime_type)})
        assert res_up.status_code == 200
        signal_id = res_up.json()["signal_id"]

        # Run API endpoint POST /api/fec/reed-solomon/{signal_id}?n=255&k=223
        res_rs = client.post(f"/api/fec/reed-solomon/{signal_id}?n={n}&k={k}")
        assert res_rs.status_code == 200, f"API failed for {filename}: {res_rs.text}"
        data = res_rs.json()

        assert data["signal_id"] == signal_id
        assert data["format"] == fmt
        assert data["fec_type"] == "REED_SOLOMON"
        assert data["n"] == 255
        assert data["k"] == 223

        decoded_bits = data["decoded_bits"]
        assert len(decoded_bits) == len(expected_original_bits)

        # Measure payload bit error rate
        err_count = sum(1 for i in range(len(decoded_bits)) if decoded_bits[i] != expected_original_bits[i])
        ber = err_count / len(expected_original_bits)

        assert ber == 0.0, f"Expected 100% recovery accuracy for {filename}, got BER = {ber*100:.2f}% ({err_count} errors)"


def test_rs_api_invalid_input():
    client = TestClient(app)

    # 1. Invalid signal ID -> 404
    res = client.post("/api/fec/reed-solomon/nonexistent-signal-id-9999")
    assert res.status_code == 404

    # 2. Non-supported parameters -> 422
    res_bad = client.post("/api/fec/reed-solomon/nonexistent-signal-id-9999?n=500")
    assert res_bad.status_code == 422


def test_viterbi_regression():
    """
    Verifies that Part 10A Viterbi FEC decoding continues working without regression.
    """
    client = TestClient(app)

    json_path = os.path.join("test_data", "test_fec_fsk.json")
    assert os.path.exists(json_path)
    with open(json_path, "r") as f:
        gt_meta = json.load(f)

    file_path = os.path.join("test_data", "test_fec_fsk.wav")
    with open(file_path, "rb") as f:
        res_up = client.post("/api/files/upload", files={"file": ("test_fec_fsk.wav", f, "audio/wav")})
    assert res_up.status_code == 200
    signal_id = res_up.json()["signal_id"]

    res_viterbi = client.post(f"/api/fec/viterbi/{signal_id}?constraint_length=3&g1=7&g2=5")
    assert res_viterbi.status_code == 200
    assert res_viterbi.json()["decoded_bits"] == gt_meta["original_bits"]
