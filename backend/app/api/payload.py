"""
Final Data / Payload Extraction API Router for SignalScope (Part 12).
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.signal_processing.session_manager import session_store
from app.signal_processing.demodulation import demodulate_fsk
from app.signal_processing.header import detect_header, DEFAULT_SYNC_PATTERN
from app.signal_processing.payload import extract_and_analyze_payload

router = APIRouter(prefix="/api/payload", tags=["Payload Recovery"])


@router.post("/extract/{signal_id}")
@router.get("/extract/{signal_id}")
async def get_payload_extraction(
    signal_id: str,
    sync_pattern: Optional[str] = Query(default=DEFAULT_SYNC_PATTERN, description="32-bit binary sync pattern to match"),
    max_errors: Optional[int] = Query(default=2, ge=0, le=8, description="Maximum allowed bit errors for sync pattern")
):
    """
    Executes complete end-to-end payload extraction on demodulated signal bitstream
    using validated Stage 07 header boundaries.
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
            detail=f"Payload extraction requires demodulated bitstream. Demodulation failed: {str(ve)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error performing demodulation prior to payload extraction: {str(e)}"
        )

    bits = demod_result.get("bits", "")
    if not bits:
        raise HTTPException(
            status_code=400,
            detail="Demodulated bitstream is empty. Cannot extract payload."
        )

    # 2. Perform Stage 07 Header Detection
    try:
        header_info = detect_header(bits, sync_pattern=sync_pattern, max_errors=max_errors)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to execute header detection prior to payload extraction: {str(e)}"
        )

    # 3. Perform Stage 08 Payload Extraction & Content Analysis
    try:
        res = extract_and_analyze_payload(bits, header_info)
        res["signal_id"] = signal_id
        return res
    except ValueError as ve:
        raise HTTPException(
            status_code=400,
            detail=f"Payload extraction error: {str(ve)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract payload: {str(e)}"
        )
