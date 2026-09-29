from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["Health"])


@router.get("/health")
async def health_check():
    """
    Health check endpoint to verify backend status.
    """
    return {
        "status": "ok",
        "service": "signalscope-backend"
    }
