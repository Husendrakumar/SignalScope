"""
WAV Signal Reader for SignalScope.

Reads standard WAV files and converts them into the canonical internal
``SignalData`` representation with ``samples.dtype == np.complex64``.

WAV files contain real-valued audio samples.  To produce the canonical
complex representation, each real sample ``x`` is mapped to ``x + 0j``.
This preserves the original signal shape exactly — no filtering,
resampling, or amplitude scaling is applied beyond the integer-to-float
normalization required for integer-coded WAV formats (int16, int32, uint8).

Stereo / multi-channel handling
-------------------------------
Multi-channel WAV files are reduced to a single mono analysis channel by
**averaging all channels**.  This is a simple, deterministic approach that
preserves energy and is appropriate for later signal-analysis stages that
expect a single-channel input.

Why complex64?
--------------
Downstream signal-processing modules (FFT, spectrogram, modulation
detection, etc.) operate on a single canonical dtype.  Using ``complex64``
everywhere means the pipeline does not need to branch on whether the
original file was WAV or IQ.
"""

import os
import numpy as np
from scipy.io import wavfile
from app.signal_processing.models import SignalData


def load_wav(path: str) -> SignalData:
    """
    Load a WAV signal file and return a ``SignalData`` with complex64 samples.

    Parameters
    ----------
    path : str
        Filesystem path to the WAV file.

    Returns
    -------
    SignalData
        Internal signal representation.  ``data_type`` is set to
        ``"float32"`` (the original source representation) for API
        reporting, while ``samples.dtype`` is always ``np.complex64``.

    Raises
    ------
    ValueError
        If the file does not exist, is empty, or cannot be parsed as WAV.
    """
    if not os.path.exists(path):
        raise ValueError("File does not exist.")

    if os.path.getsize(path) == 0:
        raise ValueError("Uploaded file is empty.")

    try:
        sample_rate, data = wavfile.read(path)
    except Exception as e:
        raise ValueError(f"Unable to read WAV file: {str(e)}")

    if data.size == 0:
        raise ValueError("Unable to read WAV file.")

    # ------------------------------------------------------------------
    # Channel handling: reduce multi-channel to mono by averaging.
    # ------------------------------------------------------------------
    channels = 1
    if data.ndim == 2:
        channels = data.shape[1]
        # Average channels → mono (deterministic, energy-preserving).
        data = data.mean(axis=1)
    elif data.ndim > 2:
        raise ValueError("Unsupported WAV format: dimensional depth greater than stereo.")

    original_dtype = data.dtype

    # ------------------------------------------------------------------
    # Integer → float32 normalization (standard PCM scaling).
    # No additional amplitude normalization is applied.
    # ------------------------------------------------------------------
    if np.issubdtype(original_dtype, np.integer):
        if original_dtype == np.int16:
            samples = (data / 32768.0).astype(np.float32)
        elif original_dtype == np.int32:
            samples = (data / 2147483648.0).astype(np.float32)
        elif original_dtype == np.uint8:
            samples = ((data.astype(np.float32) - 128.0) / 128.0).astype(np.float32)
        else:
            max_val = float(np.iinfo(original_dtype).max)
            samples = (data / max_val).astype(np.float32)
    else:
        samples = data.astype(np.float32)

    sample_count = int(samples.shape[0])
    if sample_count == 0 or sample_rate <= 0:
        raise ValueError("Unable to read WAV file.")

    duration = float(sample_count / sample_rate)

    # ------------------------------------------------------------------
    # Convert real float32 → complex64:  x  →  x + 0j
    # This is a zero-copy view when possible; NumPy handles the cast.
    # ------------------------------------------------------------------
    complex_samples = samples.astype(np.complex64)

    return SignalData(
        samples=complex_samples,
        sample_rate=int(sample_rate),
        sample_count=sample_count,
        duration=duration,
        format="WAV",
        data_type="float32",   # original source type — preserved for API
        channels=channels
    )
