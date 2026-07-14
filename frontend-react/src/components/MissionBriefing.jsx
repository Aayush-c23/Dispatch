import Panel from './Panel';

export default function MissionBriefing({ briefing }) {
  const rows = [
    ['Current assessment', briefing.crisis_assessment],
    ['Highest-risk areas', briefing.highest_risk_areas.map((area, index) => `${index + 1}. ${area.description}`).join(' · ')],
    ['Convoy assignments', briefing.convoy_assignments.map((assignment) => `${assignment.convoy_id} → ${assignment.request_id}`).join('; ')],
    ['Predicted bottlenecks', briefing.predicted_bottlenecks.map((bottleneck) => bottleneck.description).join(' · ')],
    ['Backup plan', briefing.backup_plan],
  ];
  return <Panel title="Mission Briefing" className="briefing">{rows.map(([label, text]) => <div className="brief-row" key={label}><h3>{label}</h3><p>{text || 'No current operational data.'}</p></div>)}<div className="confidence"><span>Plan confidence</span><strong>{briefing.confidence_level}</strong></div></Panel>;
}
