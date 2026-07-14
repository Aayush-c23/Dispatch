import { useState } from 'react';
import Panel from './Panel';

export default function ObjectiveInput({ onGenerate, isPlanning, error }) {
  const [value, setValue] = useState('Deliver medical supplies to Sector 4 and prioritize evacuating the shelter on Elm Street before nightfall.');
  const canGenerate = value.trim().length > 0 && !isPlanning;

  return <Panel title="Objective Input"><textarea value={value} onChange={(event) => setValue(event.target.value)} aria-label="Operational objective"/><button className="generate" onClick={() => onGenerate(value.trim())} disabled={!canGenerate}>{isPlanning ? 'Generating plan…' : 'Generate Plan'}</button>{error && <p className="plan-error" role="alert">{error}</p>}</Panel>;
}
