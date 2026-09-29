"""
Deterministic Explainable Modulation Recognition Engine for SignalScope (Part 8A).

Extracts physical signal features (envelope behavior, instantaneous frequency,
phase stability, I/Q variance, spectral structure) directly from canonical
SignalData objects and evaluates deterministic rule-based evidence for FSK, PSK,
QAM, or UNKNOWN classification.

Supported Modulations:
- FSK (Frequency Shift Keying)
- PSK (Phase Shift Keying)
- QAM (Quadrature Amplitude Modulation)
- UNKNOWN (Unmodulated SINE, noise, or unclassifiable structure)
"""

import numpy as np
import scipy.signal
from app.signal_processing.models import SignalData


def extract_modulation_features(signal: SignalData) -> dict:
    """
    Extracts physical signal features for modulation classification.
    """
    samples = signal.samples
    n_samples = signal.sample_count
    fs = signal.sample_rate

    if n_samples < 64:
        return {
            "envelope_cv": 0.0,
            "mean_amplitude": 0.0,
            "rms_amplitude": 0.0,
            "inst_freq_std_hz": 0.0,
            "inst_freq_mean_hz": 0.0,
            "num_freq_peaks": 0,
            "num_spectral_peaks": 0,
            "freq_peak_freqs": [],
            "phase_std": 0.0,
            "iq_var_ratio": 1.0,
            "amplitude_clusters": 1
        }

    # 1. Analytic / Complex samples
    if signal.format == "WAV":
        real_samples = np.real(samples).astype(np.float64)
        analytic = scipy.signal.hilbert(real_samples)
    else:
        analytic = samples.astype(np.complex128)

    # 2. Envelope statistics
    mags = np.abs(analytic)
    mean_amp = float(np.mean(mags))
    std_amp = float(np.std(mags))
    rms_amp = float(np.sqrt(np.mean(mags ** 2)))
    envelope_cv = float(std_amp / (mean_amp + 1e-12))

    # 3. Instantaneous Phase & Frequency
    phases = np.angle(analytic)
    unwrapped_phases = np.unwrap(phases)

    d_phase = np.diff(unwrapped_phases)
    inst_freq = d_phase / (2.0 * np.pi) * fs

    edge = max(1, len(inst_freq) // 50)
    inst_freq_trimmed = inst_freq[edge:-edge] if len(inst_freq) > 2 * edge else inst_freq

    inst_freq_mean = float(np.mean(inst_freq_trimmed))
    inst_freq_std = float(np.std(inst_freq_trimmed))

    # 4. Instantaneous Frequency Histogram & Peak Detection
    q5, q95 = np.percentile(inst_freq_trimmed, [5, 95])
    valid_freq_mask = (inst_freq_trimmed >= q5 - 0.5 * fs) & (inst_freq_trimmed <= q95 + 0.5 * fs)
    valid_freqs = inst_freq_trimmed[valid_freq_mask]

    hist_counts, bin_edges = np.histogram(valid_freqs, bins=64)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2.0

    if np.max(hist_counts) > 0:
        norm_counts = hist_counts / np.max(hist_counts)
        peaks, _ = scipy.signal.find_peaks(norm_counts, height=0.20, distance=3)
        num_freq_peaks = len(peaks)
        freq_peak_freqs = [float(bin_centers[p]) for p in peaks]
    else:
        num_freq_peaks = 0
        freq_peak_freqs = []

    # 5. Spectral PSD Peak Detection
    nfft = 2048
    if signal.format == "WAV":
        fft_vals = np.fft.rfft(np.real(samples), n=nfft)
        psd = (np.abs(fft_vals) ** 2)
    else:
        fft_vals = np.fft.fftshift(np.fft.fft(samples, n=nfft))
        psd = (np.abs(fft_vals) ** 2)

    max_psd = np.max(psd) if len(psd) > 0 else 1.0
    if max_psd > 0:
        norm_psd = psd / max_psd
        spec_peaks, _ = scipy.signal.find_peaks(norm_psd, height=0.15, distance=max(2, nfft // 128))
        num_spectral_peaks = len(spec_peaks)
    else:
        num_spectral_peaks = 0

    # 6. I/Q Statistics
    i_vals = np.real(analytic)
    q_vals = np.imag(analytic)
    var_i = float(np.var(i_vals))
    var_q = float(np.var(q_vals))
    max_var = max(var_i, var_q, 1e-12)
    min_var = min(var_i, var_q)
    iq_var_ratio = float(min_var / max_var)

    # 7. Phase difference statistics
    phase_diffs = np.diff(phases)
    phase_diffs_wrapped = np.arctan2(np.sin(phase_diffs), np.cos(phase_diffs))
    phase_std = float(np.std(phase_diffs_wrapped))

    # 8. Amplitude Clustering
    amp_hist, _ = np.histogram(mags, bins=32)
    if np.max(amp_hist) > 0:
        norm_amp_hist = amp_hist / np.max(amp_hist)
        amp_peaks, _ = scipy.signal.find_peaks(norm_amp_hist, height=0.25, distance=3)
        amplitude_clusters = max(1, len(amp_peaks))
    else:
        amplitude_clusters = 1

    return {
        "envelope_cv": round(envelope_cv, 4),
        "mean_amplitude": round(mean_amp, 4),
        "rms_amplitude": round(rms_amp, 4),
        "inst_freq_std_hz": round(inst_freq_std, 2),
        "inst_freq_mean_hz": round(inst_freq_mean, 2),
        "num_freq_peaks": int(num_freq_peaks),
        "num_spectral_peaks": int(num_spectral_peaks),
        "freq_peak_freqs": [round(f, 2) for f in freq_peak_freqs],
        "phase_std": round(phase_std, 4),
        "iq_var_ratio": round(iq_var_ratio, 4),
        "amplitude_clusters": int(amplitude_clusters)
    }


def classify_signal_modulation(signal: SignalData, signal_id: str = "") -> dict:
    """
    Classifies signal modulation type (FSK, PSK, QAM, UNKNOWN) using
    extracted physical features and transparent rule-based evidence.
    """
    feats = extract_modulation_features(signal)
    cv = feats["envelope_cv"]
    inst_std = feats["inst_freq_std_hz"]
    num_f_peaks = feats["num_freq_peaks"]
    num_s_peaks = feats["num_spectral_peaks"]
    peak_freqs = feats["freq_peak_freqs"]
    amp_clusters = feats["amplitude_clusters"]
    phase_std = feats["phase_std"]
    fs = signal.sample_rate

    freq_std_threshold = 0.005 * fs

    # 1. FSK Classification
    is_fsk = (
        cv < 0.25 and
        (num_f_peaks >= 2 or (num_s_peaks >= 2 and inst_std > freq_std_threshold)) and
        inst_std > freq_std_threshold
    )

    if is_fsk:
        confidence = min(0.92, round(0.72 + 0.12 * (num_f_peaks >= 2) + 0.08 * (cv < 0.10), 2))
        freq_str = ", ".join([f"{f:.1f} Hz" for f in peak_freqs[:3]]) if peak_freqs else f"{inst_std:.1f} Hz std"
        evidence = [
            f"Constant envelope signal (Envelope CV = {cv})",
            f"Instantaneous frequency distribution displays {num_f_peaks} distinct tone states ({freq_str})",
            f"Significant frequency variation across signal frames (std = {inst_std:.1f} Hz)"
        ]
        return {
            "signal_id": signal_id,
            "filename": signal.filename,
            "format": signal.format,
            "modulation": "FSK",
            "confidence_score": confidence,
            "evidence": evidence,
            "features": feats
        }

    # 2. PSK Classification
    is_psk = (
        cv < 0.18 and
        inst_std <= freq_std_threshold and
        num_f_peaks <= 1 and
        phase_std > 0.35 and
        amp_clusters <= 1
    )

    if is_psk:
        confidence = min(0.88, round(0.68 + 0.15 * (cv < 0.08), 2))
        evidence = [
            f"Constant envelope signal (Envelope CV = {cv})",
            f"Stable carrier frequency without frequency shifting (std = {inst_std:.1f} Hz)",
            f"Significant phase transitions and phase stability consistent with Phase Shift Keying"
        ]
        return {
            "signal_id": signal_id,
            "filename": signal.filename,
            "format": signal.format,
            "modulation": "PSK",
            "confidence_score": confidence,
            "evidence": evidence,
            "features": feats
        }

    # 3. QAM Classification
    is_qam = (
        (cv >= 0.25 or amp_clusters >= 2) and
        phase_std > 0.30 and
        inst_std <= 0.02 * fs
    )

    if is_qam:
        confidence = min(0.85, round(0.62 + 0.18 * (amp_clusters >= 2), 2))
        evidence = [
            f"Non-constant envelope variation (Envelope CV = {cv})",
            f"Multiple amplitude constellation levels detected ({amp_clusters} amplitude clusters)",
            f"Combined amplitude and phase variation consistent with Quadrature Amplitude Modulation"
        ]
        return {
            "signal_id": signal_id,
            "filename": signal.filename,
            "format": signal.format,
            "modulation": "QAM",
            "confidence_score": confidence,
            "evidence": evidence,
            "features": feats
        }

    # 4. UNKNOWN / Unmodulated SINE Classification
    if cv < 0.10 and inst_std <= freq_std_threshold and num_f_peaks <= 1:
        evidence = [
            f"Continuous unmodulated single frequency tone detected at {feats['inst_freq_mean_hz']:.1f} Hz",
            f"Zero frequency shifting or digital symbol transitions (std = {inst_std:.1f} Hz)",
            "No FSK, PSK, or QAM digital modulation features detected"
        ]
        return {
            "signal_id": signal_id,
            "filename": signal.filename,
            "format": signal.format,
            "modulation": "UNKNOWN",
            "confidence_score": 0.15,
            "evidence": evidence,
            "features": feats
        }

    # Default UNKNOWN fallback for arbitrary/noisy signals
    evidence = [
        f"Envelope variation (CV = {cv}) and frequency variation (std = {inst_std:.1f} Hz) do not match known modulation profiles",
        "Insufficient evidence for deterministic classification as FSK, PSK, or QAM"
    ]
    return {
        "signal_id": signal_id,
        "filename": signal.filename,
        "format": signal.format,
        "modulation": "UNKNOWN",
        "confidence_score": 0.10,
        "evidence": evidence,
        "features": feats
    }
