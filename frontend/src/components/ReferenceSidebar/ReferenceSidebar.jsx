import React from 'react';

const navItems = ['Dashboard', 'Recorded Video', 'Risk Prediction', 'Route Recommendation', 'Alerts', 'History Logs', 'Analytics', 'Map View', 'Settings', 'Users'];
const navIcons = ['⌂', '▣', '◈', '⌁', '♧', '◷', '▥', '⌖', '⚙', '♙'];

function ReferenceSidebar({ activeItem, onNavigate, online = false }) {
  return <aside className="sidebar">
    <div className="brand"><span className="brand-shield">⬡</span><div>RealityShield AI<small>Sense. Understand. Protect.</small></div></div>
    <nav className="nav-list" aria-label="Main navigation">
      {navItems.map((item, index) => <button type="button" key={item} className={`nav-item ${activeItem === item ? 'active' : ''}`} onClick={() => onNavigate(item)}><span className="nav-icon" aria-hidden="true">{navIcons[index]}</span>{item}</button>)}
    </nav>
    <div className="sidebar-status"><span className="status-dot" />{online ? 'Backend Connected' : 'Checking Backend'}</div>
    <div className="sidebar-version"><span className="brand-shield">⬡</span><span>RealityShield AI<small>Safer roads · smarter journeys</small></span></div>
  </aside>;
}

export default ReferenceSidebar;
