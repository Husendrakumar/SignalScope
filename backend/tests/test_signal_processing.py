"""
Test suite for the SignalScope signal reader / normalization layer (Part 5).

Covers:
- WAV reader → complex64 conversion
- IQ reader → complex64 conversion
- Unified load_signal() entry point
- Malformed / invalid file rejection
- Unsupported extension rejection
- API upload endpoint compatibility
"""

import os
import io
import struct
import tempfile
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.signal_processing.wav_reader import load_wav
from app.signal_processing.iq_reader import load_iq
from app.signal_processing.signal_loader import load_signal
from app.utils.validation import validate_file_extension, sanitize_filename
from scripts.generate_test_signals import generate_test_signals


@pytest.fixture(scope="module", autouse=True)
def ensure_test_signals():
    """Ensures test signals exist in backend/test_data directory."""
    generate_test_signals()


# ======================================================================
# TEST 1 — WAV reader: metadata + complex64 dtype
# ======================================================================

def test_wav_reader_fsk():
    """TEST 1: WAV reader produces correct metadata and complex64 samples."""
    test_wav = os.path.join("test_data", "test_fsk.wav")
    signal = load_wav(test_wav)

    assert signal.format == "WAV"
    assert signal.sample_rate == 48000
    assert signal.sample_count == 96000
    assert abs(signal.duration - 2.0) < 0.01
    # data_type preserved for API reporting
    assert signal.data_type == "float32"
    # Canonical dtype is complex64
    assert signal.samples.dtype == np.complex64
    assert signal.samples.shape == (96000,)
    # WAV samples should have zero imaginary part
    assert np.allclose(signal.samples.imag, 0.0, atol=1e-7)


def test_wav_reader_sine():
    """Original sine WAV test — still passes with complex64."""
    test_wav = os.path.join("test_data", "test_sine.wav")
    signal = load_wav(test_wav)

    assert signal.format == "WAV"
    assert signal.sample_rate == 48000
    assert signal.sample_count == 96000
    assert abs(signal.duration - 2.0) < 0.01
    assert signal.data_type == "float32"
    assert signal.samples.dtype == np.complex64


# ======================================================================
# TEST 2 — IQ reader: metadata + complex64 dtype
# ======================================================================

def test_iq_reader_fsk():
    """TEST 2: IQ reader produces correct metadata and complex64 samples."""
    test_iq = os.path.join("test_data", "test_fsk.iq")
    signal = load_iq(test_iq, )

    assert signal.format == "IQ"
    assert signal.sample_rate == 1000000
    assert signal.sample_count == 2000000
    assert abs(signal.duration - 2.0) < 0.01
    assert signal.data_type == "complex64"
    assert signal.samples.dtype == np.complex64
    assert signal.samples.shape == (2000000,)
    # IQ samples should have non-zero imaginary part (FSK complex exponential)
    assert not np.allclose(signal.samples.imag, 0.0, atol=1e-3)


def test_iq_reader_sine():
    """Original sine IQ test - still passes."""
    test_iq = os.path.join("test_data", "test_sine.iq")
    signal = load_iq(test_iq, )

    assert signal.format == "IQ"
    assert signal.sample_rate == 1000000
    assert signal.sample_count == 2000000
    assert abs(signal.duration - 2.0) < 0.01
    assert signal.data_type == "complex64"
    assert signal.samples.dtype == np.complex64


# ======================================================================
# TEST 3 — Malformed IQ file (odd number of float32 values)
# ======================================================================

def test_malformed_iq_odd_floats():
    """TEST 3: IQ file with odd float count (3 floats = 12 bytes) is rejected."""
    with tempfile.NamedTemporaryFile(suffix=".iq", delete=False) as tmp:
        # Write 3 float32 values = 12 bytes, not a multiple of 8
        tmp.write(struct.pack("<fff", 1.0, 2.0, 3.0))
        tmp_path = tmp.name

    try:
        with pytest.raises(ValueError, match="Expected interleaved float32 I/Q samples"):
            load_iq(tmp_path)
    finally:
        os.unlink(tmp_path)


