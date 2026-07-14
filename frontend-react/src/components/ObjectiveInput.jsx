import { useState } from 'react';
import Panel from './Panel';

export default function ObjectiveInput({ onGenerate, onInjectDisruption, onInjectFlood, onSimulateTransit, canTransit, isPlanning, isSimulatingTransit, error }) {
  const [value, setValue] = useState('Deliver medical supplies to Sector 4 and prioritize evacuating the shelter on Elm Street before nightfall.');
  const canGenerate = value.trim().length > 0 && !isPlanning;

  return (
    <Panel title="Objective Input">
      <textarea value={value} onChange={(event) => setValue(event.target.value)} aria-label="Operational objective"/>
      <div style={{ display: 'flex', gap: '4px', margin: '0 9px 9px' }}>
        <button className="generate" onClick={() => onGenerate(value.trim())} disabled={!canGenerate} style={{ margin: 0, flex: 1.1, fontSize: '7.5px', padding: '0 2px' }}>
          {isPlanning ? 'Planning…' : 'Generate Plan'}
        </button>
        <button className="generate" onClick={onInjectDisruption} disabled={isPlanning || isSimulatingTransit} style={{ margin: 0, flex: 1, backgroundColor: '#ef5350', fontSize: '7.5px', padding: '0 2px' }}>
          Disruption
        </button>
        <button className="generate" onClick={onInjectFlood} disabled={isPlanning || isSimulatingTransit} style={{ margin: 0, flex: 1, backgroundColor: '#3b82f6', fontSize: '7.5px', padding: '0 2px' }}>
          Flood
        </button>
        <button className="generate" onClick={onSimulateTransit} disabled={!canTransit} style={{ margin: 0, flex: 1, backgroundColor: '#10b981', fontSize: '7.5px', padding: '0 2px' }}>
          {isSimulatingTransit ? 'Moving…' : 'Transit'}
        </button>
      </div>
      {error && <p className="plan-error" role="alert">{error}</p>}
    </Panel>
  );
}
