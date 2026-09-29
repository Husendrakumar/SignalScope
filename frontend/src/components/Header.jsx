import React from 'react';
import { Radio, Moon, Sun } from 'lucide-react';

export default function Header({ backendConnected = false, theme, setTheme }) {
  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

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
      <div className="header-right" style={{display: 'flex', alignItems: 'center', gap: '16px'}}>
        <button 
          onClick={toggleTheme} 
          style={{
            display: 'flex', 
            alignItems: 'center', 
            gap: '8px', 
            background: 'transparent',
            border: '1px solid var(--border-color)',
            color: 'var(--text-primary)',
            padding: '6px 12px',
            borderRadius: '6px',
            cursor: 'pointer'
          }}
        >
          {theme === 'dark' ? <Sun size={16}/> : <Moon size={16}/>}
          <span>{theme === 'dark' ? 'Light' : 'Dark'}</span>
        </button>
        <div className={`header-status ${backendConnected ? 'connected' : 'offline'}`}>
          <span className={`status-dot ${backendConnected ? 'status-online' : 'status-offline'}`}></span>
          <span>{backendConnected ? 'Backend: Connected' : 'Backend: Offline'}</span>
        </div>
      </div>
    </header>
  );
}
