"""
Comprehensive Unit, Integration, False-Positive, API, and End-to-End Tests
for Part 11 Header & Synchronization Detection.
"""

import os
import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.signal_processing.header import (
    DEFAULT_SYNC_PATTERN,
    compute_crc16_ccitt,
    validate_crc16_ccitt,
    build_synthetic_header,
    build_synthetic_frame,
    find_sync_candidates,
    parse_header,
    detect_header,
    bits_to_bytes,
    bytes_to_bits
)

client = TestClient(app)

TEST_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_data")


# ---------------------------------------------------------------------------
# 1. Unit Tests for CRC-16-CCITT & Header Parsing
# ---------------------------------------------------------------------------

def test_crc16_ccitt_computation_and_validation():
    # Known CRC-16-CCITT check for b"123456789" with init 0xFFFF, poly 0x1021
    # Standard check value for b"123456789" is 0x29B1
    test_data = b"123456789"
    computed = compute_crc16_ccitt(test_data)
    assert computed == 0x29B1
    assert validate_crc16_ccitt(test_data, 0x29B1) is True
    assert validate_crc16_ccitt(test_data, 0x0000) is False


def test_build_and_parse_synthetic_header():
    header_bytes, crc_val, header_bits = build_synthetic_header(
        version=1,
        message_type=2,
        payload_length=32,
        sequence=105,
        flags=0x80
    )
    assert len(header_bits) == 72
    assert len(header_bytes) == 9

    parsed = parse_header(header_bits, header_start=0)
    assert parsed["version"] == 1
    assert parsed["message_type"] == 2
    assert parsed["payload_length"] == 32
    assert parsed["sequence"] == 105
    assert parsed["flags"] == 0x80
    assert parsed["header_crc"] == crc_val
    assert parsed["crc_valid"] is True
    assert parsed["payload_start"] == 72
    assert parsed["payload_end"] == 72 + (32 * 8)


# ---------------------------------------------------------------------------
# 2. Sync Detection & Error Tolerance Tests
# ---------------------------------------------------------------------------

def test_exact_sync_detection():
    prefix = "00001111"
    suffix = "11110000"
    bitstream = prefix + DEFAULT_SYNC_PATTERN + suffix

    candidates = find_sync_candidates(bitstream, sync_pattern=DEFAULT_SYNC_PATTERN, max_errors=0)
    assert len(candidates) == 1
    cand = candidates[0]
    assert cand["position"] == len(prefix)
    assert cand["hamming_distance"] == 0
    assert cand["match_percentage"] == 100.0


def test_sync_detection_with_1_and_2_bit_errors():
    sync_list = list(DEFAULT_SYNC_PATTERN)
    
    # 1 bit error
    sync_1err = list(sync_list)
    sync_1err[5] = '0' if sync_1err[5] == '1' else '1'
    str_1err = "".join(sync_1err)

    cands_1err = find_sync_candidates(str_1err, sync_pattern=DEFAULT_SYNC_PATTERN, max_errors=1)
    assert len(cands_1err) == 1
    assert cands_1err[0]["hamming_distance"] == 1
    assert cands_1err[0]["match_percentage"] == round((1.0 - 1/32) * 100.0, 2)

    # 2 bit errors
    sync_2err = list(sync_1err)
    sync_2err[12] = '0' if sync_2err[12] == '1' else '1'
    str_2err = "".join(sync_2err)

    cands_2err = find_sync_candidates(str_2err, sync_pattern=DEFAULT_SYNC_PATTERN, max_errors=2)
    assert len(cands_2err) == 1
    assert cands_2err[0]["hamming_distance"] == 2


def test_sync_rejection_above_threshold():
    sync_list = list(DEFAULT_SYNC_PATTERN)
    # Corrupt 3 bits
    for pos in [2, 10, 20]:
        sync_list[pos] = '0' if sync_list[pos] == '1' else '1'
    str_3err = "".join(sync_list)

    # Should be rejected when max_errors=2
    cands = find_sync_candidates(str_3err, sync_pattern=DEFAULT_SYNC_PATTERN, max_errors=2)
    assert len(cands) == 0

    # Should be accepted when max_errors=3
    cands_3 = find_sync_candidates(str_3err, sync_pattern=DEFAULT_SYNC_PATTERN, max_errors=3)
    assert len(cands_3) == 1
    assert cands_3[0]["hamming_distance"] == 3


# ---------------------------------------------------------------------------
# 3. False-Positive Protection (SYNC MATCH != VALID HEADER)
# ---------------------------------------------------------------------------

