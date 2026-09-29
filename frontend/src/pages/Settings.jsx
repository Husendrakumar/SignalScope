import React from 'react';
import { Settings as SettingsIcon, Moon, Zap, Eye } from 'lucide-react';

export default function Settings() {
  return (
    <div className="content-area">
      <header className="page-header">
        <h1 className="page-title">Settings</h1>
        <p className="page-description">
          Configure application preferences and display options.
        </p>
      </header>

      <section className="settings-card">
        <h2 className="section-title">
          <SettingsIcon size={18} className="section-title-icon" />
          <span>General Preferences</span>
        </h2>

        <div className="settings-list">
          <div className="setting-item">
            <div className="setting-info">
              <div className="setting-name">
                <Moon size={16} className="setting-icon" />
                <span>Theme</span>
              </div>
              <p className="setting-desc">Application color mode</p>
            </div>
            <div className="setting-control">
              <span className="setting-badge">Dark</span>
            </div>
          </div>

          <div className="setting-item">
            <div className="setting-info">
              <div className="setting-name">
                <Zap size={16} className="setting-icon" />
                <span>Auto Analysis</span>
              </div>
              <p className="setting-desc">Automatically trigger pipeline upon file upload</p>
            </div>
            <div className="setting-control">
              <span className="setting-badge disabled">Off</span>
            </div>
          </div>

          <div className="setting-item">
            <div className="setting-info">
              <div className="setting-name">
                <Eye size={16} className="setting-icon" />
                <span>Confidence Display</span>
              </div>
              <p className="setting-desc">Show statistical confidence metrics for detection</p>
            </div>
            <div className="setting-control">
              <span className="setting-badge active">On</span>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
