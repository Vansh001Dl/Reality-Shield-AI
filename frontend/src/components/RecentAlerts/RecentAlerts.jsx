import React from 'react';

function RecentAlerts({ alerts = [], onViewAll, hasAnalysis = false }) {
  const alertItems = alerts.slice(0, 4).map((alert, index) => {
    const message = typeof alert === 'string' ? alert : alert.message || 'System alert';
    const lower = message.toLowerCase();
    const tone = lower.includes('pedestrian') ? 'pedestrian' : lower.includes('pothole') || lower.includes('hazard') ? 'hazard' : lower.includes('traffic') ? 'traffic' : 'moderate';
    return { message, tone, time: ['5 min ago', '12 min ago', '18 min ago', '32 min ago'][index] };
  });

  return (
    <section className="panel">
      <div className="module-heading"><h2 className="card-title">Recent Alerts</h2><button type="button" className="text-action" onClick={() => onViewAll?.('Alerts')}>View All →</button></div>
      <div className="alert-list">
        {alertItems.map((alert, index) => (
          <div key={`${alert.message}-${index}`} className="alert-row"><span className={`alert-icon alert-${alert.tone}`}>{alert.tone === 'pedestrian' ? '♟' : alert.tone === 'hazard' ? '▲' : alert.tone === 'traffic' ? '◉' : '◈'}</span><span className="alert-copy"><strong>{alert.message}</strong><small>Recorded road analysis</small></span><time>{alert.time}</time></div>
        ))}
        {alertItems.length === 0 && <p className="empty-state alert-empty-state">{hasAnalysis ? 'No alerts were returned for this video.' : 'Alerts will appear after video analysis.'}</p>}
      </div>
    </section>
  );
}

export default RecentAlerts;
