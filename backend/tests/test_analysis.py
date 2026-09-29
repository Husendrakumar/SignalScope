import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from scripts.generate_test_signals import generate_test_signals


@pytest.fixture(scope="module", autouse=True)
def setup_test_signals():
    generate_test_signals()


def test_analysis_endpoint_all_signals():
    client = TestClient(app)

    test_files = [
        ("test_sine.wav", "audio/wav", "WAV"),
        ("test_sine.iq", "application/octet-stream", "IQ"),
        ("test_fsk.wav", "audio/wav", "WAV"),
        ("test_fsk.iq", "application/octet-stream", "IQ"),
    ]

    for filename, mime_type, expected_format in test_files:
        file_path = os.path.join("test_data", filename)
        assert os.path.exists(file_path), f"Test file {file_path} does not exist"

        with open(file_path, "rb") as f:
            res_upload = client.post("/api/files/upload", files={"file": (filename, f, mime_type)})
        assert res_upload.status_code == 200, f"Upload failed for {filename}"
        signal_id = res_upload.json()["signal_id"]
        assert signal_id is not None

        # Fetch analysis
        res_analysis = client.get(f"/api/analysis/{signal_id}")
        assert res_analysis.status_code == 200, f"Analysis endpoint failed for {filename}: {res_analysis.text}"
        data = res_analysis.json()

        # 1. Top-level metadata
        assert data["signal_id"] == signal_id
        assert data["filename"] == filename
        assert data["format"] == expected_format
        assert data["sample_rate"] > 0
        assert data["sample_count"] > 0
        assert data["duration_seconds"] > 0.0

        # 2. Signal statistics
        stats = data["statistics"]
        assert isinstance(stats["mean"], (int, float))
        assert stats["rms"] >= 0.0
        assert stats["peak"] >= 0.0
        assert stats["peak_to_peak"] >= 0.0
        assert stats["average_power"] >= 0.0

        # 3. Noise & SNR estimation
        noise = data["noise"]
        assert noise["estimated_noise_power"] >= 0.0
        assert noise["estimated_signal_power"] >= 0.0
        assert isinstance(noise["estimated_snr_db"], (int, float))
        assert "method" in noise

        # 4. Dominant frequency
        freq = data["frequency"]
        assert isinstance(freq["dominant_frequency_hz"], (int, float))
        assert isinstance(freq["dominant_frequency_khz"], (int, float))
        assert isinstance(freq["peak_magnitude_db"], (int, float))

        # 5. Occupied bandwidth
        bw = data["bandwidth"]
        assert bw["bandwidth_hz"] >= 0.0
        assert isinstance(bw["lower_frequency_hz"], (int, float))
        assert isinstance(bw["upper_frequency_hz"], (int, float))
        assert "method" in bw

        # 6. Activity & presence
        act = data["activity"]
        assert isinstance(act["signal_present"], bool)
        assert 0.0 <= act["activity_ratio"] <= 1.0
        assert act["active_start_time"] >= 0.0
        assert act["active_end_time"] >= act["active_start_time"]
        assert act["status"] in ["ACTIVE_SIGNAL", "LOW_ENERGY_OR_NOISE"]


def test_analysis_invalid_signal_id():
    client = TestClient(app)
    res = client.get("/api/analysis/nonexistent-signal-id-9999")
    assert res.status_code == 404
    assert res.json() == {"detail": "Signal session not found or expired. Please upload the signal file again."}
