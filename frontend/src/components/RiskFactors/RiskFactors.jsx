import React from 'react';

const fallbackFactors = [
  { name: 'Traffic Density', value: 82 },
  { name: 'Pedestrian Risk', value: 64 },
  { name: 'Road Quality', value: 71 },
  { name: 'Night Visibility', value: 59 },
];

function RiskFactors({ factors = fallbackFactors }) {
  return (
    <section className="panel">
      <h2 className="card-title">Risk Factors</h2>

      <div className="factors-list">
        {factors.map((factor) => (
          <div key={factor.name} className="factor">
            <div className="factor-row">
              <span>{factor.name}</span>
              <span>{Math.round(factor.value)}%</span>
            </div>
            <div className="bar">
              <span style={{ width: `${factor.value}%` }} />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

export default RiskFactors;
