"""
Deterministic Block and Convolutional De-Interleaving Module for SignalScope (Part 9A & 9B).

Restores the original bit ordering from interleaved binary bitstreams using:
1. Rectangular Block Matrix Interleaving / De-interleaving (Part 9A)
2. Ramsey/Forney Shift-Register Convolutional Interleaving / De-interleaving (Part 9B)

Matrix Convention (Block):
- Interleaving: Write bitstream into matrix R (rows) x C (cols) row-by-row, read out column-by-column.
- De-interleaving: Write bitstream into matrix R (rows) x C (cols) column-by-column, read out row-by-row.

Shift-Register Convention (Convolutional):
- Interleaving: B parallel branches, branch i delay = i * D (where D = delay_step).
  Input bit stream enters commutator cycling 0..B-1.
- De-interleaving: B parallel branches, branch i delay = (B - 1 - i) * D.
  Total latency across cascade per branch = (B - 1) * D * B bits.
- Flushing & Startup:
  - Interleaver appends L = (B-1)*D*B zero flush bits so all payload bits pass through.
  - De-interleaver trims the initial L pipeline startup delay zero bits.

Mathematical Proof of Inverse:
  block_deinterleave(block_interleave(bits, R, C), R, C) == bits
  convolutional_deinterleave(convolutional_interleave(bits, B, D, flush=True), B, D, trim_flush=True) == bits
"""

from typing import List, Dict, Any, Optional, Union
from collections import deque
import numpy as np


def block_interleave(bits: Union[str, List[int]], rows: int, cols: int) -> Union[str, List[int]]:
    """
    Interleaves a binary bitstream using an R x C rectangular matrix.
    Writes row-by-row, reads column-by-column.
    """
    if rows <= 0 or cols <= 0:
        raise ValueError(f"Matrix dimensions must be positive, got {rows}x{cols}.")

    block_size = rows * cols
    is_str = isinstance(bits, str)
    bit_seq = [int(b) for b in bits] if is_str else list(bits)

    for b in bit_seq:
        if b not in (0, 1):
            raise ValueError(f"Input bitstream contains non-binary symbol: {b}")

    n_bits = len(bit_seq)
    if n_bits == 0:
        return "" if is_str else []

    if n_bits % block_size != 0:
        raise ValueError(
            f"Bitstream length ({n_bits}) is not a multiple of block size ({rows}x{cols}={block_size})."
        )

    output = []
    num_blocks = n_bits // block_size

    for b in range(num_blocks):
        block = bit_seq[b * block_size : (b + 1) * block_size]
        # Reshape into (rows, cols)
        matrix = [block[r * cols : (r + 1) * cols] for r in range(rows)]
        # Read column-by-column
        for c in range(cols):
            for r in range(rows):
                output.append(matrix[r][c])

    return "".join(str(x) for x in output) if is_str else output


def block_deinterleave(bits: Union[str, List[int]], rows: int, cols: int) -> Union[str, List[int]]:
    """
    De-interleaves a binary bitstream using an R x C rectangular matrix.
    Writes column-by-column, reads row-by-row.
    Mathematically exact inverse of block_interleave.
    """
    if rows <= 0 or cols <= 0:
        raise ValueError(f"Matrix dimensions must be positive, got {rows}x{cols}.")

    block_size = rows * cols
    is_str = isinstance(bits, str)
    bit_seq = [int(b) for b in bits] if is_str else list(bits)

    for b in bit_seq:
        if b not in (0, 1):
            raise ValueError(f"Input bitstream contains non-binary symbol: {b}")

    n_bits = len(bit_seq)
    if n_bits == 0:
        return "" if is_str else []

    if n_bits % block_size != 0:
        raise ValueError(
            f"Bitstream length ({n_bits}) is not a multiple of block size ({rows}x{cols}={block_size})."
        )

    output = []
    num_blocks = n_bits // block_size

    for b in range(num_blocks):
        block = bit_seq[b * block_size : (b + 1) * block_size]
        # Fill matrix (rows, cols) column-by-column
        matrix = [[None for _ in range(cols)] for _ in range(rows)]
        idx = 0
        for c in range(cols):
            for r in range(rows):
                matrix[r][c] = block[idx]
                idx += 1

        # Read row-by-row
        for r in range(rows):
            for c in range(cols):
                output.append(matrix[r][c])

    return "".join(str(x) for x in output) if is_str else output


DEFAULT_CANDIDATES = [
    {"rows": 4, "cols": 4},
    {"rows": 4, "cols": 8},
    {"rows": 8, "cols": 8},
    {"rows": 16, "cols": 16},
]


