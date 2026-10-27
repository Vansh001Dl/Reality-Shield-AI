import React from 'react';

const metricIcons = ['◈', '⌖', '▰', '◎'];

function ReferenceDashboardMetrics({ recordingAnalysis, dashboardData }) {
  const risk = dashboardData.risk || {};
  const values = [
    { label: 'Overall Risk Score', value: recordingAnalysis ? `${Math.round((risk.score || 0) * 100)}` : '—', detail: recordingAnalysis ? (risk.severity || 'Analyzed') : 'Awaiting video', tone: 'pink' },
    { label: 'Current Location', value: recordingAnalysis?.location?.label || '—', detail: recordingAnalysis ? 'From analyzed recording' : 'Awaiting video', tone: 'mint' },
    { label: 'Vehicles Detected', value: recordingAnalysis?.vehicleCount ?? '—', detail: recordingAnalysis ? 'Unique tracked objects' : 'Awaiting video', tone: 'blue' },
    { label: 'Road Hazards', value: recordingAnalysis ? recordingAnalysis.potholeCount : '—', detail: recordingAnalysis ? 'Detected in recording' : 'Awaiting video', tone: 'violet' },
  ];
  return <section className="dashboard-metrics" aria-label="Live safety overview">
    {values.map((metric, index) => <article className={`metric-card metric-${metric.tone}`} key={metric.label}>
      <span className="metric-icon" aria-hidden="true">{metricIcons[index]}</span>
      <div><span className="metric-label">{metric.label}</span><strong>{metric.value}</strong><small>{metric.detail}</small></div>
    </article>)}
  </section>;
}

export default ReferenceDashboardMetrics;
