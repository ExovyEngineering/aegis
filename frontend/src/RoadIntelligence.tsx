import { useEffect, useMemo, useRef, useState } from 'react';
import { ArrowDownToLine, MapPin, RefreshCw, Route, TriangleAlert } from 'lucide-react';
import { CircleMarker, MapContainer, Polyline, Popup, TileLayer } from 'react-leaflet';
import { api } from './api';
import MapViewport from './MapViewport';
import JourneySteps, { focusJourneyControl } from './JourneySteps';
import type { WorkspaceView } from './WorkspaceGuide';
import './RoadIntelligence.css';

type Coordinate = [number, number];
export interface RoadJourneyContext {
  shipmentId: string; networkRevision: number; origin: Coordinate; destination: Coordinate;
  originName: string; destinationName: string;
}
interface Geometry { type: 'Point' | 'MultiPoint' | 'LineString' | 'MultiLineString'; coordinates: any }
export interface RoadEvent {
  id: string; source_id: string; title: string; description: string; geometry: Geometry | null;
  route_name?: string | null; updated_at?: string | null; starts_at?: string | null; ends_at?: string | null;
  properties?: Record<string, unknown>; proximity_m?: number;
  provider_times?: Record<string, unknown>;
}
export interface RoadSource {
  id: string; name: string; state: string; provider: string; available: boolean; fixture: boolean;
  stale: boolean; retrieved_at: string | null; source_url: string; coverage_complete: boolean;
  event_count: number; unusable_geometry_count: number; returned_event_count?: number; events_truncated?: boolean;
  error?: string | null; warning: string; events: RoadEvent[];
  attribution?: string | null; license_url?: string | null; terms_url?: string | null;
  provider_latest_record_edit_at?: string | null; provider_time_warning?: string | null;
}
interface Example { id: string; name: string; origin: Coordinate; destination: Coordinate }
interface RoadSnapshot { generated_at: string; offline: boolean; sources: RoadSource[]; examples: Example[]; limitations: string[] }
interface CompareRequest { origin: Coordinate; destination: Coordinate; routing: 'estimated' | 'osrm'; buffer_m: number }
interface RoadReview {
  source_id: string; source_name: string; coverage_complete: boolean; stale: boolean;
  nearby_events: (RoadEvent & { proximity_m: number })[]; nearby_event_count?: number; hits_truncated?: boolean;
  unusable_geometry_count: number;
}
interface Alternative {
  index: number; distance_m: number; duration_seconds: number; geometry: Geometry; fallback: boolean;
  review_required: boolean; reviews: RoadReview[];
}
interface Comparison {
  compared_at: string; request: CompareRequest; sources: RoadSource[]; alternatives: Alternative[]; limitations: string[];
  routing_provenance?: string | null; routing_error?: string | null; routing_retrieved_at?: string | null;
  routing_stale?: boolean; routing_cache?: boolean; routing_refresh_error?: string | null;
}