def try_block_deinterleavers(
    bits: str,
    candidates: Optional[List[Dict[str, int]]] = None,
    ground_truth: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evaluates candidate block de-interleaver configurations on a bitstream.
    If ground_truth is provided (for test verification), measures Bit Error Rate (BER).
    """
    if candidates is None:
        candidates = DEFAULT_CANDIDATES

    n_bits = len(bits)
    results = []

    for cand in candidates:
        r, c = cand["rows"], cand["cols"]
        bsize = r * c

        if n_bits == 0 or n_bits % bsize != 0:
            results.append({
                "rows": r,
                "cols": c,
                "compatible": False,
                "reason": f"Bit length {n_bits} not divisible by block size {bsize}",
                "status": "INCOMPATIBLE",
                "deinterleaved_bits": "",
                "ber": None
            })
            continue

        try:
            deint_bits = block_deinterleave(bits, r, c)
            ber = None
            status = "CANDIDATE_TESTED"

            if ground_truth:
                comp_len = min(len(deint_bits), len(ground_truth))
                if comp_len > 0:
                    err_count = sum(1 for i in range(comp_len) if deint_bits[i] != ground_truth[i])
                    ber = round(err_count / comp_len, 4)
                    if ber == 0.0:
                        status = "VALIDATED"

            results.append({
                "rows": r,
                "cols": c,
                "block_size": bsize,
                "compatible": True,
                "status": status,
                "deinterleaved_bits": deint_bits,
                "bits_preview": deint_bits[:128],
                "ber": ber
            })
        except Exception as e:
            results.append({
                "rows": r,
                "cols": c,
                "compatible": False,
                "reason": str(e),
                "status": "ERROR",
                "deinterleaved_bits": "",
                "ber": None
            })

    # Pick best candidate if validated, else default to first compatible
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
        "input_bit_count": n_bits,
        "selected_configuration": {
            "rows": selected["rows"] if selected else 8,
            "cols": selected["cols"] if selected else 8,
            "status": selected["status"] if selected else "NO_COMPATIBLE_CANDIDATE"
        },
        "deinterleaved_bits": selected["deinterleaved_bits"] if selected else "",
        "bits_preview": selected.get("bits_preview", "") if selected else "",
        "output_bit_count": len(selected["deinterleaved_bits"]) if selected else 0,
        "candidates": results,
        "method": "Rectangular Block De-interleaving (Matrix Column-to-Row Mapping)"
    }


# ---------------------------------------------------------------------------
# Part 9B — Convolutional Interleaving & De-interleaving
# ---------------------------------------------------------------------------

def convolutional_interleave(
    bits: Union[str, List[int]],
    branches: int = 4,
    delay_step: int = 1,
    flush: bool = True
) -> Union[str, List[int]]:
    """
    Interleaves a binary bitstream using a Ramsey/Forney shift-register convolutional interleaver.

    Parameters:
    - bits: Input binary sequence (string of '0'/'1' or list of 0/1 integers).
    - branches: Number of parallel shift-register branches B > 0.
    - delay_step: Delay step spacing D >= 0 (branch i register length = i * D).
    - flush: If True, appends L = (branches-1)*delay_step*branches zero flush bits to push all payload bits out.
    """
    if branches <= 0:
        raise ValueError(f"Branch count must be positive (branches > 0), got {branches}.")
    if delay_step < 0:
        raise ValueError(f"Delay step must be non-negative (delay_step >= 0), got {delay_step}.")

    is_str = isinstance(bits, str)
    bit_seq = [int(b) for b in bits] if is_str else list(bits)

    for b in bit_seq:
        if b not in (0, 1):
            raise ValueError(f"Input bitstream contains non-binary symbol: {b}")

    n_bits = len(bit_seq)
    if n_bits == 0:
        return "" if is_str else []

    latency = (branches - 1) * delay_step * branches
    input_data = bit_seq + [0] * (latency if flush else 0)

    registers = [
        deque([0] * (i * delay_step)) for i in range(branches)
    ]

    output = []
    for k, b_in in enumerate(input_data):
        branch_idx = k % branches
        reg = registers[branch_idx]
        reg_len = branch_idx * delay_step

        if reg_len == 0:
            output.append(b_in)
        else:
            b_out = reg.popleft()
            reg.append(b_in)
            output.append(b_out)

    return "".join(str(x) for x in output) if is_str else output


def convolutional_deinterleave(
    bits: Union[str, List[int]],
    branches: int = 4,
    delay_step: int = 1,
    trim_flush: bool = True
) -> Union[str, List[int]]:
    """
    De-interleaves a binary bitstream using a Ramsey/Forney shift-register convolutional de-interleaver.

    Parameters:
    - bits: Interleaved binary sequence.
    - branches: Number of parallel shift-register branches B > 0.
    - delay_step: Delay step spacing D >= 0 (branch i register length = (B - 1 - i) * D).
    - trim_flush: If True, trims the initial L = (branches-1)*delay_step*branches pipeline startup delay zero bits.
    """
    if branches <= 0:
        raise ValueError(f"Branch count must be positive (branches > 0), got {branches}.")
    if delay_step < 0:
        raise ValueError(f"Delay step must be non-negative (delay_step >= 0), got {delay_step}.")

    is_str = isinstance(bits, str)
    bit_seq = [int(b) for b in bits] if is_str else list(bits)

    for b in bit_seq:
        if b not in (0, 1):
            raise ValueError(f"Input bitstream contains non-binary symbol: {b}")

    n_bits = len(bit_seq)
    if n_bits == 0:
        return "" if is_str else []

    latency = (branches - 1) * delay_step * branches

    registers = [
        deque([0] * ((branches - 1 - i) * delay_step))
        for i in range(branches)
    ]

    output = []
    for k, b_in in enumerate(bit_seq):
        branch_idx = k % branches
        reg = registers[branch_idx]
        reg_len = (branches - 1 - branch_idx) * delay_step

        if reg_len == 0:
            output.append(b_in)
        else:
            b_out = reg.popleft()
            reg.append(b_in)
            output.append(b_out)

    if trim_flush and len(output) >= latency:
        output = output[latency:]

    return "".join(str(x) for x in output) if is_str else output


DEFAULT_CONV_CANDIDATES = [
    {"branches": 3, "delay_step": 1},
    {"branches": 4, "delay_step": 1},
    {"branches": 4, "delay_step": 2},
    {"branches": 5, "delay_step": 1},
]


def try_convolutional_deinterleavers(
    bits: str,
    candidates: Optional[List[Dict[str, int]]] = None,
    ground_truth: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evaluates candidate convolutional de-interleaver configurations on a bitstream.
    If ground_truth is provided (for test verification), measures Bit Error Rate (BER).
    """
    if candidates is None:
        candidates = DEFAULT_CONV_CANDIDATES

    n_bits = len(bits)
    results = []

    for cand in candidates:
        b, d = cand["branches"], cand["delay_step"]
        latency = (b - 1) * d * b

        if n_bits <= latency:
            results.append({
                "branches": b,
                "delay_step": d,
                "pipeline_latency": latency,
                "compatible": False,
                "reason": f"Bit length {n_bits} is smaller than pipeline latency {latency}",
                "status": "INCOMPATIBLE",
                "deinterleaved_bits": "",
                "ber": None
            })
            continue

        try:
            deint_bits = convolutional_deinterleave(bits, branches=b, delay_step=d, trim_flush=True)
            ber = None
            status = "CANDIDATE_TESTED"

            if ground_truth:
                comp_len = min(len(deint_bits), len(ground_truth))
                if comp_len > 0:
                    err_count = sum(1 for i in range(comp_len) if deint_bits[i] != ground_truth[i])
                    ber = round(err_count / comp_len, 4)
                    if ber == 0.0:
                        status = "VALIDATED"

            results.append({
                "branches": b,
                "delay_step": d,
                "pipeline_latency": latency,
                "compatible": True,
                "status": status,
                "deinterleaved_bits": deint_bits,
                "bits_preview": deint_bits[:128],
                "ber": ber
            })
        except Exception as e:
            results.append({
                "branches": b,
                "delay_step": d,
                "pipeline_latency": latency,
                "compatible": False,
                "reason": str(e),
                "status": "ERROR",
                "deinterleaved_bits": "",
                "ber": None
            })

    # Pick best candidate if validated, else first compatible candidate
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
        "input_bit_count": n_bits,
        "selected_configuration": {
            "branches": selected["branches"] if selected else 4,
            "delay_step": selected["delay_step"] if selected else 1,
            "pipeline_latency": selected["pipeline_latency"] if selected else 12,
            "status": selected["status"] if selected else "NO_COMPATIBLE_CANDIDATE"
        },
        "deinterleaved_bits": selected["deinterleaved_bits"] if selected else "",
        "bits_preview": selected.get("bits_preview", "") if selected else "",
        "output_bit_count": len(selected["deinterleaved_bits"]) if selected else 0,
        "startup_flush_convention": "Flushed L=(B-1)*D*B zero tail bits during interleaving; trimmed initial L pipeline startup delay zeros during de-interleaving.",
        "candidates": results,
        "method": "Convolutional Shift-Register De-interleaving (Ramsey/Forney Branch Delays)"
    }

