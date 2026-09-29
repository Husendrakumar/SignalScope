import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from scripts.generate_test_signals import generate_test_signals


@pytest.fixture(scope="module", autouse=True)
def setup_signals_and_upload():
    generate_test_signals()


def test_visualization_endpoints():
    client = TestClient(app)

    # 1. Upload test_sine.wav
    wav_path = os.path.join("test_data", "test_sine.wav")
    with open(wav_path, "rb") as f:
        res_wav = client.post("/api/files/upload", files={"file": ("test_sine.wav", f, "audio/wav")})
    assert res_wav.status_code == 200
    wav_id = res_wav.json()["signal_id"]
    assert wav_id is not None

    # Test WAV waveform
    res_wf = client.get(f"/api/visualization/waveform/{wav_id}")
    assert res_wf.status_code == 200
    wf_data = res_wf.json()
    assert wf_data["format"] == "WAV"
    assert "time" in wf_data
    assert "amplitude" in wf_data

    # Test WAV spectrum
    res_spec = client.get(f"/api/visualization/spectrum/{wav_id}")
    assert res_spec.status_code == 200
    spec_data = res_spec.json()
    assert "frequencies" in spec_data
    assert "magnitudes_db" in spec_data

    # Test WAV spectrogram
    res_sg = client.get(f"/api/visualization/spectrogram/{wav_id}")
    assert res_sg.status_code == 200
    sg_data = res_sg.json()
    assert "time_axis" in sg_data
    assert "frequency_axis" in sg_data
    assert "spectrogram_db" in sg_data

    # Test WAV constellation (should fail with 400 for non-IQ)
    res_const = client.get(f"/api/visualization/constellation/{wav_id}")
    assert res_const.status_code == 400

    # 2. Upload test_sine.iq
    iq_path = os.path.join("test_data", "test_sine.iq")
    with open(iq_path, "rb") as f:
        res_iq = client.post("/api/files/upload", files={"file": ("test_sine.iq", f, "application/octet-stream")})
    assert res_iq.status_code == 200
    iq_id = res_iq.json()["signal_id"]
    assert iq_id is not None

    # Test IQ waveform
    res_iq_wf = client.get(f"/api/visualization/waveform/{iq_id}")
    assert res_iq_wf.status_code == 200
    iq_wf_data = res_iq_wf.json()
    assert iq_wf_data["format"] == "IQ"
    assert "real_i" in iq_wf_data
    assert "imag_q" in iq_wf_data

    # Test IQ spectrum
    res_iq_spec = client.get(f"/api/visualization/spectrum/{iq_id}?nfft=2048")
    assert res_iq_spec.status_code == 200
    spec_data = res_iq_spec.json()
    assert spec_data["sample_rate"] == 1000000
    
    # Max frequency in FFT for IQ is +500,000 Hz (Nyquist)
    max_freq = max(spec_data["frequencies"])
    assert 490000 < max_freq <= 500000
    
    # Peak frequency should be near 1000 Hz for test_sine.iq
    freqs = spec_data["frequencies"]
    mags = spec_data["magnitudes_db"]
    peak_idx = mags.index(max(mags))
    assert abs(freqs[peak_idx] - 1000.0) < 500


    # Test IQ constellation
    res_iq_const = client.get(f"/api/visualization/constellation/{iq_id}")
    assert res_iq_const.status_code == 200
    const_data = res_iq_const.json()
    assert "i" in const_data
    assert "q" in const_data


    # 3. Upload test_fsk.wav
    fsk_wav_path = os.path.join("test_data", "test_fsk.wav")
    with open(fsk_wav_path, "rb") as f:
        res_fsk_wav = client.post("/api/files/upload", files={"file": ("test_fsk.wav", f, "audio/wav")})
    assert res_fsk_wav.status_code == 200
    fsk_wav_id = res_fsk_wav.json()["signal_id"]

    res_fsk_wf = client.get(f"/api/visualization/waveform/{fsk_wav_id}")
    assert res_fsk_wf.status_code == 200
    assert res_fsk_wf.json()["format"] == "WAV"

    res_fsk_spec = client.get(f"/api/visualization/spectrum/{fsk_wav_id}")
    assert res_fsk_spec.status_code == 200

    res_fsk_sg = client.get(f"/api/visualization/spectrogram/{fsk_wav_id}")
    assert res_fsk_sg.status_code == 200

    res_fsk_const = client.get(f"/api/visualization/constellation/{fsk_wav_id}")
    assert res_fsk_const.status_code == 400

    # 4. Upload test_fsk.iq
    fsk_iq_path = os.path.join("test_data", "test_fsk.iq")
    with open(fsk_iq_path, "rb") as f:
        res_fsk_iq = client.post("/api/files/upload", files={"file": ("test_fsk.iq", f, "application/octet-stream")})
    assert res_fsk_iq.status_code == 200
    fsk_iq_id = res_fsk_iq.json()["signal_id"]

    res_fsk_iq_wf = client.get(f"/api/visualization/waveform/{fsk_iq_id}")
    assert res_fsk_iq_wf.status_code == 200
    assert res_fsk_iq_wf.json()["format"] == "IQ"

    res_fsk_iq_const = client.get(f"/api/visualization/constellation/{fsk_iq_id}")
    assert res_fsk_iq_const.status_code == 200
    assert "i" in res_fsk_iq_const.json()


def test_invalid_signal_id():
    client = TestClient(app)
    res = client.get("/api/visualization/waveform/invalid-uuid-12345")
    assert res.status_code == 404
    assert res.json() == {"detail": "Signal session not found or expired. Please upload the signal file again."}