def test_malformed_iq_single_byte():
    """Malformed IQ: single odd byte is also rejected."""
    with tempfile.NamedTemporaryFile(suffix=".iq", delete=False) as tmp:
        tmp.write(b"\x01\x02\x03\x04\x05")  # 5 bytes, not multiple of 8
        tmp_path = tmp.name

    try:
        with pytest.raises(ValueError, match="Expected interleaved float32 I/Q samples"):
            load_iq(tmp_path)
    finally:
        os.unlink(tmp_path)


# ======================================================================
# TEST 4 — Invalid WAV file
# ======================================================================

def test_invalid_wav_file():
    """TEST 4: Non-WAV binary data with .wav extension is rejected."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(b"This is not a valid WAV file content at all.")
        tmp_path = tmp.name

    try:
        with pytest.raises(ValueError, match="Unable to read WAV file"):
            load_wav(tmp_path)
    finally:
        os.unlink(tmp_path)


def test_empty_wav_file():
    """Empty WAV file is rejected."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name  # 0 bytes

    try:
        with pytest.raises(ValueError, match="empty"):
            load_wav(tmp_path)
    finally:
        os.unlink(tmp_path)


# ======================================================================
# TEST 5 — Unsupported file extension
# ======================================================================

def test_unsupported_file_extension():
    """TEST 5: Unsupported extensions are rejected by validation."""
    with pytest.raises(Exception):
        validate_file_extension("file.txt")

    with pytest.raises(Exception):
        validate_file_extension("file.pdf")

    with pytest.raises(Exception):
        validate_file_extension("file.mp3")


