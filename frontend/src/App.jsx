import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import SignalAnalysis from './pages/SignalAnalysis';
import Files from './pages/Files';
import Reports from './pages/Reports';
import Settings from './pages/Settings';
import { Info, X } from 'lucide-react';
import { checkBackendHealth, fetchSignalAnalysis, fetchModulationAnalysis, fetchFskDemodulation, fetchBlockDeinterleaving, fetchConvolutionalDeinterleaving, fetchViterbiFecDecoding, fetchReedSolomonFecDecoding, fetchHeaderDetection, fetchPayloadExtraction } from './api';

export default function App() {
  const [activePage, setActivePage] = useState('dashboard');
  const [selectedFile, setSelectedFile] = useState(null);
  const [analysisData, setAnalysisData] = useState(null);
  const [modulationData, setModulationData] = useState(null);
  const [demodData, setDemodData] = useState(null);
  const [deintData, setDeintData] = useState(null);
  const [convDeintData, setConvDeintData] = useState(null);
  const [fecData, setFecData] = useState(null);
  const [rsFecData, setRsFecData] = useState(null);
  const [headerData, setHeaderData] = useState(null);
  const [payloadData, setPayloadData] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState(null);
  const [noticeMessage, setNoticeMessage] = useState('');
  const [backendConnected, setBackendConnected] = useState(false);
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem('signalScopeTheme');
    return saved ? saved : 'dark';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('signalScopeTheme', theme);
  }, [theme]);

  useEffect(() => {
    let isMounted = true;
    const checkHealth = async () => {
      const healthy = await checkBackendHealth();
      if (isMounted) {
        setBackendConnected(healthy);
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 3000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const runAnalysis = useCallback(async (signalId) => {
    if (!signalId) return;
    setIsAnalyzing(true);
    setAnalysisError(null);
    try {
      const [analysisRes, modulationRes] = await Promise.all([
        fetchSignalAnalysis(signalId),
        fetchModulationAnalysis(signalId)
      ]);
      setAnalysisData(analysisRes);
      setModulationData(modulationRes);

      if (modulationRes.modulation === 'FSK') {
        try {
          const demodRes = await fetchFskDemodulation(signalId);
          setDemodData(demodRes);

          if (demodRes && demodRes.bits) {
            const [blockRes, convRes, fecRes, rsFecRes, headerRes, payloadRes] = await Promise.allSettled([
              fetchBlockDeinterleaving(signalId),
              fetchConvolutionalDeinterleaving(signalId),
              fetchViterbiFecDecoding(signalId),
              fetchReedSolomonFecDecoding(signalId),
              fetchHeaderDetection(signalId),
              fetchPayloadExtraction(signalId)
            ]);

            if (blockRes.status === 'fulfilled') {
              setDeintData(blockRes.value);
            } else {
              console.warn('Block de-interleaving failed:', blockRes.reason?.message);
              setDeintData(null);
            }

            if (convRes.status === 'fulfilled') {
              setConvDeintData(convRes.value);
            } else {
              console.warn('Convolutional de-interleaving failed:', convRes.reason?.message);
              setConvDeintData(null);
            }

            if (fecRes.status === 'fulfilled') {
              setFecData(fecRes.value);
            } else {
              console.warn('Viterbi FEC decoding failed:', fecRes.reason?.message);
              setFecData(null);
            }

            if (rsFecRes.status === 'fulfilled') {
              setRsFecData(rsFecRes.value);
            } else {
              console.warn('Reed-Solomon FEC decoding failed:', rsFecRes.reason?.message);
              setRsFecData(null);
            }

            if (headerRes.status === 'fulfilled') {
              setHeaderData(headerRes.value);
            } else {
              console.warn('Header detection failed:', headerRes.reason?.message);
              setHeaderData(null);
            }

            if (payloadRes.status === 'fulfilled') {
              setPayloadData(payloadRes.value);
            } else {
              console.warn('Payload extraction failed:', payloadRes.reason?.message);
              setPayloadData(null);
            }
          } else {
            setDeintData(null);
            setConvDeintData(null);
            setFecData(null);
            setRsFecData(null);
            setHeaderData(null);
            setPayloadData(null);
          }
        } catch (demodErr) {
          console.warn('FSK demodulation skipped or failed:', demodErr.message);
          setDemodData(null);
          setDeintData(null);
          setConvDeintData(null);
          setFecData(null);
          setRsFecData(null);
          setHeaderData(null);
          setPayloadData(null);
        }
      } else {
        setDemodData(null);
        setDeintData(null);
        setConvDeintData(null);
        setFecData(null);
        setRsFecData(null);
        setHeaderData(null);
        setPayloadData(null);
      }
    } catch (err) {
      setAnalysisError(err.message || 'Failed to analyze signal.');
    } finally {
      setIsAnalyzing(false);
    }
  }, []);

  const handleFileSelect = (file) => {
    setSelectedFile(file);
    setAnalysisData(null);
    setModulationData(null);
    setDemodData(null);
    setDeintData(null);
    setConvDeintData(null);
    setFecData(null);
    setRsFecData(null);
    setHeaderData(null);
    setPayloadData(null);
    setAnalysisError(null);
    if (file?.signal_id) {
      runAnalysis(file.signal_id);
    }
  };

  const handleClearFile = () => {
    setSelectedFile(null);
    setAnalysisData(null);
    setModulationData(null);
    setDemodData(null);
    setDeintData(null);
    setConvDeintData(null);
    setFecData(null);
    setRsFecData(null);
    setHeaderData(null);
    setPayloadData(null);
    setAnalysisError(null);
  };

  const handleAnalyze = () => {
    if (selectedFile?.signal_id) {
      runAnalysis(selectedFile.signal_id);
    } else {
      setNoticeMessage('Please upload a signal file first.');
    }
  };

  const renderActivePage = () => {
    switch (activePage) {
      case 'analysis':
        return (
          <SignalAnalysis
            selectedFile={selectedFile}
            analysisData={analysisData}
            modulationData={modulationData}
            demodData={demodData}
            deintData={deintData}
            convDeintData={convDeintData}
            fecData={fecData}
            rsFecData={rsFecData}
            headerData={headerData}
            payloadData={payloadData}
            isAnalyzing={isAnalyzing}
            analysisError={analysisError}
            onClearFile={handleClearFile}
            onAnalyze={handleAnalyze}
            onGoToFiles={() => setActivePage('files')}
          />
        );
      case 'files':
        return (
          <Files
            selectedFile={selectedFile}
            onFileSelect={handleFileSelect}
            onClearFile={handleClearFile}
            onAnalyze={handleAnalyze}
          />
        );
      case 'reports':
        return <Reports />;
      case 'settings':
        return <Settings />;
      case 'dashboard':
      default:
        return (
          <Dashboard
            selectedFile={selectedFile}
            analysisData={analysisData}
            modulationData={modulationData}
            demodData={demodData}
            deintData={deintData}
            convDeintData={convDeintData}
            fecData={fecData}
            rsFecData={rsFecData}
            headerData={headerData}
            payloadData={payloadData}
            isAnalyzing={isAnalyzing}
            analysisError={analysisError}
            onFileSelect={handleFileSelect}
            onClearFile={handleClearFile}
            onAnalyze={handleAnalyze}
          />
        );
    }
  };


  return (
    <div className="app-container">
      <Header backendConnected={backendConnected} theme={theme} setTheme={setTheme} />
      
      {noticeMessage && (
        <div className="toast-notice">
          <div className="toast-content">
            <Info size={18} className="toast-icon" />
            <span>{noticeMessage}</span>
          </div>
          <button
            type="button"
            className="toast-close"
            onClick={() => setNoticeMessage('')}
          >
            <X size={16} />
          </button>
        </div>
      )}

      <div className="main-layout">
        <Sidebar activePage={activePage} onPageChange={setActivePage} />
        <main style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          {renderActivePage()}
        </main>
      </div>
    </div>
  );
}