const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value);
const coordinate = (value: any): value is Coordinate => Array.isArray(value) && value.length === 2 && finite(value[0]) && finite(value[1]) && Math.abs(value[0]) <= 180 && Math.abs(value[1]) <= 90;
const contextText = (value: unknown, limit: number): value is string => typeof value === 'string' && value.trim().length > 0 && value.length <= limit;
const journeyValid = (value: any): value is RoadJourneyContext => value && contextText(value.shipmentId, 100) && Number.isSafeInteger(value.networkRevision) && value.networkRevision >= 0 && contextText(value.originName, 200) && contextText(value.destinationName, 200) && coordinate(value.origin) && coordinate(value.destination) && (value.origin[0] !== value.destination[0] || value.origin[1] !== value.destination[1]);
const copyJourney = (value: RoadJourneyContext): RoadJourneyContext => ({ shipmentId: value.shipmentId, networkRevision: value.networkRevision, origin: [...value.origin], destination: [...value.destination], originName: value.originName, destinationName: value.destinationName });
const journeyLabel = (value: RoadJourneyContext) => `Selected candidate ${value.shipmentId}: ${value.originName} → ${value.destinationName}`;
const candidateChoice = '__selected_command_candidate__';
const line = (value: any) => Array.isArray(value) && value.length >= 2 && value.every(coordinate);
const geometry = (value: any): value is Geometry => value && typeof value === 'object' && (
  value.type === 'Point' ? coordinate(value.coordinates) :
  value.type === 'MultiPoint' ? Array.isArray(value.coordinates) && value.coordinates.length > 0 && value.coordinates.every(coordinate) :
  value.type === 'LineString' ? line(value.coordinates) :
  value.type === 'MultiLineString' && Array.isArray(value.coordinates) && value.coordinates.length > 0 && value.coordinates.every(line)
);
const nonnegative = (value: unknown) => finite(value) && value >= 0;
const strings = (value: any): value is string[] => Array.isArray(value) && value.every((item: unknown) => typeof item === 'string');
const eventValid = (value: any): value is RoadEvent => value && typeof value.id === 'string' && typeof value.source_id === 'string' && typeof value.title === 'string' && typeof value.description === 'string' && (value.geometry === null || geometry(value.geometry));
const sourceValid = (value: any): value is RoadSource => value && ['id', 'name', 'state', 'provider', 'source_url', 'warning'].every(key => typeof value[key] === 'string') && ['available', 'fixture', 'stale', 'coverage_complete'].every(key => typeof value[key] === 'boolean') && nonnegative(value.event_count) && nonnegative(value.unusable_geometry_count) && (value.retrieved_at === null || typeof value.retrieved_at === 'string') && Array.isArray(value.events) && value.events.length <= 200 && value.events.every(eventValid);
const snapshotValid = (value: any): value is RoadSnapshot => value && typeof value.generated_at === 'string' && typeof value.offline === 'boolean' && Array.isArray(value.sources) && value.sources.every(sourceValid) && Array.isArray(value.examples) && value.examples.every((example: any) => example && typeof example.id === 'string' && typeof example.name === 'string' && coordinate(example.origin) && coordinate(example.destination)) && strings(value.limitations);
const comparisonValid = (value: any, request: CompareRequest): value is Comparison => value && typeof value.compared_at === 'string' && value.request && coordinate(value.request.origin) && coordinate(value.request.destination) && JSON.stringify(value.request.origin) === JSON.stringify(request.origin) && JSON.stringify(value.request.destination) === JSON.stringify(request.destination) && value.request.routing === request.routing && value.request.buffer_m === request.buffer_m && Array.isArray(value.sources) && value.sources.every(sourceValid) && strings(value.limitations) && Array.isArray(value.alternatives) && value.alternatives.length > 0 && value.alternatives.length <= 10 && value.alternatives.every((alternative: any) => alternative && Number.isInteger(alternative.index) && nonnegative(alternative.distance_m) && nonnegative(alternative.duration_seconds) && alternative.geometry?.type === 'LineString' && geometry(alternative.geometry) && typeof alternative.fallback === 'boolean' && typeof alternative.review_required === 'boolean' && Array.isArray(alternative.reviews) && alternative.reviews.every((review: any) => review && typeof review.source_id === 'string' && typeof review.source_name === 'string' && typeof review.coverage_complete === 'boolean' && typeof review.stale === 'boolean' && nonnegative(review.unusable_geometry_count) && Array.isArray(review.nearby_events) && review.nearby_events.length <= 100 && review.nearby_events.every((event: any) => eventValid(event) && nonnegative(event.proximity_m))));
const timestamp = (value?: string | null) => value && Number.isFinite(Date.parse(value)) ? `${new Date(value).toLocaleString('en-US', { timeZone: 'America/Chicago' })} CT` : 'Not supplied';
const message = (error: unknown) => error instanceof Error ? error.message : String(error);
const latlng = (value: Coordinate): [number, number] => [value[1], value[0]];
const safeLink = (value: string) => /^https?:\/\//i.test(value) ? value : undefined;
const colors = ['#246b58', '#b67933', '#667ba3', '#906894'];

function SourceMetadata({ source }: { source: RoadSource }) {
  return <>{source.attribution && <p className="source-note">{source.attribution}{source.license_url && safeLink(source.license_url) && <> · <a href={source.license_url} target="_blank" rel="noreferrer">Data license</a></>}{source.terms_url && safeLink(source.terms_url) && <> · <a href={source.terms_url} target="_blank" rel="noreferrer">Provider terms</a></>}</p>}{source.provider_latest_record_edit_at && <p className="source-note">Latest provider record edit: {timestamp(source.provider_latest_record_edit_at)}. This metadata is separate from retrieval and individual event times.</p>}{source.provider_time_warning && <p className="source-note">{source.provider_time_warning}</p>}</>;
}

function EventGeometry({ event, selected }: { event: RoadEvent; selected: boolean }) {
  const value = event.geometry;
  if (!value) return null;
  const popup = <Popup><strong>{event.title}</strong><br />{event.description}<br />{event.route_name || 'Route not supplied'}<br />Official event geometry; proximity alone does not establish a blocked route.</Popup>;
  const style = { color: selected ? '#1d4339' : '#b76645', weight: selected ? 6 : 3, opacity: .8 };
  if (value.type === 'Point' || value.type === 'MultiPoint') {
    const points: Coordinate[] = value.type === 'Point' ? [value.coordinates] : value.coordinates;
    return <>{points.map((point, i) => <CircleMarker key={i} center={latlng(point)} radius={selected ? 9 : 5} pathOptions={{ color: '#fff', weight: 2, fillColor: style.color, fillOpacity: .9 }}>{popup}</CircleMarker>)}</>;
  }
  const lines: Coordinate[][] = value.type === 'LineString' ? [value.coordinates] : value.coordinates;
  return <>{lines.map((points, i) => <Polyline key={i} positions={points.map(latlng)} pathOptions={style}>{popup}</Polyline>)}</>;
}

