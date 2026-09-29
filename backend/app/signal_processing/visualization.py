"""
Visualization helpers for SignalScope.

Each function receives a ``SignalData`` object and returns a JSON-friendly
dict suitable for direct API serialization.

Since Part 5, *all* ``SignalData.samples`` arrays are ``np.complex64``,
regardless of the original file format.  The ``signal.format`` field
(``"WAV"`` or ``"IQ"``) is used to decide how to present the data:

* **WAV** (originally real-valued):
  - Waveform shows amplitude (real part only; imaginary is always 0).
  - Spectrum uses a one-sided real FFT for efficiency.
  - Spectrogram uses a one-sided real spectrogram.
  - Constellation is not meaningful (rejected with 400).

* **IQ** (originally complex):
  - Waveform shows I, Q, and magnitude channels.
  - Spectrum/spectrogram use the full complex FFT.
  - Constellation shows the I/Q scatter plot.
"""

import numpy as np
import scipy.signal
from app.signal_processing.models import SignalData


def compute_waveform(signal: SignalData, max_points: int = 1000) -> dict:
    """
    Downsamples the signal for time-domain waveform visualization.
    Returns time vector and amplitude/I/Q arrays.
    """
    n_samples = signal.sample_count
    step = max(1, n_samples // max_points)
    indices = np.arange(0, n_samples, step)[:max_points]

    subsampled = signal.samples[indices]
    time_vec = (indices / signal.sample_rate).round(6).tolist()

    if signal.format == "IQ":
        i_samples = np.real(subsampled).astype(np.float32).round(6).tolist()
        q_samples = np.imag(subsampled).astype(np.float32).round(6).tolist()
        magnitude = np.abs(subsampled).astype(np.float32).round(6).tolist()
        return {
            "format": "IQ",
            "time": time_vec,
            "real_i": i_samples,
            "imag_q": q_samples,
            "magnitude": magnitude,
            "sample_rate": signal.sample_rate,
            "total_points": len(time_vec)
        }
    else:
        # WAV: originally real — imaginary part is zero.
        amplitude = np.real(subsampled).astype(np.float32).round(6).tolist()
        return {
            "format": "WAV",
            "time": time_vec,
            "amplitude": amplitude,
            "sample_rate": signal.sample_rate,
            "total_points": len(time_vec)
        }


def compute_spectrum(signal: SignalData, nfft: int = 2048) -> dict:
    """
    Computes frequency spectrum (FFT) in decibels (dB).
    Uses full complex FFT for IQ and one-sided real FFT for WAV.
    """
    n_samples = signal.sample_count
    fft_len = min(n_samples, nfft * 8)
    start_idx = max(0, (n_samples - fft_len) // 2)
    segment = signal.samples[start_idx:start_idx + fft_len]

    window = np.hanning(len(segment))
    windowed = segment * window

    if signal.format == "IQ":
        fft_vals = np.fft.fftshift(np.fft.fft(windowed, n=nfft))
        freqs = np.fft.fftshift(np.fft.fftfreq(nfft, d=1.0 / signal.sample_rate))
        mag = np.abs(fft_vals) / nfft
        mag_db = 20 * np.log10(mag + 1e-12)
    else:
        # WAV: use real part only — imaginary is zero.
        real_windowed = np.real(windowed).astype(np.float32)
        fft_vals = np.fft.rfft(real_windowed, n=nfft)
        freqs = np.fft.rfftfreq(nfft, d=1.0 / signal.sample_rate)
        mag = np.abs(fft_vals) / (nfft / 2)
        mag_db = 20 * np.log10(mag + 1e-12)

    return {
        "format": signal.format,
        "frequencies": freqs.round(2).tolist(),
        "magnitudes_db": mag_db.round(2).tolist(),
        "sample_rate": signal.sample_rate,
        "nfft": nfft
    }


def compute_spectrogram(signal: SignalData, nfft: int = 512, hop_length: int = 256) -> dict:
    """
    Computes 2D Spectrogram / Waterfall matrix (time vs frequency vs dB power).
    Grid is bounded to max 128x128 for efficient frontend canvas rendering.
    """
    samples = signal.samples

    if signal.format == "IQ":
        f, t, Sxx = scipy.signal.spectrogram(
            samples,
            fs=signal.sample_rate,
            nperseg=nfft,
            noverlap=nfft - hop_length,
            return_onesided=False,
            mode='complex'
        )
        f = np.fft.fftshift(f)
        Sxx = np.fft.fftshift(Sxx, axes=0)
        power_db = 10 * np.log10(np.abs(Sxx)**2 + 1e-12)
    else:
        # WAV: use real part only — imaginary is zero.
        real_samples = np.real(samples).astype(np.float32)
        f, t, Sxx = scipy.signal.spectrogram(
            real_samples,
            fs=signal.sample_rate,
            nperseg=nfft,
            noverlap=nfft - hop_length,
            scaling='spectrum'
        )
        power_db = 10 * np.log10(Sxx + 1e-12)

    max_frames = 128
    max_freq_bins = 128

    if len(t) > max_frames:
        t_step = len(t) // max_frames
        t = t[::t_step][:max_frames]
        power_db = power_db[:, ::t_step][:, :max_frames]

    if len(f) > max_freq_bins:
        f_step = len(f) // max_freq_bins
        f = f[::f_step][:max_freq_bins]
        power_db = power_db[::f_step, :]

    return {
        "format": signal.format,
        "time_axis": t.round(4).tolist(),
        "frequency_axis": f.round(2).tolist(),
        "spectrogram_db": power_db.round(2).tolist(),
        "sample_rate": signal.sample_rate
    }


def compute_constellation(signal: SignalData, max_points: int = 1000) -> dict:
    """
    Computes I/Q constellation scatter points for IQ signals.
    Constellation is only meaningful for complex-baseband (IQ) signals.
    """
    if signal.format != "IQ":
        raise ValueError("Constellation visualization is only available for IQ signals.")

    n_samples = signal.sample_count
    step = max(1, n_samples // max_points)
    subsampled = signal.samples[::step][:max_points]

    i_vals = subsampled.real.astype(np.float32).round(6).tolist()
    q_vals = subsampled.imag.astype(np.float32).round(6).tolist()

    return {
        "format": "IQ",
        "i": i_vals,
        "q": q_vals,
        "total_points": len(i_vals)
    }
