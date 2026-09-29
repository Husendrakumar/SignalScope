"""
IQ Signal Reader for SignalScope.

Reads raw binary IQ files and converts them into the canonical internal
``SignalData`` representation with ``samples.dtype == np.complex64``.

Binary format (SignalScope project convention)
----------------------------------------------
SignalScope currently expects IQ files to use **interleaved float32**
encoding:

    I0  Q0  I1  Q1  I2  Q2  ...

where each value is a little-endian IEEE 754 **float32** (4 bytes).
One complex sample occupies **8 bytes** (4 bytes I + 4 bytes Q).

The reader reconstructs complex samples as:

    I0 + j·Q0,  I1 + j·Q1,  I2 + j·Q2,  ...

.. note::
    Not every ``.iq`` file in the wild uses this exact format.
    Other tools may use int16 I/Q, float64 I/Q, or include headers.
    This reader is specific to the SignalScope project's test-data
    convention.  Extending it to auto-detect or accept additional
    IQ sub-formats is a future enhancement.

Sample rate
-----------
Raw IQ files carry no header, so the sample rate cannot be determined
from the file alone.  A ``default_sample_rate`` parameter (default
1 000 000 Hz) is used.  When a companion metadata file or user input
provides the true sample rate, it should be passed explicitly.

Why complex64?
--------------
``complex64`` is the canonical dtype for the entire SignalScope signal
pipeline.  Using it everywhere means downstream modules do not need to
branch on the original file format.
"""

import os
import numpy as np
from app.signal_processing.models import SignalData


def load_iq(path: str, default_sample_rate: int = 1_000_000) -> SignalData:
    """
    Load an IQ signal file and return a ``SignalData`` with complex64 samples.

    Parameters
    ----------
    path : str
        Filesystem path to the raw IQ binary file.
    default_sample_rate : int, optional
        Sample rate in Hz to assume when no external metadata is available.
        Defaults to 1 000 000 Hz (the project's test-data convention).

    Returns
    -------
    SignalData
        Internal signal representation with ``samples.dtype == np.complex64``.

    Raises
    ------
    ValueError
        If the file does not exist, is empty, has a size that is not a
        multiple of 8 bytes (i.e. contains an incomplete I/Q pair), or
        cannot be read.
    """
    if not os.path.exists(path):
        raise ValueError("File does not exist.")

    file_size = os.path.getsize(path)
    if file_size == 0:
        raise ValueError("Uploaded file is empty.")

    # Each complex sample = 4 bytes (I) + 4 bytes (Q) = 8 bytes.
    # A file whose size is not a multiple of 8 contains a truncated sample.
    if file_size % 8 != 0:
        raise ValueError("Unable to read IQ file. Expected interleaved float32 I/Q samples.")

    try:
        raw_floats = np.fromfile(path, dtype=np.float32)
    except Exception as e:
        raise ValueError(
            f"Unable to read IQ file. Expected interleaved float32 I/Q samples. Details: {str(e)}"
        )

    if raw_floats.size == 0 or raw_floats.size % 2 != 0:
        raise ValueError("Unable to read IQ file. Expected interleaved float32 I/Q samples.")

    # ------------------------------------------------------------------
    # De-interleave I and Q channels, then combine into complex64.
    # ------------------------------------------------------------------
    i_samples = raw_floats[0::2]
    q_samples = raw_floats[1::2]

    complex_samples = (i_samples + 1j * q_samples).astype(np.complex64)
    sample_count = int(complex_samples.shape[0])
    duration = float(sample_count / default_sample_rate)

    return SignalData(
        samples=complex_samples,
        sample_rate=default_sample_rate,
        sample_count=sample_count,
        duration=duration,
        format="IQ",
        data_type="complex64",
        channels=1
    )
