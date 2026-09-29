"""
Comprehensive Unit, Integration, Robustness, API, and End-to-End Tests
for Part 12 Final Data / Payload Extraction (Stage 08).
"""

import os
import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.signal_processing.payload import (
    bits_to_bytes,
    bytes_to_bits,
    calculate_entropy,
    extract_payload_bits,
    analyze_payload,
    extract_and_analyze_payload
)

client = TestClient(app)

TEST_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_data")


# ---------------------------------------------------------------------------
# 1. Unit Tests for Bit-to-Byte Conversion & Entropy
# ---------------------------------------------------------------------------

def test_bits_to_bytes_conversion():
    bits = "0100100001000101010011000100110001001111"  # "HELLO" in ASCII
    bytes_val = bits_to_bytes(bits)
    assert bytes_val == b"HELLO"
    assert bytes_to_bits(bytes_val) == bits


def test_entropy_calculation():
    # Constant byte stream -> 0 entropy
    assert calculate_entropy(b"AAAAAAA") == 0.0
    # Uniform 4-byte stream -> log2(4) = 2.0 bits/byte
    assert calculate_entropy(b"\x00\x01\x02\x03") == 2.0


# ---------------------------------------------------------------------------
# 2. Text vs Binary Content Detection Tests
# ---------------------------------------------------------------------------

def test_printable_text_payload_detection():
    payload_text = b"HELLO_RADIO_SIGNAL"
    res = analyze_payload(payload_text)
    assert res["data_type"] == "TEXT"
    assert res["text"] == "HELLO_RADIO_SIGNAL"
    assert res["hex"] == payload_text.hex().upper()
    assert res["printable_ratio"] == 1.0
    assert res["byte_count"] == 18
    assert res["bit_count"] == 144


def test_binary_payload_detection():
    binary_bytes = bytes([0x00, 0x01, 0x7F, 0x80, 0xA5, 0xFF, 0x12, 0x34])
    res = analyze_payload(binary_bytes)
    assert res["data_type"] == "BINARY"
    assert res["text"] is None
    assert res["hex"] == "00017F80A5FF1234"
    assert res["byte_count"] == 8
    assert res["bit_count"] == 64


def test_invalid_utf8_binary_handling():
    # Invalid UTF-8 sequence (continuation byte without start byte)
    invalid_utf8 = b"\x80\x81\x82\xff\xfe"
    res = analyze_payload(invalid_utf8)
    assert res["data_type"] == "BINARY"
    assert res["text"] is None
    assert res["byte_count"] == 5


# ---------------------------------------------------------------------------
# 3. Robustness & Malformed Boundary Handling Tests
# ---------------------------------------------------------------------------

def test_extract_payload_bits_invalid_boundaries():
    bitstream = "10101010" * 10  # 80 bits

    # 1. Negative payload_start
    with pytest.raises(ValueError, match="must be non-negative"):
        extract_payload_bits(bitstream, -1, 16)

    # 2. payload_end < payload_start
    with pytest.raises(ValueError, match="payload_end"):
        extract_payload_bits(bitstream, 32, 16)

    # 3. payload_end exceeds bitstream length
    with pytest.raises(ValueError, match="exceeds bitstream length"):
        extract_payload_bits(bitstream, 0, 100)

    # 4. Non-byte-aligned payload (e.g. 7 bits)
    with pytest.raises(ValueError, match="not byte-aligned"):
        extract_payload_bits(bitstream, 0, 7)


def test_extract_and_analyze_payload_unvalidated_header():
    unvalidated_header = {
        "validation_status": "INVALID_HEADER",
        "message": "CRC failure"
    }
    res = extract_and_analyze_payload("10101010" * 10, unvalidated_header)
    assert res["status"] == "HEADER_NOT_VALIDATED"
    assert res["data_type"] is None


# ---------------------------------------------------------------------------
# 4. End-to-End WAV & IQ Pipeline Tests
# ---------------------------------------------------------------------------

