from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.signal_processing.session_manager import session_store
from app.signal_processing.demodulation import demodulate_fsk
from app.signal_processing.fec import try_viterbi_decoders, try_reed_solomon_decoders

router = APIRouter(prefix="/api/fec", tags=["Forward Error Correction"])


@router.post("/viterbi/{signal_id}")
@router.get("/viterbi/{signal_id}")
async def get_viterbi_fec_decoding(
    signal_id: str,
    constraint_length: Optional[int] = Query(default=3, ge=3, le=9),
    g1: Optional[int] = Query(default=7, ge=1, le=511),
    g2: Optional[int] = Query(default=5, ge=1, le=511)
):
    """
    Executes Hard-Decision Viterbi Trellis Decoding on demodulated signal bitstream.
    Returns input bit count, decoded payload bit count, FEC parameters, decoded payload preview,
    and method details.
    """
    signal = session_store.get_session(signal_id)
    if not signal:
        raise HTTPException(
            status_code=404,
            detail="Signal session not found or expired. Please upload the signal file again."
        )

    # 1. Obtain demodulated bitstream
    try:
        demod_result = demodulate_fsk(signal, signal_id=signal_id)
    except ValueError as ve:
        raise HTTPException(
            status_code=400,
            detail=f"FEC decoding requires a demodulated bitstream. Demodulation failed: {str(ve)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error performing demodulation prior to FEC decoding: {str(e)}"
        )

    bits = demod_result.get("bits", "")
    if not bits:
        raise HTTPException(
            status_code=400,
            detail="Demodulated bitstream is empty. Cannot perform Viterbi FEC decoding."
        )

    # 2. Evaluate candidate Viterbi decoders
    candidates = [
        {
            "fec_type": "CONVOLUTIONAL",
            "rate": "1/2",
            "constraint_length": constraint_length,
            "g1_octal": g1,
            "g2_octal": g2
        }
    ]

    analysis_res = try_viterbi_decoders(bits, candidates=candidates)
    analysis_res["signal_id"] = signal_id
    analysis_res["format"] = signal.format

    return analysis_res


@router.post("/reed-solomon/{signal_id}")
@router.get("/reed-solomon/{signal_id}")
async def get_reed_solomon_fec_decoding(
    signal_id: str,
    field_size: Optional[int] = Query(default=8, ge=8, le=8),
    n: Optional[int] = Query(default=255, ge=7, le=255),
    k: Optional[int] = Query(default=223, ge=1, le=253)
):
    """
    Executes Reed-Solomon Candidate Decoding over GF(2^8) on demodulated signal bitstream.
    Returns input bit/byte counts, output payload byte count, RS parameters, corrected symbol count,
    decoded payload preview, and method details.
    """
    signal = session_store.get_session(signal_id)
    if not signal:
        raise HTTPException(
            status_code=404,
            detail="Signal session not found or expired. Please upload the signal file again."
        )

    # 1. Obtain demodulated bitstream
    try:
        demod_result = demodulate_fsk(signal, signal_id=signal_id)
    except ValueError as ve:
        raise HTTPException(
            status_code=400,
            detail=f"Reed-Solomon FEC decoding requires a demodulated bitstream. Demodulation failed: {str(ve)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error performing demodulation prior to Reed-Solomon FEC decoding: {str(e)}"
        )

    bits = demod_result.get("bits", "")
    if not bits:
        raise HTTPException(
            status_code=400,
            detail="Demodulated bitstream is empty. Cannot perform Reed-Solomon FEC decoding."
        )

    # 2. Evaluate candidate Reed-Solomon decoders
    candidates = [
        {
            "fec_type": "REED_SOLOMON",
            "field_size": field_size,
            "n": n,
            "k": k,
            "parity_symbols": n - k,
            "correctable_symbol_errors": (n - k) // 2
        }
    ]

    analysis_res = try_reed_solomon_decoders(bits, candidates=candidates)
    analysis_res["signal_id"] = signal_id
    analysis_res["format"] = signal.format

    return analysis_res

