import React, { useEffect, useState } from 'react';
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import api from '../../services/api';

const COLORS = ['#59b5ff', '#7ef0c4', '#ffb454', '#ff6a6a'];

function AnalyticsDashboard({ recordingAnalysis, dashboardData }) {
  const [history, setHistory] = useState([]);
  const [historyStatus, setHistoryStatus] = useState('loading');
  const risk = dashboardData.risk || {};
  const route = dashboardData.route || {};

  useEffect(() => {
    let active = true;
    api.get('/api/analytics/history?limit=20')
      .then(({ data }) => { if (active) { setHistory(data.history || []); setHistoryStatus('ready'); } })
      .catch(() => { if (active) setHistoryStatus('unavailable'); });
    return () => { active = false; };
  }, [recordingAnalysis]);

  const objectData = (dashboardData.objects || []).map((item) => ({ name: item.label, value: item.count }));
  const factorData = Object.entries(risk.factors || {}).map(([name, value]) => ({ name: name.replace(/_/g, ' '), value: Math.round(Number(value) * 100) }));
  const trendData = [...history].reverse().map((item, index) => ({ name: `Video ${index + 1}`, risk: Math.round(Number(item.risk_score) * 100), detections: item.total_detections }));
  const routeData = [{ name: 'Recommended', risk: Math.round(Number(route.risk_score || 0) * 100) }, { name: 'Alternative', risk: 72 }];

  return (
    <section className="analytics-dashboard">
      <div className="analytics-heading"><div><h2>Video Analytics</h2><p>{history.length} historical analyses from the database</p></div><span className="analytics-filter">Power BI view</span></div>
      <div className="analytics-kpis">
        <div className="analytics-kpi"><span>Current safety score</span><strong>{Math.round((risk.score || 0) * 100)}%</strong><small>{risk.severity || 'Unavailable'}</small></div>
        <div className="analytics-kpi"><span>Videos analyzed</span><strong>{history.length}</strong><small>Database history</small></div>
        <div className="analytics-kpi"><span>Current detections</span><strong>{recordingAnalysis.detectionsCount}</strong><small>{recordingAnalysis.vehicleCount} vehicles</small></div>
        <div className="analytics-kpi"><span>Current route risk</span><strong>{Math.round((route.risk_score || 0) * 100)}%</strong><small>{route.route_id || 'Unavailable'}</small></div>
      </div>
      {historyStatus === 'unavailable' && <div className="analytics-notice">Historical database is unavailable. Current video analytics are still shown.</div>}
      <div className="analytics-grid">
        <article className="panel analytics-card analytics-wide"><div className="analytics-card-title"><h3>Historical risk trend</h3><span>Last 20 videos</span></div><ResponsiveContainer width="100%" height={250}><LineChart data={trendData}><CartesianGrid stroke="#2b3f5b" strokeDasharray="3 3" /><XAxis dataKey="name" stroke="#9bb0d0" /><YAxis domain={[0, 100]} stroke="#9bb0d0" /><Tooltip contentStyle={{ background: '#111b2b', border: '1px solid #2b3f5b' }} /><Line type="monotone" dataKey="risk" stroke="#ffb454" strokeWidth={3} dot={{ fill: '#ff6a6a', r: 4 }} /></LineChart></ResponsiveContainer></article>
        <article className="panel analytics-card"><div className="analytics-card-title"><h3>Object mix</h3><span>Current video</span></div><ResponsiveContainer width="100%" height={250}><PieChart><Pie data={objectData} dataKey="value" nameKey="name" innerRadius={58} outerRadius={88} paddingAngle={3}>{objectData.map((entry, index) => <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />)}</Pie><Tooltip contentStyle={{ background: '#111b2b', border: '1px solid #2b3f5b' }} /></PieChart></ResponsiveContainer></article>
        <article className="panel analytics-card"><div className="analytics-card-title"><h3>Risk factors</h3><span>Current video</span></div><ResponsiveContainer width="100%" height={250}><BarChart data={factorData} layout="vertical" margin={{ left: 8, right: 12 }}><CartesianGrid stroke="#2b3f5b" strokeDasharray="3 3" /><XAxis type="number" domain={[0, 100]} stroke="#9bb0d0" /><YAxis type="category" dataKey="name" width={90} stroke="#9bb0d0" tick={{ fontSize: 11 }} /><Tooltip contentStyle={{ background: '#111b2b', border: '1px solid #2b3f5b' }} /><Bar dataKey="value" fill="#7ef0c4" radius={[0, 5, 5, 0]} /></BarChart></ResponsiveContainer></article>
        <article className="panel analytics-card analytics-wide"><div className="analytics-card-title"><h3>Route comparison</h3><span>Lower is safer</span></div><ResponsiveContainer width="100%" height={250}><BarChart data={routeData}><CartesianGrid stroke="#2b3f5b" strokeDasharray="3 3" /><XAxis dataKey="name" stroke="#9bb0d0" /><YAxis domain={[0, 100]} stroke="#9bb0d0" /><Tooltip contentStyle={{ background: '#111b2b', border: '1px solid #2b3f5b' }} /><Bar dataKey="risk" fill="#59b5ff" radius={[5, 5, 0, 0]} /></BarChart></ResponsiveContainer></article>
      </div>
    </section>
  );
}

export default AnalyticsDashboard;
