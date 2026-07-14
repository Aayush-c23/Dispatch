import Panel from './Panel';
export default function SystemStatus(){return <Panel title="System Status & Services" className="status"><div className="status-grid">{['React Frontend','Routing Engine','Python FastAPI Backend','GPT-5.6 API'].map(x=><div key={x}><i/> {x}<span>ONLINE</span></div>)}</div></Panel>}
