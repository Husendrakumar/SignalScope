import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { LineChart, Sliders, Activity, Zap, Compass, RefreshCw, AlertCircle } from 'lucide-react';
import {
  fetchWaveformData,
  fetchSpectrumData,
  fetchSpectrogramData,
  fetchConstellationData
} from '../api';

/* ------------------------------------------------------------------ */
/*  Lazy-load Plotly to keep the initial bundle small                 */
/* ------------------------------------------------------------------ */
import Plotly from 'plotly.js-dist-min';
import createPlotlyComponent from 'react-plotly.js/factory';
const Plot = createPlotlyComponent(Plotly);

/* ------------------------------------------------------------------ */
/*  Shared Plotly dark-theme layout defaults                          */
/* ------------------------------------------------------------------ */
const DARK_BG = '#0d121c';
const GRID_COLOR = '#1e293b';
const AXIS_COLOR = '#64748b';
const TEXT_COLOR = '#94a3b8';
const ACCENT = '#00e5ff';
const ACCENT2 = '#a855f7';
const ACCENT3 = '#10b981';

function baseLayout(overrides = {}) {
  const { xaxis: xaxisOverrides = {}, yaxis: yaxisOverrides = {}, ...otherOverrides } = overrides;
  return {
    paper_bgcolor: DARK_BG,
    plot_bgcolor: DARK_BG,
    font: { family: 'JetBrains Mono, monospace', size: 11, color: TEXT_COLOR },
    margin: { l: 60, r: 25, t: 15, b: 50 },
    autosize: true,
    dragmode: 'zoom',
    modebar: {
      bgcolor: 'rgba(0,0,0,0)',
      color: AXIS_COLOR,
      activecolor: ACCENT,
      orientation: 'v',
    },
    legend: {
      font: { size: 10, color: TEXT_COLOR },
      bgcolor: 'rgba(0,0,0,0)',
      borderwidth: 0,
      x: 0.01,
      y: 0.99,
      xanchor: 'left',
      yanchor: 'top',
    },
    ...otherOverrides,
    xaxis: {
      gridcolor: GRID_COLOR,
      zerolinecolor: GRID_COLOR,
      tickfont: { size: 10, color: AXIS_COLOR },
      titlefont: { size: 11, color: TEXT_COLOR },
      ...xaxisOverrides,
    },
    yaxis: {
      gridcolor: GRID_COLOR,
      zerolinecolor: GRID_COLOR,
      tickfont: { size: 10, color: AXIS_COLOR },
      titlefont: { size: 11, color: TEXT_COLOR },
      ...yaxisOverrides,
    },
  };
}

const PLOTLY_CONFIG = {
  displaylogo: false,
  responsive: true,
  modeBarButtonsToRemove: ['lasso2d', 'select2d', 'sendDataToCloud', 'toggleSpikelines'],
  modeBarButtonsToAdd: [],
  scrollZoom: true,
};

/* ------------------------------------------------------------------ */
/*  Smart frequency formatter (Hz → kHz → MHz)                        */
/* ------------------------------------------------------------------ */
function formatFreq(hz) {
  const abs = Math.abs(hz);
  if (abs >= 1e6) return (hz / 1e6).toFixed(3) + ' MHz';
  if (abs >= 1e3) return (hz / 1e3).toFixed(2) + ' kHz';
  return hz.toFixed(1) + ' Hz';
}

