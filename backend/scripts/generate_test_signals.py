import os
import json
import numpy as np
from scipy.io import wavfile
from app.signal_processing.deinterleaving import block_interleave, convolutional_interleave
from app.signal_processing.fec import convolutional_encode, reed_solomon_encode, bytes_to_bits
from app.signal_processing.header import build_synthetic_frame, DEFAULT_SYNC_PATTERN


_GENERATED = False

def generate_test_signals():
    global _GENERATED
    if _GENERATED:
        return
    _GENERATED = True
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_backend_dir = os.path.dirname(script_dir)
    output_dir = os.path.join(project_backend_dir, "test_data")
    os.makedirs(output_dir, exist_ok=True)

    duration = 2.0  # seconds

    def _time_base(fs):
        n = int(fs * duration)
        return np.arange(n) / fs, n

    # -------------------------------------------------------------
    # 1. Real Sine Wave (.wav) & Complex Sinusoid (.iq)
    # -------------------------------------------------------------
    tone_freq = 1000.0  # Hz
    
    # WAV
    fs_wav = 48000
    t_wav, n_wav = _time_base(fs_wav)
    sine_wav_data = np.sin(2 * np.pi * tone_freq * t_wav)
    sine_int16 = (sine_wav_data * 32767.0).astype(np.int16)
    sine_wav_path = os.path.join(output_dir, "test_sine.wav")
    wavfile.write(sine_wav_path, fs_wav, sine_int16)
    print(f"Generated: {sine_wav_path}")

    # IQ
    fs_iq = 1_000_000
    t_iq, n_iq = _time_base(fs_iq)
    complex_sine = np.exp(1j * 2 * np.pi * tone_freq * t_iq)
    iq_sine_raw = np.empty(2 * n_iq, dtype=np.float32)
    iq_sine_raw[0::2] = complex_sine.real.astype(np.float32)
    iq_sine_raw[1::2] = complex_sine.imag.astype(np.float32)
    sine_iq_path = os.path.join(output_dir, "test_sine.iq")
    iq_sine_raw.tofile(sine_iq_path)
    print(f"Generated: {sine_iq_path}")

    # -------------------------------------------------------------
    # Base FSK Parameters
    # -------------------------------------------------------------
    bit_rate = 1000  # bits/sec
    mark_freq = 5000.0  # Hz (bit 1)
    space_freq = 8000.0  # Hz (bit 0)
    base_bits = "1011001011010011"

    def _generate_fsk(bits, name_prefix, extra_meta=None):
        if extra_meta is None:
            extra_meta = {}
            
        # Generate WAV
        sps_wav = fs_wav // bit_rate
        n_wav_req = len(bits) * sps_wav
        freq_arr_wav = np.zeros(n_wav_req)
        for i, bit in enumerate(bits):
            freq_arr_wav[i*sps_wav:(i+1)*sps_wav] = mark_freq if bit == '1' else space_freq
        phase_wav = 2 * np.pi * np.cumsum(freq_arr_wav) / fs_wav
        wav_data = np.sin(phase_wav)
        wav_int16 = (wav_data * 32767.0).astype(np.int16)
        wav_path = os.path.join(output_dir, f"{name_prefix}.wav")
        wavfile.write(wav_path, fs_wav, wav_int16)
        print(f"Generated: {wav_path}")

        # Generate IQ
        sps_iq = fs_iq // bit_rate
        n_iq_req = len(bits) * sps_iq
        freq_arr_iq = np.zeros(n_iq_req)
        for i, bit in enumerate(bits):
            freq_arr_iq[i*sps_iq:(i+1)*sps_iq] = mark_freq if bit == '1' else space_freq
        phase_iq = 2 * np.pi * np.cumsum(freq_arr_iq) / fs_iq
        complex_sig = np.exp(1j * phase_iq)
        iq_raw = np.empty(2 * n_iq_req, dtype=np.float32)
        iq_raw[0::2] = complex_sig.real.astype(np.float32)
        iq_raw[1::2] = complex_sig.imag.astype(np.float32)
        iq_path = os.path.join(output_dir, f"{name_prefix}.iq")
        iq_raw.tofile(iq_path)
        print(f"Generated: {iq_path}")

        # Meta
        meta = {
            "signal_type": name_prefix.upper(),
            "sample_rate_wav": fs_wav,
            "sample_rate_iq": fs_iq,
            "bit_rate": bit_rate,
            "mark_frequency": mark_freq,
            "space_frequency": space_freq,
            "original_pattern": base_bits,
            "total_bits": len(bits),
            **extra_meta
        }
        json_path = os.path.join(output_dir, f"{name_prefix}.json")
        with open(json_path, "w") as f:
            json.dump(meta, f, indent=4)
        print(f"Generated: {json_path}")

    # 2. Binary FSK
    total_bits_needed = int(duration * bit_rate)
    repetition_count = total_bits_needed // len(base_bits)
    repeated_bits = (base_bits * (repetition_count + 1))[:total_bits_needed]
    _generate_fsk(repeated_bits, "test_fsk", {
        "repetition_count": repetition_count,
        "repeated_bits": repeated_bits,
        "duration_seconds": duration,
        "sample_count": total_bits_needed * (fs_wav // bit_rate)
    })

    # 3. Block Interleaved FSK
    interleave_rows = 8
    interleave_cols = 8
    interleaved_total_bits = 2048
    interleaved_base_bits = (base_bits * (interleaved_total_bits // len(base_bits)))
    interleaved_bits = block_interleave(interleaved_base_bits, interleave_rows, interleave_cols)
    _generate_fsk(interleaved_bits, "test_interleaved_fsk", {
        "interleave_rows": interleave_rows,
        "interleave_cols": interleave_cols,
        "original_bits": interleaved_base_bits,
        "interleaved_bits": interleaved_bits
    })

    # 4. Conv Interleaved FSK
    conv_branches = 4
    conv_delay_step = 1
    conv_payload_bits_count = 2048
    conv_base_bits = (base_bits * (conv_payload_bits_count // len(base_bits)))
    conv_interleaved_bits = convolutional_interleave(
        conv_base_bits, branches=conv_branches, delay_step=conv_delay_step, flush=True
    )
    _generate_fsk(conv_interleaved_bits, "test_conv_interleaved_fsk", {
        "conv_branches": conv_branches,
        "conv_delay_step": conv_delay_step,
        "payload_bits_count": conv_payload_bits_count,
        "original_bits": conv_base_bits,
        "interleaved_bits": conv_interleaved_bits
    })

    # 5. FEC Convolutional
    fec_k = 3
    fec_g1 = 7
    fec_g2 = 5
    fec_payload_bits_count = 1024
    fec_base_bits = (base_bits * (fec_payload_bits_count // len(base_bits)))
    fec_encoded_bits = convolutional_encode(fec_base_bits, k=fec_k, g1=fec_g1, g2=fec_g2, flush=True)
    _generate_fsk(fec_encoded_bits, "test_fec_fsk", {
        "fec_type": "CONVOLUTIONAL",
        "rate": "1/2",
        "constraint_length": fec_k,
        "g1_octal": fec_g1,
        "g2_octal": fec_g2,
        "payload_bits_count": fec_payload_bits_count,
        "original_bits": fec_base_bits,
        "encoded_bits": fec_encoded_bits
    })

    # 6. Reed-Solomon
    rs_n = 255
    rs_k = 223
    rs_payload_bytes = (bytes([0xAB, 0xCD, 0x12, 0x34, 0x56, 0x78, 0x90, 0xEF]) * (rs_k // 8 + 1))[:rs_k]
    rs_payload_bits = bytes_to_bits(rs_payload_bytes)
    rs_encoded_bits = reed_solomon_encode(rs_payload_bits, n=rs_n, k=rs_k)
    _generate_fsk(rs_encoded_bits, "test_rs_fsk", {
        "fec_type": "REED_SOLOMON",
        "field_size": 8,
        "n": rs_n,
        "k": rs_k,
        "payload_bytes_count": rs_k,
        "encoded_bytes_count": rs_n,
        "payload_bits_count": len(rs_payload_bits),
        "original_bits": rs_payload_bits,
        "encoded_bits": rs_encoded_bits
    })

    # 7. Header Sync
    payload_message = b"HELLO_RADIO_SIGNAL"
    hdr_frame_bits, hdr_meta = build_synthetic_frame(
        sync_pattern=DEFAULT_SYNC_PATTERN,
        version=1,
        message_type=1,
        payload_bytes=payload_message,
        sequence=1001,
        flags=0
    )
    _generate_fsk(hdr_frame_bits, "test_header_fsk", {
        "encoded_bits": hdr_frame_bits,
        "payload_bytes": payload_message.decode('ascii'),
        **hdr_meta
    })

if __name__ == "__main__":
    generate_test_signals()
