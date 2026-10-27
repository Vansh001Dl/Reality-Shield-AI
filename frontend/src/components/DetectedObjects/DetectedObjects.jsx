import React from 'react';

function DetectedObjects({ objects = [], totalDetections, hasAnalysis = false }) {
  return <section className="panel detected-objects-panel">
    <div className="module-heading"><h2 className="card-title">Detected Objects</h2><span className="module-live">{hasAnalysis ? 'Current recording' : 'Awaiting video'}</span></div>
    <div className="object-grid">
      {objects.map((item) => <div key={item.label} className="metric"><span>{item.label}</span><strong>{hasAnalysis ? item.count : '—'}</strong></div>)}
      <div className="metric total-detections"><span>Total Detected</span><strong>{hasAnalysis && totalDetections != null ? totalDetections : '—'}</strong></div>
    </div>
  </section>;
}

export default DetectedObjects;
