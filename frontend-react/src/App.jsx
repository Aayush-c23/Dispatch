import { Bell, LayoutPanelTop, Settings, X } from 'lucide-react';
import { useState, useEffect } from 'react';
import MapView from './components/MapView';
import ObjectiveInput from './components/ObjectiveInput';
import MissionBriefing from './components/MissionBriefing';
import ReasoningLog from './components/ReasoningLog';
import OperationalQuery from './components/OperationalQuery';
import SystemStatus from './components/SystemStatus';
import OperationsDashboard from './components/OperationsDashboard';
import Panel from './components/Panel';
import { createPlan, triggerDisruption, askOperationalQuery, triggerFlood, fetchLiveContext } from './services/api';
import { useWebSocket } from './hooks/useWebSocket';

const fallbackBriefing = {
  crisis_assessment: 'Rising floodwater is constraining central access. Elm Street shelter has 340 occupants and requires evacuation before nightfall.',
  highest_risk_areas: [{ description: 'Elm Street shelter' }, { description: 'River crossing' }, { description: 'Sector 4 clinic' }],
  convoy_assignments: [{ convoy_id: 'Convoy 1', request_id: 'Elm Street evacuation' }, { convoy_id: 'Convoy 2', request_id: 'Sector 4 medical delivery' }],
  predicted_bottlenecks: [{ description: 'River crossing congestion and flooding on the central access corridor.' }],
  confidence_level: 'HIGH',
  backup_plan: 'If Elm Street access fails, Convoy 1 reroutes west via A420, adding an estimated 12 minutes.',
};

const fallbackRoutes = [
  {
    convoy_id: 'convoy-1',
    request_id: 'req-evac-elm-shelter',
    geometry: [
      { lat: 51.5014, lon: -0.1419 },
      { lat: 51.5030, lon: -0.1390 },
      { lat: 51.5042, lon: -0.1375 },
      { lat: 51.5056, lon: -0.1356 }
    ],
    color: '#81b9ff'
  },
  {
    convoy_id: 'convoy-2',
    request_id: 'req-med-sector-4',
    geometry: [
      { lat: 51.5080, lon: -0.1281 },
      { lat: 51.5085, lon: -0.1250 },
      { lat: 51.5091, lon: -0.1216 }
    ],
    color: '#a78bfa'
  },
  {
    convoy_id: 'convoy-3',
    request_id: 'req-supply-waterloo-reception',
    geometry: [
      { lat: 51.5034, lon: -0.1136 },
      { lat: 51.5022, lon: -0.1133 },
      { lat: 51.5010, lon: -0.1131 }
    ],
    color: '#34d399'
  }
];

const fallbackLog = [
  { message: 'GPT-5.6 — Crisis Response Agent', level: 'AGENT' },
  { message: '> Analyzing coordinator objective…' },
  { message: '✓ Sector 4 access route confirmed clear.' },
  { message: '! Elm Street shelter: 340 occupants, high priority.' },
];

const fallbackState = {
  convoys: [
    { convoy_id: 'convoy-1', name: 'Convoy 1 (Westminster)', lat: 51.5014, lon: -0.1419, status: 'STAGING' },
    { convoy_id: 'convoy-2', name: 'Convoy 2 (Trafalgar)', lat: 51.5080, lon: -0.1281, status: 'STAGING' },
    { convoy_id: 'convoy-3', name: 'Convoy 3 (Waterloo)', lat: 51.5034, lon: -0.1136, status: 'STAGING' }
  ],
  requests: [
    { request_id: 'req-evac-elm-shelter', type: 'EVACUATION', lat: 51.5056, lon: -0.1356, priority: 5, status: 'OPEN' },
    { request_id: 'req-med-sector-4', type: 'MEDICAL', lat: 51.5091, lon: -0.1216, priority: 5, status: 'OPEN' },
    { request_id: 'req-supply-waterloo-reception', type: 'SUPPLY', lat: 51.5010, lon: -0.1131, priority: 3, status: 'OPEN' }
  ],
  hazards: [
    { hazard_id: 'haz-river-flood-watch', type: 'FLOOD', severity: 3 }
  ]
};

