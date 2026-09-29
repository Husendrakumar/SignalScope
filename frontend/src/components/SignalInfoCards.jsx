import React from 'react';
import { Info } from 'lucide-react';
import {
  getFileExtension,
  formatSampleRate,
  formatNumber,
  formatDuration
} from '../utils/fileHelpers';

export default function SignalInfoCards({ selectedFile, analysisData }) {
  const format = selectedFile?.format || (selectedFile ? getFileExtension(selectedFile.name) : '--');
  const sampleRate = selectedFile ? formatSampleRate(selectedFile.sample_rate) : '--';
  const sampleCount = selectedFile ? formatNumber(selectedFile.sample_count) : '--';
  const duration = selectedFile ? formatDuration(selectedFile.duration_seconds) : '--';
  const dataType = selectedFile?.data_type || '--';

  const snrDisplay = analysisData?.noise?.estimated_snr_db !== undefined
    ? `${analysisData.noise.estimated_snr_db.toFixed(1)} dB SNR`
    : '--';

  const infoItems = [
    { label: 'File Format', value: format, highlight: !!selectedFile },
    { label: 'Sampling Rate', value: sampleRate, highlight: !!selectedFile?.sample_rate },
    { label: 'Sample Count', value: sampleCount, highlight: !!selectedFile?.sample_count },
    { label: 'Signal Duration', value: duration, highlight: !!selectedFile?.duration_seconds },
    { label: 'Data Type', value: dataType, highlight: !!selectedFile?.data_type },
    { label: 'Estimated Quality', value: snrDisplay, highlight: !!analysisData },
  ];

  return (
    <section className="signal-info-section">
      <h2 className="section-title">
        <Info size={18} className="section-title-icon" />
        <span>Signal Information</span>
      </h2>

      <div className="info-cards-grid">
        {infoItems.map((item) => (
          <div key={item.label} className="info-card">
            <span className="info-card-label">{item.label}</span>
            <span className={`info-card-value ${item.highlight ? 'text-accent' : ''}`}>
              {item.value}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
