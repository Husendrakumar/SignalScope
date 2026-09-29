"""
Deterministic Signal Analysis Module for SignalScope (Part 7).

Provides reproducible, explainable signal metrics derived directly from
the canonical ``SignalData`` object (np.complex64 samples).

Metrics computed:
1. Signal Statistics (mean, RMS, peak, peak-to-peak, average power)
2. Noise & SNR Estimation (spectral percentile noise floor method)
3. Dominant Frequency (FFT spectral peak)
4. Occupied Bandwidth (99% cumulative PSD)
5. Signal Activity & Presence Detection (time-block power thresholding)
"""

import numpy as np
import scipy.signal
from app.signal_processing.models import SignalData


def calculate_signal_statistics(signal: SignalData) -> dict:
    """
    Computes time-domain statistics for WAV or IQ signals.
    """
    samples = signal.samples
    n_samples = signal.sample_count

    if n_samples == 0:
        return {
            "mean": 0.0,
            "rms": 0.0,
            "peak": 0.0,
            "peak_to_peak": 0.0,
            "average_power": 0.0
        }

    mags = np.abs(samples)

    if signal.format == "WAV":
        # WAV is real-valued — use real component for mean & peak-to-peak
        real_parts = np.real(samples)
        mean_val = float(np.mean(real_parts))
        p2p_val = float(np.max(real_parts) - np.min(real_parts))
    else:
        # IQ is complex — mean of magnitude, p2p of magnitude
        mean_val = float(np.mean(mags))
        p2p_val = float(np.max(mags) - np.min(mags))

    # RMS & Power apply to both WAV and IQ via magnitude squared
    power_samples = mags ** 2
    avg_power = float(np.mean(power_samples))
    rms_val = float(np.sqrt(avg_power))
    peak_val = float(np.max(mags))

    return {
        "mean": round(mean_val, 6),
        "rms": round(rms_val, 6),
        "peak": round(peak_val, 6),
        "peak_to_peak": round(p2p_val, 6),
        "average_power": round(avg_power, 6)
    }


