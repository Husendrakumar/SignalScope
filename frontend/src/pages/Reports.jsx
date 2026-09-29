import React from 'react';
import { FileBarChart } from 'lucide-react';

export default function Reports() {
  return (
    <div className="content-area">
      <header className="page-header">
        <h1 className="page-title">Analysis Reports</h1>
        <p className="page-description">
          View reports generated from completed signal analysis.
        </p>
      </header>

      <section className="reports-empty-card">
        <div className="empty-icon-wrapper">
          <FileBarChart size={36} />
        </div>
        <h2 className="empty-title">No reports available</h2>
        <p className="empty-desc">
          Complete an automated signal analysis to generate printable and exportable reports.
        </p>
      </section>
    </div>
  );
}
