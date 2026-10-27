import React from 'react';

function RecommendedRoute({ route = { route_id: 'route_a', risk_score: 0.2 } }) {
  const routeName = route.route_id || 'route_a';
  const riskLevel = route.risk_score <= 0.3 ? 'Low' : route.risk_score <= 0.6 ? 'Moderate' : 'High';

  return (
    <section className="panel route-card">
      <h2 className="card-title">Recommended Route</h2>

      <div className="route-line">
        <span>{routeName}</span>
        <span className="score-badge">{riskLevel}</span>
      </div>
      <div className="route-line">
        <span>Route Risk</span>
        <span>{(route.risk_score || 0.2).toFixed(2)}</span>
      </div>
      <div className="route-line">
        <span>Travel Time</span>
        <span>18 mins</span>
      </div>
    </section>
  );
}

export default RecommendedRoute;
