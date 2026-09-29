import os
import json
import random
import pytest
from fastapi.testclient import TestClient
from app.main import app
from scripts.generate_test_signals import generate_test_signals
from app.signal_processing.deinterleaving import (
    block_interleave,
    block_deinterleave,
    try_block_deinterleavers,
    convolutional_interleave,
    convolutional_deinterleave,
    try_convolutional_deinterleavers
)


@pytest.fixture(scope="module", autouse=True)
def setup_test_signals():
    generate_test_signals()


def test_inverse_identity():
    """
    Proves block_deinterleave is the exact mathematical inverse of block_interleave
    across multiple matrix dimensions and pseudo-random bit sequences.
    """
    test_dims = [(4, 4), (4, 8), (8, 8), (16, 16)]
    rng = random.Random(42)

    for rows, cols in test_dims:
        bsize = rows * cols
        # Generate 4 blocks of random bits
        orig_bits = "".join(rng.choice(["0", "1"]) for _ in range(bsize * 4))

        interleaved = block_interleave(orig_bits, rows, cols)
        recovered = block_deinterleave(interleaved, rows, cols)

        assert recovered == orig_bits, f"Failed inverse identity for {rows}x{cols}"


def test_deinterleaving_invalid_dimensions():
    with pytest.raises(ValueError):
        block_interleave("1010", 0, 2)

    with pytest.raises(ValueError):
        block_deinterleave("1010", -1, 2)


def test_deinterleaving_incompatible_bit_count():
    # 7 bits cannot be arranged in 4x4=16 block size
    with pytest.raises(ValueError):
        block_interleave("1010101", 4, 4)

    with pytest.raises(ValueError):
        block_deinterleave("1010101", 4, 4)


def test_try_block_deinterleavers_candidates():
    orig_bits = "1011001011010011" * 4  # 64 bits = 8x8 block
    interleaved = block_interleave(orig_bits, 8, 8)

    res = try_block_deinterleavers(interleaved, ground_truth=orig_bits)
    assert res["input_bit_count"] == 64
    assert res["selected_configuration"]["rows"] == 8
    assert res["selected_configuration"]["cols"] == 8
    assert res["selected_configuration"]["status"] == "VALIDATED"
    assert res["deinterleaved_bits"] == orig_bits


def test_end_to_end_interleaved_fsk_pipeline():
    """
    End-to-End Pipeline Test for Part 9A:
    test_interleaved_fsk -> FSK Demodulator -> Block De-interleaver -> Original Bits (100% Accuracy)
    """
    client = TestClient(app)

    # Read ground truth metadata
    json_path = os.path.join("test_data", "test_interleaved_fsk.json")
    assert os.path.exists(json_path)
    with open(json_path, "r") as f:
        gt_meta = json.load(f)

    expected_original_bits = gt_meta["original_bits"]
    rows = gt_meta["interleave_rows"]
    cols = gt_meta["interleave_cols"]

    test_files = [
        ("test_interleaved_fsk.wav", "audio/wav", "WAV"),
        ("test_interleaved_fsk.iq", "application/octet-stream", "IQ"),
    ]

    for filename, mime_type, fmt in test_files:
        file_path = os.path.join("test_data", filename)
        assert os.path.exists(file_path)

        with open(file_path, "rb") as f:
            res_up = client.post("/api/files/upload", files={"file": (filename, f, mime_type)})
        assert res_up.status_code == 200
        signal_id = res_up.json()["signal_id"]

        # Run API endpoint POST /api/deinterleaving/block/{signal_id}?rows=8&cols=8
        res_deint = client.post(f"/api/deinterleaving/block/{signal_id}?rows={rows}&cols={cols}")
        assert res_deint.status_code == 200, f"API failed for {filename}: {res_deint.text}"
        data = res_deint.json()

        assert data["signal_id"] == signal_id
        assert data["format"] == fmt
        assert data["input_bit_count"] == len(expected_original_bits)

        recovered_bits = data["deinterleaved_bits"]
        assert len(recovered_bits) == len(expected_original_bits)

        # Measure bit error rate
        err_count = sum(1 for i in range(len(recovered_bits)) if recovered_bits[i] != expected_original_bits[i])
        ber = err_count / len(expected_original_bits)

        assert ber == 0.0, f"Expected 100% recovery accuracy for {filename}, got BER = {ber*100:.2f}% ({err_count} errors)"


def test_deinterleaving_invalid_signal_id():
    client = TestClient(app)
    res = client.post("/api/deinterleaving/block/nonexistent-signal-id-9999")
    assert res.status_code == 404
    assert res.json() == {"detail": "Signal session not found or expired. Please upload the signal file again."}