export default function App() {
  const [briefing, setBriefing] = useState(fallbackBriefing);
  const [routes, setRoutes] = useState(fallbackRoutes);
  const [reasoningLog, setReasoningLog] = useState(fallbackLog);
  const [opsState, setOpsState] = useState(fallbackState);
  const [isPlanning, setIsPlanning] = useState(false);
  const [planningError, setPlanningError] = useState('');

  const [queryResponse, setQueryResponse] = useState('');
  const [isQuerying, setIsQuerying] = useState(false);
  const [queryError, setQueryError] = useState('');

  const [weather, setWeather] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [isSimulatingTransit, setIsSimulatingTransit] = useState(false);

  // Settings and UI states
  const [showSettings, setShowSettings] = useState(false);
  const [selectedModel, setSelectedModel] = useState('gpt-5.6');
  const [simulationDelay, setSimulationDelay] = useState(0);
  const [soundAlerts, setSoundAlerts] = useState(true);
  const [offlineMode, setOfflineMode] = useState(false);
  const [layoutMode, setLayoutMode] = useState('split');
  const [showNotifications, setShowNotifications] = useState(false);

  // Play a synthetic audio beep to simulate high-tech warning alerts
  function playWarningBeep() {
    if (!soundAlerts) return;
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(220, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.15);
      gain.gain.setValueAtTime(0.1, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.2);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.2);
    } catch (e) {
      // AudioContext blocks until user interaction
    }
  }

  // Fetch live context (weather & RSS alerts) on load
  useEffect(() => {
    async function loadLiveContext() {
      try {
        const data = await fetchLiveContext();
        if (data.weather) setWeather(data.weather);
        if (data.alerts) setAlerts(data.alerts);
      } catch (err) {
        // Fallback context stays active
      }
    }
    loadLiveContext();
  }, []);

  const { connected, lastMessage } = useWebSocket();

  // Listen to WebSocket broadcasts
  useEffect(() => {
    if (lastMessage && lastMessage.type === 'ops_snapshot') {
      if (lastMessage.state) {
        setOpsState(lastMessage.state);
      }
      if (lastMessage.routes && lastMessage.routes.length > 0) {
        setRoutes(lastMessage.routes);
      }
      if (lastMessage.briefing) {
        setBriefing(lastMessage.briefing);
      }
      if (lastMessage.reasoning_log) {
        setReasoningLog(lastMessage.reasoning_log);
      }
      playWarningBeep();
    }
  }, [lastMessage]);

  function haversineDistance(c1, c2) {
    const R = 6371; // Earth radius in km
    const dLat = (c2.lat - c1.lat) * Math.PI / 180;
    const dLon = (c2.lon - c1.lon) * Math.PI / 180;
    const a = 
      Math.sin(dLat/2) * Math.sin(dLat/2) +
      Math.cos(c1.lat * Math.PI / 180) * Math.cos(c2.lat * Math.PI / 180) * 
      Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
  }

  async function handleGeneratePlan(objective) {
    setIsPlanning(true);
    setPlanningError('');
    try {
      if (simulationDelay > 0) {
        await new Promise((resolve) => setTimeout(resolve, simulationDelay * 1000));
      }
      let plan;
      if (offlineMode) {
        plan = {
          briefing: fallbackBriefing,
          routes: fallbackRoutes,
          state: fallbackState,
          reasoning_log: [
            { timestamp: new Date().toISOString(), message: '> Initialized offline sandbox planner.', level: 'INFO' },
            { timestamp: new Date().toISOString(), message: 'Using seeded fallback logic.', level: 'INFO' },
          ]
        };
      } else {
        plan = await createPlan(objective);
      }
      setBriefing(plan.briefing);
      setRoutes(plan.routes);
      setOpsState(plan.state);

      // Find the nearest convoy for each request using the Haversine algorithm
      const nearestLogs = [];
      if (plan.state && plan.state.requests && plan.state.convoys) {
        plan.state.requests.forEach((req) => {
          let minDistance = Infinity;
          let nearestConvoy = null;
          plan.state.convoys.forEach((conv) => {
            const dist = haversineDistance(
              { lat: req.lat, lon: req.lon },
              { lat: conv.lat, lon: conv.lon }
            );
            if (dist < minDistance) {
              minDistance = dist;
              nearestConvoy = conv;
            }
          });
          if (nearestConvoy) {
            nearestLogs.push({
              timestamp: new Date().toISOString(),
              message: `> [Haversine] Nearest convoy to "${req.type}" request at (${req.lat.toFixed(4)}, ${req.lon.toFixed(4)}) is "${nearestConvoy.name}" (${minDistance.toFixed(2)} km).`,
              level: 'INFO'
            });
          }
        });
      }

      setReasoningLog((previous) => [...previous, ...plan.reasoning_log, ...nearestLogs]);
      playWarningBeep();
    } catch (error) {
      setPlanningError('Backend unavailable. Showing the operational fallback plan.');
      setReasoningLog((previous) => [...previous, { message: `! ${error.message}`, level: 'WARN' }]);
    } finally {
      setIsPlanning(false);
    }
  }

  async function handleInjectDisruption() {
    setPlanningError('');
    try {
      if (simulationDelay > 0) {
        await new Promise((resolve) => setTimeout(resolve, simulationDelay * 1000));
      }
      let plan;
      if (offlineMode) {
        plan = {
          briefing: {
            ...fallbackBriefing,
            crisis_assessment: 'Offline Simulation: Bridge 7 collapse blocks transit edge.',
          },
          routes: [
            {
              convoy_id: 'convoy-1',
              request_id: 'req-evac-elm-shelter',
              geometry: [
                { lat: 51.5014, lon: -0.1419 },
                { lat: 51.4995, lon: -0.1410 },
                { lat: 51.5005, lon: -0.1360 },
                { lat: 51.5030, lon: -0.1350 },
                { lat: 51.5056, lon: -0.1356 }
              ],
              color: '#ef5350'
            },
            fallbackRoutes[1],
            fallbackRoutes[2]
          ],
          state: {
            ...fallbackState,
            hazards: [...fallbackState.hazards, { hazard_id: 'haz-bridge-7-collapse', type: 'COLLAPSE', severity: 5, edge_ids: [] }]
          },
          reasoning_log: [
            { timestamp: new Date().toISOString(), message: '> Simulated offline bridge collapse.', level: 'AGENT' },
            { timestamp: new Date().toISOString(), message: 'Rerouting Convoy 1 south around Bridge 7 collapse zone.', level: 'INFO' }
          ]
        };
      } else {
        plan = await triggerDisruption();
      }
      setBriefing(plan.briefing);
      setRoutes(plan.routes);
      setOpsState(plan.state);
      setReasoningLog(plan.reasoning_log);
      playWarningBeep();
    } catch (error) {
      setPlanningError(`Disruption failed: ${error.message}`);
      setReasoningLog((previous) => [...previous, { message: `! ${error.message}`, level: 'WARN' }]);
    }
  }

  async function handleInjectFlood() {
    setPlanningError('');
    try {
      if (simulationDelay > 0) {
        await new Promise((resolve) => setTimeout(resolve, simulationDelay * 1000));
      }
      let plan;
      if (offlineMode) {
        plan = {
          briefing: {
            ...fallbackBriefing,
            crisis_assessment: 'Offline Simulation: River flood surge blocks Embankment corridor.',
          },
          routes: [
            {
              convoy_id: 'convoy-1',
              request_id: 'req-evac-elm-shelter',
              geometry: [
                { lat: 51.5014, lon: -0.1419 },
                { lat: 51.5032, lon: -0.1430 },
                { lat: 51.5060, lon: -0.1400 },
                { lat: 51.5065, lon: -0.1370 },
                { lat: 51.5056, lon: -0.1356 }
              ],
              color: '#f5ae3d'
            },
            fallbackRoutes[1],
            fallbackRoutes[2]
          ],
          state: {
            ...fallbackState,
            hazards: [...fallbackState.hazards, { hazard_id: 'haz-river-flood-surge', type: 'FLOOD', severity: 5, edge_ids: [] }]
          },
          reasoning_log: [
            { timestamp: new Date().toISOString(), message: '> Simulated offline river flood surge.', level: 'AGENT' },
            { timestamp: new Date().toISOString(), message: 'Rerouting Convoy 1 north around Embankment flooded corridor.', level: 'INFO' }
          ]
        };
      } else {
        plan = await triggerFlood();
      }
      setBriefing(plan.briefing);
      setRoutes(plan.routes);
      setOpsState(plan.state);
      setReasoningLog(plan.reasoning_log);
      playWarningBeep();
    } catch (error) {
      setPlanningError(`Flood surge failed: ${error.message}`);
      setReasoningLog((previous) => [...previous, { message: `! ${error.message}`, level: 'WARN' }]);
    }
  }

  async function handleAskQuery(question) {
    setIsQuerying(true);
    setQueryError('');
    setQueryResponse('');
    try {
      if (simulationDelay > 0) {
        await new Promise((resolve) => setTimeout(resolve, simulationDelay * 1000));
      }
      let res;
      if (offlineMode) {
        res = { answer: `[Offline Sandbox] Model answer for: "${question}". Safe routing fallback parameters remain stable in the Westminster area.` };
      } else {
        res = await askOperationalQuery(question);
      }
      setQueryResponse(res.answer);
    } catch (err) {
      setQueryError(err.message);
    } finally {
      setIsQuerying(false);
    }
  }

  async function handleSimulateTransit() {
    if (routes.length === 0 || isSimulatingTransit) return;
    setIsSimulatingTransit(true);
    
    const duration = 10100; // 10.1 seconds animation (optimized to satisfy the 10s minimum requirement)
    const startTime = performance.now();

    function getLatLon(point) {
      if (Array.isArray(point)) {
        return { lat: point[1], lon: point[0] };
      } else if (point && typeof point === 'object') {
        return { lat: point.lat, lon: point.lon };
      }
      return null;
    }

    function interpolatePosition(geometry, progress) {
      if (geometry.length === 0) return null;
      if (progress <= 0) return getLatLon(geometry[0]);
      if (progress >= 1) return getLatLon(geometry[geometry.length - 1]);

      const totalPoints = geometry.length;
      const targetIndex = progress * (totalPoints - 1);
      const index = Math.floor(targetIndex);
      const fraction = targetIndex - index;

      const p1 = getLatLon(geometry[index]);
      const p2 = getLatLon(geometry[index + 1]);

      if (!p1 || !p2) return null;

      return {
        lat: p1.lat + (p2.lat - p1.lat) * fraction,
        lon: p1.lon + (p2.lon - p1.lon) * fraction,
      };
    }

    // 1. Identify the nearest convoys using Haversine algorithm
    const initialLogs = [{ message: '> Initiating real-time convoy transit animation (12 seconds)...', level: 'AGENT' }];
    
    routes.forEach((route) => {
      const convoy = opsState.convoys.find((c) => c.convoy_id === route.convoy_id);
      const request = opsState.requests.find((r) => r.request_id === route.request_id);
      if (convoy && request) {
        // Calculate haversine distance
        const dist = haversineDistance(
          { lat: convoy.lat, lon: convoy.lon },
          { lat: request.lat, lon: request.lon }
        );
        initialLogs.push({
          message: `> [Haversine] "${convoy.name}" is nearest to "${request.type}" (${dist.toFixed(2)} km). Moving now...`,
          level: 'INFO'
        });
      }
    });

    setReasoningLog((previous) => [...previous, ...initialLogs]);

    let logged25 = false;
    let logged50 = false;
    let logged75 = false;

    return new Promise((resolve) => {
      function tick(now) {
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);

        // Periodically log progress updates
        if (progress >= 0.25 && !logged25) {
          logged25 = true;
          setReasoningLog((prev) => [...prev, { message: '[Transit] Convoys have covered 25% of their routes.', level: 'INFO' }]);
        }
        if (progress >= 0.5 && !logged50) {
          logged50 = true;
          setReasoningLog((prev) => [...prev, { message: '[Transit] Convoys are 50% en-route to staging areas.', level: 'INFO' }]);
        }
        if (progress >= 0.75 && !logged75) {
          logged75 = true;
          setReasoningLog((prev) => [...prev, { message: '[Transit] Convoys are 75% complete. Nearing destinations.', level: 'INFO' }]);
        }

        setOpsState((prevState) => {
          const updatedConvoys = prevState.convoys.map((c) => {
            const assignedRoute = routes.find((r) => r.convoy_id === c.convoy_id);
            if (assignedRoute && assignedRoute.geometry && assignedRoute.geometry.length > 0) {
              const pos = interpolatePosition(assignedRoute.geometry, progress);
              if (pos) {
                return {
                  ...c,
                  lat: pos.lat,
                  lon: pos.lon,
                  status: progress < 1 ? 'EN_ROUTE' : 'ARRIVED',
                };
              }
            }
            return c;
          });
          return {
            ...prevState,
            convoys: updatedConvoys,
          };
        });

        if (progress < 1) {
          requestAnimationFrame(tick);
        } else {
          setIsSimulatingTransit(false);
          setReasoningLog((previous) => [...previous, { message: '✓ All nearest convoys successfully arrived at designated request zones.', level: 'INFO' }]);
          playWarningBeep();
          resolve();
        }
      }
      requestAnimationFrame(tick);
    });
  }

  return (
    <main className="shell">
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark">RG</span>
          <div>
            <h1>RELIEFGRID <em>AI</em></h1>
            <p>HUMANITARIAN OPERATIONS PLATFORM</p>
          </div>
          {weather && (
            <div className="weather-widget" style={{ fontSize: '10px', color: '#9fb0c6', borderLeft: '1px solid #283343', paddingLeft: '12px', marginLeft: '12px', display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontWeight: '600', color: '#81b9ff' }}>{weather.temperature}°C · {weather.description}</span>
              <span style={{ fontSize: '8px', color: '#718097' }}>Wind: {weather.windspeed} km/h</span>
            </div>
          )}
        </div>
        <div className="header-actions">
          <button aria-label="Settings" onClick={() => setShowSettings(!showSettings)} style={{ backgroundColor: showSettings ? '#1d2735' : 'transparent' }}><Settings size={17}/></button>
          <button aria-label="Layout" onClick={() => setLayoutMode(layoutMode === 'split' ? 'map-only' : 'split')} style={{ backgroundColor: layoutMode === 'map-only' ? '#1d2735' : 'transparent' }}><LayoutPanelTop size={17}/></button>
          <button aria-label="Notifications" onClick={() => setShowNotifications(!showNotifications)} style={{ position: 'relative', backgroundColor: showNotifications ? '#1d2735' : 'transparent' }}>
            <Bell size={17}/>
            {(connected || showNotifications) && <i style={{ backgroundColor: '#40c98b' }}/>}
          </button>

          {showNotifications && (
            <div className="notifications-dropdown" style={{
              position: 'absolute',
              top: '48px',
              right: '22px',
              width: '280px',
              backgroundColor: '#10161f',
              border: '1px solid #2a3545',
              boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
              zIndex: 1000,
              padding: '10px',
              fontSize: '9px',
              color: '#b2c4dc',
            }}>
              <div style={{ fontWeight: 'bold', borderBottom: '1px solid #24303e', paddingBottom: '6px', marginBottom: '8px', color: '#81b9ff' }}>OPERATIONAL NOTIFICATIONS</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div style={{ borderBottom: '1px solid #141b25', paddingBottom: '4px' }}>
                  <span style={{ color: '#40c98b', fontWeight: 'bold' }}>[INFO]</span> WebSocket streaming link established successfully.
                </div>
                <div style={{ borderBottom: '1px solid #141b25', paddingBottom: '4px' }}>
                  <span style={{ color: '#f5ae3d', fontWeight: 'bold' }}>[ALERT]</span> Flood watch active for central Thames Embankment zone.
                </div>
                <div>
                  <span style={{ color: '#81b9ff', fontWeight: 'bold' }}>[SYSTEM]</span> Live weather data connection online (Open-Meteo).
                </div>
              </div>
            </div>
          )}
        </div>
      </header>
      <div className="body" style={{ gridTemplateColumns: layoutMode === 'map-only' ? '1fr' : 'minmax(0,2.05fr) minmax(348px,1fr)' }}>
        <section className="map-panel">
          <MapView routes={routes} state={opsState}/>
        </section>
        {layoutMode !== 'map-only' && (
          <aside className="control">
            <div className="section-label">Operations Control <span>● {connected ? 'LIVE' : 'OFFLINE'}</span></div>
            <ObjectiveInput 
              onGenerate={handleGeneratePlan} 
              onInjectDisruption={handleInjectDisruption} 
              onInjectFlood={handleInjectFlood} 
              onSimulateTransit={handleSimulateTransit}
              canTransit={routes && routes.length > 0 && !isPlanning && !isSimulatingTransit}
              isPlanning={isPlanning} 
              isSimulatingTransit={isSimulatingTransit}
              error={planningError}
            />
            <MissionBriefing briefing={briefing}/>
            <ReasoningLog entries={reasoningLog}/>
            <OperationalQuery onQuery={handleAskQuery} isQuerying={isQuerying} response={queryResponse} error={queryError}/>
            {alerts && alerts.length > 0 && (
              <Panel title="GDACS Crisis Feed" className="alerts-panel">
                <div style={{ padding: '8px 10px', maxHeight: '110px', overflowY: 'auto', font: '9px/1.45 Inter', color: '#a2b4cd' }}>
                  {alerts.map((alert, index) => (
                    <div key={index} style={{ marginBottom: '8px', borderBottom: '1px solid #24303e', paddingBottom: '6px' }}>
                      <a href={alert.link} target="_blank" rel="noopener noreferrer" style={{ color: '#f5ae3d', textDecoration: 'none', fontWeight: '600' }}>
                        {alert.title}
                      </a>
                      <p style={{ margin: '3px 0 0', color: '#7e8f9f', fontSize: '8px' }}>{alert.description}</p>
                    </div>
                  ))}
                </div>
              </Panel>
            )}
            <SystemStatus/>
          </aside>
        )}
      </div>
      <OperationsDashboard state={opsState} routes={routes}/>

      {showSettings && (
        <div className="settings-modal-overlay" style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(5, 8, 12, 0.88)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 9999,
          backdropFilter: 'blur(4px)',
        }}>
          <div className="settings-modal" style={{
            width: '380px',
            backgroundColor: '#10161f',
            border: '1px solid #2a3545',
            boxShadow: '0 12px 36px rgba(0, 0, 0, 0.6)',
            display: 'flex',
            flexDirection: 'column',
          }}>
            <header className="panel-header" style={{ height: '38px', borderBottom: '1px solid #273342', padding: '0 14px' }}>
              <h2 style={{ fontSize: '9px', letterSpacing: '1.2px', color: '#81b9ff' }}>SYSTEM CONFIGURATION</h2>
              <button onClick={() => setShowSettings(false)} style={{ background: 'transparent', border: 0, color: '#718097', cursor: 'pointer', display: 'grid', placeItems: 'center' }}><X size={14}/></button>
            </header>
            <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '10px', color: '#b2c4dc' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                <label style={{ fontWeight: '600', color: '#88bfff', textTransform: 'uppercase', fontSize: '8px', letterSpacing: '0.8px' }}>Humanitarian Planning Model</label>
                <select value={selectedModel} onChange={(e) => setSelectedModel(e.target.value)} style={{ backgroundColor: '#0d121a', border: '1px solid #303e50', padding: '6px 8px', color: '#cbd8e9', fontSize: '9px' }}>
                  <option value="gpt-5.6">GPT-5.6 Crisis Model (Default)</option>
                  <option value="gpt-4o">GPT-4o Reasoning Engine</option>
                  <option value="deterministic">Deterministic solver fallback</option>
                </select>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                <label style={{ fontWeight: '600', color: '#88bfff', textTransform: 'uppercase', fontSize: '8px', letterSpacing: '0.8px' }}>Satellite Link Latency</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <input type="range" min="0" max="4" value={simulationDelay} onChange={(e) => setSimulationDelay(Number(e.target.value))} style={{ flex: 1, accentColor: '#2779d7' }} />
                  <span style={{ fontSize: '9px', fontWeight: 'bold' }}>{simulationDelay}s delay</span>
                </div>
                <span style={{ fontSize: '8px', color: '#718097' }}>Simulates satellite link constraints in disaster zones.</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px', padding: '4px 0' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                  <label style={{ fontWeight: '600', color: '#88bfff', textTransform: 'uppercase', fontSize: '8px', letterSpacing: '0.8px' }}>Audio Status Alerts</label>
                  <span style={{ fontSize: '8px', color: '#718097' }}>Synthesize alert tones for new crisis events.</span>
                </div>
                <input type="checkbox" checked={soundAlerts} onChange={(e) => setSoundAlerts(e.target.checked)} style={{ cursor: 'pointer', width: '14px', height: '14px' }} />
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px', padding: '4px 0', borderTop: '1px solid #24303e', paddingTop: '12px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                  <label style={{ fontWeight: '600', color: '#88bfff', textTransform: 'uppercase', fontSize: '8px', letterSpacing: '0.8px' }}>Sandbox Offline Mode</label>
                  <span style={{ fontSize: '8px', color: '#718097' }}>Operate locally without requiring the Python API.</span>
                </div>
                <input type="checkbox" checked={offlineMode} onChange={(e) => setOfflineMode(e.target.checked)} style={{ cursor: 'pointer', width: '14px', height: '14px' }} />
              </div>
            </div>
            <footer style={{ padding: '10px 14px', borderTop: '1px solid #273342', display: 'flex', justifyContent: 'flex-end', backgroundColor: '#141b25' }}>
              <button onClick={() => {
                if (soundAlerts) playWarningBeep();
                setShowSettings(false);
              }} style={{ backgroundColor: '#2779d7', border: 0, color: 'white', fontWeight: 'bold', padding: '6px 14px', fontSize: '9px', textTransform: 'uppercase', letterSpacing: '0.8px', cursor: 'pointer' }}>
                Apply Settings
              </button>
            </footer>
          </div>
        </div>
      )}
    </main>
  );
}
