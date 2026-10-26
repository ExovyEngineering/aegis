import { useMemo } from 'react';
import { CircleMarker, MapContainer, Polyline, Popup, TileLayer } from 'react-leaflet';
import type { LabNode, LabRoute } from './RouteLab';
import MapViewport from './MapViewport';
import { routingSourceLabels } from './routingProvenance';

const colors = ['#1f6b51', '#b17d2c', '#5a78a1', '#a15a4c', '#81709a', '#4e8c89'];
const latlng = (c: number[]): [number, number] => [c[1], c[0]];
export default function RouteLabMap({ nodes, routes }: { nodes: LabNode[]; routes: LabRoute[] }) {
  const coordinates = useMemo(() => nodes.map(node => node.coordinates), [nodes]);
  return <div className="lab-map-wrap">
    <MapContainer center={[38.5, -92.6]} zoom={7} scrollWheelZoom={false} trackResize={false} zoomAnimation={false} fadeAnimation={false} markerZoomAnimation={false} className="lab-map" aria-label="Farm and fleet route test map">
      <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      <MapViewport coordinates={coordinates} />
      {routes.map((route, i) => route.geometry?.coordinates?.length ? <Polyline key={`${route.truck_id}-${i}`} positions={route.geometry.coordinates.map(latlng)} pathOptions={{ color: colors[i % colors.length], weight: 4, opacity: .8, dashArray: (route.geometry_fallback ?? route.fallback) ? '7,8' : undefined }}><Popup><strong>{route.truck_id}</strong><br />{(route.geometry_fallback ?? route.fallback) ? 'Estimated travel connection; not road geometry' : 'OSRM ordinary driving geometry'}<br />{(route.distance_m / 1000).toFixed(1)} km · {Math.round(route.duration_seconds / 60)} min<br />{routingSourceLabels(route).detail}<br />Truck restrictions and current closures are not incorporated.</Popup></Polyline> : null)}
      {nodes.map(node => <CircleMarker key={node.id} center={latlng(node.coordinates)} radius={node.kind === 'destination' || node.kind === 'stop' ? 6 : 10} pathOptions={{ color: '#fff', weight: 2, fillColor: node.kind === 'destination' || node.kind === 'stop' ? '#7b9b70' : '#173f36', fillOpacity: 1 }}><Popup><strong>{node.name}</strong><br />{node.id} · simulated {node.kind}<br />{node.demand_kg != null ? `${node.demand_kg} kg simulated demand` : 'Fictional dispatch origin'}</Popup></CircleMarker>)}
    </MapContainer>
    <div className="lab-map-caption"><span><i className="dot dc" /> Dispatch origin</span><span><i className="dot destination" /> Delivery stop</span><span>Dashed lines: estimated geometry. All logistics entities are simulated.</span></div>
  </div>;
}
