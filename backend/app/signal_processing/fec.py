"""
Forward Error Correction (FEC) Module for SignalScope (Part 10A).

Implements Rate 1/2, Constraint Length K=3 Convolutional Encoding and
Hard-Decision Viterbi Decoding.

Convolutional Code Specifications:
- Rate: 1/2 (2 output bits per 1 input bit)
- Constraint Length K: 3 (2 memory register bits, 4 trellis states)
- Generator Polynomials:
    G1 = 7 (octal) = 111 (binary) -> v1 = u[k] ^ s1 ^ s2
    G2 = 5 (octal) = 101 (binary) -> v2 = u[k] ^ s2
- Trellis States: 0=(0,0), 1=(0,1), 2=(1,0), 3=(1,1)
- Trellis Termination: 2 flush zero bits appended during encoding to return to state 0.
"""

from typing import List, Dict, Any, Optional, Union, Tuple
from reedsolo import RSCodec, ReedSolomonError


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


# Transition tables for K=3, G1=7 (111), G2=5 (101)
# State representation S in {0,1,2,3}: S = (s1, s2) -> integer value (s1<<1) | s2
# Input bit u in {0,1}
# Next state S' = (u<<1) | (s1)
# Output pair:
#   v1 = u ^ s1 ^ s2
#   v2 = u ^ s2

def _get_encoder_output_and_next_state(state: int, input_bit: int) -> Tuple[Tuple[int, int], int]:
    s1 = (state >> 1) & 1
    s2 = state & 1
    u = input_bit & 1

    v1 = u ^ s1 ^ s2
    v2 = u ^ s2
    next_state = ((u << 1) | s1) & 3
    return (v1, v2), next_state


def convolutional_encode(
    bits: Union[str, List[int]],
    k: int = 3,
    g1: int = 7,
    g2: int = 5,
    flush: bool = True
) -> Union[str, List[int]]:
    """
    Encodes a binary bitstream using Rate 1/2, Constraint Length K=3 Convolutional Encoder.

    Parameters:
    - bits: Binary payload bitstream (string of '0'/'1' or list of 0/1 integers).
    - k: Constraint length (default K=3).
    - g1: Generator 1 in octal (default 7 octal = 111 binary).
    - g2: Generator 2 in octal (default 5 octal = 101 binary).
    - flush: If True, appends K-1=2 zero flush bits to terminate trellis at state 0.
    """
    if k != 3 or g1 != 7 or g2 != 5:
        raise ValueError(f"Currently supported FEC config is K=3, G1=7, G2=5. Got K={k}, G1={g1}, G2={g2}.")

    is_str = isinstance(bits, str)
    bit_seq = [int(b) for b in bits] if is_str else list(bits)

    for b in bit_seq:
        if b not in (0, 1):
            raise ValueError(f"Input bitstream contains non-binary symbol: {b}")

    n_bits = len(bit_seq)
    if n_bits == 0:
        return "" if is_str else []

    # Append flush bits (K-1 = 2 zeros) if requested
    input_data = bit_seq + [0, 0] if flush else bit_seq

    output = []
    state = 0  # Initial state is 0 (0,0)

    for u in input_data:
        (v1, v2), next_state = _get_encoder_output_and_next_state(state, u)
        output.append(v1)
        output.append(v2)
        state = next_state

    return "".join(str(x) for x in output) if is_str else output


