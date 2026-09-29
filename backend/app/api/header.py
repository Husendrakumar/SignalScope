"""
Header & Synchronization Detection API Router for SignalScope (Part 11).
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.signal_processing.session_manager import session_store
from app.signal_processing.demodulation import demodulate_fsk
from app.signal_processing.header import detect_header, DEFAULT_SYNC_PATTERN

router = APIRouter(prefix="/api/header", tags=["Header & Synchronization"])


@router.post("/detect/{signal_id}")
@router.get("/detect/{signal_id}")
async def get_header_detection(
    signal_id: str,
    sync_pattern: Optional[str] = Query(default=DEFAULT_SYNC_PATTERN, description="32-bit binary sync pattern to match"),
    max_errors: Optional[int] = Query(default=2, ge=0, le=8, description="Maximum allowed bit errors (Hamming distance)")
):
    """
    Executes synchronization word search, synthetic header parsing, CRC validation,
    and frame/payload boundary identification on demodulated signal bitstream.
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
            detail=f"Header detection requires a demodulated bitstream. Demodulation failed: {str(ve)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error performing demodulation prior to header detection: {str(e)}"
        )

    bits = demod_result.get("bits", "")
    if not bits:
        raise HTTPException(
            status_code=400,
            detail="Demodulated bitstream is empty. Cannot perform header detection."
        )

    # 2. Perform synchronization and header detection
    try:
        res = detect_header(bits, sync_pattern=sync_pattern, max_errors=max_errors)
        res["signal_id"] = signal_id
        return res
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to execute header detection: {str(e)}"
        )
