import React from 'react';
import { Radio } from 'lucide-react';

export default function Header({ backendConnected = false }) {
  return (
    <header className="top-header">
      <div className="header-left">
        <div className="header-logo-icon">
          <Radio size={20} />
        </div>
        <div className="header-titles">
          <h1 className="brand-title">SignalScope</h1>
          <span className="brand-subtitle">Automatic Radio Signal Analysis</span>
        </div>
      </div>
      <div className={`header-status ${backendConnected ? 'connected' : 'offline'}`}>
        <span className={`status-dot ${backendConnected ? 'status-online' : 'status-offline'}`}></span>
        <span>{backendConnected ? 'Backend: Connected' : 'Backend: Offline'}</span>
      </div>
    </header>
  );
}