def viterbi_decode(
    received_bits: Union[str, List[int]],
    k: int = 3,
    g1: int = 7,
    g2: int = 5,
    trim_flush: bool = True
) -> Union[str, List[int]]:
    """
    Decodes a Rate 1/2 Convolutionally Encoded bitstream using Hard-Decision Viterbi Algorithm.

    Parameters:
    - received_bits: Received binary bitstream (even length).
    - k: Constraint length (default K=3).
    - g1: Generator 1 octal (default 7).
    - g2: Generator 2 octal (default 5).
    - trim_flush: If True, trims the final K-1=2 trellis termination flush bits from decoded output.
    """
    if k != 3 or g1 != 7 or g2 != 5:
        raise ValueError(f"Currently supported FEC config is K=3, G1=7, G2=5. Got K={k}, G1={g1}, G2={g2}.")

    is_str = isinstance(received_bits, str)
    bit_seq = [int(b) for b in received_bits] if is_str else list(received_bits)

    for b in bit_seq:
        if b not in (0, 1):
            raise ValueError(f"Received bitstream contains non-binary symbol: {b}")

    n_bits = len(bit_seq)
    if n_bits == 0:
        return "" if is_str else []

    if n_bits % 2 != 0:
        raise ValueError(f"Rate 1/2 Viterbi decoding requires an even number of bits, got {n_bits}.")

    num_steps = n_bits // 2
    INF = 99999999

    # State metrics (4 states for K=3)
    path_metrics = [0 if s == 0 else INF for s in range(4)]
    traceback = []

    for t in range(num_steps):
        r1 = bit_seq[2 * t]
        r2 = bit_seq[2 * t + 1]

        next_path_metrics = [INF] * 4
        step_traceback = {}

        for state in range(4):
            if path_metrics[state] == INF:
                continue

            for u in (0, 1):
                (v1, v2), next_state = _get_encoder_output_and_next_state(state, u)
                # Hamming distance branch metric
                dist = (0 if r1 == v1 else 1) + (0 if r2 == v2 else 1)
                metric = path_metrics[state] + dist

                if metric < next_path_metrics[next_state]:
                    next_path_metrics[next_state] = metric
                    step_traceback[next_state] = (state, u)

        path_metrics = next_path_metrics
        traceback.append(step_traceback)

    # Traceback: Select final state with minimum path metric (prefer state 0 if tied)
    best_state = 0
    min_metric = path_metrics[0]
    for s in range(1, 4):
        if path_metrics[s] < min_metric:
            min_metric = path_metrics[s]
            best_state = s

    curr_state = best_state
    decoded_reversed = []

    for t in range(num_steps - 1, -1, -1):
        if curr_state not in traceback[t]:
            break
        prev_state, u = traceback[t][curr_state]
        decoded_reversed.append(u)
        curr_state = prev_state

    decoded_bits = list(reversed(decoded_reversed))

    if trim_flush and len(decoded_bits) >= 2:
        decoded_bits = decoded_bits[:-2]

    return "".join(str(x) for x in decoded_bits) if is_str else decoded_bits


DEFAULT_FEC_CANDIDATES = [
    {
        "fec_type": "CONVOLUTIONAL",
        "rate": "1/2",
        "constraint_length": 3,
        "g1_octal": 7,
        "g2_octal": 5,
        "description": "Standard Rate 1/2 K=3 Convolutional Code (7, 5 octal)"
    }
]


