from fastapi import APIRouter, HTTPException
from app.signal_processing.session_manager import session_store
from app.signal_processing.modulation import classify_signal_modulation

router = APIRouter(prefix="/api/modulation", tags=["Modulation"])


@router.get("/{signal_id}")
async def get_signal_modulation(signal_id: str):
    """
    Classifies signal modulation type for an active signal session.
    Returns modulation type (FSK, PSK, QAM, UNKNOWN), confidence score,
    evidence explanations, and extracted physical features.
    """
    signal = session_store.get_session(signal_id)
    if not signal:
        raise HTTPException(
            status_code=404,
            detail="Signal session not found or expired. Please upload the signal file again."
        )

    try:
        return classify_signal_modulation(signal, signal_id=signal_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error performing modulation classification: {str(e)}")
