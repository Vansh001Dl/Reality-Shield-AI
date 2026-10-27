import React, { useCallback, useEffect, useState } from 'react';
import './styles/dashboard.css';
import './styles/reference-dashboard.css';
import Sidebar from './components/ReferenceSidebar/ReferenceSidebar';
import Topbar from './components/ReferenceTopbar/ReferenceTopbar';
import SafetyRiskScore from './components/SafetyRiskScore/SafetyRiskScore';
import LiveRoadView from './components/LiveRoadView/LiveRoadView';
import RouteRecommendation from './components/RouteRecommendation/RouteRecommendation';
import RoadConditions from './components/RoadConditions/RoadConditions';
import DetectedObjects from './components/DetectedObjects/DetectedObjects';
import RecentAlerts from './components/RecentAlerts/RecentAlerts';
import LocationSummary from './components/LocationSummary/LocationSummary';
import WeatherSummary from './components/WeatherSummary/WeatherSummary';
import SafetyChat from './components/SafetyChat/SafetyChat';
import OperationsPage from './components/OperationsPage/OperationsPage';
import DashboardMetrics from './components/ReferenceDashboardMetrics/ReferenceDashboardMetrics';
import SpatialScene from './components/SpatialScene/SpatialScene';
import RiskForecast from './components/RiskForecast/RiskForecast';
import api from './services/api';

