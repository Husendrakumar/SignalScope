"""
Signal Processing Package for SignalScope.

This package provides:

- **Reader layer** (``signal_loader``, ``wav_reader``, ``iq_reader``):
  Loads supported file formats and converts them into the canonical
  ``SignalData`` representation (``np.complex64``).

- **Models** (``models``):
  ``SignalData`` dataclass (internal) and ``FileMetadataResponse``
  Pydantic schema (API contract).

- **Session management** (``session_manager``):
  In-memory store mapping ``signal_id`` → ``SignalData``.

- **Visualization helpers** (``visualization``):
  Waveform, spectrum, spectrogram, and constellation computations.
"""
