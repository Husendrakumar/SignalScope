import React from 'react';
import { ShieldAlert } from 'lucide-react';

export default function AnalysisStatus({ selectedFile, analysisData }) {
  const isLoaded = !!selectedFile;
  const isAnalyzed = !!analysisData;

  const statusText = isAnalyzed
    ? (analysisData.activity?.status || 'ACTIVE_SIGNAL')
    : (isLoaded ? 'Signal loaded' : 'Waiting for signal');

  const pipelineText = isAnalyzed
    ? 'Stage 02 Complete'
    : (isLoaded ? 'Stage 01 Complete' : 'Not started');

  const snrText = isAnalyzed && analysisData.noise?.estimated_snr_db !== undefined
    ? `${analysisData.noise.estimated_snr_db.toFixed(1)} dB`
    : '--';

  return (
    <div className="status-section">
      <h2 className="section-title">
        <ShieldAlert size={18} className="section-title-icon" />
        <span>Analysis Status</span>
      </h2>

      <div className="status-details-list">
        <div className="status-row">
          <span className="status-label">Status</span>
          <span className={`status-value ${isLoaded ? 'text-ready' : ''}`}>
            {statusText}
          </span>
        </div>
        <div className="status-row">
          <span className="status-label">Pipeline</span>
          <span className={`status-value ${isLoaded ? 'text-accent' : ''}`}>
            {pipelineText}
          </span>
        </div>
        <div className="status-row">
          <span className="status-label">Estimated SNR</span>
          <span className="status-value mono">{snrText}</span>
        </div>
      </div>
    </div>
  );
}