def test_end_to_end_wav_payload_recovery():
    json_path = os.path.join(TEST_DATA_DIR, "test_header_fsk.json")
    wav_path = os.path.join(TEST_DATA_DIR, "test_header_fsk.wav")
    assert os.path.exists(json_path)
    assert os.path.exists(wav_path)

    with open(json_path, "r") as f:
        ground_truth = json.load(f)

    # 1. Upload WAV file
    with open(wav_path, "rb") as f:
        upload_resp = client.post("/api/files/upload", files={"file": ("test_header_fsk.wav", f, "audio/wav")})
    assert upload_resp.status_code == 200
    signal_id = upload_resp.json()["signal_id"]

    # 2. Call Payload Extraction API
    extract_resp = client.post(f"/api/payload/extract/{signal_id}")
    assert extract_resp.status_code == 200
    data = extract_resp.json()

    assert data["signal_id"] == signal_id
    assert data["status"] == "RECOVERED"
    assert data["validation_status"] == "VALIDATED"
    assert data["payload_start"] == ground_truth["payload_start"]
    assert data["payload_end"] == ground_truth["payload_start"] + ground_truth["payload_length"]
    assert data["payload_bit_count"] == ground_truth["payload_length"]
    assert data["payload_byte_count"] == ground_truth["payload_bytes_count"]
    assert data["data_type"] == "TEXT"
    assert data["text"] == ground_truth["payload_bytes"]
    assert data["printable_ratio"] == 1.0


def test_end_to_end_iq_payload_recovery():
    json_path = os.path.join(TEST_DATA_DIR, "test_header_fsk.json")
    iq_path = os.path.join(TEST_DATA_DIR, "test_header_fsk.iq")
    assert os.path.exists(json_path)
    assert os.path.exists(iq_path)

    with open(json_path, "r") as f:
        ground_truth = json.load(f)

    # 1. Upload IQ file
    with open(iq_path, "rb") as f:
        upload_resp = client.post("/api/files/upload", files={"file": ("test_header_fsk.iq", f, "application/octet-stream")})
    assert upload_resp.status_code == 200
    signal_id = upload_resp.json()["signal_id"]

    # 2. Call Payload Extraction API
    extract_resp = client.post(f"/api/payload/extract/{signal_id}")
    assert extract_resp.status_code == 200
    data = extract_resp.json()

    assert data["status"] == "RECOVERED"
    assert data["data_type"] == "TEXT"
    assert data["text"] == ground_truth["payload_bytes"]
    assert data["payload_byte_count"] == 18


# ---------------------------------------------------------------------------
# 5. Complete 8-Stage Pipeline Integration Regression Test
# ---------------------------------------------------------------------------

def test_full_8_stage_pipeline_synthetic_ground_truth():
    """
    Demonstrates full 8-stage automated pipeline execution:
    01 Load Signal -> 02 Detect Signal -> 03 Analyze Modulation ->
    04 Demodulate -> 05 De-interleave -> 06 FEC Decode ->
    07 Header Detection -> 08 Final Data Recovery
    """
    wav_path = os.path.join(TEST_DATA_DIR, "test_header_fsk.wav")
    with open(wav_path, "rb") as f:
        upload_resp = client.post("/api/files/upload", files={"file": ("test_header_fsk.wav", f, "audio/wav")})
    assert upload_resp.status_code == 200
    signal_id = upload_resp.json()["signal_id"]

    # Stage 02: Detect Signal & Analysis
    analysis_resp = client.get(f"/api/analysis/{signal_id}")
    assert analysis_resp.status_code == 200
    assert analysis_resp.json()["activity"]["signal_present"] is True

    # Stage 03: Analyze Modulation
    mod_resp = client.get(f"/api/modulation/{signal_id}")
    assert mod_resp.status_code == 200
    assert mod_resp.json()["modulation"] == "FSK"

    # Stage 04: Demodulate FSK
    demod_resp = client.post(f"/api/demodulation/fsk/{signal_id}")
    assert demod_resp.status_code == 200
    bits = demod_resp.json()["bits"]
    assert len(bits) > 0

    # Stage 07: Header Detection
    hdr_resp = client.post(f"/api/header/detect/{signal_id}")
    assert hdr_resp.status_code == 200
    hdr_data = hdr_resp.json()
    assert hdr_data["validation_status"] == "VALIDATED"
    assert hdr_data["crc_valid"] is True

    # Stage 08: Final Data Recovery
    payload_resp = client.post(f"/api/payload/extract/{signal_id}")
    assert payload_resp.status_code == 200
    payload_data = payload_resp.json()

    assert payload_data["status"] == "RECOVERED"
    assert payload_data["data_type"] == "TEXT"
    assert payload_data["text"] == "HELLO_RADIO_SIGNAL"
    assert payload_data["payload_byte_count"] == 18
    assert payload_data["payload_bit_count"] == 144
