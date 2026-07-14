import Panel from './Panel';

export default function ReasoningLog({ entries }) {
  return <Panel title="AI Reasoning Log" className="reasoning"><div className="log">{entries.map((entry, index) => <div className={entry.level === 'AGENT' ? 'agent' : ''} key={`${entry.timestamp ?? 'fallback'}-${index}`}>{entry.message}</div>)}<span className="cursor">▋</span></div></Panel>;
}
