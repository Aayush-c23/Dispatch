import { useEffect, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import { createRoot } from 'react-dom/client';
import { AlertTriangle, Home, MapPin } from 'lucide-react';
import ConvoyMarker from './ConvoyMarker';

const center = [-0.1276, 51.5077];
const routeColors = ['#37a1ff', '#f5ae3d', '#40c98b', '#b77bff'];

function routeFeatureCollection(routes) {
  return {
    type: 'FeatureCollection',
    features: routes.filter((route) => route.geometry?.length > 1).map((route, index) => ({
      type: 'Feature',
      properties: { color: routeColors[index % routeColors.length] },
      geometry: { type: 'LineString', coordinates: route.geometry.map((point) => [point.lon, point.lat]) },
    })),
  };
}

function addReactMarker(map, point, type, label) {
  const el = document.createElement('div'); const root = createRoot(el);
  const components = { convoy: <ConvoyMarker/>, shelter: <div className="map-marker shelter"><Home size={15}/></div>, hazard: <div className="map-marker hazard"><AlertTriangle size={15}/></div>, request: <div className="map-marker request"><MapPin size={15}/></div> };
  root.render(<>{components[type]}<span className="marker-label">{label}</span></>);
  return new maplibregl.Marker({ element: el, anchor: 'bottom' }).setLngLat(point).addTo(map);
}

export default function MapView({ routes, state }) {
  const ref = useRef(null);
  const mapRef = useRef(null);
  const markersRef = useRef([]);
  const routesRef = useRef(routes);
  routesRef.current = routes;

  // Render dynamic markers based on current state
  function updateMarkers(map, currentState) {
    // Clear old markers
    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current = [];

    if (!currentState) return;

    // Add convoys
    if (currentState.convoys) {
      currentState.convoys.forEach((c) => {
        const marker = addReactMarker(map, [c.lon, c.lat], 'convoy', c.name);
        markersRef.current.push(marker);
      });
    }

    // Add requests
    if (currentState.requests) {
      currentState.requests.forEach((r) => {
        const label = `${r.type.charAt(0) + r.type.slice(1).toLowerCase()} (${r.status})`;
        const marker = addReactMarker(map, [r.lon, r.lat], 'request', label);
        markersRef.current.push(marker);
      });
    }

    // Add hazards
    if (currentState.hazards) {
      const hazardCoords = {
        'haz-river-flood-watch': [-0.131, 51.507],
        'haz-bridge-7-collapse': [-0.138, 51.5029],
      };
      currentState.hazards.forEach((h) => {
        const coords = hazardCoords[h.hazard_id] || [-0.131, 51.507];
        const label = `${h.type.replace('_', ' ')} (${h.hazard_id})`;
        const marker = addReactMarker(map, coords, 'hazard', label);
        markersRef.current.push(marker);
      });
    }
  }

  useEffect(() => {
    const map = new maplibregl.Map({ container: ref.current, style: 'https://demotiles.maplibre.org/style.json', center, zoom: 13.1, pitch: 52, bearing: -18, antialias: true, attributionControl: false });
    mapRef.current = map;
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-left');
    map.on('load', () => {
      map.addSource('plan-routes', { type: 'geojson', data: routeFeatureCollection(routesRef.current) });
      map.addLayer({ id: 'plan-routes', type: 'line', source: 'plan-routes', layout: { 'line-join': 'round', 'line-cap': 'round' }, paint: { 'line-color': ['get', 'color'], 'line-width': 5, 'line-opacity': 0.9 } });
      map.addSource('flood-zone', { type:'geojson', data:{type:'Feature',properties:{},geometry:{type:'Polygon',coordinates:[[[-0.136,51.503],[-0.128,51.503],[-0.125,51.507],[-0.132,51.510],[-0.139,51.507],[-0.136,51.503]]]}} });
      map.addLayer({id:'flood-zone',type:'fill',source:'flood-zone',paint:{'fill-color':'#ef5350','fill-opacity':0.18}});
      map.addLayer({id:'flood-outline',type:'line',source:'flood-zone',paint:{'line-color':'#ef5350','line-width':2,'line-dasharray':[2,2]}});
      
      // Load initial markers
      updateMarkers(map, state);
    });
    return () => { mapRef.current = null; map.remove(); };
  }, []);

  useEffect(() => {
    const source = mapRef.current?.getSource('plan-routes');
    if (source) source.setData(routeFeatureCollection(routes));
  }, [routes]);

  useEffect(() => {
    const map = mapRef.current;
    if (map && map.loaded()) {
      updateMarkers(map, state);
    }
  }, [state]);

  return <div className="map-wrap"><div ref={ref} className="map"/><div className="map-overlay"><span className="live-dot"/> LIVE OPERATIONAL VIEW · LONDON CENTRAL</div><div className="map-key"><span><i className="blue"/>Active delivery</span><span><i className="amber"/>At risk</span><span><i className="red"/>Hazard zone</span></div></div>;
}
