"""
Header and Synchronization Detection Module for SignalScope (Part 11).

Implements candidate-based synchronization search, synthetic protocol header parsing,
CRC-16-CCITT validation, frame boundary detection, and payload boundary identification.
"""

import struct
from typing import List, Dict, Any, Optional, Tuple

DEFAULT_SYNC_PATTERN = "10101010101010101100110011001100"  # 32 bits (0xAAAACCCC)
HEADER_BITS_LENGTH = 72  # 9 bytes (Version, Message Type, Payload Length, Sequence, Flags, Header CRC)


# ---------------------------------------------------------------------------
# Helpers for Bitstream <-> Byte Conversions
# ---------------------------------------------------------------------------

def bits_to_bytes(bits: str) -> bytes:
    """Converts a binary string ('0'/'1') of length multiple of 8 to bytes."""
    if len(bits) % 8 != 0:
        raise ValueError(f"Bitstream length ({len(bits)}) is not a multiple of 8 bits.")
    return bytes(int(bits[i:i+8], 2) for i in range(0, len(bits), 8))


def bytes_to_bits(data: bytes) -> str:
    """Converts bytes to a binary string ('0'/'1') where each byte is 8 bits."""
    return "".join(f"{b:08b}" for b in data)


# ---------------------------------------------------------------------------
# CRC-16-CCITT Calculation & Validation
# ---------------------------------------------------------------------------

