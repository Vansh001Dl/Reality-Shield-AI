import React from 'react';

function RoadConditions({ potholes = 0, location, hasAnalysis = false }) {
  const detected = hasAnalysis && potholes > 0;
  return (
    <section className="panel road-conditions-card">
      <div className="module-heading"><h2 className="card-title">Road Conditions</h2><span className={`module-live ${detected ? 'module-alert' : ''}`}>{hasAnalysis ? 'Scan result' : 'Awaiting video'}</span></div>
      {hasAnalysis ? <div className="road-condition-image" role="img" aria-label="Illustrated road surface condition visualization">
        <svg viewBox="0 0 480 150" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
          <defs>
            <linearGradient id="road-sky" x2="0" y2="1"><stop stopColor="#38171c"/><stop offset="1" stopColor="#100d0f"/></linearGradient>
            <linearGradient id="road-wet" x2="0" y2="1"><stop stopColor="#4b3437"/><stop offset=".55" stopColor="#242124"/><stop offset="1" stopColor="#0b0a0c"/></linearGradient>
            <linearGradient id="road-glint"><stop stopColor="#fff" stopOpacity="0"/><stop offset=".5" stopColor="#fff" stopOpacity=".28"/><stop offset="1" stopColor="#fff" stopOpacity="0"/></linearGradient>
          </defs>
          <rect width="480" height="150" fill="url(#road-sky)"/>
          <path d="M0 57 480 48 480 150 0 150Z" fill="url(#road-wet)"/>
          <path d="m0 65 480-12M0 77l480-12M0 97l480-15M0 126l480-20" stroke="#a7a0a0" strokeOpacity=".14" strokeWidth="2"/>
          <path d="M0 73h480M0 115h480" stroke="url(#road-glint)" strokeWidth="3"/>
          <path d="M161 104c13-12 35-13 51-5l16 9-14 8-48-1-16-5Zm107 15c17-14 45-15 62-6l13 8-13 9-55-1-17-5Z" fill="#070709" stroke="#ff4458" strokeWidth="2"/>
          <path d="m188 105 16 3m78 15 21 3" stroke="#fff" strokeOpacity=".36" strokeWidth="2"/>
          <path d="M30 147 158 65M450 145 333 56" stroke="#d9d3d4" strokeOpacity=".17" strokeWidth="3"/>
          <circle cx="201" cy="107" r="34" fill="none" stroke="#ff334b" strokeOpacity=".42" strokeWidth="2"/>
          {detected && <g><path d="M201 69v17m0 42v17m-38-38h17m42 0h17" stroke="#ff465a" strokeWidth="2"/><rect x="165" y="70" width="73" height="76" rx="5" fill="none" stroke="#ff465a" strokeWidth="2" strokeDasharray="5 4"/></g>}
          <rect width="480" height="150" fill="none" stroke="#fff" strokeOpacity=".08"/>
        </svg>
        <span className="road-image-caption">Road scan visualization</span>
      </div> : <p className="empty-state module-empty-state">Upload a road video to detect potholes and road hazards.</p>}
      {hasAnalysis && <><div className="road-condition-status"><span className="risk-alert-icon">!</span><strong>{detected ? 'Pothole Detected' : 'No pothole detected'}</strong><span className={`risk-tag ${detected ? 'high' : 'low'}`}>{detected ? 'High' : 'Clear'}</span></div>
      <div className="road-condition-meta"><span>Location<strong>{location?.label || 'Not provided'}</strong></span><span>Type<strong>{detected ? 'Pothole / road hazard' : 'Road surface'}</strong></span><span>Severity<strong className={detected ? 'text-danger' : ''}>{detected ? 'High' : 'No hazard'}</strong></span></div></>}
      <button type="button" className="module-action" disabled={!hasAnalysis} onClick={() => document.querySelector('.recorded-video')?.scrollIntoView({ behavior: 'smooth', block: 'center' })}>View Details <span>↗</span></button>
    </section>
  );
}

export default RoadConditions;
