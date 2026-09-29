from fastapi import APIRouter, HTTPException
from app.signal_processing.session_manager import session_store
from app.signal_processing.analysis import analyze_signal

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])


@router.get("/{signal_id}")
async def get_signal_analysis(signal_id: str):
    """
    Executes automated signal analysis for an active signal session.
    Returns structured measurements including statistics, noise/SNR,
    dominant frequency, occupied bandwidth, and activity metrics.
    """
    signal = session_store.get_session(signal_id)
    if not signal:
        raise HTTPException(
            status_code=404,
            detail="Signal session not found or expired. Please upload the signal file again."
        )

    try:
        return analyze_signal(signal, signal_id=signal_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error performing signal analysis: {str(e)}")
