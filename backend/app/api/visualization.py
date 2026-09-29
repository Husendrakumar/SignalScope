from fastapi import APIRouter, HTTPException, Query
from app.signal_processing.session_manager import session_store
from app.signal_processing.visualization import (
    compute_waveform,
    compute_spectrum,
    compute_spectrogram,
    compute_constellation
)

router = APIRouter(prefix="/api/visualization", tags=["Visualization"])


@router.get("/waveform/{signal_id}")
async def get_waveform(
    signal_id: str,
    max_points: int = Query(default=1000, ge=100, le=10000),
    dom_freq: float = Query(default=0.0)
):
    signal = session_store.get_session(signal_id)
    if not signal:
        raise HTTPException(
            status_code=404,
            detail="Signal session not found or expired. Please upload the signal file again."
        )

    try:
        return compute_waveform(signal, max_points=max_points, dom_freq=dom_freq)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing waveform: {str(e)}")


@router.get("/spectrum/{signal_id}")
async def get_spectrum(
    signal_id: str,
    nfft: int = Query(default=2048, ge=256, le=8192)
):
    signal = session_store.get_session(signal_id)
    if not signal:
        raise HTTPException(
            status_code=404,
            detail="Signal session not found or expired. Please upload the signal file again."
        )

    try:
        return compute_spectrum(signal, nfft=nfft)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing FFT spectrum: {str(e)}")


@router.get("/spectrogram/{signal_id}")
async def get_spectrogram(
    signal_id: str,
    nfft: int = Query(default=512, ge=128, le=2048),
    hop_length: int = Query(default=256, ge=64, le=1024)
):
    signal = session_store.get_session(signal_id)
    if not signal:
        raise HTTPException(
            status_code=404,
            detail="Signal session not found or expired. Please upload the signal file again."
        )

    try:
        return compute_spectrogram(signal, nfft=nfft, hop_length=hop_length)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing spectrogram: {str(e)}")


@router.get("/constellation/{signal_id}")
async def get_constellation(
    signal_id: str,
    max_points: int = Query(default=1000, ge=100, le=5000)
):
    signal = session_store.get_session(signal_id)
    if not signal:
        raise HTTPException(
            status_code=404,
            detail="Signal session not found or expired. Please upload the signal file again."
        )

    try:
        return compute_constellation(signal, max_points=max_points)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing constellation: {str(e)}")