def try_viterbi_decoders(
    bits: str,
    candidates: Optional[List[Dict[str, Any]]] = None,
    ground_truth: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evaluates candidate Viterbi FEC decoders on a received bitstream.
    If ground_truth is provided (for test verification), measures Bit Error Rate (BER).
    """
    if candidates is None:
        candidates = DEFAULT_FEC_CANDIDATES

    n_bits = len(bits)
    results = []

    for cand in candidates:
        k = cand.get("constraint_length", 3)
        g1 = cand.get("g1_octal", 7)
        g2 = cand.get("g2_octal", 5)

        if n_bits == 0 or n_bits % 2 != 0:
            results.append({
                "fec_type": cand.get("fec_type", "CONVOLUTIONAL"),
                "rate": "1/2",
                "constraint_length": k,
                "g1_octal": g1,
                "g2_octal": g2,
                "compatible": False,
                "reason": f"Input bit length {n_bits} is not even (required for Rate 1/2).",
                "status": "INCOMPATIBLE",
                "decoded_bits": "",
                "ber": None
            })
            continue

        try:
            decoded_bits = viterbi_decode(bits, k=k, g1=g1, g2=g2, trim_flush=True)
            ber = None
            status = "DECODED"

            if ground_truth:
                comp_len = min(len(decoded_bits), len(ground_truth))
                if comp_len > 0:
                    err_count = sum(1 for i in range(comp_len) if decoded_bits[i] != ground_truth[i])
                    ber = round(err_count / comp_len, 4)
                    if ber == 0.0:
                        status = "VALIDATED"

            results.append({
                "fec_type": cand.get("fec_type", "CONVOLUTIONAL"),
                "rate": "1/2",
                "constraint_length": k,
                "g1_octal": g1,
                "g2_octal": g2,
                "compatible": True,
                "status": status,
                "decoded_bits": decoded_bits,
                "bits_preview": decoded_bits[:128],
                "ber": ber
            })
        except Exception as e:
            results.append({
                "fec_type": cand.get("fec_type", "CONVOLUTIONAL"),
                "rate": "1/2",
                "constraint_length": k,
                "g1_octal": g1,
                "g2_octal": g2,
                "compatible": False,
                "reason": str(e),
                "status": "ERROR",
                "decoded_bits": "",
                "ber": None
            })

    selected = None
    for r_item in results:
        if r_item.get("status") == "VALIDATED":
            selected = r_item
            break

    if selected is None:
        for r_item in results:
            if r_item.get("compatible"):
                selected = r_item
                break

    if selected is None and results:
        selected = results[0]

    return {
        "fec_type": selected["fec_type"] if selected else "CONVOLUTIONAL",
        "rate": "1/2",
        "constraint_length": selected["constraint_length"] if selected else 3,
        "generator_polynomials": "G1=7, G2=5 (octal)",
        "input_bit_count": n_bits,
        "output_bit_count": len(selected["decoded_bits"]) if selected else 0,
        "selected_configuration": {
            "rate": "1/2",
            "constraint_length": selected["constraint_length"] if selected else 3,
            "g1_octal": selected["g1_octal"] if selected else 7,
            "g2_octal": selected["g2_octal"] if selected else 5,
            "status": selected["status"] if selected else "NO_COMPATIBLE_CANDIDATE"
        },
        "decoded_bits": selected["decoded_bits"] if selected else "",
        "bits_preview": selected.get("bits_preview", "") if selected else "",
        "candidates": results,
        "method": "Hard-Decision Viterbi Trellis Decoding (Rate 1/2, K=3, Generators 7, 5 octal)"
    }


# ---------------------------------------------------------------------------
# Part 10B — Reed-Solomon FEC
# ---------------------------------------------------------------------------

def reed_solomon_encode(
    data: Union[str, bytes, List[int]],
    n: int = 255,
    k: int = 223
) -> Union[str, bytes]:
    """
    Encodes binary payload data using Reed-Solomon RS(n, k) over GF(2^8).
    Default: n=255, k=223, parity_symbols=32.

    Parameters:
    - data: Payload data as a binary bitstream string ('0'/'1'), bytes, or list of byte ints.
    - n: Total codeword length in symbols/bytes (default 255).
    - k: Information/payload length in symbols/bytes (default 223).
    """
    nsym = n - k
    if nsym <= 0 or nsym > 254:
        raise ValueError(f"Invalid RS parameters: n={n}, k={k}. Parity symbols n-k must be in 1..254.")

    rsc = RSCodec(nsym)
    is_str = isinstance(data, str)

    if is_str:
        payload_bytes = bits_to_bytes(data)
    elif isinstance(data, (bytes, bytearray)):
        payload_bytes = bytes(data)
    elif isinstance(data, list):
        payload_bytes = bytes(data)
    else:
        raise ValueError("Input data must be str (bits), bytes, or list of byte ints.")

    num_blocks = (len(payload_bytes) + k - 1) // k if len(payload_bytes) > 0 else 0
    if num_blocks == 0:
        return "" if is_str else b""

    encoded_chunks = []
    for b in range(num_blocks):
        chunk = payload_bytes[b * k : (b + 1) * k]
        encoded_chunk = rsc.encode(chunk)
        encoded_chunks.append(encoded_chunk)

    encoded_bytes = b"".join(encoded_chunks)
    return bytes_to_bits(encoded_bytes) if is_str else encoded_bytes


def reed_solomon_decode(
    encoded_data: Union[str, bytes],
    n: int = 255,
    k: int = 223
) -> Tuple[Union[str, bytes], Dict[str, Any]]:
    """
    Decodes Reed-Solomon RS(n, k) codeword(s) over GF(2^8).

    Returns:
    - decoded_data: Decoded data as binary string or bytes.
    - info: Dictionary with corrected_symbol_count, status, input_byte_count, output_byte_count.
    """
    nsym = n - k
    if nsym <= 0 or nsym > 254:
        raise ValueError(f"Invalid RS parameters: n={n}, k={k}.")

    rsc = RSCodec(nsym)
    is_str = isinstance(encoded_data, str)

    if is_str:
        codeword_bytes = bits_to_bytes(encoded_data)
    else:
        codeword_bytes = bytes(encoded_data)

    total_len = len(codeword_bytes)
    if total_len == 0:
        return ("" if is_str else b""), {"corrected_symbol_count": 0, "status": "DECODED", "input_byte_count": 0, "output_byte_count": 0}

    block_size = n if (total_len % n == 0 and total_len >= n) else total_len
    num_blocks = (total_len + block_size - 1) // block_size if block_size > 0 else 1

    decoded_chunks = []
    total_corrected = 0

    for b in range(num_blocks):
        chunk = codeword_bytes[b * block_size : (b + 1) * block_size]
        try:
            dec_data, dec_full, err_pos = rsc.decode(chunk)
            decoded_chunks.append(dec_data)
            total_corrected += len(err_pos)
        except ReedSolomonError as rse:
            raise ValueError(f"Reed-Solomon decoding failed (too many symbol errors): {str(rse)}")

    decoded_bytes = b"".join(decoded_chunks)
    info = {
        "corrected_symbol_count": total_corrected,
        "input_byte_count": total_len,
        "output_byte_count": len(decoded_bytes),
        "status": "DECODED"
    }

    res_data = bytes_to_bits(decoded_bytes) if is_str else decoded_bytes
    return res_data, info


DEFAULT_RS_CANDIDATES = [
    {
        "fec_type": "REED_SOLOMON",
        "field_size": 8,
        "n": 255,
        "k": 223,
        "parity_symbols": 32,
        "correctable_symbol_errors": 16,
        "description": "Standard Reed-Solomon RS(255,223) Candidate over GF(2^8)"
    }
]


def try_reed_solomon_decoders(
    bits: str,
    candidates: Optional[List[Dict[str, Any]]] = None,
    ground_truth: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evaluates candidate Reed-Solomon FEC decoders on a received bitstream.
    If ground_truth is provided (for test verification), measures Bit Error Rate (BER).
    """
    if candidates is None:
        candidates = DEFAULT_RS_CANDIDATES

    n_bits = len(bits)
    results = []

    for cand in candidates:
        n = cand.get("n", 255)
        k = cand.get("k", 223)

        if n_bits == 0 or n_bits % 8 != 0:
            results.append({
                "fec_type": cand.get("fec_type", "REED_SOLOMON"),
                "field_size": 8,
                "n": n,
                "k": k,
                "parity_symbols": n - k,
                "compatible": False,
                "reason": f"Input bit length {n_bits} is not a multiple of 8 bits (byte-aligned).",
                "status": "INCOMPATIBLE",
                "decoded_bits": "",
                "corrected_symbol_count": 0,
                "ber": None
            })
            continue

        try:
            decoded_bits, info = reed_solomon_decode(bits, n=n, k=k)
            ber = None
            status = info.get("status", "DECODED")

            if ground_truth:
                comp_len = min(len(decoded_bits), len(ground_truth))
                if comp_len > 0:
                    err_count = sum(1 for i in range(comp_len) if decoded_bits[i] != ground_truth[i])
                    ber = round(err_count / comp_len, 4)
                    if ber == 0.0:
                        status = "VALIDATED"

            results.append({
                "fec_type": cand.get("fec_type", "REED_SOLOMON"),
                "field_size": 8,
                "n": n,
                "k": k,
                "parity_symbols": n - k,
                "compatible": True,
                "status": status,
                "decoded_bits": decoded_bits,
                "bits_preview": decoded_bits[:128],
                "corrected_symbol_count": info.get("corrected_symbol_count", 0),
                "ber": ber
            })
        except Exception as e:
            results.append({
                "fec_type": cand.get("fec_type", "REED_SOLOMON"),
                "field_size": 8,
                "n": n,
                "k": k,
                "parity_symbols": n - k,
                "compatible": False,
                "reason": str(e),
                "status": "FAILED",
                "decoded_bits": "",
                "corrected_symbol_count": 0,
                "ber": None
            })

    selected = None
    for r_item in results:
        if r_item.get("status") == "VALIDATED":
            selected = r_item
            break

    if selected is None:
        for r_item in results:
            if r_item.get("compatible"):
                selected = r_item
                break

    if selected is None and results:
        selected = results[0]

    return {
        "fec_type": selected["fec_type"] if selected else "REED_SOLOMON",
        "field_size": 8,
        "n": selected["n"] if selected else 255,
        "k": selected["k"] if selected else 223,
        "parity_symbols": selected["parity_symbols"] if selected else 32,
        "correctable_symbol_errors": 16,
        "input_bit_count": n_bits,
        "input_byte_count": n_bits // 8,
        "output_byte_count": len(selected["decoded_bits"]) // 8 if selected else 0,
        "output_bit_count": len(selected["decoded_bits"]) if selected else 0,
        "selected_configuration": {
            "n": selected["n"] if selected else 255,
            "k": selected["k"] if selected else 223,
            "parity_symbols": selected["parity_symbols"] if selected else 32,
            "status": selected["status"] if selected else "NO_COMPATIBLE_CANDIDATE"
        },
        "decoded_bits": selected["decoded_bits"] if selected else "",
        "bits_preview": selected.get("bits_preview", "") if selected else "",
        "corrected_symbol_count": selected.get("corrected_symbol_count", 0) if selected else 0,
        "candidates": results,
        "method": "Reed-Solomon RS(255,223) Candidate Decoding over GF(2^8)"
    }

