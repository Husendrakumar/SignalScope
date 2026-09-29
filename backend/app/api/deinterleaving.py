from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.signal_processing.session_manager import session_store
from app.signal_processing.demodulation import demodulate_fsk
from app.signal_processing.deinterleaving import try_block_deinterleavers, try_convolutional_deinterleavers

router = APIRouter(prefix="/api/deinterleaving", tags=["De-interleaving"])


@router.post("/block/{signal_id}")
@router.get("/block/{signal_id}")
async def get_block_deinterleaving(
    signal_id: str,
    rows: Optional[int] = Query(default=8, ge=1, le=128),
    cols: Optional[int] = Query(default=8, ge=1, le=128)
):
    """
    Executes rectangular block de-interleaving on demodulated signal bitstream.
    Returns input bit count, selected matrix configuration (rows x cols),
    de-interleaved bitstream preview, candidate configurations, and method details.
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
            detail=f"De-interleaving requires a demodulated bitstream. Demodulation failed: {str(ve)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error performing demodulation prior to de-interleaving: {str(e)}"
        )

    bits = demod_result.get("bits", "")
    if not bits:
        raise HTTPException(
            status_code=400,
            detail="Demodulated bitstream is empty. Cannot perform block de-interleaving."
        )

    # 2. Evaluate candidate block configurations (prioritizing requested rows x cols)
    candidates = [
        {"rows": rows, "cols": cols},
        {"rows": 4, "cols": 4},
        {"rows": 4, "cols": 8},
        {"rows": 8, "cols": 8},
        {"rows": 16, "cols": 16},
    ]

    analysis_res = try_block_deinterleavers(bits, candidates=candidates)
    analysis_res["signal_id"] = signal_id
    analysis_res["format"] = signal.format

    return analysis_res


@router.post("/convolutional/{signal_id}")
@router.get("/convolutional/{signal_id}")
async def get_convolutional_deinterleaving(
    signal_id: str,
    branches: Optional[int] = Query(default=4, ge=1, le=32),
    delay_step: Optional[int] = Query(default=1, ge=0, le=32)
):
    """
    Executes convolutional shift-register de-interleaving on demodulated signal bitstream.
    Returns input bit count, selected configuration (branches & delay_step),
    de-interleaved bitstream preview, startup/flush details, candidates, and method details.
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
            detail=f"Convolutional de-interleaving requires a demodulated bitstream. Demodulation failed: {str(ve)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error performing demodulation prior to convolutional de-interleaving: {str(e)}"
        )

    bits = demod_result.get("bits", "")
    if not bits:
        raise HTTPException(
            status_code=400,
            detail="Demodulated bitstream is empty. Cannot perform convolutional de-interleaving."
        )

    # 2. Evaluate candidate convolutional configurations (prioritizing requested parameters)
    candidates = [
        {"branches": branches, "delay_step": delay_step},
        {"branches": 3, "delay_step": 1},
        {"branches": 4, "delay_step": 1},
        {"branches": 4, "delay_step": 2},
        {"branches": 5, "delay_step": 1},
    ]

    analysis_res = try_convolutional_deinterleavers(bits, candidates=candidates)
    analysis_res["signal_id"] = signal_id
    analysis_res["format"] = signal.format

    return analysis_res

