import { useState, useEffect } from 'react';
import { CloudRain, Wind, AlertTriangle, ShieldAlert } from 'lucide-react';
import Panel from './Panel';

const API_BASE_URL = import.meta.env.VITE_API_URL ?? `${window.location.protocol}//${window.location.hostname}:8000`;

export default function LiveContextPanel() {
  const [weather, setWeather] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchLiveData() {
      setLoading(true);
      try {
        // 1. Fetch real-time weather DIRECTLY from Open-Meteo public API (frontend API call)
        const weatherRes = await fetch('https://api.open-meteo.com/v1/forecast?latitude=51.5074&longitude=-0.1278&current_weather=true');
        let weatherData = null;
        if (weatherRes.ok) {
          const w = await weatherRes.json();
          weatherData = {
            temperature: w.current_weather.temperature,
            windspeed: w.current_weather.windspeed,
            weathercode: w.current_weather.weathercode,
          };
        }

        // 2. Fetch GDACS disaster alerts via Backend proxy (since GDACS RSS blocks browser CORS)
        const backendRes = await fetch(`${API_BASE_URL}/live-context`);
        let alertsData = [];
        if (backendRes.ok) {
          const b = await backendRes.json();
          alertsData = b.alerts || [];
          if (!weatherData && b.weather) {
            weatherData = b.weather; // Fallback to backend weather
          }
        }

        setWeather(weatherData);
        setAlerts(alertsData);
      } catch (err) {
        console.error('Failed to fetch live context:', err);
        setError('Failed to load live data feeds.');
      } finally {
        setLoading(false);
      }
    }

    fetchLiveData();
    const interval = setInterval(fetchLiveData, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, []);

  return (
    <Panel title="Live Operational Context" className="live-context">
      {loading && !weather && <div style={{ padding: '10px', color: '#94a3b8' }}>Loading external feeds...</div>}
      {error && !weather && <div style={{ padding: '10px', color: '#ef5350' }}>{error}</div>}
      
      {!loading && weather && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
          
          <div style={{ backgroundColor: 'rgba(255,255,255,0.05)', padding: '12px', borderRadius: '6px' }}>
            <h4 style={{ margin: '0 0 10px 0', fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase' }}>
              Real-time Weather (London)
            </h4>
            <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#e2e8f0', fontSize: '13px' }}>
                <CloudRain size={16} color="#3b82f6" />
                <span>{weather.temperature}°C</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#e2e8f0', fontSize: '13px' }}>
                <Wind size={16} color="#94a3b8" />
                <span>{weather.windspeed} km/h</span>
              </div>
              <div style={{ fontSize: '11px', color: '#64748b' }}>
                Source: Open-Meteo API
              </div>
            </div>
          </div>

          <div style={{ backgroundColor: 'rgba(255,255,255,0.05)', padding: '12px', borderRadius: '6px' }}>
            <h4 style={{ margin: '0 0 10px 0', fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase' }}>
              Global Disaster Alerts (GDACS)
            </h4>
            {alerts.length === 0 ? (
              <div style={{ fontSize: '12px', color: '#64748b' }}>No active alerts.</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {alerts.slice(0, 2).map((alert, idx) => (
                  <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                    <AlertTriangle size={14} color="#f5ae3d" style={{ marginTop: '2px', flexShrink: 0 }} />
                    <div style={{ fontSize: '12px', lineHeight: '1.4' }}>
                      <strong style={{ color: '#e2e8f0', display: 'block', marginBottom: '2px' }}>{alert.title}</strong>
                      <span style={{ color: '#94a3b8' }}>{alert.description.substring(0, 80)}...</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
          
        </div>
      )}
    </Panel>
  );
}
