import React from 'react';
import { Play, Trash2, CheckCircle2 } from 'lucide-react';
import {
  formatBytes,
  formatDate,
  getFileExtension,
  formatSampleRate,
  formatNumber,
  formatDuration
} from '../utils/fileHelpers';

export default function FileInfoCard({ fileObj, onClear, onAnalyze }) {
  if (!fileObj) return null;

  const ext = fileObj.format || getFileExtension(fileObj.name);

  return (
    <div className="file-info-card">
      <div className="file-info-header">
        <div className="file-status-title">
          <CheckCircle2 size={18} className="text-ready" />
          <span>Signal file loaded</span>
        </div>
        <button
          type="button"
          onClick={onClear}
          className="btn-icon-danger"
          title="Remove file"
        >
          <Trash2 size={16} />
          <span>Remove</span>
        </button>
      </div>

      <div className="file-details-grid">
        <div className="file-detail-item">
          <span className="detail-label">File Name</span>
          <span className="detail-value mono text-highlight">{fileObj.name}</span>
        </div>

        <div className="file-detail-item">
          <span className="detail-label">Format</span>
          <span className="detail-value mono badge-ext">{ext}</span>
        </div>

        <div className="file-detail-item">
          <span className="detail-label">File Size</span>
          <span className="detail-value mono">{formatBytes(fileObj.size)}</span>
        </div>

        <div className="file-detail-item">
          <span className="detail-label">Sample Rate</span>
          <span className="detail-value mono">{formatSampleRate(fileObj.sample_rate)}</span>
        </div>

        <div className="file-detail-item">
          <span className="detail-label">Sample Count</span>
          <span className="detail-value mono">{formatNumber(fileObj.sample_count)}</span>
        </div>

        <div className="file-detail-item">
          <span className="detail-label">Duration</span>
          <span className="detail-value mono">{formatDuration(fileObj.duration_seconds)}</span>
        </div>

        <div className="file-detail-item">
          <span className="detail-label">Data Type</span>
          <span className="detail-value mono text-accent">{fileObj.data_type || '--'}</span>
        </div>

        <div className="file-detail-item">
          <span className="detail-label">Last Modified</span>
          <span className="detail-value mono">{formatDate(fileObj.lastModified)}</span>
        </div>
      </div>

      <div className="file-info-actions">
        <button type="button" className="btn-analyze" onClick={onAnalyze}>
          <Play size={16} />
          <span>Analyze Signal</span>
        </button>
      </div>
    </div>
  );
}