def compute_crc16_ccitt(data: bytes) -> int:
    """
    Computes CRC-16-CCITT over input bytes.
    Specification:
    - Polynomial: 0x1021 (x^16 + x^12 + x^5 + 1)
    - Initial value: 0xFFFF
    - RefIn: False, RefOut: False
    - XOR Out: 0x0000
    """
    crc = 0xFFFF
    for b in data:
        crc ^= (b << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def validate_crc16_ccitt(data: bytes, expected_crc: int) -> bool:
    """Validates CRC-16-CCITT for input data bytes against expected uint16 CRC."""
    return compute_crc16_ccitt(data) == (expected_crc & 0xFFFF)


# ---------------------------------------------------------------------------
# Synthetic Frame Builder (for Ground-Truth Signal Generation)
# ---------------------------------------------------------------------------

def build_synthetic_header(
    version: int = 1,
    message_type: int = 1,
    payload_length: int = 18,
    sequence: int = 1001,
    flags: int = 0
) -> Tuple[bytes, int, str]:
    """
    Builds synthetic 72-bit (9-byte) header with CRC-16-CCITT.
    Format:
    - Version: 8 bits (uint8)
    - Message Type: 8 bits (uint8)
    - Payload Length: 16 bits (uint16, big-endian)
    - Sequence: 16 bits (uint16, big-endian)
    - Flags: 8 bits (uint8)
    - Header CRC: 16 bits (uint16, big-endian)
    
    Returns (header_bytes, computed_crc, header_bits_str)
    """
    fields_bytes = struct.pack(">BBHHB", version & 0xFF, message_type & 0xFF, payload_length & 0xFFFF, sequence & 0xFFFF, flags & 0xFF)
    computed_crc = compute_crc16_ccitt(fields_bytes)
    header_bytes = fields_bytes + struct.pack(">H", computed_crc)
    header_bits = bytes_to_bits(header_bytes)
    return header_bytes, computed_crc, header_bits


def build_synthetic_frame(
    sync_pattern: str = DEFAULT_SYNC_PATTERN,
    version: int = 1,
    message_type: int = 1,
    payload_bytes: bytes = b"HELLO_RADIO_SIGNAL",
    sequence: int = 1001,
    flags: int = 0
) -> Tuple[str, Dict[str, Any]]:
    """
    Constructs complete synthetic bitstream: SYNC (32 bits) + HEADER (72 bits) + PAYLOAD.
    Returns (frame_bits_str, frame_metadata_dict).
    """
    payload_bits = bytes_to_bits(payload_bytes)
    payload_len = len(payload_bytes)
    header_bytes, crc_val, header_bits = build_synthetic_header(
        version=version,
        message_type=message_type,
        payload_length=payload_len,
        sequence=sequence,
        flags=flags
    )
    
    frame_bits = sync_pattern + header_bits + payload_bits
    metadata = {
        "sync_pattern": sync_pattern,
        "sync_length": len(sync_pattern),
        "sync_position": 0,
        "header_start": len(sync_pattern),
        "header_length": HEADER_BITS_LENGTH,
        "payload_start": len(sync_pattern) + HEADER_BITS_LENGTH,
        "payload_length": len(payload_bits),
        "payload_bytes_count": payload_len,
        "protocol_version": version,
        "message_type": message_type,
        "sequence": sequence,
        "flags": flags,
        "crc_poly": "0x1021",
        "expected_crc": crc_val,
        "total_frame_bits": len(frame_bits)
    }
    return frame_bits, metadata


# ---------------------------------------------------------------------------
# Sync & Header Detection Logic
# ---------------------------------------------------------------------------

def find_sync_candidates(
    bits: str,
    sync_pattern: str = DEFAULT_SYNC_PATTERN,
    max_errors: int = 2
) -> List[Dict[str, Any]]:
    """
    Searches bitstream for sync pattern candidates within max_errors Hamming distance.
    Returns list of sync candidates sorted by ascending Hamming distance.
    """
    candidates = []
    pattern_len = len(sync_pattern)
    bit_count = len(bits)

    if bit_count < pattern_len:
        return candidates

    for i in range(bit_count - pattern_len + 1):
        segment = bits[i : i + pattern_len]
        hamming_dist = sum(1 for a, b in zip(segment, sync_pattern) if a != b)
        if hamming_dist <= max_errors:
            match_pct = (1.0 - (hamming_dist / pattern_len)) * 100.0
            candidates.append({
                "position": i,
                "pattern_length": pattern_len,
                "hamming_distance": hamming_dist,
                "match_percentage": round(match_pct, 2)
            })

    candidates.sort(key=lambda c: c["hamming_distance"])
    return candidates


def parse_header(bits: str, header_start: int) -> Dict[str, Any]:
    """
    Parses a 72-bit header starting at bit index `header_start`.
    
    Returns structured header metadata dictionary.
    Raises ValueError if bitstream is too short or invalid format.
    """
    header_end = header_start + HEADER_BITS_LENGTH
    if len(bits) < header_end:
        raise ValueError(f"Bitstream length ({len(bits)}) insufficient for 72-bit header at index {header_start}.")

    header_bits = bits[header_start:header_end]
    header_bytes = bits_to_bytes(header_bits)

    fields_bytes = header_bytes[:7]
    raw_crc = header_bytes[7:9]

    version, msg_type, payload_length, sequence, flags = struct.unpack(">BBHHB", fields_bytes)
    header_crc = struct.unpack(">H", raw_crc)[0]

    computed_crc = compute_crc16_ccitt(fields_bytes)
    crc_valid = (header_crc == computed_crc)

    payload_start = header_end
    payload_end = payload_start + (payload_length * 8)

    return {
        "version": version,
        "message_type": msg_type,
        "payload_length": payload_length,
        "sequence": sequence,
        "flags": flags,
        "header_crc": header_crc,
        "computed_crc": computed_crc,
        "crc_valid": crc_valid,
        "header_start": header_start,
        "header_end": header_end,
        "payload_start": payload_start,
        "payload_end": payload_end
    }


def detect_header(
    bits: str,
    sync_pattern: str = DEFAULT_SYNC_PATTERN,
    max_errors: int = 2
) -> Dict[str, Any]:
    """
    Executes synchronization candidate search, header parsing, CRC validation,
    and boundary verification.
    
    Evaluates candidate sync locations and returns frame boundary details.
    
    Wording / Status values:
    - VALIDATED: Sync matched, header parsed, CRC valid, payload fits bitstream.
    - INVALID_HEADER: Sync candidate found, but header CRC or boundary validation failed.
    - HEADER_NOT_FOUND: No sync candidate met error threshold or bitstream too short.
    """
    candidates = find_sync_candidates(bits, sync_pattern=sync_pattern, max_errors=max_errors)

    if not candidates:
        return {
            "sync_found": False,
            "header_found": False,
            "validation_status": "HEADER_NOT_FOUND",
            "message": "No synchronization pattern candidate detected within error threshold.",
            "candidates_count": 0
        }

    # Evaluate each sync candidate for a valid header
    evaluated_candidates = []
    validated_result = None

    for cand in candidates:
        sync_pos = cand["position"]
        header_start = sync_pos + cand["pattern_length"]
        header_end = header_start + HEADER_BITS_LENGTH

        if len(bits) < header_end:
            cand_eval = {
                **cand,
                "header_found": False,
                "validation_status": "INSUFFICIENT_HEADER_BITS",
                "reason": "Bitstream ended before complete 72-bit header"
            }
            evaluated_candidates.append(cand_eval)
            continue

        try:
            parsed = parse_header(bits, header_start)
            payload_start = parsed["payload_start"]
            payload_end = parsed["payload_end"]

            payload_fits = len(bits) >= payload_end

            if parsed["crc_valid"] and payload_fits:
                res = {
                    "sync_found": True,
                    "sync_position": sync_pos,
                    "sync_length": cand["pattern_length"],
                    "hamming_distance": cand["hamming_distance"],
                    "match_percentage": cand["match_percentage"],
                    "header_found": True,
                    "header_start": header_start,
                    "header_length": HEADER_BITS_LENGTH,
                    "version": parsed["version"],
                    "message_type": parsed["message_type"],
                    "payload_length": parsed["payload_length"],
                    "sequence": parsed["sequence"],
                    "flags": parsed["flags"],
                    "header_crc": parsed["header_crc"],
                    "computed_crc": parsed["computed_crc"],
                    "crc_valid": True,
                    "payload_start": payload_start,
                    "payload_end": payload_end,
                    "validation_status": "VALIDATED",
                    "method": "Synthetic Protocol Header Candidate Match & CRC-16-CCITT Checksum Validation"
                }
                if validated_result is None:
                    validated_result = res
                cand_eval = {**cand, "header_found": True, "crc_valid": True, "validation_status": "VALIDATED"}
            else:
                reason = "CRC mismatch" if not parsed["crc_valid"] else "Payload exceeds bitstream length"
                cand_eval = {
                    **cand,
                    "header_found": True,
                    "crc_valid": parsed["crc_valid"],
                    "validation_status": "INVALID_HEADER",
                    "reason": reason,
                    "header_crc": parsed["header_crc"],
                    "computed_crc": parsed["computed_crc"]
                }
            evaluated_candidates.append(cand_eval)
        except Exception as err:
            evaluated_candidates.append({
                **cand,
                "header_found": False,
                "validation_status": "HEADER_PARSE_ERROR",
                "reason": str(err)
            })

    if validated_result is not None:
        return validated_result

    # Best sync candidate existed but header was invalid (Demonstrates SYNC MATCH != VALID HEADER)
    best_cand = candidates[0]
    return {
        "sync_found": True,
        "sync_position": best_cand["position"],
        "sync_length": best_cand["pattern_length"],
        "hamming_distance": best_cand["hamming_distance"],
        "match_percentage": best_cand["match_percentage"],
        "header_found": False,
        "validation_status": "INVALID_HEADER",
        "message": "Sync candidate detected, but header CRC validation or payload boundary check failed.",
        "candidates_count": len(candidates),
        "best_candidate": best_cand
    }
