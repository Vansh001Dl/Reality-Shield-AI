import React, { useState } from 'react';

function SafetyRiskScore({ risk = {}, factors = [], features = [], hasAnalysis = true }) {
  const [showShapDetails, setShowShapDetails] = useState(false);
  const percent = hasAnalysis ? Math.round((Number(risk.score) || 0) * 100) : 0;
  const severity = hasAnalysis ? risk.severity || 'unavailable' : 'Awaiting video';
  const riskFactors = features.length ? features.map((item) => ({ name: item.name, value: item.value })) : factors.map((item) => ({ name: item.name, value: item.value / 100 }));
  const visibleFactors = hasAnalysis ? riskFactors.slice(0, 5) : [];

  return <section className="panel safety-risk-panel">
    <div className="module-heading"><h2 className="card-title">Risk Factor Analysis</h2><span className="module-live">{hasAnalysis ? 'Current recording' : 'Awaiting video'}</span></div>
    <div className="risk-analysis-overview">
      <div className="gauge-box" style={{ '--risk': percent }}><div className="gauge-value"><strong>{hasAnalysis ? `${percent}` : '—'}</strong><span>{hasAnalysis ? 'Risk score' : 'Waiting'}</span></div></div>
      <div className="risk-meta-grid">
        <div><span>Risk Level</span><strong className="risk-level-badge">{hasAnalysis ? severity : '—'}</strong></div>
        <div><span>Confidence</span><strong>{hasAnalysis && risk.confidence != null ? `${Math.round(Number(risk.confidence) * 100)}%` : '—'}</strong></div>
        <div><span>Prediction</span><strong>{hasAnalysis ? 'From this video' : '—'}</strong></div>
      </div>
    </div>
    <div className="risk-factor-heading"><h3>Top Risk Factors (SHAP)</h3><button type="button" className="module-action shap-detail" disabled={!hasAnalysis} onClick={() => setShowShapDetails((value) => !value)}>{showShapDetails ? 'Hide details' : 'View SHAP details'}</button></div>
    <div className="factors-list risk-shap-list">
      {visibleFactors.map((item) => <div className="factor" key={item.name}><div className="factor-row"><span>{item.name}</span><span>{Number(item.value).toFixed(2)}</span></div><div className="bar"><span style={{ width: `${Math.min(100, Math.max(0, item.value * 100))}%` }} /></div></div>)}
    </div>
    {visibleFactors.length === 0 && <p className="empty-state risk-empty-state">{hasAnalysis ? 'No risk factors were returned for this video.' : 'Risk score and contributing factors will appear after analysis.'}</p>}
    {showShapDetails && hasAnalysis && <p className="shap-explanation-note">SHAP shows how each recorded scene factor contributes to the predicted road risk.</p>}
  </section>;
}

export default SafetyRiskScore;