/* ================================================================== */
/*  Main Component                                                    */
/* ================================================================== */
export default function VisualizationPanel({ theme = 'dark', selectedFile, analysisData }) {
  const [activeTab, setActiveTab] = useState('waveform');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  /* ---- Per-tab data cache so switching tabs doesn't re-fetch ---- */
  const [cache, setCache] = useState({});

  const isIQ = selectedFile?.format === 'IQ';
  const signalId = selectedFile?.signal_id;

  /* Reset cache when a new signal is loaded */
  useEffect(() => {
    setCache({});
    setError(null);
    setActiveTab('waveform');
  }, [signalId]);

  /* Ensure we don't show IQ Plane tab for WAV */
  useEffect(() => {
    if (!isIQ && activeTab === 'constellation') {
      setActiveTab('waveform');
    }
  }, [isIQ, activeTab]);

  /* ---- Dynamic Cache Key based on domFreq for Waveform race condition ---- */
  const domFreq = useMemo(() => {
      if (!analysisData) return null; // Analysis not yet loaded
      const snr = analysisData?.noise?.estimated_snr_db || 0;
      if (analysisData?.activity?.signal_present === false || analysisData?.activity?.status === "LOW_ENERGY_OR_NOISE" || snr < 8.0) {
          return 0.0;
      }
      return analysisData?.frequency?.dominant_frequency_hz || 0.0;
  }, [analysisData]);

  const cacheKey = useMemo(() => {
      if (activeTab === 'waveform') {
          return `waveform_${domFreq !== null ? domFreq : 'none'}`;
      }
      return activeTab;
  }, [activeTab, domFreq]);

  /* ---- Fetch data for the active tab (with caching) ---- */
  useEffect(() => {
    if (!signalId) return;
    if (cache[cacheKey]) return; // already have data for this tab + state

    let cancelled = false;
    setLoading(true);
    setError(null);

    const loadData = async () => {
      try {
        let data = null;
        if (activeTab === 'waveform') {
          const fetchFreq = domFreq || 0.0;
          data = await fetchWaveformData(signalId, 1000, fetchFreq);
        } else if (activeTab === 'spectrum') {
          data = await fetchSpectrumData(signalId);
        } else if (activeTab === 'spectrogram') {
          data = await fetchSpectrogramData(signalId);
        } else if (activeTab === 'constellation') {
          if (!isIQ) throw new Error('I/Q Plane view is only available for IQ signals.');
          data = await fetchConstellationData(signalId);
        }

        if (!cancelled) {
          setCache(prev => ({ ...prev, [cacheKey]: data }));
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'Failed to load visualization data');
          setLoading(false);
        }
      }
    };

    loadData();
    return () => { cancelled = true; };
  }, [signalId, activeTab, isIQ, cache, cacheKey, domFreq]);

  const vizData = cache[cacheKey] || null;

  /* ================================================================ */
  /*  EMPTY STATE                                                     */
  /* ================================================================ */
  if (!selectedFile) {
    return (
      <section className="visualization-section">
        <h2 className="section-title">
          <LineChart size={18} className="section-title-icon" />
          <span>Signal Visualization</span>
        </h2>
        <div className="viz-placeholder">
          <Sliders className="viz-placeholder-icon" />
          <div className="viz-primary-text">No signal loaded</div>
          <div className="viz-sub-text">Upload a WAV or IQ recording to begin visualization.</div>
        </div>
      </section>
    );
  }

  /* ================================================================ */
  /*  TAB DEFINITIONS                                                 */
  /* ================================================================ */
  const tabs = [
    { key: 'waveform', label: 'Waveform', icon: Activity },
    { key: 'spectrum', label: 'Spectrum', icon: Zap },
    { key: 'spectrogram', label: 'Spectrogram', icon: LineChart },
    ...(isIQ ? [{ key: 'constellation', label: 'I/Q Plane', icon: Compass }] : []),
  ];

  const loadingMessages = {
    waveform: 'Loading waveform…',
    spectrum: 'Calculating spectrum…',
    spectrogram: 'Generating spectrogram…',
    constellation: 'Loading I/Q data…',
  };

  /* ================================================================ */
  /*  RENDER                                                          */
  /* ================================================================ */
  return (
    <section className="visualization-section">
      <div className="viz-header">
        <h2 className="section-title">
          <LineChart size={18} className="section-title-icon" />
          <span>Signal Visualization</span>
        </h2>

        <div className="viz-tabs">
          {tabs.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              type="button"
              className={`viz-tab-btn ${activeTab === key ? 'active' : ''}`}
              onClick={() => setActiveTab(key)}
            >
              <Icon size={14} />
              <span>{label}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="viz-container viz-container-plotly">
        {loading && (
          <div className="viz-overlay">
            <RefreshCw size={24} className="spin text-accent" />
            <span>{loadingMessages[activeTab] || 'Loading…'}</span>
          </div>
        )}

        {error && (
          <div className="viz-overlay error">
            <AlertCircle size={24} className="text-danger" />
            <span>{error}</span>
          </div>
        )}

        {!loading && !error && vizData && activeTab === 'waveform' && (
          <WaveformPlot theme={theme} data={vizData} />
        )}
        {!loading && !error && vizData && activeTab === 'spectrum' && (
          <SpectrumPlot theme={theme} data={vizData} />
        )}
        {!loading && !error && vizData && activeTab === 'spectrogram' && (
          <SpectrogramPlot theme={theme} data={vizData} />
        )}
        {!loading && !error && vizData && activeTab === 'constellation' && (
          <IQPlanePlot theme={theme} data={vizData} />
        )}

        {!loading && !error && !vizData && (
          <div className="viz-placeholder" style={{ border: 'none' }}>
            <RefreshCw size={20} className="text-muted" />
            <div className="viz-sub-text">Preparing visualization…</div>
          </div>
        )}
      </div>
    </section>
  );
}

