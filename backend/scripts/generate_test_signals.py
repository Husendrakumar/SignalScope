import os
import json
import numpy as np
from scipy.io import wavfile
from app.signal_processing.deinterleaving import block_interleave, convolutional_interleave
from app.signal_processing.fec import convolutional_encode, reed_solomon_encode, bytes_to_bits
from app.signal_processing.header import build_synthetic_frame, DEFAULT_SYNC_PATTERN


def generate_test_signals():
    """
    Generates controlled test signals for SignalScope:
    - test_sine.wav & test_sine.iq
    - test_fsk.wav & test_fsk.iq + test_fsk.json
    - test_interleaved_fsk.wav & test_interleaved_fsk.iq + test_interleaved_fsk.json (Block Part 9A)
    - test_conv_interleaved_fsk.wav & test_conv_interleaved_fsk.iq + test_conv_interleaved_fsk.json (Conv Part 9B)
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_backend_dir = os.path.dirname(script_dir)
    output_dir = os.path.join(project_backend_dir, "test_data")
    os.makedirs(output_dir, exist_ok=True)

    sample_rate = 48000
    duration = 2.0  # seconds
    n_samples = int(sample_rate * duration)
    t = np.arange(n_samples) / sample_rate

    # -------------------------------------------------------------
    # 1. Real Sine Wave (.wav) & Complex Sinusoid (.iq)
    # -------------------------------------------------------------
    tone_freq = 1000.0  # Hz

    sine_wav_data = np.sin(2 * np.pi * tone_freq * t)
    sine_int16 = (sine_wav_data * 32767.0).astype(np.int16)
    sine_wav_path = os.path.join(output_dir, "test_sine.wav")
    wavfile.write(sine_wav_path, sample_rate, sine_int16)
    print(f"Generated: {sine_wav_path}")

    complex_sine = np.exp(1j * 2 * np.pi * tone_freq * t)
    iq_sine_raw = np.empty(2 * n_samples, dtype=np.float32)
    iq_sine_raw[0::2] = complex_sine.real.astype(np.float32)
    iq_sine_raw[1::2] = complex_sine.imag.astype(np.float32)

    sine_iq_path = os.path.join(output_dir, "test_sine.iq")
    iq_sine_raw.tofile(sine_iq_path)
    print(f"Generated: {sine_iq_path}")

    # -------------------------------------------------------------
    # 2. Binary FSK Signals (.wav & .iq)
    # -------------------------------------------------------------
    bit_rate = 1000  # bits/sec
    mark_freq = 5000.0  # Hz (bit 1)
    space_freq = 8000.0  # Hz (bit 0)
    base_bits = "1011001011010011"

    samples_per_bit = sample_rate // bit_rate  # 48 samples per bit
    total_bits_needed = int(duration * bit_rate)  # 2000 bits
    repetition_count = total_bits_needed // len(base_bits)  # 125 repetitions
    repeated_bits = (base_bits * (repetition_count + 1))[:total_bits_needed]

    freq_arr = np.zeros(n_samples)
    for i, bit in enumerate(repeated_bits):
        start_idx = i * samples_per_bit
        end_idx = min(start_idx + samples_per_bit, n_samples)
        freq_arr[start_idx:end_idx] = mark_freq if bit == '1' else space_freq

    phase = 2 * np.pi * np.cumsum(freq_arr) / sample_rate

    fsk_wav_data = np.sin(phase)
    fsk_int16 = (fsk_wav_data * 32767.0).astype(np.int16)
    fsk_wav_path = os.path.join(output_dir, "test_fsk.wav")
    wavfile.write(fsk_wav_path, sample_rate, fsk_int16)
    print(f"Generated: {fsk_wav_path}")

    fsk_complex = np.exp(1j * phase)
    iq_fsk_raw = np.empty(2 * n_samples, dtype=np.float32)
    iq_fsk_raw[0::2] = fsk_complex.real.astype(np.float32)
    iq_fsk_raw[1::2] = fsk_complex.imag.astype(np.float32)

    fsk_iq_path = os.path.join(output_dir, "test_fsk.iq")
    iq_fsk_raw.tofile(fsk_iq_path)
    print(f"Generated: {fsk_iq_path}")

    fsk_meta = {
        "signal_type": "FSK",
        "sample_rate": sample_rate,
        "bit_rate": bit_rate,
        "mark_frequency": mark_freq,
        "space_frequency": space_freq,
        "original_pattern": base_bits,
        "repetition_count": repetition_count,
        "total_bits": total_bits_needed,
        "repeated_bits": repeated_bits,
        "duration_seconds": duration,
        "sample_count": n_samples
    }
    fsk_json_path = os.path.join(output_dir, "test_fsk.json")
    with open(fsk_json_path, "w") as f:
        json.dump(fsk_meta, f, indent=4)
    print(f"Generated: {fsk_json_path}")

    # -------------------------------------------------------------
    # 3. Block Interleaved Binary FSK Signals (.wav & .iq) [Part 9A]
    # -------------------------------------------------------------
    # 2048 bits = 32 blocks of 8x8 (64 bits per block)
    interleave_rows = 8
    interleave_cols = 8
    interleaved_total_bits = 2048
    interleaved_samples_count = interleaved_total_bits * samples_per_bit  # 98304 samples (2.048s)
    interleaved_duration = interleaved_samples_count / sample_rate

    interleaved_base_bits = (base_bits * (interleaved_total_bits // len(base_bits)))
    interleaved_bits = block_interleave(interleaved_base_bits, interleave_rows, interleave_cols)

    freq_arr_int = np.zeros(interleaved_samples_count)
    for i, bit in enumerate(interleaved_bits):
        start_idx = i * samples_per_bit
        end_idx = min(start_idx + samples_per_bit, interleaved_samples_count)
        freq_arr_int[start_idx:end_idx] = mark_freq if bit == '1' else space_freq

    phase_int = 2 * np.pi * np.cumsum(freq_arr_int) / sample_rate

    fsk_int_wav_data = np.sin(phase_int)
    fsk_int_wav_int16 = (fsk_int_wav_data * 32767.0).astype(np.int16)
    fsk_int_wav_path = os.path.join(output_dir, "test_interleaved_fsk.wav")
    wavfile.write(fsk_int_wav_path, sample_rate, fsk_int_wav_int16)
    print(f"Generated: {fsk_int_wav_path}")

    fsk_int_complex = np.exp(1j * phase_int)
    iq_fsk_int_raw = np.empty(2 * interleaved_samples_count, dtype=np.float32)
    iq_fsk_int_raw[0::2] = fsk_int_complex.real.astype(np.float32)
    iq_fsk_int_raw[1::2] = fsk_int_complex.imag.astype(np.float32)

    fsk_int_iq_path = os.path.join(output_dir, "test_interleaved_fsk.iq")
    iq_fsk_int_raw.tofile(fsk_int_iq_path)
    print(f"Generated: {fsk_int_iq_path}")

    interleaved_meta = {
        "signal_type": "INTERLEAVED_FSK",
        "sample_rate": sample_rate,
        "bit_rate": bit_rate,
        "mark_frequency": mark_freq,
        "space_frequency": space_freq,
        "original_pattern": base_bits,
        "interleave_rows": interleave_rows,
        "interleave_cols": interleave_cols,
        "total_bits": interleaved_total_bits,
        "original_bits": interleaved_base_bits,
        "interleaved_bits": interleaved_bits,
        "duration_seconds": interleaved_duration,
        "sample_count": interleaved_samples_count
    }
    interleaved_json_path = os.path.join(output_dir, "test_interleaved_fsk.json")
    with open(interleaved_json_path, "w") as f:
        json.dump(interleaved_meta, f, indent=4)
    print(f"Generated: {interleaved_json_path}")

    # -------------------------------------------------------------
    # 4. Convolutionally Interleaved Binary FSK Signals (.wav & .iq) [Part 9B]
    # -------------------------------------------------------------
    conv_branches = 4
    conv_delay_step = 1
    conv_payload_bits_count = 2048
    conv_base_bits = (base_bits * (conv_payload_bits_count // len(base_bits)))
    conv_interleaved_bits = convolutional_interleave(
        conv_base_bits, branches=conv_branches, delay_step=conv_delay_step, flush=True
    )
    conv_total_bits = len(conv_interleaved_bits)  # 2048 + 12 = 2060 bits
    conv_samples_count = conv_total_bits * samples_per_bit
    conv_duration = conv_samples_count / sample_rate

    freq_arr_conv = np.zeros(conv_samples_count)
    for i, bit in enumerate(conv_interleaved_bits):
        start_idx = i * samples_per_bit
        end_idx = min(start_idx + samples_per_bit, conv_samples_count)
        freq_arr_conv[start_idx:end_idx] = mark_freq if bit == '1' else space_freq

    phase_conv = 2 * np.pi * np.cumsum(freq_arr_conv) / sample_rate

    fsk_conv_wav_data = np.sin(phase_conv)
    fsk_conv_wav_int16 = (fsk_conv_wav_data * 32767.0).astype(np.int16)
    fsk_conv_wav_path = os.path.join(output_dir, "test_conv_interleaved_fsk.wav")
    wavfile.write(fsk_conv_wav_path, sample_rate, fsk_conv_wav_int16)
    print(f"Generated: {fsk_conv_wav_path}")

    fsk_conv_complex = np.exp(1j * phase_conv)
    iq_fsk_conv_raw = np.empty(2 * conv_samples_count, dtype=np.float32)
    iq_fsk_conv_raw[0::2] = fsk_conv_complex.real.astype(np.float32)
    iq_fsk_conv_raw[1::2] = fsk_conv_complex.imag.astype(np.float32)

    fsk_conv_iq_path = os.path.join(output_dir, "test_conv_interleaved_fsk.iq")
    iq_fsk_conv_raw.tofile(fsk_conv_iq_path)
    print(f"Generated: {fsk_conv_iq_path}")

    conv_meta = {
        "signal_type": "CONVOLUTIONAL_INTERLEAVED_FSK",
        "sample_rate": sample_rate,
        "bit_rate": bit_rate,
        "mark_frequency": mark_freq,
        "space_frequency": space_freq,
        "original_pattern": base_bits,
        "conv_branches": conv_branches,
        "conv_delay_step": conv_delay_step,
        "pipeline_latency_bits": (conv_branches - 1) * conv_delay_step * conv_branches,
        "payload_bits_count": conv_payload_bits_count,
        "total_bits": conv_total_bits,
        "original_bits": conv_base_bits,
        "interleaved_bits": conv_interleaved_bits,
        "duration_seconds": conv_duration,
        "sample_count": conv_samples_count
    }
    conv_json_path = os.path.join(output_dir, "test_conv_interleaved_fsk.json")
    with open(conv_json_path, "w") as f:
        json.dump(conv_meta, f, indent=4)
    print(f"Generated: {conv_json_path}")

    # -------------------------------------------------------------
    # 5. Convolutional FEC Encoded FSK Signals (.wav & .iq) [Part 10A]
    # -------------------------------------------------------------
    fec_k = 3
    fec_g1 = 7
    fec_g2 = 5
    fec_payload_bits_count = 1024
    fec_base_bits = (base_bits * (fec_payload_bits_count // len(base_bits)))
    fec_encoded_bits = convolutional_encode(fec_base_bits, k=fec_k, g1=fec_g1, g2=fec_g2, flush=True)
    fec_total_bits = len(fec_encoded_bits)  # (1024 + 2) * 2 = 2052 bits
    fec_samples_count = fec_total_bits * samples_per_bit
    fec_duration = fec_samples_count / sample_rate

    freq_arr_fec = np.zeros(fec_samples_count)
    for i, bit in enumerate(fec_encoded_bits):
        start_idx = i * samples_per_bit
        end_idx = min(start_idx + samples_per_bit, fec_samples_count)
        freq_arr_fec[start_idx:end_idx] = mark_freq if bit == '1' else space_freq

    phase_fec = 2 * np.pi * np.cumsum(freq_arr_fec) / sample_rate

    fsk_fec_wav_data = np.sin(phase_fec)
    fsk_fec_wav_int16 = (fsk_fec_wav_data * 32767.0).astype(np.int16)
    fsk_fec_wav_path = os.path.join(output_dir, "test_fec_fsk.wav")
    wavfile.write(fsk_fec_wav_path, sample_rate, fsk_fec_wav_int16)
    print(f"Generated: {fsk_fec_wav_path}")

    fsk_fec_complex = np.exp(1j * phase_fec)
    iq_fsk_fec_raw = np.empty(2 * fec_samples_count, dtype=np.float32)
    iq_fsk_fec_raw[0::2] = fsk_fec_complex.real.astype(np.float32)
    iq_fsk_fec_raw[1::2] = fsk_fec_complex.imag.astype(np.float32)

    fsk_fec_iq_path = os.path.join(output_dir, "test_fec_fsk.iq")
    iq_fsk_fec_raw.tofile(fsk_fec_iq_path)
    print(f"Generated: {fsk_fec_iq_path}")

    fec_meta = {
        "signal_type": "FEC_FSK",
        "sample_rate": sample_rate,
        "bit_rate": bit_rate,
        "mark_frequency": mark_freq,
        "space_frequency": space_freq,
        "original_pattern": base_bits,
        "fec_type": "CONVOLUTIONAL",
        "rate": "1/2",
        "constraint_length": fec_k,
        "g1_octal": fec_g1,
        "g2_octal": fec_g2,
        "payload_bits_count": fec_payload_bits_count,
        "encoded_bits_count": fec_total_bits,
        "original_bits": fec_base_bits,
        "encoded_bits": fec_encoded_bits,
        "duration_seconds": fec_duration,
        "sample_count": fec_samples_count
    }
    fec_json_path = os.path.join(output_dir, "test_fec_fsk.json")
    with open(fec_json_path, "w") as f:
        json.dump(fec_meta, f, indent=4)
    print(f"Generated: {fec_json_path}")

    # -------------------------------------------------------------
    # 6. Reed-Solomon FEC Encoded FSK Signals (.wav & .iq) [Part 10B]
    # -------------------------------------------------------------
    rs_n = 255
    rs_k = 223
    rs_payload_bytes = (bytes([0xAB, 0xCD, 0x12, 0x34, 0x56, 0x78, 0x90, 0xEF]) * (rs_k // 8 + 1))[:rs_k]
    rs_payload_bits = bytes_to_bits(rs_payload_bytes)  # 223 * 8 = 1784 bits
    rs_encoded_bits = reed_solomon_encode(rs_payload_bits, n=rs_n, k=rs_k)  # 255 * 8 = 2040 bits
    rs_total_bits = len(rs_encoded_bits)
    rs_samples_count = rs_total_bits * samples_per_bit
    rs_duration = rs_samples_count / sample_rate

    freq_arr_rs = np.zeros(rs_samples_count)
    for i, bit in enumerate(rs_encoded_bits):
        start_idx = i * samples_per_bit
        end_idx = min(start_idx + samples_per_bit, rs_samples_count)
        freq_arr_rs[start_idx:end_idx] = mark_freq if bit == '1' else space_freq

    phase_rs = 2 * np.pi * np.cumsum(freq_arr_rs) / sample_rate

    fsk_rs_wav_data = np.sin(phase_rs)
    fsk_rs_wav_int16 = (fsk_rs_wav_data * 32767.0).astype(np.int16)
    fsk_rs_wav_path = os.path.join(output_dir, "test_rs_fsk.wav")
    wavfile.write(fsk_rs_wav_path, sample_rate, fsk_rs_wav_int16)
    print(f"Generated: {fsk_rs_wav_path}")

    fsk_rs_complex = np.exp(1j * phase_rs)
    iq_fsk_rs_raw = np.empty(2 * rs_samples_count, dtype=np.float32)
    iq_fsk_rs_raw[0::2] = fsk_rs_complex.real.astype(np.float32)
    iq_fsk_rs_raw[1::2] = fsk_rs_complex.imag.astype(np.float32)

    fsk_rs_iq_path = os.path.join(output_dir, "test_rs_fsk.iq")
    iq_fsk_rs_raw.tofile(fsk_rs_iq_path)
    print(f"Generated: {fsk_rs_iq_path}")

    rs_meta = {
        "signal_type": "REED_SOLOMON_FSK",
        "sample_rate": sample_rate,
        "bit_rate": bit_rate,
        "mark_frequency": mark_freq,
        "space_frequency": space_freq,
        "fec_type": "REED_SOLOMON",
        "field_size": 8,
        "n": rs_n,
        "k": rs_k,
        "parity_symbols": rs_n - rs_k,
        "payload_bytes_count": rs_k,
        "encoded_bytes_count": rs_n,
        "payload_bits_count": len(rs_payload_bits),
        "encoded_bits_count": rs_total_bits,
        "original_bits": rs_payload_bits,
        "encoded_bits": rs_encoded_bits,
        "duration_seconds": rs_duration,
        "sample_count": rs_samples_count
    }
    rs_json_path = os.path.join(output_dir, "test_rs_fsk.json")
    with open(rs_json_path, "w") as f:
        json.dump(rs_meta, f, indent=4)
    print(f"Generated: {rs_json_path}")

    # -------------------------------------------------------------
    # 7. Header & Synchronization FSK Signals (.wav & .iq) [Part 11]
    # -------------------------------------------------------------
    payload_message = b"HELLO_RADIO_SIGNAL"  # 18 bytes = 144 bits
    hdr_frame_bits, hdr_meta = build_synthetic_frame(
        sync_pattern=DEFAULT_SYNC_PATTERN,
        version=1,
        message_type=1,
        payload_bytes=payload_message,
        sequence=1001,
        flags=0
    )
    hdr_total_bits = len(hdr_frame_bits)  # 32 + 72 + 144 = 248 bits
    hdr_samples_count = hdr_total_bits * samples_per_bit
    hdr_duration = hdr_samples_count / sample_rate

    freq_arr_hdr = np.zeros(hdr_samples_count)
    for i, bit in enumerate(hdr_frame_bits):
        start_idx = i * samples_per_bit
        end_idx = min(start_idx + samples_per_bit, hdr_samples_count)
        freq_arr_hdr[start_idx:end_idx] = mark_freq if bit == '1' else space_freq

    phase_hdr = 2 * np.pi * np.cumsum(freq_arr_hdr) / sample_rate

    fsk_hdr_wav_data = np.sin(phase_hdr)
    fsk_hdr_wav_int16 = (fsk_hdr_wav_data * 32767.0).astype(np.int16)
    fsk_hdr_wav_path = os.path.join(output_dir, "test_header_fsk.wav")
    wavfile.write(fsk_hdr_wav_path, sample_rate, fsk_hdr_wav_int16)
    print(f"Generated: {fsk_hdr_wav_path}")

    fsk_hdr_complex = np.exp(1j * phase_hdr)
    iq_fsk_hdr_raw = np.empty(2 * hdr_samples_count, dtype=np.float32)
    iq_fsk_hdr_raw[0::2] = fsk_hdr_complex.real.astype(np.float32)
    iq_fsk_hdr_raw[1::2] = fsk_hdr_complex.imag.astype(np.float32)

    fsk_hdr_iq_path = os.path.join(output_dir, "test_header_fsk.iq")
    iq_fsk_hdr_raw.tofile(fsk_hdr_iq_path)
    print(f"Generated: {fsk_hdr_iq_path}")

    hdr_meta_full = {
        "signal_type": "HEADER_SYNC_FSK",
        "sample_rate": sample_rate,
        "bit_rate": bit_rate,
        "mark_frequency": mark_freq,
        "space_frequency": space_freq,
        "encoded_bits": hdr_frame_bits,
        "duration_seconds": hdr_duration,
        "sample_count": hdr_samples_count,
        "payload_bytes": payload_message.decode('ascii'),
        **hdr_meta
    }
    hdr_json_path = os.path.join(output_dir, "test_header_fsk.json")
    with open(hdr_json_path, "w") as f:
        json.dump(hdr_meta_full, f, indent=4)
    print(f"Generated: {hdr_json_path}")


if __name__ == "__main__":
    generate_test_signals()



