import React from 'react';
import RiskMap from '../RiskMap/RiskMap';
import AnalyticsDashboard from '../AnalyticsDashboard/AnalyticsDashboard';

const content = {
  'Recorded Video': ['Recorded video analysis', 'Upload a road recording on the dashboard and review its risk, object, route, and alert results.', 'Use the dashboard refresh control after selecting a recording to retrieve the newest analysis.'],
  'Risk Prediction': ['Risk assessment', 'Risk scores combine traffic, pedestrians, vehicles, road condition, speed, weather, and visibility.', 'Scores are categorised as low, moderate, high, or critical.'],
  'Route Recommendation': ['Safer route comparison', 'Routes are ranked using congestion, traffic density, potholes, pedestrian activity, speed limit, and weather.', 'The lowest combined route risk is presented as the recommended option.'],
  Alerts: ['Safety alerts', 'Alerts are raised when the current scene needs operator attention.', 'Review the dashboard alert feed for the latest risk notification.'],
  'History Logs': ['Event history', 'Historical detections and risk assessments are ready to be stored in the included PostgreSQL schema.', 'Use recorded road videos as the source for new operational records.'],
  Analytics: ['Safety analytics', 'Monitor risk patterns across corridors, times, and environmental conditions.', 'The current prototype keeps its calculations transparent for auditability.'],
  'Map View': ['Network map', 'Route candidates support coordinates and can be rendered with the included Leaflet dependencies.', 'Add a mapping provider token when deploying a production map.'],
  Settings: ['System settings', 'Configure the API endpoint through VITE_API_BASE_URL and the database through DATABASE_URL.', 'Use environment variables instead of committing credentials.'],
  Users: ['Operator access', 'The application is prepared for role-based operator and administrator accounts.', 'Add your identity provider before enabling multi-user deployment.'],
};

function OperationsPage({ title, recordingAnalysis, dashboardData, onNavigate }) {
  const [heading, description, detail] = content[title] || content.Analytics;

  if (!recordingAnalysis) {
    return (
      <section className="panel empty-workspace">
        <h2>{heading}</h2>
        <p>Select a recorded road video from the Dashboard first. This workspace will populate after analysis completes.</p>
        <button type="button" className="workspace-action" onClick={() => onNavigate('Dashboard')}>Go to Dashboard</button>
      </section>
    );
  }

  const risk = dashboardData.risk || {};
  const route = dashboardData.route || {};
  const alerts = dashboardData.alerts || [];
  const explanation = dashboardData.explanation || [];
  if (title === 'Map View') {
    return (
      <section className="map-workspace">
        <div className="panel map-panel-heading"><h2>{heading}</h2><p>{description}</p></div>
        <RiskMap location={recordingAnalysis.location} />
        <div className="panel map-route-summary"><strong>India-wide map</strong><span>Video location: {recordingAnalysis.location.label}</span><span>Recommended route: {route.route_id || 'Unavailable'}</span><span>Risk score: {Number(route.risk_score || 0).toFixed(2)}</span></div>
      </section>
    );
  }
  if (title === 'Analytics') {
    return <AnalyticsDashboard recordingAnalysis={recordingAnalysis} dashboardData={dashboardData} />;
  }
  const metrics = {
    'Recorded Video': [
      ['File', recordingAnalysis.fileName],
      ['Objects detected', recordingAnalysis.detectionsCount],
      ['Vehicles', recordingAnalysis.vehicleCount],
      ['Pedestrians', recordingAnalysis.pedestrianCount],
    ],
    'Risk Prediction': [
      ['Risk score', `${Math.round((risk.score || 0) * 100)}%`],
      ['Severity', risk.severity || 'Unavailable'],
      ['Confidence', `${Math.round((risk.confidence || 0) * 100)}%`],
      ['Potholes', recordingAnalysis.potholeCount],
    ],
    'Route Recommendation': [
      ['Recommended route', route.route_id || 'Unavailable'],
      ['Route risk', Number(route.risk_score || 0).toFixed(2)],
      ['Travel time', `${route.estimated_time_minutes || 18} mins`],
    ],
    Alerts: [['Active alerts', alerts.length], ['Video source', recordingAnalysis.fileName]],
    Analytics: [['Objects detected', recordingAnalysis.detectionsCount], ['Risk score', `${Math.round((risk.score || 0) * 100)}%`], ['Top factors', explanation.length]],
    'History Logs': [['Latest recording', recordingAnalysis.fileName], ['Objects detected', recordingAnalysis.detectionsCount], ['Analysis status', 'Complete']],
    'Map View': [['Route', route.route_id || 'Unavailable'], ['Route risk', Number(route.risk_score || 0).toFixed(2)], ['Source', recordingAnalysis.fileName]],
    Settings: [['API status', dashboardData.health.status], ['Video analysis', 'Enabled'], ['Source mode', 'Recorded video']],
    Users: [['Workspace status', 'Ready'], ['Analysis source', 'Recorded video'], ['Last file', recordingAnalysis.fileName]],
  }[title] || [];

  return (
    <section className="workspace-grid">
      <article className="panel workspace-card">
        <h2>{heading}</h2>
        <p>{description}</p>
        <div className="workspace-metrics">
          {metrics.map(([label, value]) => <div className="workspace-metric" key={label}><span>{label}</span><strong>{value}</strong></div>)}
        </div>
      </article>
      <article className="panel workspace-card">
        <h2>Operational guidance</h2>
        <p>{detail}</p>
      </article>
      <article className="panel workspace-card">
        <h2>Analysis status</h2>
        <ul>
          <li>Video: {recordingAnalysis.fileName}</li>
          <li>Risk, route, and explanation APIs connected.</li>
          <li>Recorded video is the source for scene analysis.</li>
        </ul>
      </article>
    </section>
  );
}

export default OperationsPage;
