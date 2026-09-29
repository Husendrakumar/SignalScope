/**
 * Formats file size bytes to human-readable string (KB, MB, etc.)
 */
export function formatBytes(bytes, decimals = 2) {
  if (!bytes || bytes === 0) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

/**
 * Formats timestamp to readable date string e.g., "29 Sep 2026"
 */
export function formatDate(timestamp) {
  if (!timestamp) return '--';
  const d = new Date(timestamp);
  return d.toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric'
  });
}

/**
 * Extracts normalized file extension (e.g. "WAV" or "IQ")
 */
export function getFileExtension(filename) {
  if (!filename) return '';
  const parts = filename.split('.');
  if (parts.length < 2) return '';
  return parts.pop().toUpperCase();
}

/**
 * Formats sample rate Hz into readable string e.g. "48000 Hz"
 */
export function formatSampleRate(hz) {
  if (hz == null || isNaN(hz)) return '--';
  return `${hz} Hz`;
}

/**
 * Formats sample count number e.g. "96000"
 */
export function formatNumber(num) {
  if (num == null || isNaN(num)) return '--';
  return String(num);
}

/**
 * Formats duration seconds into readable string e.g. "2.00 s"
 */
export function formatDuration(seconds) {
  if (seconds == null || isNaN(seconds)) return '--';
  return `${Number(seconds).toFixed(2)} s`;
}
