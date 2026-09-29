import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from scripts.generate_test_signals import generate_test_signals


@pytest.fixture(scope="module", autouse=True)
def setup_test_signals():
    generate_test_signals()


def test_fsk_demodulation_wav_and_iq():
    client = TestClient(app)
    expected_pattern = "1011001011010011"
    expected_full_bits = expected_pattern * 125  # 2000 bits

    fsk_files = [
        ("test_fsk.wav", "audio/wav", "WAV"),
        ("test_fsk.iq", "application/octet-stream", "IQ"),
    ]

    for filename, mime_type, fmt in fsk_files:
        file_path = os.path.join("test_data", filename)
        with open(file_path, "rb") as f:
            res_upload = client.post("/api/files/upload", files={"file": (filename, f, mime_type)})
        assert res_upload.status_code == 200
        signal_id = res_upload.json()["signal_id"]

        # Run FSK demodulation
        res_demod = client.post(f"/api/demodulation/fsk/{signal_id}")
        assert res_demod.status_code == 200, f"Demodulation failed for {filename}: {res_demod.text}"
        data = res_demod.json()

        # 1. Output structure & format
        assert data["signal_id"] == signal_id
        assert data["format"] == fmt
        assert data["modulation"] == "FSK"

        # 2. Parameter estimates
        assert abs(data["frequency_1_hz"] - 5000.0) < 150.0, f"Tone 1 freq error for {filename}: {data['frequency_1_hz']}"
        assert abs(data["frequency_0_hz"] - 8000.0) < 150.0, f"Tone 0 freq error for {filename}: {data['frequency_0_hz']}"
        assert abs(data["symbol_rate"] - 1000.0) < 50.0, f"Symbol rate error for {filename}: {data['symbol_rate']}"

        # 3. Bit accuracy against ground truth
        recovered_bits = data["bits"]
        assert len(recovered_bits) > 1900, f"Expected ~2000 bits, got {len(recovered_bits)}"

        # Measure bit error rate (BER) over minimum shared length
        compare_len = min(len(recovered_bits), len(expected_full_bits))
        bit_errors = sum(1 for i in range(compare_len) if recovered_bits[i] != expected_full_bits[i])
        ber = bit_errors / compare_len

        assert ber < 0.01, f"Bit error rate for {filename} is too high: {ber*100:.2f}% ({bit_errors} errors out of {compare_len})"


def test_non_fsk_sine_rejection():
    client = TestClient(app)

    sine_files = [
        ("test_sine.wav", "audio/wav"),
        ("test_sine.iq", "application/octet-stream"),
    ]

    for filename, mime_type in sine_files:
        file_path = os.path.join("test_data", filename)
        with open(file_path, "rb") as f:
            res_upload = client.post("/api/files/upload", files={"file": (filename, f, mime_type)})
        assert res_upload.status_code == 200
        signal_id = res_upload.json()["signal_id"]

        # Attempt FSK demodulation on unmodulated sine wave -> should fail with HTTP 400
        res_demod = client.post(f"/api/demodulation/fsk/{signal_id}")
        assert res_demod.status_code == 400, f"Expected 400 rejection for {filename}, got {res_demod.status_code}"


def test_demodulation_invalid_signal_id():
    client = TestClient(app)
    res = client.post("/api/demodulation/fsk/nonexistent-signal-id-9999")
    assert res.status_code == 404
    assert res.json() == {"detail": "Signal session not found or expired. Please upload the signal file again."}
