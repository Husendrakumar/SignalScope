from dataclasses import dataclass, field
from typing import Optional
import numpy as np
from pydantic import BaseModel


@dataclass
class SignalData:
    """
    Canonical internal signal representation for the SignalScope pipeline.

    All signal-processing modules downstream of the reader layer consume this
    object.  Regardless of the original file format (WAV or IQ), the ``samples``
    array is **always** stored as ``np.complex64``.

    Conversion rules
    ----------------
    * **WAV (real-valued)**:  Each real sample ``x`` becomes ``x + 0j``.
    * **IQ  (complex)**:      Interleaved float32 I/Q pairs are reconstructed
      as ``I + jQ`` and stored directly as ``complex64``.

    Fields
    ------
    samples : np.ndarray
        1-D NumPy array with ``dtype == np.complex64``.  This is the **only**
        representation later pipeline stages should use.
    sample_rate : int
        Samples per second (Hz).
    sample_count : int
        Total number of complex samples (``len(samples)``).
    duration : float
        Signal duration in seconds (``sample_count / sample_rate``).
    format : str
        Original file format identifier: ``"WAV"`` or ``"IQ"``.
    data_type : str
        Original *source* data type string (e.g. ``"float32"`` for WAV,
        ``"complex64"`` for IQ).  Preserved for API reporting so that
        frontend consumers see the format they expect.  **Not** necessarily
        the dtype of ``samples`` (which is always ``complex64``).
    channels : int
        Number of channels in the *original* file (relevant for WAV).
        Multi-channel files are mixed down to mono before complex conversion.
    filename : str
        Original filename as provided by the uploader.
    """
    samples: np.ndarray
    sample_rate: int
    sample_count: int
    duration: float
    format: str        # "WAV" or "IQ"
    data_type: str     # original source dtype string for API reporting
    channels: int = 1
    filename: str = ""


class FileMetadataResponse(BaseModel):
    """
    Pydantic schema for file analysis metadata API responses.

    This is the public contract with the frontend.  It deliberately does
    **not** include the raw samples array — only lightweight metadata.
    """
    signal_id: str
    filename: str
    format: str
    sample_rate: int
    sample_count: int
    duration_seconds: float
    data_type: str
    channels: Optional[int] = None
