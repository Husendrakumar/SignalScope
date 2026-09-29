import React from 'react';
import { Radio, ArrowRight } from 'lucide-react';
import FileInfoCard from '../components/FileInfoCard';
import VisualizationPanel from '../components/VisualizationPanel';
import Pipeline from '../components/Pipeline';
import SignalInfoCards from '../components/SignalInfoCards';
import AnalysisResultsSection from '../components/AnalysisResultsSection';

export default function SignalAnalysis({
  selectedFile,
  analysisData,
  modulationData,
  demodData,
  deintData,
  convDeintData,
  fecData,
  rsFecData,
  headerData,
  payloadData,
  isAnalyzing,
  analysisError,
  onClearFile,
  onAnalyze,
  onGoToFiles
}) {
  return (
    <div className="content-area">
      <header className="page-header">
        <h1 className="page-title">Signal Analysis</h1>
        <p className="page-description">
          Upload a radio recording to begin automated signal analysis.
        </p>
      </header>

      {selectedFile ? (
        <div className="analysis-page-content">
          <FileInfoCard
            fileObj={selectedFile}
            onClear={onClearFile}
            onAnalyze={onAnalyze}
          />
          <Pipeline
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
          />
          <SignalInfoCards selectedFile={selectedFile} analysisData={analysisData} />
          <AnalysisResultsSection
            analysisData={analysisData}
            modulationData={modulationData}
            demodData={demodData}
            deintData={deintData}
            convDeintData={convDeintData}
            fecData={fecData}
            rsFecData={rsFecData}
            headerData={headerData}
            payloadData={payloadData}
            loading={isAnalyzing}
            error={analysisError}
            onAnalyze={onAnalyze}
          />
          <VisualizationPanel selectedFile={selectedFile} />
        </div>
      ) : (
        <div className="empty-analysis-card">
          <div className="empty-icon-wrapper">
            <Radio size={36} />
          </div>
          <h2 className="empty-title">No signal loaded</h2>
          <p className="empty-desc">
            Upload a .WAV or .IQ recording from the Files section to begin automated signal analysis.
          </p>
          <button type="button" className="btn-primary" onClick={onGoToFiles}>
            <span>Go to Files</span>
            <ArrowRight size={16} />
          </button>
        </div>
      )}
    </div>
  );
}
