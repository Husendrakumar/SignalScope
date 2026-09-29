import os
import numpy as np
import scipy.signal
from fastapi.testclient import TestClient
from app.main import app

def test_demod_padded():
    client = TestClient(app)
    path = os.path.join("test_data", "test_fsk.wav")
    with open(path, "rb") as f:
        res = client.post("/api/files/upload", files={"file": ("test_fsk.wav", f, "audio/wav")})
    sig_id = res.json()["signal_id"]
    from app.signal_processing.session_manager import session_store
    signal = session_store.get_session(sig_id)

    fs = signal.sample_rate
    sps = 48
    real_samples = np.real(signal.samples).astype(np.float64)

    # Pad before Hilbert transform to eliminate boundary transients!
    pad_len = sps * 4
    padded = np.pad(real_samples, (pad_len, pad_len), mode='reflect')
    analytic_padded = scipy.signal.hilbert(padded)
    analytic = analytic_padded[pad_len : -pad_len]

    phases = np.angle(analytic)
    unwrapped = np.unwrap(phases)
    inst_freq = np.diff(unwrapped) / (2.0 * np.pi) * fs

    f_low = 5000.0
    f_high = 8000.0
    n_samples = len(inst_freq)
    num_symbols = n_samples // sps

    best_offset = 0
    min_error = float("inf")
    search_symbols = min(num_symbols, 200)

    for offset in range(sps):
        err = 0.0
        for j in range(search_symbols):
            start_i = offset + j * sps
            end_i = start_i + sps
            if end_i > n_samples:
                break
            block_f = np.mean(inst_freq[start_i:end_i])
            err += min((block_f - f_low) ** 2, (block_f - f_high) ** 2)

        if err < min_error:
            min_error = err
            best_offset = offset

    print("Best offset with padded Hilbert:", best_offset)

    bits = []
    for j in range(num_symbols):
        start_i = best_offset + j * sps
        end_i = start_i + sps
        if end_i > n_samples:
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

    print("Recovered first 64:", bit_string[:64])
    print("Expected  first 64:", expected_full[:64])

    compare_len = min(len(bit_string), len(expected_full))
    errors = sum(1 for i in range(compare_len) if bit_string[i] != expected_full[i])
    print(f"Errors: {errors} / {compare_len} (Accuracy: {(1 - errors/compare_len)*100:.2f}%)")

if __name__ == "__main__":
    test_demod_padded()
