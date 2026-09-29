"""
Final Data / Payload Extraction Module for SignalScope (Part 12).

Implements payload bit extraction using validated Stage 07 header boundaries,
MSB-first bit-to-byte conversion, text vs binary content analysis, Shannon entropy calculation,
and safe payload presentation.
"""

import math
from collections import Counter
from typing import Dict, Any, Optional, Tuple


# ---------------------------------------------------------------------------
# Bit <-> Byte Helpers
# ---------------------------------------------------------------------------

def bits_to_bytes(bits: str) -> bytes:
    """Converts a binary string ('0'/'1') of length multiple of 8 to bytes."""
    if len(bits) % 8 != 0:
        raise ValueError(f"Bitstream length ({len(bits)}) is not a multiple of 8 bits.")
    return bytes(int(bits[i:i+8], 2) for i in range(0, len(bits), 8))


def bytes_to_bits(data: bytes) -> str:
    """Converts bytes to a binary string ('0'/'1') where each byte is 8 bits."""
    return "".join(f"{b:08b}" for b in data)


def calculate_entropy(data: bytes) -> float:
    """Calculates Shannon entropy (bits per byte, 0.0 to 8.0) of payload bytes."""
    if not data:
        return 0.0
    counts = Counter(data)
    total = len(data)
    entropy = 0.0
    for count in counts.values():
        p = count / total
        entropy -= p * math.log2(p)
    return round(entropy, 4)


# ---------------------------------------------------------------------------
# Payload Bit Extraction & Validation
# ---------------------------------------------------------------------------

def extract_payload_bits(bits: str, payload_start: int, payload_end: int) -> str:
    """
    Extracts binary payload slice bits[payload_start:payload_end] with boundary validation.
    
    Raises ValueError on invalid boundaries or non-byte alignment.
    """
    if payload_start < 0:
        raise ValueError(f"Invalid payload_start ({payload_start}): must be non-negative.")
    if payload_end < payload_start:
        raise ValueError(f"Invalid payload boundaries: payload_end ({payload_end}) < payload_start ({payload_start}).")
    if payload_end > len(bits):
        raise ValueError(f"Payload boundary ({payload_end}) exceeds bitstream length ({len(bits)}).")

    bit_count = payload_end - payload_start
    if bit_count % 8 != 0:
        raise ValueError(f"Payload bit count ({bit_count}) is not byte-aligned (divisible by 8).")

    return bits[payload_start:payload_end]


# ---------------------------------------------------------------------------
# Payload Content Analysis (Text vs Binary)
# ---------------------------------------------------------------------------

def analyze_payload(payload_bytes: bytes) -> Dict[str, Any]:
    """
    Analyzes payload bytes to detect UTF-8 text vs arbitrary binary format.
    Computes byte count, printable character ratio, hex representation, and entropy.
    """
    byte_count = len(payload_bytes)
    bit_count = byte_count * 8
    hex_str = payload_bytes.hex().upper()

    if byte_count == 0:
        return {
            "data_type": "EMPTY",
            "text": "",
            "hex": "",
            "byte_count": 0,
            "bit_count": 0,
            "printable_ratio": 0.0,
            "entropy": 0.0
        }

    printable_count = sum(1 for b in payload_bytes if 32 <= b <= 126 or b in (9, 10, 13))
    printable_ratio = round(printable_count / byte_count, 4)
    entropy = calculate_entropy(payload_bytes)

    # Attempt UTF-8 text decoding
    is_text = False
    text_content = None

    try:
        decoded = payload_bytes.decode("utf-8")
        # Consider text if printable ratio >= 0.80 and no control chars other than tab/newline
        if printable_ratio >= 0.80:
            is_text = True
            text_content = decoded
    except UnicodeDecodeError:
        is_text = False
        text_content = None

    return {
        "data_type": "TEXT" if is_text else "BINARY",
        "text": text_content,
        "hex": hex_str,
        "byte_count": byte_count,
        "bit_count": bit_count,
        "printable_ratio": printable_ratio,
        "entropy": entropy
    }


# ---------------------------------------------------------------------------
# Complete Pipeline Payload Recovery Entry Point
# ---------------------------------------------------------------------------

def extract_and_analyze_payload(bits: str, header_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Takes validated Stage 07 header metadata, extracts payload bits, converts to bytes,
    and returns complete structured payload recovery result.
    """
    if not isinstance(header_info, dict):
        raise ValueError("Header information must be a valid dictionary.")

    validation_status = header_info.get("validation_status")
    if validation_status != "VALIDATED":
        return {
            "status": "HEADER_NOT_VALIDATED",
            "message": f"Cannot extract payload: header validation status is '{validation_status}'.",
            "data_type": None,
            "text": None,
            "hex": None,
            "payload_byte_count": 0,
            "payload_bit_count": 0
        }

    payload_start = header_info.get("payload_start")
    payload_end = header_info.get("payload_end")
    expected_bytes = header_info.get("payload_length")

    if payload_start is None or payload_end is None:
        raise ValueError("Header info missing payload_start or payload_end boundaries.")

    # Extract payload bits
    payload_bits = extract_payload_bits(bits, payload_start, payload_end)
    payload_bytes = bits_to_bytes(payload_bits)

    if expected_bytes is not None and len(payload_bytes) != expected_bytes:
        raise ValueError(
            f"Extracted payload byte count ({len(payload_bytes)}) disagrees with header-declared payload length ({expected_bytes})."
        )

    analysis = analyze_payload(payload_bytes)

    return {
        "status": "RECOVERED",
        "validation_status": "VALIDATED",
        "payload_start": payload_start,
        "payload_end": payload_end,
        "payload_bit_count": analysis["bit_count"],
        "payload_byte_count": analysis["byte_count"],
        "data_type": analysis["data_type"],
        "text": analysis["text"],
        "hex": analysis["hex"],
        "printable_ratio": analysis["printable_ratio"],
        "entropy": analysis["entropy"],
        "method": "Validated header boundary payload extraction & UTF-8/Binary analysis"
    }
