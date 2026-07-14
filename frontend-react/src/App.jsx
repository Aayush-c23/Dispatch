import { Bell, LayoutPanelTop, Settings } from 'lucide-react';
import { useState } from 'react';
import MapView from './components/MapView';
import ObjectiveInput from './components/ObjectiveInput';
import MissionBriefing from './components/MissionBriefing';
import ReasoningLog from './components/ReasoningLog';
import SystemStatus from './components/SystemStatus';
import OperationsDashboard from './components/OperationsDashboard';
import { createPlan } from './services/api';

const fallbackBriefing = {
  crisis_assessment: 'Rising floodwater is constraining central access. Elm Street shelter has 340 occupants and requires evacuation before nightfall.',
  highest_risk_areas: [{ description: 'Elm Street shelter' }, { description: 'River crossing' }, { description: 'Sector 4 clinic' }],
  convoy_assignments: [{ convoy_id: 'Convoy 1', request_id: 'Elm Street evacuation' }, { convoy_id: 'Convoy 2', request_id: 'Sector 4 medical delivery' }],
  predicted_bottlenecks: [{ description: 'River crossing congestion and flooding on the central access corridor.' }],
  confidence_level: 'HIGH',
  backup_plan: 'If Elm Street access fails, Convoy 1 reroutes west via A420, adding an estimated 12 minutes.',
};

const fallbackRoutes = [
  { convoy_id: 'convoy-1', geometry: [{ lat: 51.516, lon: -0.149 }, { lat: 51.512, lon: -0.141 }, { lat: 51.511, lon: -0.129 }, { lat: 51.505, lon: -0.118 }, { lat: 51.501, lon: -0.112 }] },
  { convoy_id: 'convoy-2', geometry: [{ lat: 51.499, lon: -0.147 }, { lat: 51.502, lon: -0.137 }, { lat: 51.506, lon: -0.128 }, { lat: 51.510, lon: -0.120 }, { lat: 51.513, lon: -0.109 }] },
  { convoy_id: 'evacuation', geometry: [{ lat: 51.497, lon: -0.106 }, { lat: 51.502, lon: -0.114 }, { lat: 51.507, lon: -0.122 }, { lat: 51.514, lon: -0.128 }] },
];

const fallbackLog = [
  { message: 'GPT-5.6 — Crisis Response Agent', level: 'AGENT' },
  { message: '> Analyzing coordinator objective…' },
  { message: '✓ Sector 4 access route confirmed clear.' },
  { message: '! Elm Street shelter: 340 occupants, high priority.' },
];

export default function App() {
  const [briefing, setBriefing] = useState(fallbackBriefing);
  const [routes, setRoutes] = useState(fallbackRoutes);
  const [reasoningLog, setReasoningLog] = useState(fallbackLog);
  const [isPlanning, setIsPlanning] = useState(false);
  const [planningError, setPlanningError] = useState('');

  async function handleGeneratePlan(objective) {
    setIsPlanning(true);
    setPlanningError('');
    try {
      const plan = await createPlan(objective);
      setBriefing(plan.briefing);
      setRoutes(plan.routes);
      setReasoningLog((previous) => [...previous, ...plan.reasoning_log]);
    } catch (error) {
      setPlanningError('Backend unavailable. Showing the operational fallback plan.');
      setReasoningLog((previous) => [...previous, { message: `! ${error.message}`, level: 'WARN' }]);
    } finally {
      setIsPlanning(false);
    }
  }

  return <main className="shell"><header className="app-header"><div className="brand"><span className="brand-mark">RG</span><div><h1>RELIEFGRID <em>AI</em></h1><p>HUMANITARIAN OPERATIONS PLATFORM</p></div></div><div className="header-actions"><button aria-label="Settings"><Settings size={17}/></button><button aria-label="Layout"><LayoutPanelTop size={17}/></button><button aria-label="Notifications"><Bell size={17}/><i/></button></div></header><div className="body"><section className="map-panel"><MapView routes={routes}/></section><aside className="control"><div className="section-label">Operations Control <span>● LIVE</span></div><ObjectiveInput onGenerate={handleGeneratePlan} isPlanning={isPlanning} error={planningError}/><MissionBriefing briefing={briefing}/><ReasoningLog entries={reasoningLog}/><SystemStatus/></aside></div><OperationsDashboard/></main>;
}
