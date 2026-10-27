import React from 'react';

const fallbackFeatures = [
  { name: 'Traffic density', value: 0.34 },
  { name: 'Pothole count', value: 0.26 },
  { name: 'Pedestrian activity', value: 0.22 },
  { name: 'Low visibility', value: 0.18 },
];

function ShapExplanation({ features = fallbackFeatures }) {
  return (
    <section className="panel">
      <h2 className="card-title">SHAP Explanation</h2>
      <div className="factors-list">
        {features.map((feature) => (
          <div key={feature.name} className="factor">
            <div className="factor-row">
              <span>{feature.name}</span>
              <span>{feature.value.toFixed(2)}</span>
            </div>
            <div className="bar">
              <span style={{ width: `${(feature.value * 100).toFixed(0)}%` }} />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

export default ShapExplanation;
