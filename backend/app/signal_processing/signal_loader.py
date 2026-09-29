"""
Common Signal Loader — unified entry point for the SignalScope reader layer.

This module provides ``load_signal()``, the **single function** that
downstream pipeline stages should call to obtain a ``SignalData`` object
from any supported file format.

Supported formats
-----------------
========  ===========  ====================================================
Extension Reader       Notes
========  ===========  ====================================================
``.wav``  ``load_wav``  Standard PCM WAV (int16, int32, uint8, float32).
                       Multi-channel files are averaged to mono.
``.iq``   ``load_iq``   Raw interleaved float32 I/Q (SignalScope convention).
========  ===========  ====================================================

Canonical representation
------------------------
Regardless of the input format, the returned ``SignalData.samples`` array
is **always** ``np.complex64``.  Downstream modules can therefore process
the signal without branching on the original file type.

Pipeline position
-----------------
::

    File Upload
        ↓
    **Signal Reader / Normalization**   ← this module
        ↓
    Signal Detection
        ↓
    Visualization / Modulation Detection / …
"""

import os
import logging

from app.signal_processing.models import SignalData
from app.signal_processing.wav_reader import load_wav
from app.signal_processing.iq_reader import load_iq

logger = logging.getLogger("signalscope.signal_loader")


def load_signal(
    path: str,
    *,
    filename: str = "",
    sample_rate: int | None = None,
) -> SignalData:
    """
    Load a signal file and return the canonical ``SignalData`` representation.

    The caller does **not** need to know whether the input is WAV or IQ —
    the format is determined from the file extension.

    Parameters
    ----------
    path : str
        Filesystem path to the signal file.
    filename : str, optional
        Original filename to store in the returned ``SignalData``.  If not
        provided, the basename of *path* is used.
    sample_rate : int or None, optional
        Override the sample rate.  For WAV files the rate is read from the
        file header and this parameter is ignored.  For IQ files, if
        ``None`` the reader's default (48 000 Hz) is used.

    Returns
    -------
    SignalData
        Canonical signal object with ``samples.dtype == np.complex64``.

    Raises
    ------
    ValueError
        If the file extension is not supported, or the file cannot be read.

    Examples
    --------
    >>> signal = load_signal("test_data/test_fsk.wav")
    >>> signal.samples.dtype
    dtype('complex64')
    >>> signal.format
    'WAV'
    >>> signal.data_type   # original source type for API reporting
    'float32'
    """
    if not filename:
        filename = os.path.basename(path)

    ext = os.path.splitext(path)[1].lower().lstrip(".")

    if ext == "wav":
        signal = load_wav(path)
    elif ext == "iq":
        kwargs = {}
        if sample_rate is not None:
            kwargs["default_sample_rate"] = sample_rate
        signal = load_iq(path, **kwargs)
    else:
        raise ValueError(
            f"Unsupported file format '.{ext}'. "
            "SignalScope currently supports .wav and .iq files."
        )

    # Attach the filename for traceability.
    signal.filename = filename

    logger.info(
        "Loaded signal: file=%s format=%s rate=%d samples=%d duration=%.4fs dtype=%s",
        filename,
        signal.format,
        signal.sample_rate,
        signal.sample_count,
        signal.duration,
        signal.samples.dtype,
    )

    return signal