/* ================================================================== */
/*  WAVEFORM PLOT                                                     */
/* ================================================================== */
function WaveformPlot({ theme, data }) {
  const traces = useMemo(() => {
    if (data.format === 'IQ') {
      const realI = data.real_i || [];
      const imagQ = data.imag_q || [];
      const mag = data.magnitude || [];
      const time = data.time || [];
      return [
        {
          x: time, y: realI, type: 'scattergl', mode: 'lines',
          name: 'In-Phase (I)', line: { color: ACCENT, width: 1.2 },
          hovertemplate: 't = %{x:.6f} s<br>I = %{y:.4f}<extra>I</extra>',
        },
        {
          x: time, y: imagQ, type: 'scattergl', mode: 'lines',
          name: 'Quadrature (Q)', line: { color: ACCENT2, width: 1.2 },
          hovertemplate: 't = %{x:.6f} s<br>Q = %{y:.4f}<extra>Q</extra>',
        },
        {
          x: time, y: mag, type: 'scattergl', mode: 'lines',
          name: 'Magnitude', line: { color: ACCENT3, width: 1, dash: 'dot' },
          visible: 'legendonly',
          hovertemplate: 't = %{x:.6f} s<br>|z| = %{y:.4f}<extra>Mag</extra>',
        },
      ];
    } else {
      const amp = data.amplitude || [];
      const time = data.time || [];
      return [{
        x: time, y: amp, type: 'scattergl', mode: 'lines',
        name: 'Amplitude', line: { color: ACCENT, width: 1.2 },
        hovertemplate: 't = %{x:.6f} s<br>Amp = %{y:.4f}<extra></extra>',
      }];
    }
  }, [data]);

  const layout = useMemo(() => baseLayout(theme, {
    xaxis: { title: 'Time (s)' },
    yaxis: { title: 'Amplitude' },
    showlegend: data.format === 'IQ',
  }), [data.format]);

  return <Plot data={traces} layout={layout} config={PLOTLY_CONFIG} useResizeHandler style={{ width: '100%', height: '100%' }} />;
}

/* ================================================================== */
/*  SPECTRUM PLOT                                                     */
/* ================================================================== */
function SpectrumPlot({ theme, data }) {
  const { scaledFreqs, xTitle, peakFreq, peakMag, scaledPeakFreq } = useMemo(() => {
    const freqs = data.frequencies || [];
    const mags = data.magnitudes_db || [];

    const absMax = freqs.length > 0 ? Math.max(...freqs.map(Math.abs)) : 1;
    let factor = 1;
    let title = 'Frequency (Hz)';
    if (absMax >= 1e6) {
      factor = 1e6;
      title = 'Frequency (MHz)';
    } else if (absMax >= 1e3) {
      factor = 1e3;
      title = 'Frequency (kHz)';
    }

    const sFreqs = freqs.map(f => f / factor);

    let peakIdx = 0;
    for (let i = 1; i < mags.length; i++) {
      if (mags[i] > mags[peakIdx]) peakIdx = i;
    }
    const pFreq = freqs[peakIdx] || 0;
    const pMag = mags[peakIdx] || 0;

    return {
      scaledFreqs: sFreqs,
      xTitle: title,
      peakFreq: pFreq,
      peakMag: pMag,
      scaledPeakFreq: pFreq / factor,
    };
  }, [data]);

  const traces = useMemo(() => {
    const mags = data.magnitudes_db || [];

    return [
      {
        x: scaledFreqs, y: mags, type: 'scattergl', mode: 'lines',
        name: 'Magnitude',
        line: { color: ACCENT, width: 1.2 },
        fill: 'tozeroy',
        fillcolor: 'rgba(0, 229, 255, 0.08)',
        hovertemplate: '%{x:.2f}<br>%{y:.1f} dB<extra></extra>',
      },
      {
        x: [scaledPeakFreq], y: [peakMag], type: 'scatter', mode: 'markers+text',
        name: `Peak: ${formatFreq(peakFreq)} (${peakMag.toFixed(1)} dB)`,
        marker: { color: ACCENT3, size: 8, symbol: 'diamond' },
        text: [`${formatFreq(peakFreq)}`],
        textposition: 'top center',
        textfont: { color: ACCENT3, size: 10 },
        hovertemplate: `Peak: ${formatFreq(peakFreq)}<br>${peakMag.toFixed(1)} dB<extra></extra>`,
      },
    ];
  }, [data, scaledFreqs, peakFreq, peakMag, scaledPeakFreq]);

  const layout = useMemo(() => {
    return baseLayout(theme, {
      xaxis: { title: xTitle },
      yaxis: { title: 'Magnitude (dB)' },
      showlegend: true,
    });
  }, [xTitle]);

  return <Plot data={traces} layout={layout} config={PLOTLY_CONFIG} useResizeHandler style={{ width: '100%', height: '100%' }} />;
}

