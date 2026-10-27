import React from 'react';

function HowItWorks() {
  return (
    <section className="panel">
      <h2 className="card-title">How It Works</h2>
      <div className="list-card">
        <div className="route-line">
          <span>1. Vision Agent</span>
          <span>YOLO + OpenCV</span>
        </div>
        <div className="route-line">
          <span>2. Risk Agent</span>
          <span>XGBoost</span>
        </div>
        <div className="route-line">
          <span>3. Explanation Agent</span>
          <span>SHAP</span>
        </div>
        <div className="route-line">
          <span>4. Route Agent</span>
          <span>Leaflet + PostGIS</span>
        </div>
      </div>
    </section>
  );
}

export default HowItWorks;
