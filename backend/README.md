# SignalScope - Backend API & Signal Visualization

FastAPI backend, signal reading foundation, and real-time visualization engine for **SignalScope: Automatic Radio Signal Analysis** (SIH PS 147).

## Overview

This stage implements real-time, interactive signal visualization powered by actual loaded signal samples in memory:
1. **Time-Domain Waveform**: Downsampled time-voltage waveform (supports real WAV and dual I/Q streams).
2. **Frequency Spectrum (FFT)**: Hanning-windowed FFT power spectrum in decibels (dB) across positive and negative frequencies.
3. **Spectrogram / Waterfall**: 2D Short-Time Fourier Transform (STFT) matrix representing frequency power over time.
4. **I/Q Constellation**: 2D scatter plot plane of In-Phase (I) vs Quadrature (Q) sample points.

---

## Signal Session Architecture

SignalScope uses an in-memory session manager (`SignalSessionStore`) for temporary signal storage during local development:

```
POST /api/files/upload
        ↓
Receive & validate WAV/IQ file
        ↓
Read into common SignalData (NumPy samples + metadata)
        ↓
Generate unique signal_id (UUID)
        ↓
Store in SignalSessionStore (Memory, TTL: 30 minutes)
        ↓
Return signal_id + metadata JSON (samples array is NOT returned in upload)
        ↓
GET /api/visualization/{type}/{signal_id}
        ↓
Compute waveform / FFT / spectrogram / constellation on demand
```

---

## API Visualization Endpoints

- **Waveform Data**: `GET /api/visualization/waveform/{signal_id}?max_points=1000`
- **FFT Spectrum**: `GET /api/visualization/spectrum/{signal_id}?nfft=2048`
- **Spectrogram / Waterfall**: `GET /api/visualization/spectrogram/{signal_id}?nfft=512&hop_length=256`
- **I/Q Constellation**: `GET /api/visualization/constellation/{signal_id}?max_points=1000` *(IQ signals only)*

---

## Test Signal Generator & Test Suite

To generate synthetic test signals (`test_sine.wav`, `test_sine.iq`, `test_fsk.wav`, `test_fsk.iq`):

```powershell
python scripts/generate_test_signals.py
```

To run the automated backend test suite (11 unit tests):

```powershell
pytest tests/
```

To start the FastAPI server:

```powershell
python -m uvicorn app.main:app --reload --port 8000
```
