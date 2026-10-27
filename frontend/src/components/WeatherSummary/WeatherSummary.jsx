import React, { useEffect, useState } from 'react';
import api from '../../services/api';


function weatherLabel(code) {
  if (code === 0) return 'Clear sky';
  if ([1, 2, 3].includes(code)) return 'Partly cloudy';
  if ([45, 48].includes(code)) return 'Foggy';
  if ([51, 53, 55, 56, 57].includes(code)) return 'Drizzle';
  if ([61, 63, 65, 80, 81, 82].includes(code)) return 'Rain';
  if ([95, 96, 99].includes(code)) return 'Thunderstorm';
  return 'Mixed conditions';
}

function WeatherSummary({ location }) {
  const [weather, setWeather] = useState({ status: 'loading' });

  useEffect(() => {
    const loadWeather = async (location) => {
      try {
        const { data } = await api.get('/api/weather/current', { params: { latitude: location.latitude, longitude: location.longitude } });
        setWeather({
          status: 'ready',
          label: location.label,
          temperature: Math.round(data.current.temperature_2m),
          feelsLike: Math.round(data.current.apparent_temperature),
          humidity: data.current.relative_humidity_2m,
          wind: Math.round(data.current.wind_speed_10m),
          rain: data.hourly?.precipitation_probability?.[0] ?? 0,
          condition: weatherLabel(data.current.weather_code),
        });
      } catch {
        setWeather({ status: 'error' });
      }
    };

    if (location?.latitude && location?.longitude) loadWeather(location);
    else setWeather({ status: 'waiting', label: location?.label || '—' });
  }, [location]);

  return (
    <section className="panel info-card weather-card">
      <div className="weather-title-row">
        <h2 className="card-title">Weather &amp; Location</h2>
        <span className="weather-location">{weather.label || 'Current conditions'}</span>
      </div>
      {weather.status === 'ready' ? (
        <>
          <div className="weather-main"><strong>{weather.temperature}°C</strong><span>{weather.condition}</span></div>
          <div className="weather-grid">
            <span>Humidity <b>{weather.humidity}%</b></span>
            <span>Wind <b>{weather.wind} km/h</b></span>
            <span>Rain chance <b>{weather.rain}%</b></span>
          </div>
        </>
      ) : <p className="empty-state">{weather.status === 'error' ? 'Local weather is unavailable' : location ? 'Set a location for this video to load its weather.' : 'Weather will appear after video analysis.'}</p>}
    </section>
  );
}

export default WeatherSummary;
