import { Bell, LayoutPanelTop, Settings, X } from 'lucide-react';
import { useState, useEffect, useRef } from 'react';
import MapView from './components/MapView';
import ObjectiveInput from './components/ObjectiveInput';
import MissionBriefing from './components/MissionBriefing';
import ReasoningLog from './components/ReasoningLog';
import OperationalQuery from './components/OperationalQuery';
import SystemStatus from './components/SystemStatus';
import OperationsDashboard from './components/OperationsDashboard';
import Panel from './components/Panel';
import LiveContextPanel from './components/LiveContextPanel';
import { createPlan, triggerDisruption, askOperationalQuery, triggerFlood, fetchLiveContext, startTransit, selectRoute } from './services/api';
import { useWebSocket } from './hooks/useWebSocket';



export default function App() {
  const [briefing, setBriefing] = useState(null);
  const [routes, setRoutes] = useState([]);
  const [reasoningLog, setReasoningLog] = useState([]);
  const [opsState, setOpsState] = useState(null);
  const [isPlanning, setIsPlanning] = useState(false);
  const [planningError, setPlanningError] = useState('');
  const hasBootstrapped = useRef(false);

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
        // Handle failure silently or set error state if needed
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

  useEffect(() => {
    if (!opsState && !isPlanning && routes.length === 0 && !hasBootstrapped.current) {
      hasBootstrapped.current = true;
      handleGeneratePlan("Deliver medical supplies to Sector 4 and prioritize evacuating the shelter on Elm Street before nightfall.");
    }
  }, [opsState, isPlanning, routes]);

  async function handleRouteSelect(convoyId, label) {
    try {
      await selectRoute(convoyId, label);
    } catch (err) {
      setReasoningLog((previous) => [...previous, { message: `! Route selection failed: ${err.message}`, level: 'WARN' }]);
    }
  }

  async function executePlanAction(apiCall, actionName, args = []) {
    setIsPlanning(true);
    setPlanningError('');
    try {
      if (simulationDelay > 0) {
        await new Promise((resolve) => setTimeout(resolve, simulationDelay * 1000));
      }
      const plan = await apiCall(...args);
      setBriefing(plan.briefing);
      setRoutes(plan.routes);
      setOpsState(plan.state);
      setReasoningLog((previous) => [...previous, ...(plan.reasoning_log || [])]);
      playWarningBeep();
    } catch (error) {
      setPlanningError(`${actionName} failed: ${error.message}`);
      setReasoningLog((previous) => [...previous, { message: `! ${error.message}`, level: 'WARN' }]);
    } finally {
      setIsPlanning(false);
    }
  }

  const handleGeneratePlan = (objective) => executePlanAction(createPlan, 'Planning request', [objective]);
  const handleInjectDisruption = () => executePlanAction(triggerDisruption, 'Disruption');
  const handleInjectFlood = () => executePlanAction(triggerFlood, 'Flood surge');

  async function handleAskQuery(question) {
    setIsQuerying(true);
    setQueryError('');
    setQueryResponse('');
    try {
      if (simulationDelay > 0) {
        await new Promise((resolve) => setTimeout(resolve, simulationDelay * 1000));
      }
      const res = await askOperationalQuery(question);
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
    try {
      await startTransit();
      setReasoningLog((previous) => [...previous, { message: '> Initiating real-time convoy transit...', level: 'AGENT' }]);
    } catch (err) {
      setReasoningLog((previous) => [...previous, { message: `! Transit start failed: ${err.message}`, level: 'WARN' }]);
    } finally {
      setIsSimulatingTransit(false);
    }
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
          <MapView routes={routes} state={opsState} onRouteSelect={handleRouteSelect} />
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
            <LiveContextPanel />
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
