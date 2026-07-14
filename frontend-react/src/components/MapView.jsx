import { useEffect, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import { createRoot } from 'react-dom/client';
import { AlertTriangle, Home, MapPin, XOctagon } from 'lucide-react';
import ConvoyMarker from './ConvoyMarker';

const center = [-0.1276, 51.5077];
const routeColors = ['#37a1ff', '#f5ae3d', '#40c98b', '#b77bff'];

function routeFeatureCollection(routes) {
  const convoyColors = {};
  let colorIndex = 0;
  routes.forEach(r => {
    if (!convoyColors[r.convoy_id]) {
       convoyColors[r.convoy_id] = routeColors[colorIndex % routeColors.length];
       colorIndex++;
    }
  });

  return {
    type: 'FeatureCollection',
    features: routes.filter((route) => route.geometry?.length > 1).map((route) => ({
      type: 'Feature',
      properties: { 
        color: convoyColors[route.convoy_id],
        is_primary: route.is_primary ?? true,
        convoy_id: route.convoy_id,
        label: route.label
      },
      geometry: { type: 'LineString', coordinates: route.geometry.map((point) => [point.lon, point.lat]) },
    })),
  };
}

// Generate circular polygon for hazards
function createCirclePolygon(lat, lon, radiusMeters, points = 32) {
  const coords = [];
  const earthRadius = 6371000;
  for (let i = 0; i <= points; i++) {
    const angle = (i * 360) / points;
    const bearing = angle * Math.PI / 180;
    
    const lat1 = lat * Math.PI / 180;
    const lon1 = lon * Math.PI / 180;
    const dByR = radiusMeters / earthRadius;

    const lat2 = Math.asin(Math.sin(lat1) * Math.cos(dByR) + 
                 Math.cos(lat1) * Math.sin(dByR) * Math.cos(bearing));
    const lon2 = lon1 + Math.atan2(Math.sin(bearing) * Math.sin(dByR) * Math.cos(lat1), 
                         Math.cos(dByR) - Math.sin(lat1) * Math.sin(lat2));

    coords.push([lon2 * 180 / Math.PI, lat2 * 180 / Math.PI]);
  }
  return [coords];
}


function addReactMarker(map, point, type, label) {
  const el = document.createElement('div'); const root = createRoot(el);
  const components = { 
    convoy: <ConvoyMarker/>, 
    shelter: <div className="map-marker shelter"><Home size={15}/></div>, 
    hazard: <div className="map-marker hazard"><AlertTriangle size={15}/></div>, 
    collapse: <div className="map-marker hazard" style={{backgroundColor: '#ef5350', borderColor: '#b71c1c'}}><XOctagon size={15} color="white"/></div>,
    request: <div className="map-marker request"><MapPin size={15}/></div>,
    route_start: <div style={{width:'12px',height:'12px',borderRadius:'50%',backgroundColor:'#4ade80',border:'2px solid white',boxShadow:'0 0 6px rgba(0,0,0,0.5)'}}/>,
    route_end: <div style={{width:'12px',height:'12px',borderRadius:'50%',backgroundColor:'#ef4444',border:'2px solid white',boxShadow:'0 0 6px rgba(0,0,0,0.5)'}}/>
  };
  root.render(<>{components[type]}<span className="marker-label">{label}</span></>);
  return new maplibregl.Marker({ element: el, anchor: 'bottom' }).setLngLat(point).addTo(map);
}

export default function MapView({ routes, state, onRouteSelect }) {
  const ref = useRef(null);
  const mapRef = useRef(null);
  const markersRef = useRef({});
  const stateRef = useRef(state);
  const routesRef = useRef(routes);

  useEffect(() => {
    stateRef.current = state;
    routesRef.current = routes;
  }, [state, routes]);

  // Render dynamic markers based on current state and routes
  function updateMarkers(map, currentState, currentRoutes) {
    if (!currentState) return;

    const seenIds = new Set();

    function upsertMarker(id, lngLat, type, label) {
      seenIds.add(id);
      if (markersRef.current[id]) {
        markersRef.current[id].setLngLat(lngLat);
        // Also update the label text if needed
        const labelEl = markersRef.current[id].getElement().querySelector('.marker-label');
        if (labelEl && labelEl.innerText !== label) {
           labelEl.innerText = label;
        }
      } else {
        markersRef.current[id] = addReactMarker(map, lngLat, type, label);
      }
    }

    // Add Route Start and End markers first so they are under convoys
    if (currentRoutes && currentRoutes.length > 0) {
      currentRoutes.forEach((route, i) => {
        if (route.geometry && route.geometry.length > 1) {
          const start = route.geometry[0];
          const end = route.geometry[route.geometry.length - 1];
          upsertMarker(`route_${route.convoy_id}_${i}_start`, [start.lon, start.lat], 'route_start', 'Origin');
          upsertMarker(`route_${route.convoy_id}_${i}_end`, [end.lon, end.lat], 'route_end', 'Destination');
        }
      });
    }

    // Add convoys
    if (currentState.convoys) {
      currentState.convoys.forEach((c) => {
        upsertMarker(`convoy_${c.convoy_id}`, [c.lon, c.lat], 'convoy', c.name);
      });
    }

    // Add requests
    if (currentState.requests) {
      currentState.requests.forEach((r) => {
        const label = `${r.type.charAt(0) + r.type.slice(1).toLowerCase()} (${r.status})`;
        upsertMarker(`request_${r.request_id}`, [r.lon, r.lat], 'request', label);
      });
    }

    // Add hazards and dynamic polygons
    const floodPolygons = [];
    if (currentState.hazards) {
      currentState.hazards.forEach((h) => {
        const parts = h.hazard_id.split('|');
        let coords = [-0.131, 51.507];
        let hazardRadius = 100;
        let isDynamic = false;

        if (parts.length === 4) {
          coords = [parseFloat(parts[2]), parseFloat(parts[1])]; // lon, lat
          hazardRadius = parseFloat(parts[3]);
          isDynamic = true;
        }

        const label = `${h.type.replace('_', ' ')}`;
        const markerType = h.type === 'collapse' ? 'collapse' : 'hazard';
        upsertMarker(`hazard_${parts[0]}`, coords, markerType, label);

        // Build dynamic polygon if it's a flood or collapse
        if (isDynamic) {
           floodPolygons.push({
             type: 'Feature',
             properties: {},
             geometry: {
               type: 'Polygon',
               coordinates: createCirclePolygon(coords[1], coords[0], hazardRadius)
             }
           });
        }
      });
    }
    
    // Remove stale markers
    Object.keys(markersRef.current).forEach(id => {
      if (!seenIds.has(id)) {
        markersRef.current[id].remove();
        delete markersRef.current[id];
      }
    });

    // Update flood zone polygons layer
    const floodSource = map.getSource('flood-zone');
    if (floodSource) {
      floodSource.setData({
        type: 'FeatureCollection',
        features: floodPolygons
      });
    }
  }

  useEffect(() => {
    const map = new maplibregl.Map({ container: ref.current, style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json', center, zoom: 13.1, pitch: 52, bearing: -18, antialias: true, attributionControl: false });
    mapRef.current = map;
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-left');
    map.on('load', () => {
      
      map.addSource('flood-zone', { type:'geojson', data:{type:'FeatureCollection', features:[]} });
      map.addLayer({id:'flood-zone',type:'fill',source:'flood-zone',paint:{'fill-color':'#ef5350','fill-opacity':0.18}});
      map.addLayer({id:'flood-outline',type:'line',source:'flood-zone',paint:{'line-color':'#ef5350','line-width':2,'line-dasharray':[2,2]}});
      
      map.addSource('plan-routes', { type: 'geojson', data: routeFeatureCollection(routesRef.current) });
      
      // Outline Layer (wider, for clicking)
      map.addLayer({ 
        id: 'plan-routes-outline', 
        type: 'line', 
        source: 'plan-routes', 
        layout: { 'line-join': 'round', 'line-cap': 'round' }, 
        paint: { 'line-color': '#05080c', 'line-width': ['case', ['boolean', ['get', 'is_primary'], false], 11, 7], 'line-opacity': 0.7 } 
      });
      
      // Main Line Layer
      map.addLayer({ 
        id: 'plan-routes', 
        type: 'line', 
        source: 'plan-routes', 
        layout: { 'line-join': 'round', 'line-cap': 'round' }, 
        paint: { 
          'line-color': ['get', 'color'], 
          'line-width': ['case', ['boolean', ['get', 'is_primary'], false], 5, 2], 
          'line-opacity': ['case', ['boolean', ['get', 'is_primary'], false], 0.9, 0.5],
          'line-dasharray': ['case', ['boolean', ['get', 'is_primary'], false], ['literal', [1]], ['literal', [2, 2]]]
        } 
      });
      
      // Arrows Layer
      map.addLayer({
        id: 'plan-routes-arrows',
        type: 'symbol',
        source: 'plan-routes',
        layout: {
          'symbol-placement': 'line',
          'symbol-spacing': 70,
          'text-field': '▶',
          'text-size': 12,
          'text-keep-upright': false
        },
        paint: {
          'text-color': '#ffffff',
          'text-opacity': 0.8
        }
      });
      
      // Load initial markers using refs
      updateMarkers(map, stateRef.current, routesRef.current);

      // Interactions
      map.on('click', 'plan-routes-outline', (e) => {
        if (!e.features || e.features.length === 0) return;
        const feature = e.features[0];
        if (feature.properties.convoy_id && feature.properties.label && onRouteSelect) {
           onRouteSelect(feature.properties.convoy_id, feature.properties.label);
        }
      });
      map.on('mouseenter', 'plan-routes-outline', () => map.getCanvas().style.cursor = 'pointer');
      map.on('mouseleave', 'plan-routes-outline', () => map.getCanvas().style.cursor = '');
    });
    return () => { mapRef.current = null; map.remove(); };
  }, []);

  useEffect(() => {
    const source = mapRef.current?.getSource('plan-routes');
    if (source) source.setData(routeFeatureCollection(routes));
    if (mapRef.current && mapRef.current.loaded()) {
      updateMarkers(mapRef.current, state, routes);
    }
  }, [routes, state]);

  return <div className="map-wrap"><div ref={ref} className="map"/><div className="map-overlay"><span className="live-dot"/> LIVE OPERATIONAL VIEW · LONDON CENTRAL</div><div className="map-key"><span><i className="blue"/>Active delivery</span><span><i className="amber"/>At risk</span><span><i className="red"/>Hazard zone</span></div></div>;
}
