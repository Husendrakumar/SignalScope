import os
from fastapi import HTTPException

ALLOWED_EXTENSIONS = {"wav", "iq"}


def validate_file_extension(filename: str) -> str:
    """
    Validates file extension case-insensitively.
    Returns normalized lowercase extension without leading dot (e.g. 'wav' or 'iq').
    Raises HTTP 400 exception if unsupported.
    """
    if not filename:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Only .WAV and .IQ files are supported."
        )

    parts = filename.split(".")
    ext = parts[-1].lower() if len(parts) > 1 else ""

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Only .WAV and .IQ files are supported."
        )

    return ext


def sanitize_filename(filename: str) -> str:
    """
    Strips directory paths to prevent path traversal vulnerability.
    """
    if not filename:
        return "unnamed_file"
    return os.path.basename(filename)