function RoadMap({ events, selectedEvent, alternatives, selectedRoute, origin, destination }: { events: RoadEvent[]; selectedEvent?: RoadEvent; alternatives: Alternative[]; selectedRoute: number; origin: Coordinate; destination: Coordinate }) {
  const coordinates = useMemo(() => {
    const route = alternatives.find(item => item.index === selectedRoute);
    return route ? route.geometry.coordinates as Coordinate[] : [origin, destination];
  }, [alternatives, selectedRoute, origin[0], origin[1], destination[0], destination[1]]);
  // A comparison can contain a newer/older version of the same provider ID.
  // Always draw the selected record itself, rather than a different preview snapshot.
  const visibleEvents = selectedEvent ? [selectedEvent, ...events.filter(event => event.id !== selectedEvent.id || event.source_id !== selectedEvent.source_id).slice(0, 99)] : events.slice(0, 100);
  return <div className="road-map-wrap">
    <MapContainer center={[40, -93.5]} zoom={6} scrollWheelZoom={false} trackResize={false} zoomAnimation={false} fadeAnimation={false} markerZoomAnimation={false} className="road-map" aria-label="Official road events and planning routes map">
      <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      <MapViewport coordinates={coordinates} />
      {alternatives.map(alternative => <Polyline key={alternative.index} positions={alternative.geometry.coordinates.map(latlng)} pathOptions={{ color: colors[alternative.index % colors.length], weight: alternative.index === selectedRoute ? 6 : 3, opacity: alternative.index === selectedRoute ? .9 : .5, dashArray: alternative.fallback ? '8,8' : undefined }}><Popup><strong>Route {alternative.index + 1}</strong><br />{alternative.fallback ? 'Estimated connection; not road geometry' : 'OSRM ordinary driving geometry'}<br />{(alternative.distance_m / 1000).toFixed(1)} km · {Math.round(alternative.duration_seconds / 60)} min<br />No commercial-truck restrictions or closure avoidance are verified.</Popup></Polyline>)}
      {visibleEvents.map((event, i) => <EventGeometry key={`${event.source_id}-${event.id}-${i}`} event={event} selected={event.id === selectedEvent?.id && event.source_id === selectedEvent.source_id} />)}
      <CircleMarker center={latlng(origin)} radius={8} pathOptions={{ color: '#fff', fillColor: '#225a48', fillOpacity: 1, weight: 2 }}><Popup>Planning origin · no truck assignment</Popup></CircleMarker>
      <CircleMarker center={latlng(destination)} radius={8} pathOptions={{ color: '#fff', fillColor: '#577798', fillOpacity: 1, weight: 2 }}><Popup>Planning destination · no supply contract implied</Popup></CircleMarker>
    </MapContainer>
    <p className="road-map-caption">Orange: captured official event geometries. Dashed route: estimated connection. Map displays up to 100 filtered events; source tables and route review retain their stated limits.</p>
  </div>;
}

