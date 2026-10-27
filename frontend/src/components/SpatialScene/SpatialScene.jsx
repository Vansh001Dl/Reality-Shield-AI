import React, { useMemo, useState } from 'react';

function SpatialScene({ analysis }) {
  const [view, setView] = useState('oblique');
  const [showLabels, setShowLabels] = useState(false);
  const [showGrid, setShowGrid] = useState(true);
  const hasAnalysis = Boolean(analysis);
  const detections = analysis?.detections || [];
  const metadata = analysis?.metadata || {};
  const entityCounts = Object.entries(analysis?.counts || {})
    .filter(([, count]) => Number(count) > 0)
    .sort((left, right) => Number(right[1]) - Number(left[1]));
  const entitySummary = entityCounts.map(([name, count]) => `${count} ${name.replace(/_/g, ' ')}`).join(', ');

  const points = useMemo(() => detections.map((item, index) => {
    const [x1 = 0, y1 = 0, x2 = 0, y2 = 0] = item.bbox || item.bbox_json || [];
    const width = Number(metadata.frame_width) || 1;
    const height = Number(metadata.frame_height) || 1;
    const centerX = (Number(x1) + Number(x2)) / 2;
    const centerY = (Number(y1) + Number(y2)) / 2;
    return {
      id: `${item.track_id ?? 'object'}-${item.frame_index ?? index}-${index}`,
      x: Math.min(96, Math.max(4, (centerX / width) * 100)),
      y: Math.min(90, Math.max(8, (centerY / height) * 100)),
      label: item.class_name || 'Object',
      confidence: Math.round((Number(item.confidence) || 0) * 100),
      critical: ['pedestrian', 'person', 'pothole'].includes(String(item.class_name || '').toLowerCase()),
    };
  }).filter((_, index) => detections.length <= 36 || index % Math.ceil(detections.length / 36) === 0).slice(0, 36), [detections, metadata]);

  return (
    <section className="spatial-deck" aria-label="Interactive spatial scene">
      <div className="spatial-heading">
        <div>
          <span className="spatial-eyebrow"><i /> SPATIAL INTELLIGENCE / 01</span>
          <h2>Scene reconstruction</h2>
          <p>Explore detected entities in a 2.5D frame projection of the uploaded recording.</p>
        </div>
        <div className="spatial-controls" aria-label="Scene controls">
          <div className="scene-toggle" role="group" aria-label="Scene angle">
            <button type="button" className={view === 'oblique' ? 'selected' : ''} aria-pressed={view === 'oblique'} onClick={() => setView('oblique')}>3D ORBIT</button>
            <button type="button" className={view === 'plan' ? 'selected' : ''} aria-pressed={view === 'plan'} onClick={() => setView('plan')}>TOP VIEW</button>
          </div>
          <button type="button" className={`scene-chip ${showGrid ? 'selected' : ''}`} aria-pressed={showGrid} onClick={() => setShowGrid((value) => !value)}>Grid</button>
          <button type="button" className={`scene-chip ${showLabels ? 'selected' : ''}`} aria-pressed={showLabels} onClick={() => setShowLabels((value) => !value)}>Labels</button>
        </div>
      </div>

      <div className="spatial-body">
        <div className={`scene-stage ${view} ${showGrid ? 'grid-on' : ''}`}>
          <div className="scene-horizon" />
          <div className="scene-plane">
            <div className="scene-road"><span className="road-lane lane-one" /><span className="road-lane lane-two" /><span className="road-edge edge-one" /><span className="road-edge edge-two" /></div>
            {hasAnalysis && points.map((point, index) => (
              <div className={`scene-entity ${point.critical ? 'critical' : ''}`} key={point.id} style={{ left: `${point.x}%`, top: `${point.y}%` }} title={`${point.label} · ${point.confidence}%`} aria-label={`${point.label}, ${point.confidence}% confidence`}>
                <span className="entity-pulse" />
                {showLabels && index < 10 && <span className="entity-label">{point.label}<small>{point.confidence}%</small></span>}
              </div>
            ))}
          </div>
          <div className="scene-caption"><span>{hasAnalysis ? 'VIDEO FRAME PROJECTION' : 'AWAITING VIDEO ANALYSIS'}</span><span>{hasAnalysis ? `${detections.length} FRAME OBSERVATIONS` : 'NO SCENE DATA'}</span></div>
        </div>
        <aside className="scene-readout">
          <div className="readout-top"><span className="readout-mark">RS</span><span>{hasAnalysis ? 'ANALYSIS READY' : 'SYSTEM STANDBY'}</span></div>
          <div className="readout-value">{hasAnalysis ? points.length : '—'}<small>{hasAnalysis ? 'projected markers' : 'entities detected'}</small></div>
          <div className="readout-divider" />
          <p>{hasAnalysis ? `${analysis.fileName} · detection positions mapped from the analyzed frames.` : 'Upload a recording to map its detections into this interactive scene.'}</p>
          <div className="readout-legend"><span><i className="legend-safe" /> Road user</span><span><i className="legend-critical" /> Person / hazard</span></div>
        </aside>
      </div>
      <div className="scene-entity-summary" aria-live="polite">
        <div className="scene-summary-heading">
          <div><span className="scene-summary-kicker">FRAME NOTES</span><h3>Detected entity summary</h3></div>
          {hasAnalysis && <span className="scene-summary-total">{analysis.detectionsCount ?? entityCounts.reduce((total, [, count]) => total + Number(count), 0)} reported objects</span>}
        </div>
        {hasAnalysis ? <>
          <p className="scene-summary-copy">Video analysis reported {entitySummary || 'no classified objects'} in this recording. The projection shows sampled positions; detections can repeat across video frames.</p>
          {entityCounts.length > 0 && <div className="scene-count-list">{entityCounts.map(([name, count]) => <span className="scene-count-item" key={name}><strong>{count}</strong><span>{name.replace(/_/g, ' ')}</span></span>)}</div>}
        </> : <p className="scene-summary-copy">Entity counts and notes will appear here after a video is analyzed.</p>}
      </div>
    </section>
  );
}

export default SpatialScene;