/* ================================================================== */
/*  SPECTROGRAM PLOT                                                  */
/* ================================================================== */
function SpectrogramPlot({ theme, data }) {
  const { scaledFreqs, yTitle } = useMemo(() => {
    const freqAxis = data.frequency_axis || [];
    const absMax = freqAxis.length > 0 ? Math.max(...freqAxis.map(Math.abs)) : 1;
    let factor = 1;
    let title = 'Frequency (Hz)';
    if (absMax >= 1e6) {
      factor = 1e6;
      title = 'Frequency (MHz)';
    } else if (absMax >= 1e3) {
      factor = 1e3;
      title = 'Frequency (kHz)';
    }

    return {
      scaledFreqs: freqAxis.map(f => f / factor),
      yTitle: title,
    };
  }, [data]);

  const traces = useMemo(() => {
    const matrix = data.spectrogram_db || [];
    const timeAxis = data.time_axis || [];

    return [{
      z: matrix,
      x: timeAxis,
      y: scaledFreqs,
      type: 'heatmap',
      colorscale: 'Viridis',
      colorbar: {
        title: { text: 'dB', font: { size: 10, color: TEXT_COLOR } },
        tickfont: { size: 9, color: AXIS_COLOR },
        thickness: 14,
        len: 0.9,
        outlinewidth: 0,
        bgcolor: 'rgba(0,0,0,0)',
      },
      hovertemplate: 't = %{x:.3f} s<br>f = %{y:.2f}<br>%{z:.1f} dB<extra></extra>',
      zsmooth: 'best',
    }];
  }, [data, scaledFreqs]);

  const layout = useMemo(() => {
    return baseLayout(theme, {
      xaxis: { title: 'Time (s)' },
      yaxis: { title: yTitle },
    });
  }, [yTitle]);

  return <Plot data={traces} layout={layout} config={PLOTLY_CONFIG} useResizeHandler style={{ width: '100%', height: '100%' }} />;
}

/* ================================================================== */
/*  I/Q PLANE PLOT                                                    */
/* ================================================================== */
function IQPlanePlot({ theme, data }) {
  const traces = useMemo(() => {
    const iVals = data.i || [];
    const qVals = data.q || [];
    return [{
      x: iVals, y: qVals, type: 'scattergl', mode: 'markers',
      name: 'I/Q Samples',
      marker: { color: ACCENT, size: 3, opacity: 0.7 },
      hovertemplate: 'I = %{x:.4f}<br>Q = %{y:.4f}<extra></extra>',
    }];
  }, [data]);

  const layout = useMemo(() => {
    // Compute a symmetric range so axes are equally scaled
    const iVals = data.i || [];
    const qVals = data.q || [];
    const allVals = [...iVals.map(Math.abs), ...qVals.map(Math.abs)];
    const maxVal = allVals.length > 0 ? Math.max(...allVals) * 1.15 : 1.2;

    return baseLayout(theme, {
      xaxis: {
        title: 'In-Phase (I)',
        range: [-maxVal, maxVal],
        scaleanchor: 'y',
        scaleratio: 1,
        zeroline: true,
        zerolinecolor: '#334155',
        zerolinewidth: 1.5,
      },
      yaxis: {
        title: 'Quadrature (Q)',
        range: [-maxVal, maxVal],
        zeroline: true,
        zerolinecolor: '#334155',
        zerolinewidth: 1.5,
      },
      showlegend: false,
    });
  }, [data]);

  return <Plot data={traces} layout={layout} config={PLOTLY_CONFIG} useResizeHandler style={{ width: '100%', height: '100%' }} />;
}
