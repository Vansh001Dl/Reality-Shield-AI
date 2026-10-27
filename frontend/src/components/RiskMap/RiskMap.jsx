import React, { useEffect, useState } from 'react';
import { MapContainer, Marker, Polyline, Popup, TileLayer } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

function RiskMap({ location }) {
  const indiaCenter = [22.5, 79];
  const videoPoint = [location.latitude, location.longitude];
  const [routes, setRoutes] = useState([]);
  const [routeStatus, setRouteStatus] = useState('loading');

  useEffect(() => {
    let active = true;
    const destinations = [
      { name: 'Route A', latitude: location.latitude + 0.04, longitude: location.longitude + 0.05, color: '#7ef0c4' },
      { name: 'Route B', latitude: location.latitude - 0.035, longitude: location.longitude + 0.06, color: '#ff6a6a' },
    ];

    const loadRoutes = async () => {
      try {
        const loadedRoutes = await Promise.all(destinations.map(async (destination) => {
          const coordinates = `${location.longitude},${location.latitude};${destination.longitude},${destination.latitude}`;
          const response = await fetch(`https://router.project-osrm.org/route/v1/driving/${coordinates}?overview=full&geometries=geojson&alternatives=false`);
          if (!response.ok) throw new Error('Routing service failed');
          const data = await response.json();
          const route = data.routes?.[0];
          if (!route) throw new Error('No route found');
          return {
            name: destination.name,
            color: destination.color,
            distance: `${(route.distance / 1000).toFixed(1)} km`,
            duration: `${Math.round(route.duration / 60)} min`,
            positions: route.geometry.coordinates.map(([longitude, latitude]) => [latitude, longitude]),
          };
        }));
        if (active) { setRoutes(loadedRoutes); setRouteStatus('ready'); }
      } catch {
        if (active) setRouteStatus('unavailable');
      }
    };
    loadRoutes();
    return () => { active = false; };
  }, [location.latitude, location.longitude]);

  return (
    <div className="risk-map">
      <MapContainer center={indiaCenter} zoom={5} minZoom={4} maxZoom={18} scrollWheelZoom className="leaflet-map">
        <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        {routes.map((route) => <Polyline key={route.name} positions={route.positions} pathOptions={{ color: route.color, weight: 5 }}><Popup>{route.name}: {route.distance}, {route.duration}</Popup></Polyline>)}
        <Marker position={videoPoint}><Popup>Recorded video location: {location.label}</Popup></Marker>
      </MapContainer>
      <div className="map-legend"><span className="safe-dot" /> Route A <span className="risk-dot" /> Route B {routeStatus === 'loading' && <span> · Loading road routes...</span>} {routeStatus === 'unavailable' && <span> · Routing unavailable</span>}</div>
    </div>
  );
}

export default RiskMap;