def test_false_sync_candidate_rejection_with_invalid_header_crc():
    """
    Constructs a bitstream containing a 100% valid sync word followed by corrupt header bytes.
    Verifies that detect_header identifies the sync candidate but REJECTS the frame
    with status 'INVALID_HEADER'.
    """
    dummy_header_bytes = b"\x01\x01\x00\x12\x03\xe9\x00\xff\xff"  # Invalid CRC 0xFFFF
    dummy_header_bits = bytes_to_bits(dummy_header_bytes)
    corrupt_frame = DEFAULT_SYNC_PATTERN + dummy_header_bits + ("0" * 144)

    result = detect_header(corrupt_frame, sync_pattern=DEFAULT_SYNC_PATTERN, max_errors=0)
    assert result["sync_found"] is True
    assert result["sync_position"] == 0
    assert result["hamming_distance"] == 0
    assert result["header_found"] is False
    assert result["validation_status"] == "INVALID_HEADER"
    assert "CRC validation" in result["message"] or result.get("crc_valid") is False


def test_invalid_payload_length_rejection():
    """
    Header indicates payload length of 1000 bytes (8000 bits), but bitstream ends early.
    """
    _, _, header_bits = build_synthetic_header(payload_length=1000)
    short_frame = DEFAULT_SYNC_PATTERN + header_bits + ("0" * 64)

    result = detect_header(short_frame, sync_pattern=DEFAULT_SYNC_PATTERN, max_errors=0)
    assert result["sync_found"] is True
    assert result["header_found"] is False
    assert result["validation_status"] == "INVALID_HEADER"


# ---------------------------------------------------------------------------
# 4. Integration & End-to-End Pipeline Tests
# ---------------------------------------------------------------------------

def test_complete_synthetic_frame_detection():
    frame_bits, meta = build_synthetic_frame(
        sync_pattern=DEFAULT_SYNC_PATTERN,
        version=1,
        message_type=1,
        payload_bytes=b"TEST_PAYLOAD_DATA",
        sequence=42,
        flags=0
    )
    padded_bits = "00000000" + frame_bits + "11111111"

    result = detect_header(padded_bits, sync_pattern=DEFAULT_SYNC_PATTERN, max_errors=0)
    assert result["sync_found"] is True
    assert result["sync_position"] == 8
    assert result["hamming_distance"] == 0
    assert result["match_percentage"] == 100.0
    assert result["header_found"] is True
    assert result["version"] == 1
    assert result["message_type"] == 1
    assert result["payload_length"] == len(b"TEST_PAYLOAD_DATA")
    assert result["sequence"] == 42
    assert result["crc_valid"] is True
    assert result["validation_status"] == "VALIDATED"
    assert result["payload_start"] == 8 + 32 + 72
    assert result["payload_end"] == 8 + 32 + 72 + (len(b"TEST_PAYLOAD_DATA") * 8)


def test_end_to_end_header_fsk_wav_pipeline():
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

    # 2. Call Header Detection API
    detect_resp = client.post(f"/api/header/detect/{signal_id}")
    assert detect_resp.status_code == 200
    data = detect_resp.json()

    assert data["signal_id"] == signal_id
    assert data["sync_found"] is True
    assert data["sync_position"] == ground_truth["sync_position"]
    assert data["sync_length"] == ground_truth["sync_length"]
    assert data["hamming_distance"] == 0
    assert data["match_percentage"] == 100.0
    assert data["header_found"] is True
    assert data["header_start"] == ground_truth["header_start"]
    assert data["version"] == ground_truth["protocol_version"]
    assert data["message_type"] == ground_truth["message_type"]
    assert data["payload_length"] == ground_truth["payload_bytes_count"]
    assert data["sequence"] == ground_truth["sequence"]
    assert data["header_crc"] == ground_truth["expected_crc"]
    assert data["crc_valid"] is True
    assert data["payload_start"] == ground_truth["payload_start"]
    assert data["payload_end"] == ground_truth["payload_start"] + ground_truth["payload_length"]
    assert data["validation_status"] == "VALIDATED"


def test_end_to_end_header_fsk_iq_pipeline():
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

    # 2. Call Header Detection API
    detect_resp = client.post(f"/api/header/detect/{signal_id}")
    assert detect_resp.status_code == 200
    data = detect_resp.json()

    assert data["sync_found"] is True
    assert data["sync_position"] == ground_truth["sync_position"]
    assert data["header_found"] is True
    assert data["version"] == ground_truth["protocol_version"]
    assert data["payload_length"] == ground_truth["payload_bytes_count"]
    assert data["crc_valid"] is True
    assert data["validation_status"] == "VALIDATED"
