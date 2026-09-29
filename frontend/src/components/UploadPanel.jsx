import React, { useRef, useState } from 'react';
import { UploadCloud, FileAudio, AlertCircle, Loader2 } from 'lucide-react';
import FileInfoCard from './FileInfoCard';
import { uploadSignalFile } from '../api';

export default function UploadPanel({ selectedFile, onFileSelect, onClearFile, onAnalyze }) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const fileInputRef = useRef(null);

  const processFile = async (file) => {
    if (!file) return;

    const filename = file.name || '';
    const parts = filename.split('.');
    const ext = parts.length > 1 ? parts.pop().toLowerCase() : '';

    if (ext !== 'wav' && ext !== 'iq') {
      setErrorMessage('Unsupported file format. Only .WAV and .IQ files are supported.');
      return;
    }

    setErrorMessage('');
    setIsUploading(true);

    try {
      const metadata = await uploadSignalFile(file);
      onFileSelect({
        signal_id: metadata.signal_id,
        name: metadata.filename || file.name,
        filename: metadata.filename || file.name,
        format: metadata.format,
        sample_rate: metadata.sample_rate,
        sample_count: metadata.sample_count,
        duration_seconds: metadata.duration_seconds,
        data_type: metadata.data_type,
        channels: metadata.channels,
        size: file.size,
        lastModified: file.lastModified,
        fileRef: file
      });
    } catch (err) {
      setErrorMessage(err.message || 'Unable to connect to the analysis backend');
    } finally {
      setIsUploading(false);
    }
  };

  const handleInputChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      processFile(e.target.files[0]);
    }
    e.target.value = '';
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      processFile(e.dataTransfer.files[0]);
    }
  };

  const triggerFilePicker = () => {
    if (fileInputRef.current && !isUploading) {
      fileInputRef.current.click();
    }
  };

  return (
    <section className="upload-card">
      <input
        type="file"
        ref={fileInputRef}
        accept=".wav,.iq"
        onChange={handleInputChange}
        style={{ display: 'none' }}
      />

      <div className="upload-header">
        <div>
          <h2 className="upload-title">Upload a Radio Recording</h2>
          <p className="upload-desc">Select a recorded radio signal for analysis.</p>
        </div>
        <div className="supported-badge">
          Supported Formats: .WAV, .IQ
        </div>
      </div>

      {errorMessage && (
        <div className="upload-error-alert">
          <AlertCircle size={16} />
          <span>{errorMessage}</span>
        </div>
      )}

      {selectedFile ? (
        <FileInfoCard
          fileObj={selectedFile}
          onClear={() => {
            setErrorMessage('');
            onClearFile();
          }}
          onAnalyze={onAnalyze}
        />
      ) : (
        <div
          className={`drop-zone ${isDragging ? 'drag-over' : ''} ${isUploading ? 'uploading' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={triggerFilePicker}
        >
          <div className="upload-icon-wrapper">
            {isUploading ? <Loader2 size={24} className="spin" /> : <UploadCloud size={24} />}
          </div>
          <div className="drop-main-text">
            {isUploading ? 'Uploading signal file to backend...' : 'Drag and drop a signal file here'}
          </div>
          <div className="drop-sub-text">
            {isUploading ? 'Validating file format' : 'or select a file from your computer'}
          </div>

          <button
            type="button"
            className="btn-primary"
            disabled={isUploading}
            onClick={(e) => {
              e.stopPropagation();
              triggerFilePicker();
            }}
          >
            <FileAudio size={16} />
            <span>{isUploading ? 'Uploading...' : 'Select Signal File'}</span>
          </button>
        </div>
      )}
    </section>
  );
}
