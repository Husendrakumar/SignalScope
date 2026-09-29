const API_BASE_URL = '';

/**
 * Checks if the FastAPI backend is running and healthy.
 * @returns {Promise<boolean>} True if backend responds with ok status.
 */
export async function checkBackendHealth() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/health`);
    if (!response.ok) return false;
    const data = await response.json();
    return data.status === 'ok';
  } catch (error) {
    return false;
  }
}

/**
 * Uploads a signal file (.wav or .iq) to the backend.
 * @param {File} file - The file to upload.
 * @returns {Promise<Object>} Metadata object containing signal_id and properties.
 */
export async function uploadSignalFile(file) {
  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await fetch(`${API_BASE_URL}/api/files/upload`, {
      method: 'POST',
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || 'Failed to upload file to backend.');
    }

    return data;
  } catch (error) {
    if (error.message && (error.message.includes('Failed to fetch') || error.message.includes('NetworkError'))) {
      throw new Error('Unable to connect to the analysis backend. Please ensure the FastAPI server is running.');
    }
    throw error;
  }
}

/**
 * Fetches downsampled time-domain waveform data for a signal session.
 */
export async function fetchWaveformData(signalId, maxPoints = 1000, domFreq = 0.0) {
  const response = await fetch(`${API_BASE_URL}/api/visualization/waveform/${signalId}?max_points=${maxPoints}&dom_freq=${domFreq}`);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || 'Failed to fetch waveform visualization.');
  }
  return data;
}

/**
 * Fetches FFT frequency spectrum data (in dB) for a signal session.
 */
export async function fetchSpectrumData(signalId, nfft = 2048) {
  const response = await fetch(`${API_BASE_URL}/api/visualization/spectrum/${signalId}?nfft=${nfft}`);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || 'Failed to fetch FFT spectrum visualization.');
  }
  return data;
}

/**
 * Fetches 2D Spectrogram / Waterfall matrix data for a signal session.
 */
export async function fetchSpectrogramData(signalId, nfft = 512, hopLength = 256) {
  const response = await fetch(`${API_BASE_URL}/api/visualization/spectrogram/${signalId}?nfft=${nfft}&hop_length=${hopLength}`);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || 'Failed to fetch spectrogram visualization.');
  }
  return data;
}

/**
 * Fetches I/Q constellation scatter plot points for an IQ signal session.
 */
export async function fetchConstellationData(signalId, maxPoints = 1000) {
  const response = await fetch(`${API_BASE_URL}/api/visualization/constellation/${signalId}?max_points=${maxPoints}`);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || 'Failed to fetch constellation visualization.');
  }
  return data;
}

/**
 * Fetches deterministic signal analysis measurements for a signal session.
 */
export async function fetchSignalAnalysis(signalId) {
  const response = await fetch(`${API_BASE_URL}/api/analysis/${signalId}`);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || 'Failed to fetch signal analysis.');
  }
  return data;
}

/**
 * Fetches explainable modulation classification for a signal session.
 */
export async function fetchModulationAnalysis(signalId) {
  const response = await fetch(`${API_BASE_URL}/api/modulation/${signalId}`);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || 'Failed to fetch modulation classification.');
  }
  return data;
}

/**
 * Executes binary FSK demodulation for an FSK signal session.
 */
export async function fetchFskDemodulation(signalId) {
  const response = await fetch(`${API_BASE_URL}/api/demodulation/fsk/${signalId}`, {
    method: 'POST',
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || 'Failed to execute FSK demodulation.');
  }
  return data;
}

/**
 * Executes rectangular block de-interleaving on demodulated bitstream.
 */
export async function fetchBlockDeinterleaving(signalId, rows = 8, cols = 8) {
  const response = await fetch(`${API_BASE_URL}/api/deinterleaving/block/${signalId}?rows=${rows}&cols=${cols}`, {
    method: 'POST',
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || 'Failed to execute block de-interleaving.');
  }
  return data;
}

/**
 * Executes convolutional shift-register de-interleaving on demodulated bitstream.
 */
export async function fetchConvolutionalDeinterleaving(signalId, branches = 4, delayStep = 1) {
  const response = await fetch(`${API_BASE_URL}/api/deinterleaving/convolutional/${signalId}?branches=${branches}&delay_step=${delayStep}`, {
    method: 'POST',
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || 'Failed to execute convolutional de-interleaving.');
  }
  return data;
}

/**
 * Executes Hard-Decision Viterbi Trellis Decoding on demodulated bitstream.
 */
export async function fetchViterbiFecDecoding(signalId, constraintLength = 3, g1 = 7, g2 = 5) {
  const response = await fetch(`${API_BASE_URL}/api/fec/viterbi/${signalId}?constraint_length=${constraintLength}&g1=${g1}&g2=${g2}`, {
    method: 'POST',
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || 'Failed to execute Viterbi FEC decoding.');
  }
  return data;
}

/**
 * Executes Reed-Solomon FEC Decoding on demodulated bitstream.
 */
export async function fetchReedSolomonFecDecoding(signalId, n = 255, k = 223) {
  const response = await fetch(`${API_BASE_URL}/api/fec/reed-solomon/${signalId}?n=${n}&k=${k}`, {
    method: 'POST',
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || 'Failed to execute Reed-Solomon FEC decoding.');
  }
  return data;
}

/**
 * Executes Synchronization Pattern Search, Header Parsing, and CRC Validation.
 */
export async function fetchHeaderDetection(signalId, syncPattern = '10101010101010101100110011001100', maxErrors = 2) {
  const response = await fetch(`${API_BASE_URL}/api/header/detect/${signalId}?sync_pattern=${encodeURIComponent(syncPattern)}&max_errors=${maxErrors}`, {
    method: 'POST',
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || 'Failed to execute header and sync detection.');
  }
  return data;
}

/**
 * Executes Final Payload/Data Extraction based on Stage 07 validated header boundaries.
 */
export async function fetchPayloadExtraction(signalId, syncPattern = '10101010101010101100110011001100', maxErrors = 2) {
  const response = await fetch(`${API_BASE_URL}/api/payload/extract/${signalId}?sync_pattern=${encodeURIComponent(syncPattern)}&max_errors=${maxErrors}`, {
    method: 'POST',
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || 'Failed to execute final payload extraction.');
  }
  return data;
}






