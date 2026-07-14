import { useState, useEffect } from 'react';
import Panel from './Panel';

const API_BASE_URL = import.meta.env.VITE_API_URL ?? `${window.location.protocol}//${window.location.hostname}:8000`;

export default function SystemStatus() {
  const [backendStatus, setBackendStatus] = useState('CHECKING...');
  const [llmStatus, setLlmStatus] = useState('CHECKING...');

  useEffect(() => {
    async function checkHealth() {
      try {
        const res = await fetch(`${API_BASE_URL}/health`);
        if (res.ok) {
          const data = await res.json();
          setBackendStatus('ONLINE');
          setLlmStatus(data.llm_configured ? 'ONLINE' : 'OFFLINE');
        } else {
          setBackendStatus('OFFLINE');
          setLlmStatus('OFFLINE');
        }
      } catch (err) {
        setBackendStatus('OFFLINE');
        setLlmStatus('OFFLINE');
      }
    }
    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Panel title="System Status & Services" className="status">
      <div className="status-grid">
        <div><i className="online"/> React Frontend<span>ONLINE</span></div>
        <div><i className="online"/> Routing Engine<span>ONLINE</span></div>
        <div><i className={backendStatus === 'ONLINE' ? 'online' : 'offline'}/> Python FastAPI Backend<span>{backendStatus}</span></div>
        <div><i className={llmStatus === 'ONLINE' ? 'online' : 'offline'}/> GPT-5.6 API<span>{llmStatus}</span></div>
      </div>
    </Panel>
  );
}