function App() {
  const [activePage, setActivePage] = useState('Dashboard');
  const [refreshKey, setRefreshKey] = useState(0);
  const [recordingAnalysis, setRecordingAnalysis] = useState(null);
  const [dashboardData, setDashboardData] = useState({
    health: { status: 'checking' },
    risk: { score: null, severity: 'awaiting video', confidence: null, factors: {} },
    alerts: [],
    route: null,
    routes: [],
    objects: [
      { label: 'Cars', count: 0 },
      { label: 'Buses', count: 0 },
      { label: 'Bikes', count: 0 },
      { label: 'Pedestrians', count: 0 },
      { label: 'Trucks', count: 0 },
      { label: 'Potholes', count: 0 },
      { label: 'Debris', count: 0 },
      { label: 'Waterlogging', count: 0 },
    ],
    factors: undefined,
    explanation: undefined,
  });

  const currentUser = null;

  useEffect(() => {
    let mounted = true;
    api.get('/health')
      .then(({ data }) => {
        if (mounted) setDashboardData((previous) => ({ ...previous, health: data }));
      })
      .catch(() => {
        if (mounted) setDashboardData((previous) => ({ ...previous, health: { status: 'offline' } }));
      });
    return () => { mounted = false; };
  }, [refreshKey]);

  useEffect(() => {
    let mounted = true;

    const loadDashboard = async () => {
      if (!recordingAnalysis) return;

      const payload = {
        camera_id: 'recorded_video',
        traffic_density: Math.min(1, recordingAnalysis.vehicleCount / 25),
        pedestrian_count: recordingAnalysis.pedestrianCount,
        vehicle_count: recordingAnalysis.vehicleCount,
        pothole_count: recordingAnalysis.potholeCount,
        speed_kmh: 0,
        weather_risk: 0,
        road_quality: 0.5,
        night_mode: false,
        critical_objects: recordingAnalysis.criticalObjects,
        metadata: { source: recordingAnalysis.fileName, location: recordingAnalysis.location.label },
      };

      try {
        const [riskResponse, routeResponse, alertResponse, explanationResponse] = await Promise.all([
          api.post('/api/risk/score', payload),
          api.post('/api/route/recommend', { start: recordingAnalysis.location.label, end: recordingAnalysis.location.label, routes: [] }),
          api.get('/api/alerts/recent'),
          api.post('/api/explain/summary', payload),
        ]);

        if (!mounted) return;

        const risk = riskResponse?.data?.risk || { score: 0, severity: 'unavailable', confidence: 0 };
        const recommendedRoute = routeResponse?.data?.recommended_route || null;
        const routes = routeResponse?.data?.all_routes || [];
        const alerts = alertResponse?.data?.alerts || [];
        const explanation = explanationResponse?.data?.explanation?.top_factors || [];

        setDashboardData((previous) => ({
          ...previous,
          risk,
          alerts,
          route: recommendedRoute,
          routes,
          objects: [
            { label: 'Cars', count: recordingAnalysis.counts.car || 0 },
            { label: 'Buses', count: recordingAnalysis.counts.bus || 0 },
            { label: 'Bikes', count: (recordingAnalysis.counts.bike || 0) + (recordingAnalysis.counts.motorcycle || 0) },
            { label: 'Pedestrians', count: recordingAnalysis.pedestrianCount },
            { label: 'Trucks', count: recordingAnalysis.counts.truck || 0 },
            { label: 'Potholes', count: recordingAnalysis.potholeCount },
            { label: 'Debris', count: recordingAnalysis.counts.debris || 0 },
            { label: 'Waterlogging', count: recordingAnalysis.counts.waterlogging || recordingAnalysis.counts.flood || 0 },
          ],
          explanation,
        }));

        if (!recordingAnalysis.archived) {
          await api.post('/api/analytics/history', {
            source_name: recordingAnalysis.fileName,
            location_name: recordingAnalysis.location.label,
            total_detections: recordingAnalysis.detectionsCount,
            vehicle_count: recordingAnalysis.vehicleCount,
            pedestrian_count: recordingAnalysis.pedestrianCount,
            pothole_count: recordingAnalysis.potholeCount,
            risk_score: risk.score || 0,
            severity: risk.severity || 'unknown',
            route_risk: recommendedRoute.risk_score || 0,
          }).catch((historyError) => console.warn('History save unavailable:', historyError));
        }
      } catch (error) {
        console.error('Dashboard fetch failed:', error);
      }
    };

    loadDashboard();
    return () => {
      mounted = false;
    };
  }, [refreshKey, recordingAnalysis]);

  const riskFactors = Object.entries(dashboardData.risk.factors || {}).map(([name, value]) => ({
    name: name.replace(/_/g, ' '),
    value: Math.min(100, Math.max(0, Number(value) * 100)),
  }));

  const explanationFeatures = (dashboardData.explanation || []).map((item) => ({
    name: String(item.feature || '').replace(/_/g, ' '),
    value: Math.min(1, Math.max(0, Number(item.impact))),
  }));

  const refresh = () => setRefreshKey((key) => key + 1);

  const handleAnalysisComplete = useCallback(({ fileName, detections, metadata, location, datasetId, archived = false }) => {
    const tracks = new Map();
    detections.forEach((detection, index) => {
      const label = String(detection.class_name || '').toLowerCase();
      const key = detection.track_id != null
        ? `${label}:${detection.track_id}`
        : `untracked:${detection.frame_index ?? 'image'}:${index}`;
      const track = tracks.get(key) || { detection, frames: new Set(), maxConfidence: 0 };
      if (detection.frame_index != null) track.frames.add(detection.frame_index);
      track.maxConfidence = Math.max(track.maxConfidence, Number(detection.confidence) || 0);
      tracks.set(key, track);
    });
    const entities = [...tracks.values()]
      .filter(({ detection, frames, maxConfidence }) => {
        if (String(detection.class_name || '').toLowerCase() !== 'truck') return true;
        return frames.size >= 2 || maxConfidence >= 0.65;
      })
      .map(({ detection }) => detection);
    const counts = entities.reduce((result, detection) => {
      const label = String(detection.class_name || '').toLowerCase();
      result[label] = (result[label] || 0) + 1;
      return result;
    }, {});
    const pedestrianCount = counts.person || counts.pedestrian || 0;
    const potholeCount = counts.pothole || 0;
    const vehicleCount = ['car', 'truck', 'bus', 'bike', 'motorcycle'].reduce(
      (total, label) => total + (counts[label] || 0),
      0,
    );

    setRecordingAnalysis({
      fileName,
      location,
      detections,
      metadata,
      datasetId,
      archived,
      counts,
      detectionsCount: entities.length,
      sampledDetectionsCount: detections.length,
      pedestrianCount,
      potholeCount,
      vehicleCount,
      criticalObjects: [potholeCount ? 'pothole' : '', pedestrianCount ? 'pedestrian' : ''].filter(Boolean),
    });
  }, []);

  const handleAnalysisReset = () => {
    setRecordingAnalysis(null);
    setDashboardData((previous) => ({
      ...previous,
      risk: { score: null, severity: 'awaiting video', confidence: null, factors: {} },
      alerts: [],
      route: null,
      routes: [],
      objects: [
        { label: 'Cars', count: 0 },
        { label: 'Buses', count: 0 },
        { label: 'Bikes', count: 0 },
        { label: 'Pedestrians', count: 0 },
        { label: 'Trucks', count: 0 },
        { label: 'Potholes', count: 0 },
        { label: 'Debris', count: 0 },
        { label: 'Waterlogging', count: 0 },
      ],
      explanation: undefined,
    }));
  };

  return (
    <div className="dashboard-shell">
      <Sidebar activeItem={activePage} onNavigate={setActivePage} user={currentUser} online={['ok', 'healthy'].includes(dashboardData.health.status)} />

      <main className="dashboard-main">
        <Topbar
          title={activePage === 'Dashboard' ? 'Road Safety Analysis' : activePage}
          online={['ok', 'healthy'].includes(dashboardData.health.status)}
          statusText={dashboardData.health.status === 'checking' ? 'Connecting to backend' : (!['ok', 'healthy'].includes(dashboardData.health.status) ? 'Backend offline' : (!recordingAnalysis ? 'Waiting for video' : undefined))}
          alertCount={recordingAnalysis ? dashboardData.alerts.length : null}
          hasRecording={Boolean(recordingAnalysis)}
          onRefresh={refresh}
          user={currentUser}
        />

        {activePage === 'Dashboard' ? (
          <>
            <DashboardMetrics recordingAnalysis={recordingAnalysis} dashboardData={dashboardData} />
            <SpatialScene analysis={recordingAnalysis} />
            <section className="reference-dashboard-grid" aria-label="Road safety dashboard modules">
              <div className="reference-column reference-column-video">
                <LiveRoadView onAnalysisComplete={handleAnalysisComplete} onAnalysisReset={handleAnalysisReset} />
                <DetectedObjects objects={dashboardData.objects} totalDetections={recordingAnalysis?.detectionsCount} hasAnalysis={Boolean(recordingAnalysis)} />
              </div>
              <div className="reference-column reference-column-map">
                <RouteRecommendation route={dashboardData.route} routes={dashboardData.routes} onNavigate={setActivePage} hasAnalysis={Boolean(recordingAnalysis)} />
                <SafetyRiskScore risk={dashboardData.risk} factors={riskFactors} features={explanationFeatures} hasAnalysis={Boolean(recordingAnalysis)} />
                <SafetyChat recordingAnalysis={recordingAnalysis} dashboardData={dashboardData} user={currentUser} />
              </div>
              <div className="reference-column reference-column-forecast">
                <RiskForecast routes={dashboardData.routes} hasAnalysis={Boolean(recordingAnalysis)} />
                <RecentAlerts alerts={dashboardData.alerts} onViewAll={setActivePage} hasAnalysis={Boolean(recordingAnalysis)} />
                <WeatherSummary location={recordingAnalysis?.location} />
                <LocationSummary risk={dashboardData.risk} location={recordingAnalysis?.location} hasAnalysis={Boolean(recordingAnalysis)} />
                <RoadConditions potholes={recordingAnalysis?.potholeCount ?? 0} location={recordingAnalysis?.location} hasAnalysis={Boolean(recordingAnalysis)} />
              </div>
            </section>
          </>
        ) : (
          <OperationsPage
            title={activePage}
            recordingAnalysis={recordingAnalysis}
            dashboardData={dashboardData}
            onNavigate={setActivePage}
            user={currentUser}
          />
        )}
      </main>
    </div>
  );
}

export default App;