export default function RoadIntelligence({ onNavigate, initialJourney, currentNetworkRevision }: { onNavigate?: (view: WorkspaceView) => void; initialJourney?: RoadJourneyContext; currentNetworkRevision?: number } = {}) {
  const [data, setData] = useState<RoadSnapshot>();
  const [loadError, setLoadError] = useState('');
  const [compareError, setCompareError] = useState('');
  const [loading, setLoading] = useState(false);
  const [comparing, setComparing] = useState(false);
  const [sourceId, setSourceId] = useState('');
  const [filter, setFilter] = useState('');
  const [selectedEvent, setSelectedEvent] = useState<RoadEvent>();
  const [selectedRetrievedAt, setSelectedRetrievedAt] = useState<string | null>();
  const [selectedFromComparison, setSelectedFromComparison] = useState(false);
  const [originText, setOriginText] = useState(['-92.3341', '38.9517']);
  const [destinationText, setDestinationText] = useState(['-93.6250', '41.5868']);
  const [exampleId, setExampleId] = useState('');
  const [showCoordinates, setShowCoordinates] = useState(false);
  const [activeJourney, setActiveJourney] = useState<RoadJourneyContext>();
  const [journeyError, setJourneyError] = useState('');
  const receivedJourney = useRef(false);
  const initialChoice = useRef(false);
  const [routing, setRouting] = useState<'estimated' | 'osrm'>('estimated');
  const [buffer, setBuffer] = useState('250');
  const [result, setResult] = useState<Comparison>();
  const [resultJourney, setResultJourney] = useState<RoadJourneyContext>();
  const [resultJourneyLabel, setResultJourneyLabel] = useState('');
  const [selectedRoute, setSelectedRoute] = useState(0);
  const [changed, setChanged] = useState(false);
  const loadEpoch = useRef(0);
  const compareEpoch = useRef(0);
  const inputRevision = useRef(0);
  const sourceRevision = useRef(0);
  const requestBusy = useRef(false);

  async function load(refresh = false) {
    if (requestBusy.current) return;
    requestBusy.current = true;
    const epoch = ++loadEpoch.current;
    setLoading(true); setLoadError('');
    try {
      const response = await api<RoadSnapshot>(`/road-intelligence${refresh ? '/refresh' : ''}`, refresh ? {} : undefined);
      if (epoch !== loadEpoch.current) return;
      if (!snapshotValid(response)) throw new Error('The road-evidence response has an unsupported schema. No new coverage was inferred.');
      sourceRevision.current++; setData(response); setSelectedEvent(undefined); setChanged(!!result);
      setSourceId(current => response.sources.some(source => source.id === current) ? current : response.sources[0]?.id ?? '');
      if (!initialChoice.current) {
        initialChoice.current = true;
        const matching = response.examples.find(item => JSON.stringify(item.origin) === JSON.stringify(originText.map(Number)) && JSON.stringify(item.destination) === JSON.stringify(destinationText.map(Number)));
        setExampleId(matching?.id ?? ''); setShowCoordinates(!matching);
      }
    } catch (error) { if (epoch === loadEpoch.current) setLoadError(message(error)); }
    finally { if (epoch === loadEpoch.current) { setLoading(false); requestBusy.current = false; } }
  }

  useEffect(() => { void load(); return () => { loadEpoch.current++; compareEpoch.current++; requestBusy.current = false; }; }, []);

  // Only a changed handoff applies again. Ordinary rerenders and late evidence
  // loads must not restore a candidate after the user chose another journey.
  useEffect(() => {
    if (initialJourney === undefined && !receivedJourney.current) return;
    inputRevision.current++; setChanged(!!result || comparing); setSelectedEvent(undefined); setSelectedFromComparison(false); setCompareError('');
    setActiveJourney(undefined); setJourneyError('');
    if (initialJourney === undefined) {
      receivedJourney.current = false;
      const matching = data?.examples.find(item => JSON.stringify(item.origin) === '[-92.3341,38.9517]' && JSON.stringify(item.destination) === '[-93.625,41.5868]');
      initialChoice.current = !!data; setOriginText(['-92.3341', '38.9517']); setDestinationText(['-93.6250', '41.5868']); setExampleId(matching?.id ?? ''); setShowCoordinates(!!data && !matching);
      return;
    }
    receivedJourney.current = true; initialChoice.current = true;
    if (!journeyValid(initialJourney)) {
      setOriginText(['', '']); setDestinationText(['', '']); setExampleId(''); setShowCoordinates(true);
      setJourneyError('The selected Command candidate has incomplete or invalid journey details. Choose a named journey below or enter two valid, different locations before comparing.');
      return;
    }
    const captured = copyJourney(initialJourney);
    setActiveJourney(captured); setOriginText(captured.origin.map(String)); setDestinationText(captured.destination.map(String)); setExampleId(candidateChoice); setShowCoordinates(false);
  }, [initialJourney !== undefined, !!journeyValid(initialJourney), initialJourney?.shipmentId, initialJourney?.networkRevision, initialJourney?.origin?.[0], initialJourney?.origin?.[1], initialJourney?.destination?.[0], initialJourney?.destination?.[1], initialJourney?.originName, initialJourney?.destinationName]);

  function change(update: () => void) { inputRevision.current++; update(); setChanged(!!result || comparing); setCompareError(''); }
  function detachJourney() { initialChoice.current = true; setActiveJourney(undefined); setJourneyError(''); }
  const origin = originText.map(value => value.trim() === '' ? NaN : Number(value)) as Coordinate;
  const destination = destinationText.map(value => value.trim() === '' ? NaN : Number(value)) as Coordinate;
  const bufferValue = buffer.trim() === '' ? NaN : Number(buffer);
  const validInput = coordinate(origin) && coordinate(destination) && Number.isInteger(bufferValue) && bufferValue >= 50 && bufferValue <= 2000 && !(origin[0] === destination[0] && origin[1] === destination[1]);
  async function compare() {
    if (requestBusy.current || !validInput || !data) return;
    requestBusy.current = true;
    const epoch = ++compareEpoch.current;
    const revision = inputRevision.current;
    const sources = sourceRevision.current;
    const request: CompareRequest = { origin: [...origin], destination: [...destination], routing, buffer_m: bufferValue };
    const capturedContext = activeJourney ? copyJourney(activeJourney) : undefined;
    const capturedLabel = capturedContext ? journeyLabel(capturedContext) : data.examples.find(item => item.id === exampleId)?.name ?? 'Custom journey';
    setComparing(true); setCompareError('');
    try {
      const response = await api<Comparison>('/road-intelligence/compare', request);
      if (epoch !== compareEpoch.current) return;
      if (!comparisonValid(response, request)) throw new Error('The route comparison has an unsupported or inconsistent response. Review is unavailable for this request.');
      setResult(response); setSelectedRoute(response.alternatives[0].index); setSelectedEvent(undefined);
      setResultJourney(capturedContext); setResultJourneyLabel(capturedLabel);
      setChanged(revision !== inputRevision.current || sources !== sourceRevision.current);
    } catch (error) { if (epoch === compareEpoch.current) setCompareError(message(error)); }
    finally { if (epoch === compareEpoch.current) { setComparing(false); requestBusy.current = false; } }
  }

  function exportComparison() {
    if (!result) return;
    const blob = new Blob([JSON.stringify({ ...result, journey_label: resultJourneyLabel, journey_context: resultJourney ? { ...copyJourney(resultJourney), label: resultJourneyLabel, kind: 'simulated_command_candidate', approved_assignment: false, provenance: 'Selected simulated Command candidate at the captured network revision; read-only route inspection.' } : null, exported_at: new Date().toISOString(), inputs_changed_since_comparison: changed, export_note: 'Read-only planning evidence. Source timestamps and limitations apply; no dispatch or truck-safety approval.' }, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = `aegis-road-comparison-${result.compared_at.replace(/[^0-9T]/g, '').slice(0, 15)}.json`; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 0);
  }

  const source = data?.sources.find(item => item.id === sourceId);
  const query = filter.trim().toLocaleLowerCase();
  const events = (source?.events ?? []).filter(event => `${event.title} ${event.description} ${event.route_name ?? ''} ${event.id}`.toLocaleLowerCase().includes(query));
  const alternative = result?.alternatives.find(item => item.index === selectedRoute);
  const mapOrigin = result?.request.origin ?? (coordinate(origin) ? origin : [-92.3341, 38.9517] as Coordinate);
  const mapDestination = result?.request.destination ?? (coordinate(destination) ? destination : [-93.625, 41.5868] as Coordinate);
  const baseline = result?.alternatives[0];
  const busy = loading || comparing;
  const selectedJourney = data?.examples.find(item => item.id === exampleId);
  const selectedJourneyLabel = activeJourney ? journeyLabel(activeJourney) : selectedJourney?.name;
  const olderJourney = !!activeJourney && currentNetworkRevision !== undefined && activeJourney.networkRevision !== currentNetworkRevision;
  const nearby = alternative?.reviews.flatMap(review => review.nearby_events) ?? [];
  const reviewGaps = alternative?.reviews.filter(review => review.stale || !review.coverage_complete || review.unusable_geometry_count > 0).length ?? 0;
  function inspectComparisonEvent(event: RoadEvent) {
    setSelectedEvent(event); setSelectedFromComparison(true);
    setSelectedRetrievedAt(result?.sources.find(item => item.id === event.source_id)?.retrieved_at);
    setSourceId(event.source_id); setFilter('');
  }
  useEffect(() => { if (result) focusJourneyControl('road-comparison-result'); }, [result]);
  useEffect(() => { if (selectedEvent) focusJourneyControl('road-selected-event'); }, [selectedEvent, selectedFromComparison]);

  return <section className="road-intelligence" aria-label="Road intelligence workspace">
    <div className="road-intro"><span className="road-intro-icon"><Route size={24} /></span><div><div className="eyebrow">CHECK A JOURNEY</div><h2>What could affect this delivery route?</h2><p>Choose where the trip starts and ends. Compare travel options, then inspect saved road notices near the path before a dispatcher chooses a response.</p></div><span className="pill amber">ROUTE REVIEW</span></div>
    {activeJourney && <section className="road-candidate-context" aria-label="Selected Command candidate"><strong>{journeyLabel(activeJourney)}</strong><p>Simulated Command candidate · captured network revision {activeJourney.networkRevision}. Compare these endpoints, then return to Command for the separate response-plan review.</p><small>This handoff is a candidate inspection. It does not approve a trip or change its planning duration, driver assignment or road route.</small>{olderJourney && <p role="status" className="road-context-warning">Command is now at network revision {currentNetworkRevision}; this candidate was captured at revision {activeJourney.networkRevision}. You are inspecting the older endpoints. Open the candidate again from Command to use current inputs.</p>}</section>}
    {journeyError && <div role="alert" className="feedback error"><TriangleAlert size={17} />{journeyError}</div>}
    <JourneySteps title="Check a journey in three steps" summary={loadError && !data ? 'Road information could not be loaded. Retry the saved evidence before comparing a journey.' : 'Start with a named journey below. This screen compares routes; Command and Dispatcher desk handle the separate operational decision.'} steps={[
      {id:'choose',title:'Choose the journey',detail:selectedJourneyLabel ?? 'Pick a named journey, or enter your own start and end coordinates.',state:data && validInput ? 'complete' : 'current',actionLabel:'Choose or change journey',onAction:() => focusJourneyControl('road-journey-choice'),disabled:!data},
      {id:'compare',title:'Compare travel options',detail:result && !changed ? `${result.alternatives.length} option${result.alternatives.length === 1 ? '' : 's'} computed. Select an option to read its nearby notices.` : changed ? 'The journey or evidence changed. Run the comparison again.' : 'Click once to calculate the selected journey and screen the saved road notices.',state:result && !changed ? 'complete' : data ? 'current' : 'waiting',actionLabel:comparing ? 'Comparing journey…' : 'Compare this journey',onAction:() => void compare(),disabled:busy || !data || !validInput},
      {id:'review',title:'Read the notices, then decide',detail:result && !changed ? nearby.length ? `${nearby.length} listed notices are near this option. Check their location and timing.` : 'No listed notice matched this option. Check the coverage limits before deciding.' : 'The comparison will show notices to inspect; it will not change a driver assignment.',state:result && !changed ? selectedFromComparison && selectedEvent ? 'complete' : 'current' : 'waiting',actionLabel:nearby.length ? 'Inspect first nearby notice' : 'Read comparison result',onAction:() => nearby[0] ? inspectComparisonEvent(nearby[0]) : focusJourneyControl('road-comparison-result'),disabled:!result || changed},
    ]} />
    <div className="road-toolbar"><span className="source-note">{data ? `Workspace read ${timestamp(data.generated_at)}` : 'Loading source coverage…'}</span><div><button className="secondary small" onClick={() => void load()} disabled={busy}><RefreshCw size={14} />Recheck saved road evidence</button><button className="secondary small" onClick={() => void load(true)} disabled={busy || !data || data.offline} title={data?.offline ? 'Offline rehearsal uses dated fixtures and disables provider refresh.' : 'Request official providers; cache and rate limits apply.'}><RefreshCw size={14} />Refresh official road feeds</button></div></div>
    {loading && <p role="status">Reading road-event coverage…</p>}
    {loadError && <div role="alert" className="feedback error"><TriangleAlert size={17} /><div>{loadError}{data && <p>The previous saved snapshot remains visible. This request did not establish fresh coverage.</p>}</div><button className="secondary small" disabled={busy} onClick={() => void load()}>Retry road evidence</button></div>}
    {data?.offline && <div className="coverage-warning"><TriangleAlert size={17} />Offline rehearsal: dated evidence fixtures and estimated routing remain available. Provider refresh is disabled. Map tiles may still require internet.</div>}
    {data && <>

      <div className="road-columns">
        <section className="panel road-planner road-guided-scroll" id="road-journey-setup" tabIndex={-1}><div className="panel-heading"><div><h2>Where is the delivery going?</h2><span>Real locations; no shipment or supply contract is implied</span></div><Route size={21} /></div><div className="padded">
          <p className="journey-place-label">{selectedJourneyLabel ?? 'Your custom journey'}</p><label className="field">Planning corridor<select id="road-journey-choice" value={exampleId} onChange={event => { const example = data.examples.find(item => item.id === event.target.value); change(() => { detachJourney(); setExampleId(event.target.value); setShowCoordinates(!example); if (example) { setOriginText(example.origin.map(String)); setDestinationText(example.destination.map(String)); } }); }}><option value="">Custom coordinates</option>{activeJourney && <option value={candidateChoice}>{journeyLabel(activeJourney)}</option>}{data.examples.map(example => <option key={example.id} value={example.id}>{example.name}</option>)}</select></label>
          <details className="journey-technical" open={showCoordinates} onToggle={event => setShowCoordinates(event.currentTarget.open)}><summary>Edit map coordinates</summary><p className="source-note">Optional: use a custom longitude/latitude pair when the named journeys do not cover your trip. Editing an endpoint detaches the selected Command candidate.</p><div className="road-coordinate-grid"><label className="field">Origin longitude<input type="number" min={-180} max={180} step="any" value={originText[0]} onChange={event => change(() => { detachJourney(); setExampleId(''); setOriginText([event.target.value, originText[1]]); })} /></label><label className="field">Origin latitude<input type="number" min={-90} max={90} step="any" value={originText[1]} onChange={event => change(() => { detachJourney(); setExampleId(''); setOriginText([originText[0], event.target.value]); })} /></label><label className="field">Destination longitude<input type="number" min={-180} max={180} step="any" value={destinationText[0]} onChange={event => change(() => { detachJourney(); setExampleId(''); setDestinationText([event.target.value, destinationText[1]]); })} /></label><label className="field">Destination latitude<input type="number" min={-90} max={90} step="any" value={destinationText[1]} onChange={event => change(() => { detachJourney(); setExampleId(''); setDestinationText([destinationText[0], event.target.value]); })} /></label></div>
          </details>
          <label className="field">Road comparison travel source<select value={routing} onChange={event => change(() => setRouting(event.target.value as 'estimated' | 'osrm'))}><option value="estimated">Offline estimated connection</option><option value="osrm">Public OSRM ordinary driving</option></select></label><label className="field">Event proximity buffer (meters)<input type="number" min={50} max={2000} value={buffer} onChange={event => change(() => setBuffer(event.target.value))} /></label>
          <p className="source-note">Longitude comes first. A larger buffer can include parallel roads or separate carriageways. Estimated routes are straight connections, not roads.</p>
          {!validInput && <p className="road-source-caution">Enter two different valid longitude/latitude locations and a buffer from 50 to 2,000 meters.</p>}
          <button className="road-compare-button" disabled={busy || !validInput} onClick={() => void compare()}><Route size={16} />{comparing ? 'Comparing captured evidence…' : 'Compare planning routes'}</button>
          <p className="source-note">This tool does not assign a truck, bypass a closure, or change an approved plan. Commercial restrictions need separate validation.</p>
        </div></section>
        <section className="panel road-map-panel"><div className="panel-heading"><div><h2>Corridor and event geometry</h2><span>{result ? `Comparison captured ${timestamp(result.compared_at)}` : 'Choose a corridor and compare to add a route'}</span></div><MapPin size={21} /></div>{result || coordinate(origin) && coordinate(destination) ? <RoadMap events={events} selectedEvent={selectedEvent} alternatives={result?.alternatives ?? []} selectedRoute={selectedRoute} origin={mapOrigin} destination={mapDestination} /> : <p className="road-empty">Choose valid start and end locations to show this journey on the map.</p>}</section>
      </div>
      {compareError && <div role="alert" className="feedback error"><TriangleAlert size={17} />{compareError}{result && <span>The previous comparison remains visible.</span>}</div>}
      {changed && <div className="coverage-warning" role="status"><TriangleAlert size={16} />Inputs or saved evidence changed. Displayed routes describe the previous comparison; compare again to review the current inputs.</div>}
      {result && <section className="panel road-comparison road-guided-scroll" id="road-comparison-result" tabIndex={-1}><div className="panel-heading"><div><h2>Alternative review</h2><span>{resultJourneyLabel || 'Custom journey'} · comparison captured {timestamp(result.compared_at)}</span></div><button className="secondary small" onClick={exportComparison}><ArrowDownToLine size={14} />Export comparison JSON</button></div><div className="padded">{resultJourney && <p className="road-captured-candidate" aria-label="Captured candidate provenance">Captured simulated Command candidate {resultJourney.shipmentId} · network revision {resultJourney.networkRevision}. These are the compared endpoints; this result is not an approved assignment or replacement route.</p>}<div className="road-alternatives">{result.alternatives.map(item => <button key={item.index} aria-pressed={selectedRoute === item.index} className={`road-alternative ${selectedRoute === item.index ? 'selected' : ''}`} onClick={() => { setSelectedRoute(item.index); setSelectedEvent(undefined); }}><span><strong>Route {item.index + 1}</strong><span className="pill amber">{item.fallback ? 'ESTIMATED CONNECTION' : 'OSRM DRIVING'}</span></span><b>{(item.distance_m / 1000).toFixed(1)} km <small>· {Math.round(item.duration_seconds / 60)} min</small></b><small>{item.index === baseline?.index ? 'Comparison reference' : `${((item.distance_m - (baseline?.distance_m ?? 0)) / 1000).toFixed(1)} km / ${Math.round((item.duration_seconds - (baseline?.duration_seconds ?? 0)) / 60)} min versus route ${(baseline?.index ?? 0) + 1}`}</small><small>{item.review_required ? 'Review required' : 'Screened captured geometry; review before use'}</small></button>)}</div>
        {alternative && <div className="journey-plain-result" aria-label="Road comparison meaning"><h3>What should I do with this result?</h3><p><strong>Route {alternative.index + 1}: {(alternative.distance_m / 1000).toFixed(1)} km, about {Math.round(alternative.duration_seconds / 60)} minutes.</strong> {alternative.fallback ? 'This is a rough estimated connection, not the shape of a road.' : 'This is an ordinary-driving estimate from the routing service.'}</p><p>{nearby.length ? `${nearby.length} listed notice${nearby.length === 1 ? ' is' : 's are'} near this option. Open a notice below and check whether its location and time matter for your delivery.` : 'No listed notice matched this option. That does not establish a clear road.'}{reviewGaps ? ` ${reviewGaps} source review${reviewGaps === 1 ? ' has' : 's have'} stale, incomplete or unscored information.` : ''}</p><p>Driver use still needs a dispatcher's review of road conditions and vehicle restrictions.</p><div className="road-next-actions">{nearby[0] && <button className="secondary" disabled={changed} onClick={() => inspectComparisonEvent(nearby[0])}>Read first nearby notice</button>}{onNavigate && <button className="secondary" onClick={() => onNavigate('command')}>Compare delivery responses in Command</button>}</div></div>}
        <details className="journey-technical"><summary>How this comparison was calculated</summary><p>Captured comparison · {result.request.origin.join(', ')} → {result.request.destination.join(', ')} · {result.request.buffer_m} m buffer</p><div className="road-routing-metadata"><h3>Travel source and retrieval</h3><p>{result.routing_provenance || (result.alternatives.every(item => item.fallback) ? 'Estimated planning connection; no provider road geometry is represented.' : 'OSRM ordinary driving route.')}</p><p>Requested source: {result.request.routing === 'osrm' ? 'public OSRM ordinary driving' : 'offline estimate'}. {result.routing_retrieved_at ? <>Provider response retrieved {timestamp(result.routing_retrieved_at)}.{result.routing_cache && ' A saved response was reused.'}</> : 'No provider retrieval timestamp is available for this route.'}</p>{result.routing_stale && <p className="road-source-caution">The routing response is stale. Its travel estimates require review against current conditions.</p>}{(result.routing_error || result.routing_refresh_error) && <p className="road-source-error"><strong>{result.alternatives.every(item => item.fallback) ? 'Estimated fallback reason' : 'Routing refresh failure'}:</strong> {result.routing_error || result.routing_refresh_error}</p>}</div>
        </details>
        {alternative && <div className="road-review-grid">{alternative.reviews.map(review => <article key={review.source_id} className="road-review-card"><h3>{review.source_name}</h3><p>{review.nearby_event_count ?? review.nearby_events.length} captured geometries within the buffer{review.hits_truncated ? `; first ${review.nearby_events.length} shown` : ''}.</p><p className="source-note">{review.stale ? 'Stale source evidence. ' : ''}{!review.coverage_complete ? 'Incomplete coverage. ' : ''}{review.unusable_geometry_count > 0 ? `${review.unusable_geometry_count} unscored geometries. ` : ''}No listed match does not establish a clear road.</p>{review.nearby_events.length > 0 ? <ul className="road-hits">{review.nearby_events.map((event, i) => <li key={`${event.id}-${i}`}><button className="text-button" onClick={() => { inspectComparisonEvent(event); }}><span>{event.title}</span><b>{event.proximity_m.toFixed(0)} m</b></button></li>)}</ul> : <p className="road-no-hits">No matching geometry in this captured source and buffer. Unreported events and uncovered roads remain possible.</p>}</article>)}</div>}
        <div className="coverage-warning"><TriangleAlert size={16} />OSRM does not incorporate these events or validate commercial-truck height, weight or other restrictions. Nearby events can describe parallel roads. No alternative is certified truck-safe.</div><ul className="road-limitations">{result.limitations.map((item, i) => <li key={i}>{item}</li>)}</ul>
      </div></section>}
      <div className="road-source-grid">{data.sources.map(item => <article key={item.id} className={`road-source-card ${sourceId === item.id ? 'selected' : ''}`}><div className="road-source-heading"><span className="eyebrow">{item.state} · {item.provider}</span><span className={`pill ${!item.available || item.stale || !item.coverage_complete || item.fixture ? 'amber' : 'green'}`}>{!item.available ? 'UNAVAILABLE' : item.fixture ? 'DATED FIXTURE' : item.stale ? 'STALE SNAPSHOT' : 'CAPTURED RESPONSE'}</span></div><h3>{item.name}</h3><p><strong>{item.available ? item.event_count.toLocaleString() : '—'}</strong> captured event records</p><p className="source-note">Retrieved {timestamp(item.retrieved_at)}. {item.coverage_complete ? 'Provider query completed; route coverage remains unverified.' : 'Coverage incomplete or unavailable.'}</p>{item.unusable_geometry_count > 0 && <p className="road-source-caution">{item.unusable_geometry_count} records lack usable geometry for screening.</p>}{item.error && <p className="road-source-error">{item.error}</p>}<SourceMetadata source={item} /><button className="text-button" onClick={() => { setSourceId(item.id); setSelectedEvent(undefined); setFilter(''); }} aria-pressed={sourceId === item.id}>Inspect {item.state} events <MapPin size={13} /></button></article>)}</div>
      <section className="panel road-event-panel"><div className="panel-heading"><div><h2>Inspect captured events</h2><span>Provider text and timestamps remain separate from retrieval time</span></div></div><div className="padded"><div className="road-event-toolbar"><label className="field">Official road feed<select value={sourceId} onChange={event => { setSourceId(event.target.value); setSelectedEvent(undefined); }} >{data.sources.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label className="field">Filter captured road events<input type="search" value={filter} onChange={event => setFilter(event.target.value)} placeholder="Route, description or event ID" /></label></div>
        {source && <><p className="source-note">{source.warning}</p><p className="source-note">{events.length} filtered rows from {source.events.length} listed / {source.event_count} captured records{source.events_truncated ? '. The source preview is truncated; route screening uses all usable captured geometries.' : '.'} {source.unusable_geometry_count} records cannot be screened geometrically. <a href={safeLink(source.source_url)} target="_blank" rel="noreferrer">Official provider endpoint</a></p>{!source.available && !selectedEvent ? <p className="road-empty">This feed is unavailable. No road-clear conclusion can be drawn.</p> : events.length === 0 && !selectedEvent ? <p className="road-empty">No listed events match this view. This does not establish clear roads or full coverage.</p> : <div className="road-event-layout"><div className="road-event-list" aria-label="Captured event list">{events.map((event, i) => <button key={`${event.id}-${i}`} className={`road-event-row ${selectedEvent?.id === event.id && selectedEvent.source_id === event.source_id ? 'selected' : ''}`} onClick={() => { setSelectedEvent(event); setSelectedFromComparison(false); setSelectedRetrievedAt(source.retrieved_at); }}><strong>{event.title}</strong><span>{event.route_name || 'Route name not supplied'}</span><small>{event.geometry ? 'Geometry captured' : 'No usable geometry'} · {event.id}</small></button>)}</div><article className="road-event-detail road-guided-scroll" id="road-selected-event" tabIndex={-1} aria-label="Road event detail">{selectedEvent ? <><span className="eyebrow">{selectedEvent.source_id} · {selectedFromComparison ? 'COMPARISON SNAPSHOT RECORD' : 'SOURCE PREVIEW RECORD'}</span>{selectedFromComparison && <p className="source-note road-selected-provenance">This record belongs to the captured route comparison. Its source retrieval and geometry may differ from the saved evidence preview above; the selected map geometry uses this exact record.</p>}<h3>{selectedEvent.title}</h3><div className="dispatch-next-state"><strong>What to check</strong><p>Does this notice overlap your delivery time and the actual road you would use? Read the provider text below before choosing a response.</p>{onNavigate && <div className="road-next-actions"><button className="secondary small" onClick={() => onNavigate('dispatch')}>Open dispatcher review</button><button className="secondary small" onClick={() => onNavigate('command')}>Test a response in Command</button></div>}</div><p className="road-event-description">{selectedEvent.description || 'Description not supplied.'}</p><dl><dt>Event identifier</dt><dd>{selectedEvent.id}</dd><dt>Route</dt><dd>{selectedEvent.route_name || 'Not supplied'}</dd><dt>Provider update</dt><dd>{timestamp(selectedEvent.updated_at)}</dd><dt>Reported start</dt><dd>{timestamp(selectedEvent.starts_at)}</dd><dt>Reported end</dt><dd>{timestamp(selectedEvent.ends_at)}</dd><dt>Source retrieval</dt><dd>{timestamp(selectedRetrievedAt)}</dd><dt>Geometry</dt><dd>{selectedEvent.geometry?.type || 'Unavailable; excluded from proximity screening'}</dd></dl>{selectedEvent.provider_times && Object.keys(selectedEvent.provider_times).length > 0 && <details><summary>Original provider time values</summary><p className="source-note">Time zones and provider formatting are unverified. These literal values have not been converted into event observation times.</p><pre>{JSON.stringify(selectedEvent.provider_times, null, 2)}</pre></details>}{selectedEvent.properties && <details><summary>Original provider fields</summary><pre>{JSON.stringify(selectedEvent.properties, null, 2)}</pre></details>}</> : <div className="road-detail-empty"><MapPin size={28} /><p>Select an event to inspect its provider text, source timestamps and geometry availability.</p></div>}</article></div>}</>}
      </div></section>
      <details className="panel road-boundaries"><summary>Coverage and interpretation limits</summary><ul>{data.limitations.map((item, i) => <li key={i}>{item}</li>)}</ul><p>Official road evidence is separate from simulated cargo, fuel, shipments and food-safety sampling. This workspace creates no mandatory hold or dispatcher approval.</p></details>
    </>}
  </section>;
}