def test_load_signal_unsupported_extension():
    """load_signal rejects unsupported extensions with ValueError."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        tmp.write(b"not a signal")
        tmp_path = tmp.name

    try:
        with pytest.raises(ValueError, match="Unsupported file format"):
            load_signal(tmp_path)
    finally:
        os.unlink(tmp_path)


# ======================================================================
# Unified load_signal() tests
# ======================================================================

def test_load_signal_wav():
    """load_signal() with WAV → complex64 + correct metadata."""
    path = os.path.join("test_data", "test_fsk.wav")
    signal = load_signal(path, filename="test_fsk.wav")

    assert signal.format == "WAV"
    assert signal.data_type == "float32"
    assert signal.samples.dtype == np.complex64
    assert signal.sample_rate == 48000
    assert signal.sample_count == 96000
    assert abs(signal.duration - 2.0) < 0.01
    assert signal.filename == "test_fsk.wav"


def test_load_signal_iq():
    """load_signal() with IQ -> complex64 + correct metadata."""
    path = os.path.join("test_data", "test_fsk.iq")
    signal = load_signal(path, filename="test_fsk.iq")

    assert signal.format == "IQ"
    assert signal.data_type == "complex64"
    assert signal.samples.dtype == np.complex64
    assert signal.sample_rate == 1000000
    assert signal.sample_count == 2000000
    assert abs(signal.duration - 2.0) < 0.01
    assert signal.filename == "test_fsk.iq" 


def test_load_signal_auto_filename():
    """load_signal() auto-extracts filename from path when not provided."""
    path = os.path.join("test_data", "test_fsk.wav")
    signal = load_signal(path)
    assert signal.filename == "test_fsk.wav"


# ======================================================================
# Validation helper tests
# ======================================================================

def test_file_validation_helpers():
    """Extension validation is case-insensitive, sanitize strips directories."""
    assert validate_file_extension("test.wav") == "wav"
    assert validate_file_extension("TEST.WAV") == "wav"
    assert validate_file_extension("signal.iq") == "iq"
    assert validate_file_extension("SIGNAL.IQ") == "iq"

    with pytest.raises(Exception):
        validate_file_extension("file.txt")

    assert sanitize_filename("../../../etc/passwd") == "passwd"


# ======================================================================
# API upload endpoint tests — MUST match existing frontend contract
# ======================================================================

def test_api_upload_wav():
    """API upload for WAV returns correct metadata (data_type=float32)."""
    client = TestClient(app)
    test_wav_path = os.path.join("test_data", "test_sine.wav")
    with open(test_wav_path, "rb") as f:
        res = client.post("/api/files/upload", files={"file": ("test_sine.wav", f, "audio/wav")})

    assert res.status_code == 200
    data = res.json()
    assert data["filename"] == "test_sine.wav"
    assert data["format"] == "WAV"
    assert data["sample_rate"] == 48000
    assert data["sample_count"] == 96000
    assert data["duration_seconds"] == 2.0
    assert data["data_type"] == "float32"  # API reports original source type


def test_api_upload_iq():
    """API upload for IQ returns correct metadata (data_type=complex64)."""
    client = TestClient(app)
    test_iq_path = os.path.join("test_data", "test_sine.iq")
    with open(test_iq_path, "rb") as f:
        res = client.post("/api/files/upload", files={"file": ("test_sine.iq", f, "application/octet-stream")})

    assert res.status_code == 200
    data = res.json()
    assert data["filename"] == "test_sine.iq"
    assert data["format"] == "IQ"
    assert data["sample_rate"] == 1000000
    assert data["sample_count"] == 2000000
    assert data["duration_seconds"] == 2.0
    assert data["data_type"] == "complex64" 


def test_api_upload_fsk_wav():
    """API upload for FSK WAV — verifies the exact values from the spec."""
    client = TestClient(app)
    test_wav_path = os.path.join("test_data", "test_fsk.wav")
    with open(test_wav_path, "rb") as f:
        res = client.post("/api/files/upload", files={"file": ("test_fsk.wav", f, "audio/wav")})

    assert res.status_code == 200
    data = res.json()
    assert data["format"] == "WAV"
    assert data["sample_rate"] == 48000
    assert data["sample_count"] == 96000
    assert data["duration_seconds"] == 2.0
    assert data["data_type"] == "float32"


def test_api_upload_fsk_iq():
    """API upload for FSK IQ - verifies the exact values from the spec."""
    client = TestClient(app)
    test_iq_path = os.path.join("test_data", "test_fsk.iq")
    with open(test_iq_path, "rb") as f:
        res = client.post("/api/files/upload", files={"file": ("test_fsk.iq", f, "application/octet-stream")})

    assert res.status_code == 200
    data = res.json()
    assert data["format"] == "IQ"
    assert data["sample_rate"] == 1000000
    assert data["sample_count"] == 2000000
    assert data["duration_seconds"] == 2.0
    assert data["data_type"] == "complex64" 


def test_api_upload_invalid_extension():
    """Unsupported extension returns 400."""
    client = TestClient(app)
    res = client.post("/api/files/upload", files={"file": ("document.pdf", io.BytesIO(b"pdf data"), "application/pdf")})
    assert res.status_code == 400
    assert res.json() == {"detail": "Unsupported file format. Only .WAV and .IQ files are supported."}


def test_api_upload_empty_file():
    """Empty file upload returns 400."""
    client = TestClient(app)
    res = client.post("/api/files/upload", files={"file": ("empty.wav", io.BytesIO(b""), "audio/wav")})
    assert res.status_code == 400
    assert res.json() == {"detail": "Uploaded file is empty."}


def test_api_upload_invalid_iq_format():
    """Malformed IQ file upload returns 400."""
    client = TestClient(app)
    # 5 bytes is not a multiple of 8 bytes for float32 I/Q pairs
    res = client.post("/api/files/upload", files={"file": ("corrupted.iq", io.BytesIO(b"12345"), "application/octet-stream")})
    assert res.status_code == 400
    assert res.json() == {"detail": "Unable to read IQ file. Expected interleaved float32 I/Q samples."}
import os
import struct
import tempfile
import numpy as np

def test_raw_iq_parsing_values():
    """Verify raw float32 interleaved parses correctly to complex64"""
    import numpy as np
    from app.signal_processing.iq_reader import load_iq

    # Create dummy IQ data: [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    # which is 3 complex samples: 1+2j, 3+4j, 5+6j
    raw_floats = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    raw_bytes = struct.pack(f"<{len(raw_floats)}f", *raw_floats)

    with tempfile.NamedTemporaryFile(suffix=".iq", delete=False) as tmp:
        tmp.write(raw_bytes)
        tmp_path = tmp.name

    try:
        # Load the IQ file
        signal = load_iq(tmp_path, default_sample_rate=1000000)

        assert signal.format == "IQ"
        assert signal.data_type == "complex64"
        assert signal.samples.dtype == np.complex64
        assert signal.sample_count == 3
        
        # Verify actual values!
        expected = np.array([1.0 + 2.0j, 3.0 + 4.0j, 5.0 + 6.0j], dtype=np.complex64)
        np.testing.assert_array_equal(signal.samples, expected)
        
    finally:
        os.unlink(tmp_path)