# ---------------------------------------------------------------------------
# Part 9B Tests — Convolutional De-interleaving
# ---------------------------------------------------------------------------

def test_convolutional_inverse_identity():
    """
    Proves convolutional_deinterleave is the exact mathematical inverse of convolutional_interleave
    across multiple branch/delay configurations and non-repeating/pseudo-random bit patterns.
    """
    param_configs = [
        (3, 1),
        (4, 1),
        (4, 2),
        (5, 1),
    ]
    rng = random.Random(12345)

    test_patterns = [
        "10101010101010101010101010101010",  # Alternating
        "11001100110011001100110011001100",  # Doubled
        "".join(rng.choice(["0", "1"]) for _ in range(512)),  # Pseudo-random 512 bits
    ]

    for branches, delay_step in param_configs:
        for pattern in test_patterns:
            interleaved = convolutional_interleave(pattern, branches=branches, delay_step=delay_step, flush=True)
            recovered = convolutional_deinterleave(interleaved, branches=branches, delay_step=delay_step, trim_flush=True)
            assert recovered == pattern, f"Convolutional inverse failed for B={branches}, D={delay_step}"


def test_convolutional_invalid_parameters():
    with pytest.raises(ValueError):
        convolutional_interleave("1010", branches=0, delay_step=1)

    with pytest.raises(ValueError):
        convolutional_deinterleave("1010", branches=3, delay_step=-1)

    with pytest.raises(ValueError):
        convolutional_interleave("10201", branches=3, delay_step=1)  # Non-binary character '2'


def test_try_convolutional_deinterleavers():
    rng = random.Random(999)
    orig_bits = "".join(rng.choice(["0", "1"]) for _ in range(256))
    interleaved = convolutional_interleave(orig_bits, branches=4, delay_step=1, flush=True)

    res = try_convolutional_deinterleavers(interleaved, ground_truth=orig_bits)
    assert res["input_bit_count"] == len(interleaved)
    assert res["selected_configuration"]["branches"] == 4
    assert res["selected_configuration"]["delay_step"] == 1
    assert res["selected_configuration"]["status"] == "VALIDATED"
    assert res["deinterleaved_bits"] == orig_bits


def test_end_to_end_conv_interleaved_fsk_pipeline():
    """
    End-to-End Pipeline Test for Part 9B:
    test_conv_interleaved_fsk -> FSK Demodulator -> Conv De-interleaver -> Original Bits (100% Accuracy)
    """
    client = TestClient(app)

    json_path = os.path.join("test_data", "test_conv_interleaved_fsk.json")
    assert os.path.exists(json_path)
    with open(json_path, "r") as f:
        gt_meta = json.load(f)

    expected_original_bits = gt_meta["original_bits"]
    branches = gt_meta["conv_branches"]
    delay_step = gt_meta["conv_delay_step"]

    test_files = [
        ("test_conv_interleaved_fsk.wav", "audio/wav", "WAV"),
        ("test_conv_interleaved_fsk.iq", "application/octet-stream", "IQ"),
    ]

    for filename, mime_type, fmt in test_files:
        file_path = os.path.join("test_data", filename)
        assert os.path.exists(file_path)

        with open(file_path, "rb") as f:
            res_up = client.post("/api/files/upload", files={"file": (filename, f, mime_type)})
        assert res_up.status_code == 200
        signal_id = res_up.json()["signal_id"]

        # Run API endpoint POST /api/deinterleaving/convolutional/{signal_id}?branches=4&delay_step=1
        res_deint = client.post(f"/api/deinterleaving/convolutional/{signal_id}?branches={branches}&delay_step={delay_step}")
        assert res_deint.status_code == 200, f"API failed for {filename}: {res_deint.text}"
        data = res_deint.json()

        assert data["signal_id"] == signal_id
        assert data["format"] == fmt

        recovered_bits = data["deinterleaved_bits"]
        assert len(recovered_bits) == len(expected_original_bits)

        # Measure bit error rate
        err_count = sum(1 for i in range(len(recovered_bits)) if recovered_bits[i] != expected_original_bits[i])
        ber = err_count / len(expected_original_bits)

        assert ber == 0.0, f"Expected 100% recovery accuracy for {filename}, got BER = {ber*100:.2f}% ({err_count} errors)"


def test_conv_deinterleaving_invalid_signal_id():
    client = TestClient(app)
    res = client.post("/api/deinterleaving/convolutional/nonexistent-signal-id-9999")
    assert res.status_code == 404
    assert res.json() == {"detail": "Signal session not found or expired. Please upload the signal file again."}

