import os
import numpy as np
import scipy.signal
from fastapi.testclient import TestClient
from app.main import app

def test_fixed_offset_iq():
    client = TestClient(app)
    path = os.path.join("test_data", "test_fsk.iq")
    with open(path, "rb") as f:
        res = client.post("/api/files/upload", files={"file": ("test_fsk.iq", f, "application/octet-stream")})
    sig_id = res.json()["signal_id"]
    from app.signal_processing.session_manager import session_store
    signal = session_store.get_session(sig_id)

    fs = signal.sample_rate
    sps = 48
    analytic = signal.samples.astype(np.complex128)

    phases = np.angle(analytic)
    unwrapped = np.unwrap(phases)
    inst_freq = np.diff(unwrapped) / (2.0 * np.pi) * fs

    f_low = 5000.0
    f_high = 8000.0
    n_samples = len(inst_freq)
    num_symbols = (n_samples + sps - 1) // sps

    best_offset = 0
    min_error = float("inf")
    search_symbols = min(num_symbols, 200)

    for offset in range(sps):
        err = 0.0
        for j in range(search_symbols):
            start_i = offset + j * sps
            end_i = min(start_i + sps, n_samples)
            if start_i >= n_samples:
                break
            block_f = np.mean(inst_freq[start_i:end_i])
            err += min((block_f - f_low) ** 2, (block_f - f_high) ** 2)

        if err < min_error:
            min_error = err
            best_offset = offset

    aligned_offset = (best_offset + 1) % sps
    print("IQ best_offset:", best_offset, "-> aligned_offset:", aligned_offset)

    bits = []
    for j in range(num_symbols):
        start_i = aligned_offset + j * sps
        end_i = min(start_i + sps, n_samples)
        if start_i >= n_samples:
            break
        block_f = float(np.mean(inst_freq[start_i:end_i]))
        dist_low = abs(block_f - f_low)
        dist_high = abs(block_f - f_high)
        if dist_low <= dist_high:
            bits.append('1')
        else:
            bits.append('0')

    bit_string = "".join(bits)
    expected_pattern = "1011001011010011"
    expected_full = expected_pattern * 125

    print("Recovered IQ first 64:", bit_string[:64])
    print("Expected  IQ first 64:", expected_full[:64])

    compare_len = min(len(bit_string), len(expected_full))
    errors = sum(1 for i in range(compare_len) if bit_string[i] != expected_full[i])
    print(f"Errors IQ: {errors} / {compare_len} (Accuracy: {(1 - errors/compare_len)*100:.2f}%)")

if __name__ == "__main__":
    test_fixed_offset_iq()
