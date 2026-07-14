import { useState } from 'react';
import { Minus, Maximize2, X, Plus } from 'lucide-react';

export default function Panel({ title, children, className = '' }) {
  const [isMinimized, setIsMinimized] = useState(false);
  const [isMaximized, setIsMaximized] = useState(false);
  const [isClosed, setIsClosed] = useState(false);

  if (isClosed) return null;

  const maximizedStyle = {
    position: 'fixed',
    top: '10%',
    left: '10%',
    width: '80%',
    height: '80%',
    zIndex: 5000,
    boxShadow: '0 20px 50px rgba(0, 0, 0, 0.95)',
    backgroundColor: '#10161f',
  };

  const normalStyle = {
    display: 'flex',
    flexDirection: 'column',
  };

  return (
    <section 
      className={`panel ${className} ${isMaximized ? 'panel-maximized' : ''}`}
      style={isMaximized ? { ...normalStyle, ...maximizedStyle } : normalStyle}
    >
      <header className="panel-header" style={{ flexShrink: 0, width: '100%' }}>
        <h2>{title}</h2>
        <div className="panel-actions">
          <button 
            aria-label={isMinimized ? "Expand" : "Minimize"} 
            onClick={() => setIsMinimized(!isMinimized)}
          >
            {isMinimized ? <Plus size={11}/> : <Minus size={11}/>}
          </button>
          <button 
            aria-label="Maximize" 
            onClick={() => setIsMaximized(!isMaximized)}
            style={{ backgroundColor: isMaximized ? '#1d2735' : 'transparent' }}
          >
            <Maximize2 size={10}/>
          </button>
          <button 
            aria-label="Close" 
            onClick={() => setIsClosed(true)}
          >
            <X size={11}/>
          </button>
        </div>
      </header>
      {!isMinimized && (
        <div 
          className="panel-body" 
          style={{ 
            flex: 1, 
            minHeight: 0, 
            display: 'flex', 
            flexDirection: 'column',
            width: '100%',
            height: '100%'
          }}
        >
          {children}
        </div>
      )}
    </section>
  );
}
