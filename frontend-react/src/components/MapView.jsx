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
  new maplibregl.Marker({ element: el, anchor: 'bottom' }).setLngLat(point).addTo(map);
}

export default function MapView({ routes }) {
  const ref = useRef(null);
  const mapRef = useRef(null);
  const routesRef = useRef(routes);
  routesRef.current = routes;

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
      addReactMarker(map, [-0.141,51.512], 'convoy', 'Convoy 1'); addReactMarker(map, [-0.121,51.510], 'convoy', 'Convoy 2');
      addReactMarker(map, [-0.108,51.514], 'shelter', 'Elm Street Shelter'); addReactMarker(map, [-0.131,51.507], 'hazard', 'Flooded access'); addReactMarker(map, [-0.112,51.501], 'request', 'Sector 4 medical');
    });
    return () => { mapRef.current = null; map.remove(); };
  }, []);

  useEffect(() => {
    const source = mapRef.current?.getSource('plan-routes');
    if (source) source.setData(routeFeatureCollection(routes));
  }, [routes]);

  return <div className="map-wrap"><div ref={ref} className="map"/><div className="map-overlay"><span className="live-dot"/> LIVE OPERATIONAL VIEW · LONDON CENTRAL</div><div className="map-key"><span><i className="blue"/>Active delivery</span><span><i className="amber"/>At risk</span><span><i className="red"/>Hazard zone</span></div></div>;
}
