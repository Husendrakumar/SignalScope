import React from 'react';
import { LayoutDashboard, Activity, FolderOpen, FileBarChart, Settings } from 'lucide-react';

export default function Sidebar({ activePage, onPageChange }) {
  const navItems = [
    { id: 'dashboard', name: 'Dashboard', icon: LayoutDashboard },
    { id: 'analysis', name: 'Signal Analysis', icon: Activity },
    { id: 'files', name: 'Files', icon: FolderOpen },
    { id: 'reports', name: 'Reports', icon: FileBarChart },
    { id: 'settings', name: 'Settings', icon: Settings },
  ];

  return (
    <aside className="sidebar">
      <nav className="sidebar-nav">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activePage === item.id;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onPageChange(item.id)}
              className={`nav-item ${isActive ? 'active' : ''}`}
            >
              <Icon className="nav-item-icon" />
              <span>{item.name}</span>
            </button>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div className="badge-ps">PS 147</div>
        <div className="badge-sih">SIH Project</div>
      </div>
    </aside>
  );
}