def estimate_noise_and_snr(signal: SignalData, nfft: int = 2048) -> dict:
    """
    Estimates background noise power and SNR using spectral percentile power estimation.
    Takes lower 20th percentile of PSD bins as noise floor estimate.
    """
    samples = signal.samples
    n_samples = signal.sample_count

    if n_samples == 0:
        return {
            "estimated_noise_power": 0.0,
            "estimated_signal_power": 0.0,
            "estimated_snr_db": 0.0,
            "method": "Spectral percentile noise estimation (20th percentile PSD)"
        }

    # Total signal power
    total_power = float(np.mean(np.abs(samples) ** 2))

    # FFT power spectrum
    fft_len = min(n_samples, nfft * 8)
    start_idx = max(0, (n_samples - fft_len) // 2)
    segment = samples[start_idx:start_idx + fft_len]
    windowed = segment * np.hanning(len(segment))

    if signal.format == "WAV":
        fft_vals = np.fft.rfft(np.real(windowed), n=nfft)
        psd = (np.abs(fft_vals) ** 2) / (nfft / 2)
    else:
        fft_vals = np.fft.fft(windowed, n=nfft)
        psd = (np.abs(fft_vals) ** 2) / nfft

    # Noise floor estimated from 20th percentile of PSD bins
    noise_bin_power = float(np.percentile(psd, 20))
    total_psd_power = float(np.mean(psd))
    if total_psd_power > 0:
        noise_ratio = min(1.0, max(1e-6, noise_bin_power / total_psd_power))
        est_noise_power = total_power * noise_ratio
    else:
        est_noise_power = 1e-12

    est_signal_power = max(0.0, total_power - est_noise_power)

    if est_noise_power > 0 and est_signal_power > 0:
        snr_db = 10.0 * np.log10(est_signal_power / est_noise_power)
    else:
        snr_db = 0.0

    return {
        "estimated_noise_power": round(float(est_noise_power), 6),
        "estimated_signal_power": round(float(est_signal_power), 6),
        "estimated_snr_db": round(float(snr_db), 2),
        "method": "Spectral percentile noise estimation (20th percentile PSD)"
    }


def estimate_dominant_frequency(signal: SignalData, nfft: int = 4096) -> dict:
    """
    Finds the frequency with highest power spectral density using FFT.
    """
    samples = signal.samples
    n_samples = signal.sample_count

    if n_samples == 0:
        return {
            "dominant_frequency_hz": 0.0,
            "dominant_frequency_khz": 0.0,
            "peak_magnitude_db": 0.0
        }

    fft_len = min(n_samples, nfft * 8)
    start_idx = max(0, (n_samples - fft_len) // 2)
    segment = samples[start_idx:start_idx + fft_len]
    windowed = segment * np.hanning(len(segment))

    if signal.format == "IQ":
        fft_vals = np.fft.fftshift(np.fft.fft(windowed, n=nfft))
        freqs = np.fft.fftshift(np.fft.fftfreq(nfft, d=1.0 / signal.sample_rate))
        mag = np.abs(fft_vals) / nfft
    else:
        real_windowed = np.real(windowed).astype(np.float32)
        fft_vals = np.fft.rfft(real_windowed, n=nfft)
        freqs = np.fft.rfftfreq(nfft, d=1.0 / signal.sample_rate)
        mag = np.abs(fft_vals) / (nfft / 2)

    peak_idx = int(np.argmax(mag))
    dom_freq = float(freqs[peak_idx])
    peak_mag = float(mag[peak_idx])
    peak_db = float(20 * np.log10(peak_mag + 1e-12))

    return {
        "dominant_frequency_hz": round(dom_freq, 2),
        "dominant_frequency_khz": round(dom_freq / 1000.0, 3),
        "peak_magnitude_db": round(peak_db, 2)
    }


def estimate_occupied_bandwidth(signal: SignalData, nfft: int = 2048, obw_percent: float = 0.99) -> dict:
    """
    Estimates occupied bandwidth (99% OBW) from cumulative power spectral density.
    """
    samples = signal.samples
    n_samples = signal.sample_count

    if n_samples == 0:
        return {
            "bandwidth_hz": 0.0,
            "lower_frequency_hz": 0.0,
            "upper_frequency_hz": 0.0,
            "method": f"{int(obw_percent*100)}% Cumulative Power Spectral Density (OBW)"
        }

    fft_len = min(n_samples, nfft * 8)
    start_idx = max(0, (n_samples - fft_len) // 2)
    segment = samples[start_idx:start_idx + fft_len]
    windowed = segment * np.hanning(len(segment))

    if signal.format == "IQ":
        fft_vals = np.fft.fftshift(np.fft.fft(windowed, n=nfft))
        freqs = np.fft.fftshift(np.fft.fftfreq(nfft, d=1.0 / signal.sample_rate))
        psd = np.abs(fft_vals) ** 2
    else:
        fft_vals = np.fft.rfft(np.real(windowed), n=nfft)
        freqs = np.fft.rfftfreq(nfft, d=1.0 / signal.sample_rate)
        psd = np.abs(fft_vals) ** 2

    tot_power = np.sum(psd)
    if tot_power <= 0:
        return {
            "bandwidth_hz": 0.0,
            "lower_frequency_hz": 0.0,
            "upper_frequency_hz": 0.0,
            "method": f"{int(obw_percent*100)}% Cumulative Power Spectral Density (OBW)"
        }

    cum_power = np.cumsum(psd) / tot_power
    tail = (1.0 - obw_percent) / 2.0

    low_idx = int(np.searchsorted(cum_power, tail))
    high_idx = int(np.searchsorted(cum_power, 1.0 - tail))

    low_idx = min(max(0, low_idx), len(freqs) - 1)
    high_idx = min(max(0, high_idx), len(freqs) - 1)

    f_low = float(freqs[low_idx])
    f_high = float(freqs[high_idx])
    bw = float(abs(f_high - f_low))

    return {
        "bandwidth_hz": round(bw, 2),
        "lower_frequency_hz": round(f_low, 2),
        "upper_frequency_hz": round(f_high, 2),
        "method": f"{int(obw_percent*100)}% Cumulative Power Spectral Density (OBW)"
    }


def detect_signal_presence(signal: SignalData, stats: dict, noise_est: dict) -> dict:
    """
    Determines signal presence and estimates active time intervals.
    """
    samples = signal.samples
    n_samples = signal.sample_count

    if n_samples == 0:
        return {
            "signal_present": False,
            "activity_ratio": 0.0,
            "active_start_time": 0.0,
            "active_end_time": 0.0,
            "status": "LOW_ENERGY_OR_NOISE"
        }

    snr_db = noise_est.get("estimated_snr_db", 0.0)
    avg_power = stats.get("average_power", 0.0)
    noise_power = noise_est.get("estimated_noise_power", 0.0)

    block_size = max(64, n_samples // 200)
    num_blocks = n_samples // block_size

    if num_blocks == 0:
        return {
            "signal_present": bool(snr_db > 3.0),
            "activity_ratio": 1.0 if snr_db > 3.0 else 0.0,
            "active_start_time": 0.0,
            "active_end_time": round(signal.duration, 4),
            "status": "ACTIVE_SIGNAL" if snr_db > 3.0 else "LOW_ENERGY_OR_NOISE"
        }

    reshaped = samples[:num_blocks * block_size].reshape(num_blocks, block_size)
    block_powers = np.mean(np.abs(reshaped) ** 2, axis=1)

    peak_block_power = np.max(block_powers) if len(block_powers) > 0 else 0.0
    thresh = max(noise_power * 1.5, peak_block_power * 0.15, 1e-7)

    active_mask = block_powers >= thresh
    active_count = int(np.sum(active_mask))
    activity_ratio = float(active_count / num_blocks)

    if active_count > 0:
        active_indices = np.where(active_mask)[0]
        start_idx = int(active_indices[0])
        end_idx = int(active_indices[-1])
        start_time = float(start_idx * block_size / signal.sample_rate)
        end_time = float((end_idx + 1) * block_size / signal.sample_rate)
    else:
        start_time = 0.0
        end_time = 0.0

    signal_present = bool(snr_db >= 3.0 or (activity_ratio > 0.1 and avg_power > 1e-6))

    return {
        "signal_present": signal_present,
        "activity_ratio": round(activity_ratio, 4),
        "active_start_time": round(start_time, 4),
        "active_end_time": round(end_time, 4),
        "status": "ACTIVE_SIGNAL" if signal_present else "LOW_ENERGY_OR_NOISE"
    }


def analyze_signal(signal: SignalData, signal_id: str = "") -> dict:
    """
    Main signal analysis entrypoint. Runs all analysis routines and
    returns a clean, structured JSON-serializable dictionary.
    """
    stats = calculate_signal_statistics(signal)
    noise_est = estimate_noise_and_snr(signal)
    dom_freq = estimate_dominant_frequency(signal)
    obw = estimate_occupied_bandwidth(signal)
    presence = detect_signal_presence(signal, stats, noise_est)

    return {
        "signal_id": signal_id,
        "filename": signal.filename,
        "format": signal.format,
        "sample_rate": signal.sample_rate,
        "sample_count": signal.sample_count,
        "duration_seconds": round(signal.duration, 4),
        "statistics": stats,
        "noise": noise_est,
        "frequency": dom_freq,
        "bandwidth": obw,
        "activity": presence
    }
