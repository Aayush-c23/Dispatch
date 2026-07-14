import { Truck } from 'lucide-react';

export default function ConvoyMarker({ status = 'on-time' }) { return <div className={`convoy-marker ${status}`}><Truck size={15}/></div>; }
