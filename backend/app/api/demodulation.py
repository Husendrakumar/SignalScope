from fastapi import APIRouter, HTTPException
from app.signal_processing.session_manager import session_store
from app.signal_processing.demodulation import demodulate_fsk

router = APIRouter(prefix="/api/demodulation", tags=["Demodulation"])


@router.post("/fsk/{signal_id}")
@router.get("/fsk/{signal_id}")
async def get_fsk_demodulation(signal_id: str):
    """
    Executes binary FSK demodulation for an active FSK signal session.
    Returns recovered bitstream, estimated FSK tone frequencies, estimated
    symbol rate, bit count, and uncertain symbol count.
    """
    signal = session_store.get_session(signal_id)
    if not signal:
        raise HTTPException(
            status_code=404,
            detail="Signal session not found or expired. Please upload the signal file again."
        )

    try:
        return demodulate_fsk(signal, signal_id=signal_id)
    except ValueError as ve:
        raise HTTPException(
            status_code=400,
            detail=f"FSK demodulation failed: {str(ve)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error performing FSK demodulation: {str(e)}"
        )
