import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from scripts.generate_test_signals import generate_test_signals


@pytest.fixture(scope="module", autouse=True)
def setup_test_signals():
    generate_test_signals()


def test_modulation_endpoint_all_signals():
    client = TestClient(app)

    test_files = [
        ("test_fsk.wav", "audio/wav", "FSK"),
        ("test_fsk.iq", "application/octet-stream", "FSK"),
        ("test_sine.wav", "audio/wav", "UNKNOWN"),
        ("test_sine.iq", "application/octet-stream", "UNKNOWN"),
    ]

    for filename, mime_type, expected_modulation in test_files:
        file_path = os.path.join("test_data", filename)
        assert os.path.exists(file_path), f"Test file {file_path} does not exist"

        with open(file_path, "rb") as f:
            res_upload = client.post("/api/files/upload", files={"file": (filename, f, mime_type)})
        assert res_upload.status_code == 200, f"Upload failed for {filename}"
        signal_id = res_upload.json()["signal_id"]
        assert signal_id is not None

        # Fetch modulation classification
        res_mod = client.get(f"/api/modulation/{signal_id}")
        assert res_mod.status_code == 200, f"Modulation endpoint failed for {filename}: {res_mod.text}"
        data = res_mod.json()

        # 1. Top-level properties
        assert data["signal_id"] == signal_id
        assert data["filename"] == filename
        assert data["modulation"] in ["FSK", "PSK", "QAM", "UNKNOWN"]
        assert data["modulation"] == expected_modulation, f"Expected {expected_modulation} for {filename}, got {data['modulation']}"

        # 2. Confidence & evidence
        assert 0.0 <= data["confidence_score"] <= 1.0
        assert isinstance(data["evidence"], list)
        assert len(data["evidence"]) > 0

        # 3. Extracted features
        feats = data["features"]
        assert isinstance(feats["envelope_cv"], (int, float))
        assert isinstance(feats["inst_freq_std_hz"], (int, float))
        assert isinstance(feats["num_freq_peaks"], int)
        assert isinstance(feats["num_spectral_peaks"], int)
        assert isinstance(feats["phase_std"], (int, float))


def test_modulation_invalid_signal_id():
    client = TestClient(app)
    res = client.get("/api/modulation/nonexistent-signal-id-9999")
    assert res.status_code == 404
    assert res.json() == {"detail": "Signal session not found or expired. Please upload the signal file again."}
