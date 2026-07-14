import { useState } from 'react';
import Panel from './Panel';

export default function OperationalQuery({ onQuery, isQuerying, response, error }) {
  const [value, setValue] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (value.trim()) {
      onQuery(value.trim());
      setValue('');
    }
  };

  return (
    <Panel title="Operational Query (Ask AI)">
      <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '8px', margin: '9px' }}>
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Ask about live status, convoys, routes..."
          style={{
            flex: 1,
            backgroundColor: '#0d121a',
            border: '1px solid #303e50',
            color: '#cbd8e9',
            padding: '6px 8px',
            fontSize: '10px',
            fontFamily: 'Inter, sans-serif'
          }}
        />
        <button
          className="generate"
          type="submit"
          disabled={isQuerying || !value.trim()}
          style={{ margin: 0, width: '60px', height: '28px', padding: 0 }}
        >
          {isQuerying ? '...' : 'Ask'}
        </button>
      </form>
      {response && (
        <div style={{ margin: '0 9px 9px', padding: '8px', backgroundColor: '#141b25', border: '1px solid #273342', borderRadius: '2px', fontSize: '9px', lineHeight: '1.45', color: '#c5d0de' }}>
          <strong>Answer:</strong> {response}
        </div>
      )}
      {error && <p className="plan-error" style={{ margin: '0 9px 9px' }} role="alert">{error}</p>}
    </Panel>
  );
}
