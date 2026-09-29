import React from 'react';
import { History } from 'lucide-react';

export default function RecentActivity() {
  return (
    <div className="activity-section">
      <h2 className="section-title">
        <History size={18} className="section-title-icon" />
        <span>Recent Activity</span>
      </h2>

      <div className="activity-empty">
        No analysis performed yet.
      </div>
    </div>
  );
}
