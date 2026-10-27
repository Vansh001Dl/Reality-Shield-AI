import React from 'react';

function RiskForecast({ routes = [], hasAnalysis = false }) {
  const points = routes.slice(0, 4).map((route, index) => ({
    label: String(route.route_id || `Route ${index + 1}`).replace(/[_-]/g, ' '),
    score: Math.max(0, Math.min(100, Math.round((Number(route.risk_score) || 0) * 100))),
  }));
  const chartPoints = points.map((point, index) => ({
    ...point,
    x: points.length === 1 ? 150 : 20 + (index * 260) / (points.length - 1),
    y: 108 - point.score * 0.86,
  }));
  const line = chartPoints.map((point, index) => `${index ? 'L' : 'M'} ${point.x} ${point.y}`).join(' ');

  return <section className="panel forecast-panel">
    <div className="module-heading"><h2 className="card-title">Future Risk Forecast</h2><span className="forecast-badge">ROUTE DATA</span></div>
    {chartPoints.length ? <>
      <div className="forecast-chart" role="img" aria-label="Risk scores for analyzed route options">
        <div className="forecast-axis"><span>100</span><span>75</span><span>50</span><span>25</span><span>0</span></div>
        <svg viewBox="0 0 300 120" preserveAspectRatio="none" aria-hidden="true">
          {[22, 43, 64, 85, 107].map((y) => <line key={y} x1="0" y1={y} x2="300" y2={y} />)}
          {points.length > 1 && <path className="forecast-area" d={`${line} L ${chartPoints.at(-1).x} 108 L ${chartPoints[0].x} 108 Z`} />}
          {points.length > 1 && <path className="forecast-line" d={line} />}
          {chartPoints.map((point) => <g key={point.label}><circle cx={point.x} cy={point.y} r="4" /><text x={point.x} y={point.y - 9} textAnchor="middle">{point.score}</text></g>)}
        </svg>
      </div>
      <div className="forecast-route-list">{chartPoints.map((point) => <div className="forecast-route-row" key={point.label}><span>{point.label}</span><strong>{point.score}<small>/100 risk</small></strong></div>)}</div>
    </> : <div className="forecast-empty"><div className="forecast-empty-chart" aria-hidden="true"><span /><span /><span /><span /><span /></div><p>{hasAnalysis ? 'Route forecast is unavailable for this recording.' : 'Forecast data will appear after video analysis.'}</p></div>}
  </section>;
}

export default RiskForecast;
