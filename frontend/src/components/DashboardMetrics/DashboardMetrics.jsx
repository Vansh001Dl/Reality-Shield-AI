import React from 'react';

const metricIcons = ['◉', '▰', '♙', '▲', '▥'];

function DashboardMetrics({ recordingAnalysis, dashboardData }) {
  const risk = dashboardData.risk || {};
  const values = [
    { label: 'Overall Safety Score', value: recordingAnalysis ? `${Math.round((risk.score || 0) * 100)}%` : '—', detail: recordingAnalysis ? (risk.severity || 'Analyzed') : 'Upload a video', tone: 'aqua' },
    { label: 'Vehicles Detected', value: recordingAnalysis?.vehicleCount ?? '—', detail: recordingAnalysis ? 'Recorded video' : 'Awaiting video', tone: 'blue' },
    { label: 'Pedestrians Detected', value: recordingAnalysis?.pedestrianCount ?? '—', detail: recordingAnalysis ? 'Scene activity' : 'Awaiting video', tone: 'mint' },
    { label: 'Active Alerts', value: recordingAnalysis ? (dashboardData.alerts?.length ?? 0) : '—', detail: recordingAnalysis ? 'Operator attention' : 'Awaiting analysis', tone: 'pink' },
    { label: 'Traffic Density', value: recordingAnalysis && risk.factors?.traffic_density != null ? `${Math.round(risk.factors.traffic_density * 100)}%` : '—', detail: recordingAnalysis ? 'Current video' : 'Awaiting video', tone: 'violet' },
  ];

  return (
    <section className="dashboard-metrics" aria-label="Live safety overview">
      {values.map((metric, index) => (
        <article className={`metric-card metric-${metric.tone}`} key={metric.label}>
          <span className="metric-icon" aria-hidden="true">{metricIcons[index]}</span>
          <div><span className="metric-label">{metric.label}</span><strong>{metric.value}</strong><small>{metric.detail}</small></div>
        </article>
      ))}
    </section>
  );
}

export default DashboardMetrics;
