import React, { useState } from 'react';
import { Cpu, Activity, Zap, Radio, ShieldCheck, RefreshCw, AlertCircle, Compass, Binary, Copy, Check, Grid } from 'lucide-react';

function formatFrequencyDisplay(hz) {
  if (hz === undefined || hz === null || isNaN(hz)) return '--';
  const abs = Math.abs(hz);
  if (abs >= 1e6) return `${(hz / 1e6).toFixed(3)} MHz`;
  if (abs >= 1e3) return `${(hz / 1e3).toFixed(2)} kHz`;
  return `${hz.toFixed(1)} Hz`;
}

function formatPower(val) {
  if (val === undefined || val === null || isNaN(val)) return '--';
  if (val < 1e-4) return val.toExponential(3);
  return val.toFixed(5);
}

export default function AnalysisResultsSection({
  analysisData,
  modulationData,
  demodData,
  deintData,
  convDeintData,
  fecData,
  rsFecData,
  headerData,
  payloadData,
  loading,
  error,
  onAnalyze
}) {
  const [copiedBits, setCopiedBits] = useState(false);
  const [copiedDeintBits, setCopiedDeintBits] = useState(false);
  const [copiedConvBits, setCopiedConvBits] = useState(false);
  const [copiedFecBits, setCopiedFecBits] = useState(false);
  const [copiedRsBits, setCopiedRsBits] = useState(false);
  const [copiedPayloadText, setCopiedPayloadText] = useState(false);
  const [copiedPayloadHex, setCopiedPayloadHex] = useState(false);

  const handleCopyBits = (text, type) => {
    if (text) {
      navigator.clipboard.writeText(text);
      if (type === 'demod') {
        setCopiedBits(true);
        setTimeout(() => setCopiedBits(false), 2000);
      } else if (type === 'deint') {
        setCopiedDeintBits(true);
        setTimeout(() => setCopiedDeintBits(false), 2000);
      } else if (type === 'conv') {
        setCopiedConvBits(true);
        setTimeout(() => setCopiedConvBits(false), 2000);
      } else if (type === 'fec') {
        setCopiedFecBits(true);
        setTimeout(() => setCopiedFecBits(false), 2000);
      } else if (type === 'rs') {
        setCopiedRsBits(true);
        setTimeout(() => setCopiedRsBits(false), 2000);
      } else if (type === 'payloadText') {
        setCopiedPayloadText(true);
        setTimeout(() => setCopiedPayloadText(false), 2000);
      } else if (type === 'payloadHex') {
        setCopiedPayloadHex(true);
        setTimeout(() => setCopiedPayloadHex(false), 2000);
      }
    }
  };

  if (loading) {
    return (
      <section className="analysis-results-section">
        <h2 className="section-title">
          <Cpu size={18} className="section-title-icon" />
          <span>Signal Analysis & De-interleaving Results</span>
        </h2>
        <div className="viz-placeholder">
          <RefreshCw size={24} className="spin text-accent" />
          <div className="viz-primary-text">Running signal processing pipeline…</div>
          <div className="viz-sub-text">Executing statistics, noise estimation, modulation recognition, FSK demodulation, and de-interleaving analysis.</div>
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="analysis-results-section">
        <h2 className="section-title">
          <Cpu size={18} className="section-title-icon" />
          <span>Signal Analysis & De-interleaving Results</span>
        </h2>
        <div className="viz-placeholder error">
          <AlertCircle size={24} className="text-danger" />
          <div className="viz-primary-text text-danger">Analysis Failed</div>
          <div className="viz-sub-text">{error}</div>
          {onAnalyze && (
            <button type="button" className="btn-primary mt-2" onClick={onAnalyze}>
              <span>Retry Analysis</span>
            </button>
          )}
        </div>
      </section>
    );
  }

  if (!analysisData) {
    return (
      <section className="analysis-results-section">
        <div className="section-header-row">
          <h2 className="section-title">
            <Cpu size={18} className="section-title-icon" />
            <span>Signal Analysis & De-interleaving Results</span>
          </h2>
          {onAnalyze && (
            <button type="button" className="btn-analyze" onClick={onAnalyze}>
              <Cpu size={14} />
              <span>Run Signal Analysis</span>
            </button>
          )}
        </div>
        <div className="viz-placeholder">
          <Activity className="viz-placeholder-icon" />
          <div className="viz-primary-text">Signal Analysis Pending</div>
          <div className="viz-sub-text">Click "Run Signal Analysis" to calculate statistics, SNR, frequency, bandwidth, modulation, and de-interleaved bitstream.</div>
        </div>
      </section>
    );
  }

  const { statistics = {}, noise = {}, frequency = {}, bandwidth = {}, activity = {} } = analysisData;

  const modType = modulationData?.modulation || 'PENDING';
  const confidencePct = modulationData?.confidence_score !== undefined
    ? `${(modulationData.confidence_score * 100).toFixed(0)}%`
    : '--';
  const evidenceList = modulationData?.evidence || [];

  const selectedConfig = deintData?.selected_configuration || { rows: 8, cols: 8, status: 'PENDING' };
  const selectedConvConfig = convDeintData?.selected_configuration || { branches: 4, delay_step: 1, status: 'PENDING' };
  const selectedFecConfig = fecData?.selected_configuration || { rate: '1/2', constraint_length: 3, g1_octal: 7, g2_octal: 5, status: 'PENDING' };

  return (
    <section className="analysis-results-section">
      <div className="section-header-row">
        <h2 className="section-title">
          <Cpu size={18} className="section-title-icon" />
          <span>Signal Analysis & Decoding Results</span>
        </h2>
        {onAnalyze && (
          <button type="button" className="btn-analyze" onClick={onAnalyze}>
            <RefreshCw size={14} />
            <span>Re-analyze Signal</span>
          </button>
        )}
      </div>

      <div className="analysis-cards-grid">
        {/* Card 1: Statistics */}
        <div className="analysis-card">
          <div className="analysis-card-header">
            <Activity size={16} className="text-accent" />
            <span className="analysis-card-title">Signal Statistics</span>
          </div>
          <div className="analysis-metric-list">
            <div className="metric-row">
              <span className="metric-label">RMS Amplitude</span>
              <span className="metric-value mono text-highlight">{statistics.rms?.toFixed(4) ?? '--'}</span>
            </div>
            <div className="metric-row">
              <span className="metric-label">Peak Value</span>
              <span className="metric-value mono">{statistics.peak?.toFixed(4) ?? '--'}</span>
            </div>
            <div className="metric-row">
              <span className="metric-label">Peak-to-Peak</span>
              <span className="metric-value mono">{statistics.peak_to_peak?.toFixed(4) ?? '--'}</span>
            </div>
            <div className="metric-row">
              <span className="metric-label">Average Power</span>
              <span className="metric-value mono">{formatPower(statistics.average_power)}</span>
            </div>
          </div>
        </div>

        {/* Card 2: Frequency & Bandwidth */}
        <div className="analysis-card">
          <div className="analysis-card-header">
            <Zap size={16} className="text-accent" />
            <span className="analysis-card-title">Frequency & Bandwidth</span>
          </div>
          <div className="analysis-metric-list">
            <div className="metric-row">
              <span className="metric-label">Dominant Freq</span>
              <span className="metric-value mono text-accent">
                {formatFrequencyDisplay(frequency.dominant_frequency_hz)}
              </span>
            </div>
            <div className="metric-row">
              <span className="metric-label">Peak Spectrum Power</span>
              <span className="metric-value mono">{frequency.peak_magnitude_db?.toFixed(1) ?? '--'} dB</span>
            </div>
            <div className="metric-row">
              <span className="metric-label">Occupied Bandwidth (99%)</span>
              <span className="metric-value mono text-highlight">
                {formatFrequencyDisplay(bandwidth.bandwidth_hz)}
              </span>
            </div>
            <div className="metric-row">
              <span className="metric-label">Bandwidth Bounds</span>
              <span className="metric-value mono" style={{ fontSize: '0.78rem' }}>
                {formatFrequencyDisplay(bandwidth.lower_frequency_hz)} … {formatFrequencyDisplay(bandwidth.upper_frequency_hz)}
              </span>
            </div>
          </div>
        </div>

        {/* Card 3: Noise & SNR */}
        <div className="analysis-card">
          <div className="analysis-card-header">
            <ShieldCheck size={16} className="text-accent" />
            <span className="analysis-card-title">Noise & Quality</span>
          </div>
          <div className="analysis-metric-list">
            <div className="metric-row">
              <span className="metric-label">Estimated SNR</span>
              <span className={`metric-value mono ${noise.estimated_snr_db >= 3 ? 'text-ready' : 'text-secondary'}`}>
                {noise.estimated_snr_db !== undefined ? `${noise.estimated_snr_db.toFixed(1)} dB` : '--'}
              </span>
            </div>
            <div className="metric-row">
              <span className="metric-label">Est. Signal Power</span>
              <span className="metric-value mono">{formatPower(noise.estimated_signal_power)}</span>
            </div>
            <div className="metric-row">
              <span className="metric-label">Est. Noise Power</span>
              <span className="metric-value mono">{formatPower(noise.estimated_noise_power)}</span>
            </div>
            <div className="metric-row">
              <span className="metric-label">Estimation Method</span>
              <span className="metric-value text-muted" style={{ fontSize: '0.75rem' }}>
                20th Percentile PSD
              </span>
            </div>
          </div>
        </div>

        {/* Card 4: Activity & Presence */}
        <div className="analysis-card">
          <div className="analysis-card-header">
            <Radio size={16} className="text-accent" />
            <span className="analysis-card-title">Signal Presence</span>
          </div>
          <div className="analysis-metric-list">
            <div className="metric-row">
              <span className="metric-label">Signal Status</span>
              <span className={`metric-badge ${activity.signal_present ? 'ready' : 'pending'}`}>
                {activity.status || (activity.signal_present ? 'ACTIVE_SIGNAL' : 'LOW_ENERGY')}
              </span>
            </div>
            <div className="metric-row">
              <span className="metric-label">Activity Ratio</span>
              <span className="metric-value mono">
                {activity.activity_ratio !== undefined ? `${(activity.activity_ratio * 100).toFixed(1)}%` : '--'}
              </span>
            </div>
            <div className="metric-row">
              <span className="metric-label">Active Time Interval</span>
              <span className="metric-value mono">
                {activity.active_start_time !== undefined ? `${activity.active_start_time.toFixed(2)}s – ${activity.active_end_time.toFixed(2)}s` : '--'}
              </span>
            </div>
            <div className="metric-row">
              <span className="metric-label">Pipeline Stage 02</span>
              <span className="metric-badge ready">
                COMPLETE
              </span>
            </div>
          </div>
        </div>

        {/* Card 5: Modulation Recognition */}
        <div className="analysis-card modulation-card" style={{ gridColumn: '1 / -1' }}>
          <div className="analysis-card-header">
            <Compass size={16} className="text-accent" />
            <span className="analysis-card-title">Modulation Recognition (Stage 03)</span>
          </div>
          <div className="modulation-content-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginTop: '8px' }}>
            <div className="mod-main-info" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div className="metric-row">
                <span className="metric-label">Modulation Type</span>
                <span className={`metric-badge ${modType !== 'UNKNOWN' && modType !== 'PENDING' ? 'ready' : 'pending'}`} style={{ fontSize: '0.85rem', padding: '4px 10px' }}>
                  {modType}
                </span>
              </div>
              <div className="metric-row">
                <span className="metric-label">Confidence Score</span>
                <span className="metric-value mono text-accent" style={{ fontSize: '1.1rem', fontWeight: 'bold' }}>
                  {confidencePct}
                </span>
              </div>
              <div className="metric-row">
                <span className="metric-label">Pipeline Stage 03</span>
                <span className={`metric-badge ${modType !== 'PENDING' ? 'ready' : 'pending'}`}>
                  {modType !== 'PENDING' ? 'COMPLETE' : 'PENDING'}
                </span>
              </div>
            </div>

            <div className="mod-evidence-info">
              <span className="metric-label" style={{ display: 'block', marginBottom: '6px', fontWeight: '600' }}>Classification Evidence:</span>
              {evidenceList.length > 0 ? (
                <ul className="evidence-list" style={{ listStyle: 'none', paddingLeft: 0, margin: 0, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  {evidenceList.map((item, idx) => (
                    <li key={idx} style={{ marginBottom: '4px', display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
                      <span className="text-accent">•</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <span className="text-muted" style={{ fontSize: '0.8rem' }}>No evidence calculated.</span>
              )}
            </div>
          </div>
        </div>

        {/* Card 6: FSK Demodulation Section */}
        {demodData && (
          <div className="analysis-card demodulation-card" style={{ gridColumn: '1 / -1' }}>
            <div className="analysis-card-header">
              <Binary size={16} className="text-accent" />
              <span className="analysis-card-title">FSK Digital Demodulation (Stage 04)</span>
            </div>
            <div className="demod-content-grid" style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '8px' }}>
              <div className="demod-metrics-row" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px' }}>
                <div className="metric-row">
                  <span className="metric-label">Estimated Tone 1 (mark)</span>
                  <span className="metric-value mono text-accent">{formatFrequencyDisplay(demodData.frequency_1_hz)}</span>
                </div>
                <div className="metric-row">
                  <span className="metric-label">Estimated Tone 0 (space)</span>
                  <span className="metric-value mono text-accent">{formatFrequencyDisplay(demodData.frequency_0_hz)}</span>
                </div>
                <div className="metric-row">
                  <span className="metric-label">Estimated Symbol Rate</span>
                  <span className="metric-value mono text-highlight">{demodData.symbol_rate?.toFixed(1)} symbols/sec</span>
                </div>
                <div className="metric-row">
                  <span className="metric-label">Recovered Bit Count</span>
                  <span className="metric-value mono">{demodData.bit_count} bits</span>
                </div>
                <div className="metric-row">
                  <span className="metric-label">Uncertain Symbols</span>
                  <span className="metric-value mono">{demodData.uncertain_symbols}</span>
                </div>
                <div className="metric-row">
                  <span className="metric-label">Pipeline Stage 04</span>
                  <span className="metric-badge ready">COMPLETE</span>
                </div>
              </div>

              <div className="bitstream-preview-wrapper" style={{ marginTop: '8px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <span className="metric-label" style={{ fontWeight: '600' }}>Demodulated Bitstream Preview:</span>
                  <button type="button" className="btn-icon-danger" style={{ color: 'var(--text-accent)', borderColor: 'var(--border-color)', background: 'var(--bg-card-subtle)' }} onClick={() => handleCopyBits(demodData.bits, 'demod')}>
                    {copiedBits ? <Check size={12} className="text-ready" /> : <Copy size={12} />}
                    <span>{copiedBits ? 'Copied!' : 'Copy Bits'}</span>
                  </button>
                </div>
                <div
                  className="bitstream-box mono"
                  style={{
                    backgroundColor: '#090d14',
                    border: '1px solid var(--border-color)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '10px 14px',
                    fontSize: '0.85rem',
                    color: 'var(--text-accent)',
                    letterSpacing: '1px',
                    wordBreak: 'break-all',
                    maxHeight: '100px',
                    overflowY: 'auto'
                  }}
                >
                  {demodData.bits_preview || demodData.bits || 'No bits recovered'}
                  {demodData.bits && demodData.bits.length > 128 && (
                    <span className="text-muted" style={{ display: 'block', marginTop: '6px', fontSize: '0.75rem', fontStyle: 'italic' }}>
                      … showing first 128 of {demodData.bits.length} bits
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Card 7: Block De-interleaving Section (Stage 05) */}
        {deintData && (
          <div className="analysis-card deint-card" style={{ gridColumn: '1 / -1' }}>
            <div className="analysis-card-header">
              <Grid size={16} className="text-accent" />
              <span className="analysis-card-title">Block De-Interleaving (Stage 05)</span>
            </div>
            <div className="deint-content-grid" style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '8px' }}>
              <div className="deint-metrics-row" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px' }}>
                <div className="metric-row">
                  <span className="metric-label">Block Configuration</span>
                  <span className="metric-value mono text-accent">
                    {selectedConfig.rows} × {selectedConfig.cols} ({selectedConfig.rows * selectedConfig.cols} bits)
                  </span>
                </div>
                <div className="metric-row">
                  <span className="metric-label">Validation Status</span>
                  <span className={`metric-badge ${selectedConfig.status === 'VALIDATED' ? 'ready' : 'pending'}`}>
                    {selectedConfig.status || 'CANDIDATE_TESTED'}
                  </span>
                </div>
                <div className="metric-row">
                  <span className="metric-label">Input / Output Bits</span>
                  <span className="metric-value mono text-highlight">
                    {deintData.input_bit_count} / {deintData.output_bit_count} bits
                  </span>
                </div>
                <div className="metric-row">
                  <span className="metric-label">Pipeline Stage 05</span>
                  <span className="metric-badge ready">COMPLETE</span>
                </div>
              </div>

              <div className="bitstream-preview-wrapper" style={{ marginTop: '8px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <span className="metric-label" style={{ fontWeight: '600' }}>De-Interleaved Bitstream Preview:</span>
                  <button type="button" className="btn-icon-danger" style={{ color: 'var(--text-accent)', borderColor: 'var(--border-color)', background: 'var(--bg-card-subtle)' }} onClick={() => handleCopyBits(deintData.deinterleaved_bits, 'deint')}>
                    {copiedDeintBits ? <Check size={12} className="text-ready" /> : <Copy size={12} />}
                    <span>{copiedDeintBits ? 'Copied!' : 'Copy De-interleaved Bits'}</span>
                  </button>
                </div>
                <div
                  className="bitstream-box mono"
                  style={{
                    backgroundColor: '#090d14',
                    border: '1px solid var(--border-color)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '10px 14px',
                    fontSize: '0.85rem',
                    color: '#10b981',
                    letterSpacing: '1px',
                    wordBreak: 'break-all',
                    maxHeight: '100px',
                    overflowY: 'auto'
                  }}
                >
                  {deintData.bits_preview || deintData.deinterleaved_bits || 'No bits de-interleaved'}
                  {deintData.deinterleaved_bits && deintData.deinterleaved_bits.length > 128 && (
                    <span className="text-muted" style={{ display: 'block', marginTop: '6px', fontSize: '0.75rem', fontStyle: 'italic' }}>
                      … showing first 128 of {deintData.deinterleaved_bits.length} bits
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Card 8: Convolutional De-interleaving Section (Stage 05) */}
        {convDeintData && (
          <div className="analysis-card conv-deint-card" style={{ gridColumn: '1 / -1' }}>
            <div className="analysis-card-header">
              <Grid size={16} className="text-accent" />
              <span className="analysis-card-title">Convolutional De-Interleaving (Stage 05)</span>
            </div>
            <div className="deint-content-grid" style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '8px' }}>
              <div className="deint-metrics-row" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px' }}>
                <div className="metric-row">
                  <span className="metric-label">Shift-Register Config</span>
                  <span className="metric-value mono text-accent">
                    Branches: {selectedConvConfig.branches}, Delay Step: {selectedConvConfig.delay_step}
                  </span>
                </div>
                <div className="metric-row">
                  <span className="metric-label">Validation Status</span>
                  <span className={`metric-badge ${selectedConvConfig.status === 'VALIDATED' ? 'ready' : 'pending'}`}>
                    {selectedConvConfig.status || 'CANDIDATE_TESTED'}
                  </span>
                </div>
                <div className="metric-row">
                  <span className="metric-label">Input / Output Bits</span>
                  <span className="metric-value mono text-highlight">
                    {convDeintData.input_bit_count} / {convDeintData.output_bit_count} bits
                  </span>
                </div>
                <div className="metric-row">
                  <span className="metric-label">Pipeline Stage 05</span>
                  <span className="metric-badge ready">COMPLETE</span>
                </div>
              </div>

              <div className="bitstream-preview-wrapper" style={{ marginTop: '8px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <span className="metric-label" style={{ fontWeight: '600' }}>Convolutional De-Interleaved Bitstream Preview:</span>
                  <button type="button" className="btn-icon-danger" style={{ color: 'var(--text-accent)', borderColor: 'var(--border-color)', background: 'var(--bg-card-subtle)' }} onClick={() => handleCopyBits(convDeintData.deinterleaved_bits, 'conv')}>
                    {copiedConvBits ? <Check size={12} className="text-ready" /> : <Copy size={12} />}
                    <span>{copiedConvBits ? 'Copied!' : 'Copy Conv Bits'}</span>
                  </button>
                </div>
                <div
                  className="bitstream-box mono"
                  style={{
                    backgroundColor: '#090d14',
                    border: '1px solid var(--border-color)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '10px 14px',
                    fontSize: '0.85rem',
                    color: '#34d399',
                    letterSpacing: '1px',
                    wordBreak: 'break-all',
                    maxHeight: '100px',
                    overflowY: 'auto'
                  }}
                >
                  {convDeintData.bits_preview || convDeintData.deinterleaved_bits || 'No bits de-interleaved'}
                  {convDeintData.deinterleaved_bits && convDeintData.deinterleaved_bits.length > 128 && (
                    <span className="text-muted" style={{ display: 'block', marginTop: '6px', fontSize: '0.75rem', fontStyle: 'italic' }}>
                      … showing first 128 of {convDeintData.deinterleaved_bits.length} bits
                    </span>
                  )}
                </div>
              </div>
              <div className="metric-row" style={{ marginTop: '4px' }}>
                <span className="metric-label" style={{ fontSize: '0.78rem' }}>Method:</span>
                <span className="metric-value text-muted" style={{ fontSize: '0.78rem' }}>{convDeintData.method}</span>
              </div>
            </div>
          </div>
        )}

        {/* Card 9: Viterbi FEC Decoding Section (Stage 06) */}
        {fecData && (
          <div className="analysis-card fec-card" style={{ gridColumn: '1 / -1' }}>
            <div className="analysis-card-header">
              <Cpu size={16} className="text-accent" />
              <span className="analysis-card-title">Viterbi FEC Decoding (Stage 06)</span>
            </div>
            <div className="fec-content-grid" style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '8px' }}>
              <div className="fec-metrics-row" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px' }}>
                <div className="metric-row">
                  <span className="metric-label">FEC Type / Rate</span>
                  <span className="metric-value mono text-accent">
                    {fecData.fec_type} (Rate {fecData.rate})
                  </span>
                </div>
                <div className="metric-row">
                  <span className="metric-label">Constraint Length (K)</span>
                  <span className="metric-value mono text-accent">
                    K = {selectedFecConfig.constraint_length} (Generators {selectedFecConfig.g1_octal}, {selectedFecConfig.g2_octal} octal)
                  </span>
                </div>
                <div className="metric-row">
                  <span className="metric-label">Encoded / Decoded Bits</span>
                  <span className="metric-value mono text-highlight">
                    {fecData.input_bit_count} / {fecData.output_bit_count} bits
                  </span>
                </div>
                <div className="metric-row">
                  <span className="metric-label">Validation Status</span>
                  <span className={`metric-badge ${selectedFecConfig.status === 'VALIDATED' ? 'ready' : 'pending'}`}>
                    {selectedFecConfig.status || 'DECODED'}
                  </span>
                </div>
                <div className="metric-row">
                  <span className="metric-label">Pipeline Stage 06</span>
                  <span className="metric-badge ready">COMPLETE</span>
                </div>
              </div>

              <div className="bitstream-preview-wrapper" style={{ marginTop: '8px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <span className="metric-label" style={{ fontWeight: '600' }}>Decoded Payload Bitstream Preview:</span>
                  <button type="button" className="btn-icon-danger" style={{ color: 'var(--text-accent)', borderColor: 'var(--border-color)', background: 'var(--bg-card-subtle)' }} onClick={() => handleCopyBits(fecData.decoded_bits, 'fec')}>
                    {copiedFecBits ? <Check size={12} className="text-ready" /> : <Copy size={12} />}
                    <span>{copiedFecBits ? 'Copied!' : 'Copy Payload Bits'}</span>
                  </button>
                </div>
                <div
                  className="bitstream-box mono"
                  style={{
                    backgroundColor: '#090d14',
                    border: '1px solid var(--border-color)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '10px 14px',
                    fontSize: '0.85rem',
                    color: '#60a5fa',
                    letterSpacing: '1px',
                    wordBreak: 'break-all',
                    maxHeight: '100px',
                    overflowY: 'auto'
                  }}
                >
                  {fecData.bits_preview || fecData.decoded_bits || 'No payload bits decoded'}
                  {fecData.decoded_bits && fecData.decoded_bits.length > 128 && (
                    <span className="text-muted" style={{ display: 'block', marginTop: '6px', fontSize: '0.75rem', fontStyle: 'italic' }}>
                      … showing first 128 of {fecData.decoded_bits.length} bits
                    </span>
                  )}
                </div>
              </div>
              <div className="metric-row" style={{ marginTop: '4px' }}>
                <span className="metric-label" style={{ fontSize: '0.78rem' }}>Method:</span>
                <span className="metric-value text-muted" style={{ fontSize: '0.78rem' }}>{fecData.method}</span>
              </div>
            </div>
          </div>
        )}

        {/* Card 10: Reed-Solomon FEC Decoding Section (Stage 06) */}
        {rsFecData && (
          <div className="analysis-card rs-fec-card" style={{ gridColumn: '1 / -1' }}>
            <div className="analysis-card-header">
              <Cpu size={16} className="text-accent" />
              <span className="analysis-card-title">Reed-Solomon RS(255,223) Candidate (Stage 06)</span>
            </div>
            <div className="fec-content-grid" style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '8px' }}>
              <div className="fec-metrics-row" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px' }}>
                <div className="metric-row">
                  <span className="metric-label">FEC Type / Scheme</span>
                  <span className="metric-value mono text-accent">
                    {rsFecData.fec_type}
                  </span>
                </div>
                <div className="metric-row">
                  <span className="metric-label">Codeword (n) / Data (k)</span>
                  <span className="metric-value mono text-accent">
                    RS({rsFecData.n}, {rsFecData.k}) — {rsFecData.parity_symbols} parity symbols
                  </span>
                </div>
                <div className="metric-row">
                  <span className="metric-label">Symbol Errors Corrected</span>
                  <span className="metric-value mono text-highlight">
                    {rsFecData.corrected_errors} symbols (max 16)
                  </span>
                </div>
                <div className="metric-row">
                  <span className="metric-label">Block Count</span>
                  <span className="metric-value mono">
                    {rsFecData.total_blocks} block(s)
                  </span>
                </div>
                <div className="metric-row">
                  <span className="metric-label">Validation Status</span>
                  <span className={`metric-badge ${rsFecData.status === 'VALIDATED' ? 'ready' : 'pending'}`}>
                    {rsFecData.status || 'DECODED'}
                  </span>
                </div>
                <div className="metric-row">
                  <span className="metric-label">Pipeline Stage 06</span>
                  <span className="metric-badge ready">COMPLETE</span>
                </div>
              </div>

              <div className="bitstream-preview-wrapper" style={{ marginTop: '8px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <span className="metric-label" style={{ fontWeight: '600' }}>Decoded Payload Bitstream Preview:</span>
                  <button type="button" className="btn-icon-danger" style={{ color: 'var(--text-accent)', borderColor: 'var(--border-color)', background: 'var(--bg-card-subtle)' }} onClick={() => handleCopyBits(rsFecData.decoded_bits, 'rs')}>
                    {copiedRsBits ? <Check size={12} className="text-ready" /> : <Copy size={12} />}
                    <span>{copiedRsBits ? 'Copied!' : 'Copy RS Payload Bits'}</span>
                  </button>
                </div>
                <div
                  className="bitstream-box mono"
                  style={{
                    backgroundColor: '#090d14',
                    border: '1px solid var(--border-color)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '10px 14px',
                    fontSize: '0.85rem',
                    color: '#a7f3d0',
                    letterSpacing: '1px',
                    wordBreak: 'break-all',
                    maxHeight: '100px',
                    overflowY: 'auto'
                  }}
                >
                  {rsFecData.bits_preview || rsFecData.decoded_bits || 'No RS payload bits decoded'}
                  {rsFecData.decoded_bits && rsFecData.decoded_bits.length > 128 && (
                    <span className="text-muted" style={{ display: 'block', marginTop: '6px', fontSize: '0.75rem', fontStyle: 'italic' }}>
                      … showing first 128 of {rsFecData.decoded_bits.length} bits
                    </span>
                  )}
                </div>
              </div>
              <div className="metric-row" style={{ marginTop: '4px' }}>
                <span className="metric-label" style={{ fontSize: '0.78rem' }}>Method:</span>
                <span className="metric-value text-muted" style={{ fontSize: '0.78rem' }}>{rsFecData.method}</span>
              </div>
            </div>
          </div>
        )}

        {/* Card 11: Header & Synchronization Detection Section (Stage 07) */}
        {headerData && (
          <div className="analysis-card header-card" style={{ gridColumn: '1 / -1' }}>
            <div className="analysis-card-header">
              <Compass size={16} className="text-accent" />
              <span className="analysis-card-title">Header & Synchronization Detection (Stage 07)</span>
            </div>
            <div className="fec-content-grid" style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '8px' }}>
              <div className="fec-metrics-row" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px' }}>
                <div className="metric-row">
                  <span className="metric-label">Sync Word Candidate</span>
                  <span className="metric-value mono text-accent">
                    {headerData.sync_found ? `32 bits (Pos ${headerData.sync_position})` : 'NOT FOUND'}
                  </span>
                </div>
                <div className="metric-row">
                  <span className="metric-label">Hamming Dist / Match</span>
                  <span className="metric-value mono text-accent">
                    {headerData.hamming_distance !== undefined ? `${headerData.hamming_distance} err (${headerData.match_percentage}%)` : '--'}
                  </span>
                </div>
                <div className="metric-row">
                  <span className="metric-label">Header Candidate</span>
                  <span className={`metric-badge ${headerData.validation_status === 'VALIDATED' ? 'ready' : 'pending'}`}>
                    {headerData.validation_status || 'CHECKING'}
                  </span>
                </div>
                <div className="metric-row">
                  <span className="metric-label">Protocol Version / Type</span>
                  <span className="metric-value mono text-highlight">
                    {headerData.version !== undefined ? `v${headerData.version} (Type ${headerData.message_type})` : '--'}
                  </span>
                </div>
                <div className="metric-row">
                  <span className="metric-label">Payload Length / Seq</span>
                  <span className="metric-value mono">
                    {headerData.payload_length !== undefined ? `${headerData.payload_length} bytes (Seq ${headerData.sequence})` : '--'}
                  </span>
                </div>
                <div className="metric-row">
                  <span className="metric-label">Header CRC-16</span>
                  <span className={`metric-badge ${headerData.crc_valid ? 'ready' : 'pending'}`}>
                    {headerData.crc_valid ? 'VALIDATED' : 'INVALID'}
                  </span>
                </div>
                <div className="metric-row">
                  <span className="metric-label">Payload Bit Boundary</span>
                  <span className="metric-value mono text-highlight">
                    {headerData.payload_start !== undefined ? `[${headerData.payload_start} → ${headerData.payload_end}]` : '--'}
                  </span>
                </div>
                <div className="metric-row">
                  <span className="metric-label">Pipeline Stage 07</span>
                  <span className={`metric-badge ${headerData.validation_status === 'VALIDATED' ? 'ready' : 'pending'}`}>
                    {headerData.validation_status === 'VALIDATED' ? 'COMPLETE' : 'PENDING'}
                  </span>
                </div>
              </div>

              <div className="metric-row" style={{ marginTop: '4px' }}>
                <span className="metric-label" style={{ fontSize: '0.78rem' }}>Frame Boundary Note:</span>
                <span className="metric-value text-muted" style={{ fontSize: '0.78rem' }}>
                  {headerData.validation_status === 'VALIDATED'
                    ? `Payload boundaries identified at bits [${headerData.payload_start} .. ${headerData.payload_end}]. Ready for Stage 08 extraction.`
                    : headerData.message || 'Header candidate validation incomplete.'}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Card 12: Final Data Recovery Section (Stage 08) */}
        {payloadData && (
          <div className="analysis-card payload-card" style={{ gridColumn: '1 / -1', border: '1px solid #10b981' }}>
            <div className="analysis-card-header">
              <ShieldCheck size={16} className="text-ready" />
              <span className="analysis-card-title" style={{ color: '#10b981' }}>Final Data Recovery (Stage 08)</span>
            </div>
            <div className="fec-content-grid" style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '8px' }}>
              <div className="fec-metrics-row" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px' }}>
                <div className="metric-row">
                  <span className="metric-label">Recovery Status</span>
                  <span className={`metric-badge ${payloadData.status === 'RECOVERED' ? 'ready' : 'pending'}`}>
                    {payloadData.status || 'PENDING'}
                  </span>
                </div>
                <div className="metric-row">
                  <span className="metric-label">Detected Content Format</span>
                  <span className="metric-value mono text-accent">
                    {payloadData.data_type === 'TEXT' ? 'Printable UTF-8 Text' : payloadData.data_type || 'Binary'}
                  </span>
                </div>
                <div className="metric-row">
                  <span className="metric-label">Payload Size</span>
                  <span className="metric-value mono text-highlight">
                    {payloadData.payload_byte_count} bytes ({payloadData.payload_bit_count} bits)
                  </span>
                </div>
                <div className="metric-row">
                  <span className="metric-label">Printable Char Ratio</span>
                  <span className="metric-value mono text-accent">
                    {payloadData.printable_ratio !== undefined ? `${(payloadData.printable_ratio * 100).toFixed(1)}%` : '--'}
                  </span>
                </div>
                <div className="metric-row">
                  <span className="metric-label">Shannon Entropy</span>
                  <span className="metric-value mono">
                    {payloadData.entropy !== undefined ? `${payloadData.entropy} bits/byte` : '--'}
                  </span>
                </div>
                <div className="metric-row">
                  <span className="metric-label">Payload Bit Boundary</span>
                  <span className="metric-value mono text-highlight">
                    [{payloadData.payload_start} → {payloadData.payload_end}]
                  </span>
                </div>
                <div className="metric-row">
                  <span className="metric-label">Pipeline Stage 08</span>
                  <span className="metric-badge ready">COMPLETE</span>
                </div>
              </div>

              {/* Text Payload Display */}
              {payloadData.data_type === 'TEXT' && payloadData.text && (
                <div className="bitstream-preview-wrapper" style={{ marginTop: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                    <span className="metric-label" style={{ fontWeight: '600', color: '#10b981' }}>Recovered Text Payload:</span>
                    <button type="button" className="btn-icon-danger" style={{ color: '#10b981', borderColor: 'rgba(16, 185, 129, 0.3)', background: 'var(--bg-card-subtle)' }} onClick={() => handleCopyBits(payloadData.text, 'payloadText')}>
                      {copiedPayloadText ? <Check size={12} className="text-ready" /> : <Copy size={12} />}
                      <span>{copiedPayloadText ? 'Copied!' : 'Copy Text'}</span>
                    </button>
                  </div>
                  <div
                    className="bitstream-box mono"
                    style={{
                      backgroundColor: '#051a14',
                      border: '1px solid #10b981',
                      borderRadius: 'var(--radius-sm)',
                      padding: '12px 16px',
                      fontSize: '1rem',
                      fontWeight: 'bold',
                      color: '#34d399',
                      letterSpacing: '1px',
                      wordBreak: 'break-all',
                      maxHeight: '120px',
                      overflowY: 'auto'
                    }}
                  >
                    {payloadData.text}
                  </div>
                </div>
              )}

              {/* Hex Payload Display */}
              {payloadData.hex && (
                <div className="bitstream-preview-wrapper" style={{ marginTop: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                    <span className="metric-label" style={{ fontWeight: '600' }}>Hexadecimal Payload View:</span>
                    <button type="button" className="btn-icon-danger" style={{ color: 'var(--text-accent)', borderColor: 'var(--border-color)', background: 'var(--bg-card-subtle)' }} onClick={() => handleCopyBits(payloadData.hex, 'payloadHex')}>
                      {copiedPayloadHex ? <Check size={12} className="text-ready" /> : <Copy size={12} />}
                      <span>{copiedPayloadHex ? 'Copied!' : 'Copy Hex'}</span>
                    </button>
                  </div>
                  <div
                    className="bitstream-box mono"
                    style={{
                      backgroundColor: '#090d14',
                      border: '1px solid var(--border-color)',
                      borderRadius: 'var(--radius-sm)',
                      padding: '10px 14px',
                      fontSize: '0.85rem',
                      color: '#a7f3d0',
                      letterSpacing: '1.5px',
                      wordBreak: 'break-all',
                      maxHeight: '100px',
                      overflowY: 'auto'
                    }}
                  >
                    {payloadData.hex.match(/.{1,2}/g)?.join(' ') || payloadData.hex}
                  </div>
                </div>
              )}

              <div className="metric-row" style={{ marginTop: '4px' }}>
                <span className="metric-label" style={{ fontSize: '0.78rem' }}>Extraction Note:</span>
                <span className="metric-value text-muted" style={{ fontSize: '0.78rem' }}>
                  {payloadData.method || 'Validated header boundary payload extraction. Safe data presentation.'}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

