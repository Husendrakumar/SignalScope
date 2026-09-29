import React from 'react';
import UploadPanel from '../components/UploadPanel';
import Pipeline from '../components/Pipeline';
import SignalInfoCards from '../components/SignalInfoCards';
import AnalysisResultsSection from '../components/AnalysisResultsSection';
import VisualizationPanel from '../components/VisualizationPanel';
import AnalysisStatus from '../components/AnalysisStatus';
import RecentActivity from '../components/RecentActivity';

export default function Dashboard({
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
  onFileSelect,
  onClearFile,
  onAnalyze
}) {
  return (
    <div className="content-area">
      <header className="page-header">
        <h1 className="page-title">Radio Signal Analysis</h1>
        <p className="page-description">
          Analyze recorded radio signals and recover useful information through an automated signal-processing pipeline.
        </p>
      </header>

      <UploadPanel
        selectedFile={selectedFile}
        onFileSelect={onFileSelect}
        onClearFile={onClearFile}
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
      
      {selectedFile && (
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
      )}

      <VisualizationPanel selectedFile={selectedFile} />

      <div className="bottom-grid">
        <AnalysisStatus selectedFile={selectedFile} analysisData={analysisData} />
        <RecentActivity selectedFile={selectedFile} />
      </div>
    </div>
  );
}
