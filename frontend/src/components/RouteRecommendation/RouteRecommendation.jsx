import React from 'react';

const paths = [
  'M24 168 C58 150 50 120 82 112 S125 111 147 76 186 62 213 36',
  'M24 168 C57 154 77 160 92 130 S118 90 139 100 172 122 190 86 191 53 213 36',
  'M24 168 C45 137 62 134 83 112 S114 72 144 78 169 103 180 81 197 52 213 36',
];

function routeLabel(route, index) {
  const key = String(route.route_id || `Route ${index + 1}`).replace(/[_-]/g, ' ');
  return key.replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function RouteRecommendation({ route, routes = [], onNavigate, hasAnalysis = false }) {
  const options = hasAnalysis ? (routes.length ? routes : route ? [route] : []) : [];
  const selected = String(route?.route_id || '').toLowerCase();
  const selectedIndex = Math.max(0, options.findIndex((option) => String(option.route_id || '').toLowerCase() === selected));
  return <section className="panel route-recommendation-panel">
    <div className="module-heading"><h2 className="card-title">Route Map &amp; Recommendations</h2><span className="map-live-pill"><i />{hasAnalysis ? (options.length ? 'Available' : 'No routes') : 'Awaiting video'}</span></div>
    <div className="route-recommendation-content">
      <div className="route-map-visual">
        <svg viewBox="0 0 240 200" role="img" aria-label={options.length ? 'Schematic comparison of returned route options' : 'Route map waiting for available route data'}>
          <defs><pattern id="route-grid" width="30" height="30" patternUnits="userSpaceOnUse"><path d="M30 0H0V30" fill="none" stroke="#9ac7ef" strokeOpacity=".09" /></pattern></defs>
          <rect width="240" height="200" fill="#08182b" /><rect width="240" height="200" fill="url(#route-grid)" />
          <g fill="none" stroke="#a4bed8" strokeOpacity=".18" strokeWidth="7"><path d="M-10 44 238 160M28-8l176 220M-12 154 252 52M92-8 72 210M178-8 152 212" /><path d="M-10 44 238 160M28-8l176 220M-12 154 252 52M92-8 72 210M178-8 152 212" stroke="#08182b" strokeWidth="2" /></g>
          {options.length > 0 && paths.slice(0, options.length).map((path, index) => <path key={path} d={path} transform="translate(5 8)" fill="none" stroke={index === selectedIndex ? '#5de1b7' : index === 1 ? '#f3c65c' : '#55aafa'} strokeWidth={index === selectedIndex ? 4 : 2.5} strokeOpacity={index === selectedIndex ? 1 : .7} strokeLinecap="round" strokeLinejoin="round" strokeDasharray={index === selectedIndex ? '0' : '6 5'} />)}
          {options.length > 0 && <><circle cx="29" cy="176" r="7" fill="#fff" stroke="#5de1b7" strokeWidth="3" /><path d="m213 27 10 18h-20Z" fill="#59b3ff" stroke="#fff" strokeWidth="1.5" /><text x="18" y="194" fill="#dceaff" fontSize="9">START</text><text x="193" y="22" fill="#dceaff" fontSize="9">END</text></>}
        </svg>
        <span className="map-location-chip">{options.length ? 'Schematic route comparison' : hasAnalysis ? 'No route data returned' : 'Map waits for analyzed video'}</span>
      </div>
      <div className="route-options">
        {options.slice(0, 3).map((option, index) => {
          const isSelected = String(option.route_id || '').toLowerCase() === selected || (!selected && index === 0);
          return <div className={`route-option ${isSelected ? 'selected' : ''}`} key={option.route_id || index}>
            <span className={`route-marker marker-${index + 1}`} />
            <span className="route-option-name"><strong>{routeLabel(option, index)}</strong><small>{isSelected ? 'Recommended by route model' : 'Alternative returned route'}</small></span>
            <span className="route-risk-score">Risk {Math.round(Number(option.risk_score || 0) * 100)}</span>
          </div>;
        })}
        {!hasAnalysis && <p className="empty-state route-empty-state">Route options appear after video analysis.</p>}
        {hasAnalysis && options.length === 0 && <p className="empty-state route-empty-state">The route service returned no route options for this recording.</p>}
        <button type="button" className="module-action route-view-all" disabled={!hasAnalysis || options.length === 0} onClick={() => onNavigate?.('Route Recommendation')}>View all routes <span aria-hidden="true">→</span></button>
      </div>
    </div>
  </section>;
}

export default RouteRecommendation;
