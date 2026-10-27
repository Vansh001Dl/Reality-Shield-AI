import React from 'react';

function Topbar({ title = 'Operational Dashboard', online = true, statusText, alertCount = 0, hasRecording = false, onRefresh }) {
  return (
    <header className="topbar">
      <div><h1 className="page-title">{title}</h1><p className="page-subtitle">AI-powered insights from recorded road video</p></div>

      <div className="topbar-actions">
        <span className="topbar-video">{hasRecording ? 'Recorded Video' : 'No video selected'}</span>
        <span className={`status-pill ${online ? 'online' : 'offline'}`}>● {statusText || (online ? 'System online' : 'Offline mode')}</span>
        <button type="button" className="pill" onClick={onRefresh}>Refresh</button>
        <span className="pill">Alerts: {alertCount == null ? '—' : String(alertCount).padStart(2, '0')}</span>
      </div>
    </header>
  );
}

export default Topbar;
