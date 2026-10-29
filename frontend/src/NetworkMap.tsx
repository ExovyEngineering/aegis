import { useMemo, useState } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, Polyline, GeoJSON } from 'react-leaflet';
import type { LatLngExpression } from 'leaflet';
import { circleMarker } from 'leaflet';
import { Layers3 } from 'lucide-react';
import type { Evidence, Facility, Network, Shipment } from './types';
import MapViewport from './MapViewport';
import { connectionOverlay, readCoordinate, routePaths, selectedRoutePath, shipmentCoordinates } from './networkMapModel';
import type { PlanOverlay } from './networkMapModel';
import './NetworkMap.css';

interface Props {
  network: Network; facilities: Facility[]; weather?: Evidence; roads?: Evidence; route?: any;
  selected?: Shipment; onSelect: (id: string) => void;
  selectedAlternative?: number; planOverlay?: PlanOverlay;
}
const latlng = (coordinate: number[]): LatLngExpression => [coordinate[1], coordinate[0]];
const sourcePopup = (value: unknown) => { const element = document.createElement('div'); element.textContent = String(value); return element; };
export default function NetworkMap({ network, facilities, weather, roads, route, selected, onSelect, selectedAlternative = 0, planOverlay }: Props) {
  const [layers, setLayers] = useState({ logistics: true, facilities: false, alerts: true, roads: true, routes: true });
  const overlay = useMemo(() => connectionOverlay(network, planOverlay), [network.nodes, network.shipments, planOverlay?.scope, planOverlay?.label, planOverlay?.shipments]);
  const paths = useMemo(() => routePaths(route), [route]);
  const activePath = selectedRoutePath(paths, selectedAlternative);
  const candidateCoordinates = useMemo(() => shipmentCoordinates(network.nodes, selected), [network.nodes, selected?.origin, selected?.destination]);
  // Stable coordinates avoid recentering when layers or unrelated controls change.
  const focusCoordinates = activePath?.coordinates ?? candidateCoordinates;
  const orderedPaths = useMemo(() => [...paths.filter(path => path.index !== activePath?.index), ...(activePath ? [activePath] : [])], [paths, activePath]);
  const scopeName = overlay.scope === 'candidate' ? 'Candidate' : overlay.scope === 'scenario' ? 'Proposed scenario' : 'Approved assignment';
  const selectedInOverlay = overlay.connections.some(connection => connection.shipment.id === selected?.id);
  const rejectedGeometryCount = (Array.isArray(route?.payload?.routes) ? route.payload.routes.length : 0) - paths.length;
  const alerts = weather?.payload?.features?.filter((f: any) => f.geometry) ?? [];
  const roadFeatures = roads?.incident_layers?.flatMap((l: any) => l.payload?.features ?? []) ?? roads?.payload?.features ?? [];
  return <><div className="map-frame">
    <MapContainer center={[38.48, -92.52]} zoom={7} scrollWheelZoom={false} trackResize={false} zoomAnimation={false} fadeAnimation={false} markerZoomAnimation={false} className="network-map" aria-label="Missouri logistics map">
      <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      <MapViewport coordinates={focusCoordinates} />
      {layers.logistics && overlay.connections.map(({ shipment: s, coordinates }) => <Polyline key={s.id} positions={coordinates.map(latlng)} pathOptions={{ color: selected?.id === s.id ? '#d89427' : overlay.scope === 'scenario' ? '#99743a' : '#3b8175', opacity: selected?.id === s.id ? .95 : .3, weight: selected?.id === s.id ? 3 : 1.8, dashArray: '6,8' }} eventHandlers={{ click: () => onSelect(s.id) }}><Popup><strong>{s.id} · {scopeName.toLowerCase()} connection</strong><br />Lot {s.lot_id} · truck {s.truck_id} · {s.quantity_kg} kg<br />Simulated origin–destination link; not road geometry or a vehicle location.</Popup></Polyline>)}
      {layers.logistics && network.nodes.filter(n => readCoordinate(n.coordinates)).map(n => <CircleMarker key={n.id} center={latlng(n.coordinates)} radius={n.kind === 'dc' ? 10 : n.kind === 'supplier' ? 7 : 5} pathOptions={{ color: '#fff', weight: 2, fillColor: n.kind === 'dc' ? '#173f36' : n.kind === 'supplier' ? '#b28d4c' : '#57867b', fillOpacity: 1 }}><Popup><strong>{n.name}</strong><br />{n.id} · fictional logistics entity</Popup></CircleMarker>)}
      {layers.logistics && network.trucks.map(t => { const connection = overlay.connections.find(row => row.shipment.truck_id === t.id); if (!connection) return null; const [a, b] = connection.coordinates; const position: LatLngExpression = [(a[1] + b[1]) / 2, (a[0] + b[0]) / 2]; return <CircleMarker key={t.id} center={position} radius={5} pathOptions={{ color: '#fff', weight: 1.5, fillColor: '#ba8740', fillOpacity: 1 }} eventHandlers={{ click: () => onSelect(connection.shipment.id) }}><Popup><strong>{t.id} · illustrative truck marker</strong><br />Midpoint of a displayed simulated OD connection.<br />Not GPS or actual progress. {scopeName} {connection.shipment.id}.</Popup></CircleMarker>; })}
      {layers.facilities && facilities.filter(f => readCoordinate([f.longitude, f.latitude])).map(f => <CircleMarker key={f.establishment_id} center={[f.latitude, f.longitude]} radius={4} pathOptions={{ color: '#496e9b', fillOpacity: .7, weight: 1 }}><Popup><strong>{f.establishment_name}</strong><br />FSIS ID {f.establishment_id}<br />Official supplied directory coordinates; no simulated supply contract implied.</Popup></CircleMarker>)}
      {layers.alerts && alerts.map((f: any, i: number) => <GeoJSON key={`alert-${i}-${weather?.retrieved_at}`} data={f} pointToLayer={(_feature, location) => circleMarker(location, { radius: 5, color: '#c67a36', fillOpacity: .45, weight: 1.5 })} style={{ color: '#c67a36', weight: 2, fillOpacity: .08 }} onEachFeature={(feature, layer) => layer.bindPopup(sourcePopup(feature.properties?.headline ?? feature.properties?.event ?? 'NWS alert'))} />)}
      {layers.roads && roadFeatures.filter((f: any) => f.geometry).map((f: any, i: number) => <GeoJSON key={`road-${i}-${roads?.retrieved_at}`} data={f} pointToLayer={(_feature, location) => circleMarker(location, { radius: 4, color: '#bc5743', fillOpacity: .65, weight: 1 })} style={{ color: '#bc5743', weight: 3 }} onEachFeature={(feature, layer) => layer.bindPopup(sourcePopup(feature.properties?.Description ?? feature.properties?.description ?? 'MoDOT road event; review details'))} />)}
      {layers.routes && orderedPaths.map(path => { const active = path.index === activePath?.index; return <Polyline key={`route-${path.index}`} positions={path.coordinates.map(latlng)} pathOptions={{ color: route?.fallback ? '#b47a35' : active ? '#176953' : '#81a29a', weight: active ? 5 : 2.5, dashArray: route?.fallback ? '8,8' : undefined, opacity: active ? .95 : .4 }}><Popup><strong>Alternative {path.index + 1}{active ? ' · displayed comparison' : ''}</strong><br />{route?.fallback ? 'Estimated straight-line fallback' : 'OSRM driving geometry'} · {path.distanceM === null ? 'Distance unavailable' : `${Math.round(path.distanceM / 1000)} km`} · {path.durationSeconds === null ? 'Duration unavailable' : `${Math.round(path.durationSeconds / 60)} min`}<br />Separate route comparison; not applied to allocation or driver instructions.<br />Commercial truck restrictions and current closures not validated.</Popup></Polyline>; })}
    </MapContainer>
    {route?.displayLabel && <div className="map-route-label">{route.displayLabel}{route.shipmentId && route.shipmentId !== selected?.id ? ' · differs from current selection' : ''}</div>}
    <div className="map-tag"><span className="live-dot" /> MISSOURI <span>REGIONAL NETWORK</span></div>
    <div className="map-layers"><strong><Layers3 size={15} /> Evidence layers</strong>{Object.entries(layers).map(([key, value]) => <label key={key}><input type="checkbox" checked={value} onChange={() => setLayers({ ...layers, [key]: !value })} />{{ logistics: 'Simulated logistics', facilities: 'FSIS establishments', alerts: 'NWS alert geometry', roads: 'MoDOT incident geometry', routes: 'Route geometry' }[key]}</label>)}</div>
    <div className="map-legend"><i className="dot dc" /> Distribution center <i className="dot supplier" /> Supplier <i className="dot destination" /> Destination <span>Dashed links: {scopeName.toLowerCase()} OD connections</span></div>
  </div><div className="command-map-caption" aria-label="What this map shows">
    <p><strong>{overlay.label}:</strong> {overlay.connections.length} {scopeName.toLowerCase()} connections shown. {overlay.scope === 'candidate' ? 'Candidates are available trips, not approved deliveries.' : overlay.scope === 'scenario' ? 'This is a proposed allocation; it needs separate human approval.' : 'These are recorded simulated assignments, not moving vehicles or physical departures.'} Changing the overlay does not dispatch or edit a plan.</p>
    <p>Dashed lines connect fixed origins and destinations. Changing a lot or hiding a candidate does not recalculate roads. Truck markers are illustrative midpoints. Evidence-layer checkboxes change visibility only.</p>
    {activePath ? <p><strong>{route?.shipmentId ? `Road comparison for ${route.shipmentId}` : 'Independent cached reference route'} · alternative {activePath.index + 1}:</strong> {route?.fallback ? 'Estimated straight-line geometry.' : 'Driving geometry returned by OSRM.'} The highlighted comparison does not change shipment ETAs, the chosen lot, approved assignments or driver instructions. {route?.shipmentId && route.shipmentId !== selected?.id ? 'It belongs to a different shipment from the current selection.' : ''}</p> : <p>No usable road geometry is displayed. The map focuses on the selected candidate’s origin and destination when available.</p>}
    {activePath && activePath.index !== selectedAlternative && <p className="map-geometry-warning">The requested alternative has no usable geometry. The map displays valid alternative {activePath.index + 1}; review the comparison before interpreting it.</p>}
    {rejectedGeometryCount > 0 && <p className="map-geometry-warning">{rejectedGeometryCount} route {rejectedGeometryCount === 1 ? 'geometry was' : 'geometries were'} not drawn because coordinates or LineString structure were unusable.</p>}
    {overlay.connections.length !== overlay.requestedCount && <p className="map-geometry-warning">{overlay.requestedCount - overlay.connections.length} overlay rows could not be drawn because a connection was duplicated or had no usable endpoints.</p>}
    {selected && !selectedInOverlay && <p>The selected candidate {selected.id} is outside this overlay; its dashed connection is hidden.</p>}
  </div></>;
}
