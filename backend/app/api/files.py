import os
import shutil
import tempfile
import logging
from fastapi import APIRouter, File, UploadFile, HTTPException

from app.signal_processing.models import FileMetadataResponse
from app.signal_processing.session_manager import session_store
from app.signal_processing.signal_loader import load_signal
from app.utils.validation import validate_file_extension, sanitize_filename

logger = logging.getLogger("signalscope.files")
router = APIRouter(prefix="/api/files", tags=["Files"])


@router.post("/upload", response_model=FileMetadataResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    Processes uploaded signal files (.wav or .iq).
    Safely stores temporary file, invokes signal reader, registers session,
    and returns FileMetadataResponse schema with signal_id.

    The internal ``SignalData`` object always stores samples as
    ``np.complex64``, but the API response preserves the original
    ``data_type`` string (e.g. ``"float32"`` for WAV) so that the
    frontend contract is not broken.
    """
    raw_filename = file.filename or ""
    filename = sanitize_filename(raw_filename)
    ext = validate_file_extension(filename)

    # Create safe temporary file
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"signalscope_{os.urandom(8).hex()}_{filename}")

    try:
        # Save uploaded bytes to temp file safely
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Check for empty file
        if os.path.getsize(temp_path) == 0:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty."
            )

        # ---------------------------------------------------------------
        # Load signal through the unified reader.
        # load_signal() auto-detects WAV vs IQ from the temp file's name,
        # so we need the temp file to carry the correct extension.
        # Since the temp filename already ends with the original filename
        # (which includes the extension), this works transparently.
        # ---------------------------------------------------------------
        if ext == "wav":
            try:
                signal = load_signal(temp_path, filename=filename)
            except HTTPException:
                raise
            except ValueError as ve:
                logger.error(f"WAV reading error for {filename}: {str(ve)}")
                raise HTTPException(status_code=400, detail="Unable to read WAV file.")
            except Exception as e:
                logger.error(f"Unexpected error reading WAV file {filename}: {str(e)}")
                raise HTTPException(status_code=400, detail="Unable to read WAV file.")

        elif ext == "iq":
            try:
                signal = load_signal(temp_path, filename=filename)
            except HTTPException:
                raise
            except ValueError as ve:
                logger.error(f"IQ reading error for {filename}: {str(ve)}")
                raise HTTPException(
                    status_code=400,
                    detail="Unable to read IQ file. Expected interleaved float32 I/Q samples."
                )
            except Exception as e:
                logger.error(f"Unexpected error reading IQ file {filename}: {str(e)}")
                raise HTTPException(
                    status_code=400,
                    detail="Unable to read IQ file. Expected interleaved float32 I/Q samples."
                )

        # Register signal session in memory
        signal_id = session_store.create_session(signal, filename)

        return FileMetadataResponse(
            signal_id=signal_id,
            filename=filename,
            format=signal.format,
            sample_rate=signal.sample_rate,
            sample_count=signal.sample_count,
            duration_seconds=round(signal.duration, 4),
            data_type=signal.data_type,
            channels=signal.channels if signal.format == "WAV" else None
        )

    finally:
        # Clean up temporary file safely
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as clean_err:
                logger.warning(f"Failed to delete temp file {temp_path}: {str(clean_err)}")
