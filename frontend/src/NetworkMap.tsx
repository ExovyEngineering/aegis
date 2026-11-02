import { useMemo, useState } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, Polyline, GeoJSON } from 'react-leaflet';
import type { LatLngExpression } from 'leaflet';
import { circleMarker } from 'leaflet';
import { HelpCircle, Layers3 } from 'lucide-react';
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
const layerInfo = {
  logistics: { label: 'Simulated deliveries', purpose: 'See the sites and loads in the displayed plan.', use: 'Start here when checking which locations and candidate trips a response plan includes.', meaning: 'The dark sites are distribution centers, gold sites are suppliers and green sites are delivery destinations. These logistics sites and supply relationships are fictional.', limit: 'Dashed links join fixed origins and destinations. Truck markers are illustrative midpoints, not GPS positions or delivery progress.' },
  facilities: { label: 'FSIS facilities', purpose: 'Locate establishments from the inspection directory.', use: 'Use this for geographic context when inspecting official food-safety evidence.', meaning: 'Blue dots are supplied FSIS establishment-directory coordinates, separate from the fictional network.', limit: 'A nearby establishment does not establish a supply contract, an affected lot or a recall match.' },
  alerts: { label: 'Weather warnings', purpose: 'Look for official warning areas around a journey.', use: 'Check this when deciding whether weather conditions need a closer human review.', meaning: 'Orange areas or points represent the available NWS alert geometry. Open a shape to read its warning text.', limit: 'These warnings are separate from cargo temperature. Turning them on does not add a delay, predict spoilage or reroute a truck.' },
  roads: { label: 'Road incidents', purpose: 'See reported disruption locations near a journey.', use: 'Check this before opening Road intelligence to compare routes with incident evidence.', meaning: 'Red lines or points show captured MoDOT road-event geometries. Open a shape for its recorded description.', limit: 'A nearby event can be on a parallel road or outside the trip time. OSRM does not automatically avoid these incidents, and truck restrictions remain unverified.' },
  routes: { label: 'Requested route', purpose: 'View the travel comparison requested for a trip.', use: 'Select a shipment, click Request road route in trip detail, then highlight an alternative in its result.', meaning: 'A strong route line is the selected road comparison. A dashed estimated fallback is a connection estimate, not a road path.', limit: 'This comparison does not change Command’s fixed planning duration, lot, driver assignment or stop order. Those decisions use their separate review workflow.' },
} as const;
type Layer = keyof typeof layerInfo;
type Layers = Record<Layer, boolean>;
const presets: { id: string; label: string; description: string; layers: Layers; help: Layer }[] = [
  { id: 'deliveries', label: 'Plan deliveries', description: 'Focus on the displayed logistics plan and any route you requested.', layers: { logistics: true, facilities: false, alerts: false, roads: false, routes: true }, help: 'logistics' },
  { id: 'weather', label: 'Check weather', description: 'Add official warning areas to the logistics and route comparison.', layers: { logistics: true, facilities: false, alerts: true, roads: false, routes: true }, help: 'alerts' },
  { id: 'roads', label: 'Review roads', description: 'Add captured road incidents beside the logistics and requested route.', layers: { logistics: true, facilities: false, alerts: false, roads: true, routes: true }, help: 'roads' },
  { id: 'facilities', label: 'View facilities', description: 'Compare official establishment locations with the fictional network.', layers: { logistics: true, facilities: true, alerts: false, roads: false, routes: false }, help: 'facilities' },
];
function evidenceTime(value?: Evidence) {
  if (!value?.payload && !value?.incident_layers?.length) return 'No source response is loaded.';
  const instant = value.retrieved_at;
  const valid = typeof instant === 'string' && /(?:Z|[+-]\d{2}:\d{2})$/.test(instant) && Number.isFinite(Date.parse(instant)) && Date.parse(instant) <= Date.now() + 60000;
  return `${value.fixture ? 'Dated fixture' : value.stale ? 'Stale saved response' : 'Saved response'}${value.stale ? ' · source age needs review' : ''}. ${valid ? `Retrieved ${new Date(instant).toLocaleString('en-US', { timeZone: 'America/Chicago' })} CT.` : 'Retrieval time is missing or unverified.'}`;
}
export default function NetworkMap({ network, facilities, weather, roads, route, selected, onSelect, selectedAlternative = 0, planOverlay }: Props) {
  const [layers, setLayers] = useState<Layers>(presets[0].layers);
  const [presetId, setPresetId] = useState('deliveries');
  const [explainedLayer, setExplainedLayer] = useState<Layer | null>(null);
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
  const weatherFeatures = Array.isArray(weather?.payload?.features) ? weather.payload.features : [];
  const alerts = weatherFeatures.filter((f: any) => f?.geometry);
  const roadLayers = Array.isArray(roads?.incident_layers) ? roads.incident_layers : [];
  const roadFeatures = roadLayers.length ? roadLayers.flatMap((layer: any) => Array.isArray(layer?.payload?.features) ? layer.payload.features : []) : Array.isArray(roads?.payload?.features) ? roads.payload.features : [];
  const drawableRoads = roadFeatures.filter((f: any) => f?.geometry);
  const drawableFacilities = facilities.filter(f => readCoordinate([f.longitude, f.latitude]));
  const counts: Record<Layer, string> = {
    logistics: `${overlay.connections.length} displayed trip connections · ${network.nodes.filter(n => readCoordinate(n.coordinates)).length} fictional sites`,
    facilities: drawableFacilities.length ? `${drawableFacilities.length} usable directory location${drawableFacilities.length === 1 ? '' : 's'}` : 'No usable directory locations loaded',
    alerts: !weather?.payload ? 'No weather response loaded' : alerts.length ? `${alerts.length} warning ${alerts.length === 1 ? 'geometry' : 'geometries'} available` : 'No drawable warning geometry in this response',
    roads: !roads?.payload && !roads?.incident_layers?.length ? 'No road response loaded' : drawableRoads.length ? `${drawableRoads.length} event ${drawableRoads.length === 1 ? 'geometry' : 'geometries'} available` : 'No drawable incident geometry in this response',
    routes: paths.length ? `${paths.length} ${route?.fallback ? 'estimated' : 'road'} alternative${paths.length === 1 ? '' : 's'} available` : 'No route result yet · request one in trip detail',
  };
  const activePreset = presets.find(preset => preset.id === presetId);
  function usePreset(id: string) {
    const preset = presets.find(item => item.id === id);
    if (!preset) return;
    setLayers({ ...preset.layers }); setPresetId(id); setExplainedLayer(preset.help);
  }
  function toggleLayer(key: Layer) { setLayers(previous => ({ ...previous, [key]: !previous[key] })); setPresetId('custom'); }
  return <><div className="map-purpose-bar"><div><strong>What do you want to check?</strong><span>Choose a view. These controls change the picture, not the delivery plan.</span></div><div className="map-presets" role="group" aria-label="Map views">{presets.map(preset => <button key={preset.id} className={presetId === preset.id ? 'small' : 'secondary small'} aria-pressed={presetId === preset.id} onClick={() => usePreset(preset.id)}>{preset.label}</button>)}</div><p role="status" className="map-view-status">{activePreset?.description ?? 'Custom view: use the layer switches below to choose what is visible.'}</p></div><div className="map-frame">
    <MapContainer center={[38.48, -92.52]} zoom={7} scrollWheelZoom={false} trackResize={false} zoomAnimation={false} fadeAnimation={false} markerZoomAnimation={false} className="network-map" aria-label="Missouri logistics map">
      <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      <MapViewport coordinates={focusCoordinates} />
      {layers.logistics && overlay.connections.map(({ shipment: s, coordinates }) => <Polyline key={s.id} positions={coordinates.map(latlng)} pathOptions={{ color: selected?.id === s.id ? '#d89427' : overlay.scope === 'scenario' ? '#99743a' : '#3b8175', opacity: selected?.id === s.id ? .95 : .3, weight: selected?.id === s.id ? 3 : 1.8, dashArray: '6,8' }} eventHandlers={{ click: () => onSelect(s.id) }}><Popup><strong>{s.id} · {scopeName.toLowerCase()} connection</strong><br />Lot {s.lot_id} · truck {s.truck_id} · {s.quantity_kg} kg<br />Simulated origin–destination link; not road geometry or a vehicle location.</Popup></Polyline>)}
      {layers.logistics && network.nodes.filter(n => readCoordinate(n.coordinates)).map(n => <CircleMarker key={n.id} center={latlng(n.coordinates)} radius={n.kind === 'dc' ? 10 : n.kind === 'supplier' ? 7 : 5} pathOptions={{ color: '#fff', weight: 2, fillColor: n.kind === 'dc' ? '#173f36' : n.kind === 'supplier' ? '#b28d4c' : '#57867b', fillOpacity: 1 }}><Popup><strong>{n.name}</strong><br />{n.id} · fictional logistics entity</Popup></CircleMarker>)}
      {layers.logistics && network.trucks.map(t => { const connection = overlay.connections.find(row => row.shipment.truck_id === t.id); if (!connection) return null; const [a, b] = connection.coordinates; const position: LatLngExpression = [(a[1] + b[1]) / 2, (a[0] + b[0]) / 2]; return <CircleMarker key={t.id} center={position} radius={5} pathOptions={{ color: '#fff', weight: 1.5, fillColor: '#ba8740', fillOpacity: 1 }} eventHandlers={{ click: () => onSelect(connection.shipment.id) }}><Popup><strong>{t.id} · illustrative truck marker</strong><br />Midpoint of a displayed simulated OD connection.<br />Not GPS or actual progress. {scopeName} {connection.shipment.id}.</Popup></CircleMarker>; })}
      {layers.facilities && drawableFacilities.map(f => <CircleMarker key={f.establishment_id} center={[f.latitude, f.longitude]} radius={4} pathOptions={{ color: '#496e9b', fillOpacity: .7, weight: 1 }}><Popup><strong>{f.establishment_name}</strong><br />FSIS ID {f.establishment_id}<br />Official supplied directory coordinates; no simulated supply contract implied.</Popup></CircleMarker>)}
      {layers.alerts && alerts.map((f: any, i: number) => <GeoJSON key={`alert-${i}-${weather?.retrieved_at}`} data={f} pointToLayer={(_feature, location) => circleMarker(location, { radius: 5, color: '#c67a36', fillOpacity: .45, weight: 1.5 })} style={{ color: '#c67a36', weight: 2, fillOpacity: .08 }} onEachFeature={(feature, layer) => layer.bindPopup(sourcePopup(feature.properties?.headline ?? feature.properties?.event ?? 'NWS alert'))} />)}
      {layers.roads && drawableRoads.map((f: any, i: number) => <GeoJSON key={`road-${i}-${roads?.retrieved_at}`} data={f} pointToLayer={(_feature, location) => circleMarker(location, { radius: 4, color: '#bc5743', fillOpacity: .65, weight: 1 })} style={{ color: '#bc5743', weight: 3 }} onEachFeature={(feature, layer) => layer.bindPopup(sourcePopup(feature.properties?.Description ?? feature.properties?.description ?? 'MoDOT road event; review details'))} />)}
      {layers.routes && orderedPaths.map(path => { const active = path.index === activePath?.index; return <Polyline key={`route-${path.index}`} positions={path.coordinates.map(latlng)} pathOptions={{ color: route?.fallback ? '#b47a35' : active ? '#176953' : '#81a29a', weight: active ? 5 : 2.5, dashArray: route?.fallback ? '8,8' : undefined, opacity: active ? .95 : .4 }}><Popup><strong>Alternative {path.index + 1}{active ? ' · displayed comparison' : ''}</strong><br />{route?.fallback ? 'Estimated straight-line fallback' : 'OSRM driving geometry'} · {path.distanceM === null ? 'Distance unavailable' : `${Math.round(path.distanceM / 1000)} km`} · {path.durationSeconds === null ? 'Duration unavailable' : `${Math.round(path.durationSeconds / 60)} min`}<br />Separate route comparison; not applied to allocation or driver instructions.<br />Commercial truck restrictions and current closures not validated.</Popup></Polyline>; })}
    </MapContainer>
    {route?.displayLabel && <div className="map-route-label">{route.displayLabel}{route.shipmentId && route.shipmentId !== selected?.id ? ' · differs from current selection' : ''}</div>}
    <div className="map-tag"><span className="live-dot" /> MISSOURI <span>REGIONAL NETWORK</span></div>
    <div className="map-legend"><i className="dot dc" /> Distribution center <i className="dot supplier" /> Supplier <i className="dot destination" /> Destination <span>Dashed links: {scopeName.toLowerCase()} OD connections</span></div>
  </div><section className="map-layer-guide" aria-label="Map layer guide"><div className="map-layer-heading"><h3><Layers3 size={17} /> What is on this map?</h3><span>{activePreset?.label ?? 'Custom view'}</span></div><div className="map-layer-options">{(Object.keys(layerInfo) as Layer[]).map(key => <article className={layers[key] ? 'map-layer-option enabled' : 'map-layer-option'} key={key}><label><input type="checkbox" checked={layers[key]} aria-label={layerInfo[key].label} aria-describedby={`map-layer-purpose-${key}`} onChange={() => toggleLayer(key)} /><strong>{layerInfo[key].label}</strong></label><p id={`map-layer-purpose-${key}`}>{layerInfo[key].purpose}</p><small>{counts[key]}</small><button className="text-button map-layer-explain" aria-label={`Explain ${layerInfo[key].label.toLowerCase()}`} aria-expanded={explainedLayer === key} aria-controls="map-layer-explanation" onClick={() => setExplainedLayer(previous => previous === key ? null : key)}><HelpCircle size={13} /> What is this for?</button></article>)}</div>{explainedLayer && <div className="map-layer-explanation" id="map-layer-explanation" role="region" aria-label="Layer explanation"><div><strong>{layerInfo[explainedLayer].label}</strong><span className="pill">{explainedLayer === 'logistics' ? 'SIMULATED' : explainedLayer === 'routes' ? route?.fallback ? 'ESTIMATED COMPARISON' : 'TRAVEL COMPARISON' : 'PUBLIC EVIDENCE'}</span></div><p>{layerInfo[explainedLayer].use}</p><p>{layerInfo[explainedLayer].meaning}</p><p className="map-layer-limit">{layerInfo[explainedLayer].limit}</p>{explainedLayer === 'alerts' && <small>{evidenceTime(weather)}</small>}{explainedLayer === 'roads' && <small>{evidenceTime(roads)}</small>}{explainedLayer === 'facilities' && <small>Supplied establishment directory. Its retrieval time is not available in these map rows; inspect Sources &amp; evidence for provenance.</small>}{explainedLayer === 'routes' && !paths.length && <small>No route result is loaded yet. A switch cannot generate a route.</small>}</div>}</section><div className="command-map-caption" aria-label="What this map shows">
    <p><strong>{overlay.label}:</strong> {layers.logistics ? overlay.connections.length : 0} {scopeName.toLowerCase()} connections shown. {!layers.logistics ? `${overlay.connections.length} remain in the selected overlay; Simulated deliveries is hidden. ` : ''}{overlay.scope === 'candidate' ? 'Candidates are available trips, not approved deliveries.' : overlay.scope === 'scenario' ? 'This is a proposed allocation; it needs separate human approval.' : 'These are recorded simulated assignments, not moving vehicles or physical departures.'} Changing the overlay does not dispatch or edit a plan.</p>
    <details className="map-comparison-details"><summary>Read the map symbols and comparison limits</summary><p>Dark circles are fictional distribution centers: where loads leave the warehouse. Gold circles are fictional suppliers: where product would enter the simulated network. Green circles are fictional destinations: where a load would be delivered.</p><p>Dashed lines connect fixed origins and destinations. Changing a lot or hiding a candidate does not recalculate roads. Truck markers are illustrative midpoints. Evidence-layer checkboxes change visibility only.</p>
    {activePath ? <p><strong>{route?.shipmentId ? `Road comparison for ${route.shipmentId}` : 'Independent cached reference route'} · alternative {activePath.index + 1}:</strong> {route?.fallback ? 'Estimated straight-line geometry.' : 'Driving geometry returned by OSRM.'} The highlighted comparison does not change shipment ETAs, the chosen lot, approved assignments or driver instructions. {route?.shipmentId && route.shipmentId !== selected?.id ? 'It belongs to a different shipment from the current selection.' : ''}</p> : <p>No usable road geometry is displayed. The map focuses on the selected candidate’s origin and destination when available.</p>}
    </details>{activePath && activePath.index !== selectedAlternative && <p className="map-geometry-warning">The requested alternative has no usable geometry. The map displays valid alternative {activePath.index + 1}; review the comparison before interpreting it.</p>}
    {rejectedGeometryCount > 0 && <p className="map-geometry-warning">{rejectedGeometryCount} route {rejectedGeometryCount === 1 ? 'geometry was' : 'geometries were'} not drawn because coordinates or LineString structure were unusable.</p>}
    {overlay.connections.length !== overlay.requestedCount && <p className="map-geometry-warning">{overlay.requestedCount - overlay.connections.length} overlay rows could not be drawn because a connection was duplicated or had no usable endpoints.</p>}
    {selected && !selectedInOverlay && <p>The selected candidate {selected.id} is outside this overlay; its dashed connection is hidden.</p>}
  </div></>;
}
