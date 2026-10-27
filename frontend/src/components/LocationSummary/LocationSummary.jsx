import React from 'react';

function LocationSummary({ risk, location, hasAnalysis = false }) {
  return (
    <section className="panel info-card">
      <h2 className="card-title">Location Summary</h2>

      <div className="summary-grid">
        <div className="summary-box">
          <span>Area</span>
          <strong>{hasAnalysis ? (location?.label || 'Location not provided') : '—'}</strong>
        </div>
        <div className="summary-box">
          <span>Source</span>
          <strong>{hasAnalysis ? 'Recorded video' : '—'}</strong>
        </div>
        <div className="summary-box">
          <span>Road Status</span>
          <strong>{hasAnalysis ? (risk?.severity || 'Unavailable') : '—'}</strong>
        </div>
      </div>
    </section>
  );
}

export default LocationSummary;
