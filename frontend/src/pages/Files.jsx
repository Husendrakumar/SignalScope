import React, { useRef, useState } from 'react';
import { FolderOpen, UploadCloud, FileAudio, AlertCircle, Loader2 } from 'lucide-react';
import FileInfoCard from '../components/FileInfoCard';
import { uploadSignalFile } from '../api';

export default function Files({ selectedFile, onFileSelect, onClearFile, onAnalyze }) {
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
    <div className="content-area">
      <header className="page-header">
        <h1 className="page-title">Signal Files</h1>
        <p className="page-description">
          Manage uploaded radio signal recordings.
        </p>
      </header>

      <input
        type="file"
        ref={fileInputRef}
        accept=".wav,.iq"
        onChange={handleInputChange}
        style={{ display: 'none' }}
      />

      {errorMessage && (
        <div className="upload-error-alert" style={{ marginBottom: '20px' }}>
          <AlertCircle size={16} />
          <span>{errorMessage}</span>
        </div>
      )}

      {selectedFile ? (
        <section className="files-section">
          <div className="files-section-header">
            <h2 className="section-title">
              <FolderOpen size={18} className="section-title-icon" />
              <span>Active Signal File</span>
            </h2>
            <button type="button" className="btn-secondary" onClick={triggerFilePicker} disabled={isUploading}>
              <UploadCloud size={16} />
              <span>Upload Different File</span>
            </button>
          </div>

          <FileInfoCard
            fileObj={selectedFile}
            onClear={() => {
              setErrorMessage('');
              onClearFile();
            }}
            onAnalyze={onAnalyze}
          />
        </section>
      ) : (
        <section className="files-upload-container">
          <div
            className={`drop-zone ${isDragging ? 'drag-over' : ''} ${isUploading ? 'uploading' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={triggerFilePicker}
            style={{ padding: '48px 24px' }}
          >
            <div className="upload-icon-wrapper">
              {isUploading ? <Loader2 size={28} className="spin" /> : <UploadCloud size={28} />}
            </div>
            <div className="drop-main-text">
              {isUploading ? 'Uploading signal file to backend...' : 'Drag and drop a signal file here'}
            </div>
            <div className="drop-sub-text">
              {isUploading ? 'Validating file format' : 'or select a file from your computer'}
            </div>
            <div className="supported-badge" style={{ margin: '12px 0 20px 0' }}>
              Supported formats: .WAV and .IQ
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
              <span>{isUploading ? 'Uploading...' : 'Upload Signal'}</span>
            </button>
          </div>

          <div className="files-empty-state">
            <div className="empty-files-text">No signal files uploaded</div>
          </div>
        </section>
      )}
    </div>
  );
}
