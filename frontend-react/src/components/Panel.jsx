import { Minus, Maximize2, X } from 'lucide-react';

export default function Panel({ title, children, className = '' }) {
  return <section className={`panel ${className}`}>
    <header className="panel-header"><h2>{title}</h2><div className="panel-actions"><button aria-label="Minimize"><Minus size={12}/></button><button aria-label="Expand"><Maximize2 size={11}/></button><button aria-label="Close"><X size={12}/></button></div></header>
    {children}
  </section>;
}
