import { useState } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, Polyline, GeoJSON } from 'react-leaflet';
import type { LatLngExpression } from 'leaflet';
import { circleMarker } from 'leaflet';
import { Layers3 } from 'lucide-react';
import type { Evidence, Facility, Network, Shipment } from './types';
import MapViewport from './MapViewport';

interface Props { network: Network; facilities: Facility[]; weather?: Evidence; roads?: Evidence; route?: any; selected?: Shipment; onSelect: (id: string) => void }
const latlng = (coordinate: number[]): LatLngExpression => [coordinate[1], coordinate[0]];
export default function NetworkMap({ network, facilities, weather, roads, route, selected, onSelect }: Props) {
  const [layers, setLayers] = useState({ logistics: true, facilities: false, alerts: true, roads: true, routes: true });
  const nodes = Object.fromEntries(network.nodes.map(n => [n.id, n]));
  const alerts = weather?.payload?.features?.filter((f: any) => f.geometry) ?? [];
  const roadFeatures = roads?.incident_layers?.flatMap((l: any) => l.payload?.features ?? []) ?? roads?.payload?.features ?? [];
  const routeItems = route?.payload?.routes ?? [];
  return <div className="map-frame">
    <MapContainer center={[38.48, -92.52]} zoom={7} scrollWheelZoom={false} trackResize={false} zoomAnimation={false} fadeAnimation={false} markerZoomAnimation={false} className="network-map" aria-label="Missouri logistics map">
      <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      <MapViewport />
      {layers.logistics && network.shipments.map(s => { const a = nodes[s.origin], b = nodes[s.destination]; if (!a || !b) return null; return <Polyline key={s.id} positions={[latlng(a.coordinates), latlng(b.coordinates)]} pathOptions={{ color: selected?.id === s.id ? '#d89427' : '#3b8175', opacity: selected?.id === s.id ? .95 : .17, weight: selected?.id === s.id ? 3 : 1.5, dashArray: '6,8' }} eventHandlers={{ click: () => onSelect(s.id) }}><Popup>{s.id} · simulated connection<br />Estimated travel line; not road geometry.</Popup></Polyline>; })}
      {layers.logistics && network.nodes.map(n => <CircleMarker key={n.id} center={latlng(n.coordinates)} radius={n.kind === 'dc' ? 10 : n.kind === 'supplier' ? 7 : 5} pathOptions={{ color: '#fff', weight: 2, fillColor: n.kind === 'dc' ? '#173f36' : n.kind === 'supplier' ? '#b28d4c' : '#57867b', fillOpacity: 1 }}><Popup><strong>{n.name}</strong><br />{n.id} · fictional logistics entity</Popup></CircleMarker>)}
      {layers.logistics && network.trucks.map(t => { const trip = network.shipments.find(s => s.truck_id === t.id); if (!trip) return null; const a = nodes[trip.origin], b = nodes[trip.destination]; if (!a || !b) return null; const position: LatLngExpression = [(a.coordinates[1] + b.coordinates[1]) / 2, (a.coordinates[0] + b.coordinates[0]) / 2]; return <CircleMarker key={t.id} center={position} radius={5} pathOptions={{ color: '#fff', weight: 1.5, fillColor: '#ba8740', fillOpacity: 1 }} eventHandlers={{ click: () => onSelect(trip.id) }}><Popup><strong>{t.id} · simulated truck position</strong><br />Illustrative midpoint of estimated OD connection.<br />Not GPS telemetry. Shipment {trip.id}.</Popup></CircleMarker>; })}
      {layers.facilities && facilities.map(f => <CircleMarker key={f.establishment_id} center={[f.latitude, f.longitude]} radius={4} pathOptions={{ color: '#496e9b', fillOpacity: .7, weight: 1 }}><Popup><strong>{f.establishment_name}</strong><br />FSIS ID {f.establishment_id}<br />Official supplied directory coordinates; no simulated supply contract implied.</Popup></CircleMarker>)}
      {layers.alerts && alerts.map((f: any, i: number) => <GeoJSON key={`alert-${i}-${weather?.retrieved_at}`} data={f} pointToLayer={(_feature, location) => circleMarker(location, { radius: 5, color: '#c67a36', fillOpacity: .45, weight: 1.5 })} style={{ color: '#c67a36', weight: 2, fillOpacity: .08 }} onEachFeature={(feature, layer) => layer.bindPopup(String(feature.properties?.headline ?? feature.properties?.event ?? 'NWS alert'))} />)}
      {layers.roads && roadFeatures.filter((f: any) => f.geometry).map((f: any, i: number) => <GeoJSON key={`road-${i}-${roads?.retrieved_at}`} data={f} pointToLayer={(_feature, location) => circleMarker(location, { radius: 4, color: '#bc5743', fillOpacity: .65, weight: 1 })} style={{ color: '#bc5743', weight: 3 }} onEachFeature={(feature, layer) => layer.bindPopup(String(feature.properties?.Description ?? feature.properties?.description ?? 'MoDOT road event; review details'))} />)}
      {layers.routes && routeItems.slice(0, 3).map((r: any, i: number) => r.geometry?.coordinates ? <Polyline key={`route-${i}`} positions={r.geometry.coordinates.map(latlng)} pathOptions={{ color: route?.fallback ? '#b47a35' : i ? '#81a29a' : '#176953', weight: i ? 3 : 4, dashArray: route?.fallback ? '8,8' : undefined, opacity: .85 }}><Popup>{route?.fallback ? 'Estimated straight-line fallback' : 'OSRM driving route'} · {Math.round(r.distance / 1000)} km · {Math.round(r.duration / 60)} min<br />Commercial truck restrictions and current closures not validated.</Popup></Polyline> : null)}
    </MapContainer>
    {route?.displayLabel && <div className="map-route-label">{route.displayLabel}{route.shipmentId && route.shipmentId !== selected?.id ? ' · differs from current selection' : ''}</div>}
    <div className="map-tag"><span className="live-dot" /> MISSOURI <span>REGIONAL NETWORK</span></div>
    <div className="map-layers"><strong><Layers3 size={15} /> Evidence layers</strong>{Object.entries(layers).map(([key, value]) => <label key={key}><input type="checkbox" checked={value} onChange={() => setLayers({ ...layers, [key]: !value })} />{{ logistics: 'Simulated logistics', facilities: 'FSIS establishments', alerts: 'NWS alert geometry', roads: 'MoDOT incident geometry', routes: 'Route geometry' }[key]}</label>)}</div>
    <div className="map-legend"><i className="dot dc" /> Distribution center <i className="dot supplier" /> Supplier <i className="dot destination" /> Destination <span>Dashed links: simulated, estimated travel</span></div>
  </div>;
}
