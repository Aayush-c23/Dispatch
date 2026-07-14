import { useState } from 'react';
import Panel from './Panel';

export default function ObjectiveInput() { const [value,setValue]=useState('Deliver medical supplies to Sector 4 and prioritize evacuating the shelter on Elm Street before nightfall.'); return <Panel title="Objective Input"><textarea value={value} onChange={e=>setValue(e.target.value)} aria-label="Operational objective"/><button className="generate" onClick={()=>console.log('Phase 0 visual scaffold: plan generation pending backend')}>Generate Plan</button></Panel>; }
