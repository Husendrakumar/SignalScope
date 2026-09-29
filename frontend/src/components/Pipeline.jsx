import React from 'react';
import { GitCommit } from 'lucide-react';

export default function Pipeline({ selectedFile, analysisData, modulationData, demodData, deintData, convDeintData, fecData, rsFecData, headerData, payloadData }) {
  const isLoaded = !!selectedFile;
  const isAnalyzed = !!analysisData;
  const isModulated = !!modulationData;
  const isDemodulated = !!demodData;
  const isDeinterleaved = !!deintData || !!convDeintData;
  const isFecDecoded = !!fecData || !!rsFecData;
  const isHeaderDetected = headerData?.validation_status === 'VALIDATED';
  const isDataRecovered = payloadData?.status === 'RECOVERED';

  const stages = [
    { num: '01', name: 'Load Signal', status: isLoaded ? 'COMPLETE' : 'READY' },
    { num: '02', name: 'Detect Signal', status: isAnalyzed ? 'COMPLETE' : (isLoaded ? 'READY' : 'PENDING') },
    { num: '03', name: 'Analyze Modulation', status: isModulated ? 'COMPLETE' : (isAnalyzed ? 'READY' : 'PENDING') },
    { num: '04', name: 'Demodulate', status: isDemodulated ? 'COMPLETE' : (isModulated ? 'READY' : 'PENDING') },
    { num: '05', name: 'De-interleave', status: isDeinterleaved ? 'COMPLETE' : (isDemodulated ? 'READY' : 'PENDING') },
    { num: '06', name: 'FEC Decode', status: isFecDecoded ? 'COMPLETE' : (isDeinterleaved || isDemodulated ? 'READY' : 'PENDING') },
    { num: '07', name: 'Detect Header', status: isHeaderDetected ? 'COMPLETE' : (isDemodulated || isFecDecoded ? 'READY' : 'PENDING') },
    { num: '08', name: 'Recover Data', status: isDataRecovered ? 'COMPLETE' : (isHeaderDetected ? 'READY' : 'PENDING') },
  ];

  return (
    <section className="pipeline-section">
      <h2 className="section-title">
        <GitCommit size={18} className="section-title-icon" />
        <span>Analysis Pipeline</span>
      </h2>
      
      <div className="pipeline-grid">
        {stages.map((stage) => {
          const isComplete = stage.status === 'COMPLETE';
          const isReady = stage.status === 'READY';
          const badgeClass = isComplete || isReady ? 'ready' : 'pending';

          return (
            <div
              key={stage.num}
              className={`pipeline-stage ${isComplete || isReady ? 'ready' : ''}`}
            >
              <div className="stage-header">
                <span className="stage-num">{stage.num}</span>
                <span className={`stage-status-badge ${badgeClass}`}>
                  {stage.status}
                </span>
              </div>
              <div className="stage-name">{stage.name}</div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
