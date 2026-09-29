from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.files import router as files_router
from app.api.visualization import router as visualization_router
from app.api.analysis import router as analysis_router
from app.api.modulation import router as modulation_router
from app.api.demodulation import router as demodulation_router
from app.api.deinterleaving import router as deinterleaving_router
from app.api.fec import router as fec_router
from app.api.header import router as header_router
from app.api.payload import router as payload_router

app = FastAPI(
    title="SignalScope API",
    description="Backend API for the SignalScope automatic radio signal analysis system.",
    version="1.0.0"
)

# Configure CORS
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """
    Root endpoint returning system running message.
    """
    return {
        "message": "SignalScope API is running"
    }


# Include API Routers
app.include_router(health_router)
app.include_router(files_router)
app.include_router(visualization_router)
app.include_router(analysis_router)
app.include_router(modulation_router)
app.include_router(demodulation_router)
app.include_router(deinterleaving_router)
app.include_router(fec_router)
app.include_router(header_router)
app.include_router(payload_router)

