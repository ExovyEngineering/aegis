import DriverWorkspace from './DriverWorkspace';
import RuntimeBanner from './RuntimeBanner';
import ModelErrorAnalysis from './ModelErrorAnalysis';
import ProjectBrief from './ProjectBrief';
import DataExplorer from './DataExplorer';
import FoodAccessContext from './FoodAccessContext';
import ScenarioDetails from './ScenarioDetails';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Activity, ArrowDownToLine, ArrowRight, Bell, Check, CheckCircle2, ChevronRight, ClipboardCheck, CloudSun, Database, Gauge, MapPin, Radio, RefreshCw, Route, ShieldCheck, Smartphone, Snowflake, Truck, TriangleAlert, X } from 'lucide-react';
import { Area, AreaChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import NetworkMap from './NetworkMap';
import RouteLab from './RouteLab';
import RoadIntelligence, { type RoadJourneyContext } from './RoadIntelligence';
import EvidenceAssistant from './EvidenceAssistant';
import DeliveryOutlook from './DeliveryOutlook';
import FreshnessLab from './FreshnessLab';
import WorkspaceGuide from './WorkspaceGuide';
import EventImpactPanel from './EventImpactPanel';
import ActivityTimeline from './ActivityTimeline';
import CommandRouteReview, { hasUsableRoadRoutes, downloadCaptured } from './CommandRouteReview';
import DispatcherDesk from './DispatcherDesk';
import { NOAACoverageCard, ModelTimingCard } from './ScientificCoverage';
import { api, fixed, formatNumber, recallRows } from './api';
import type { Audit, Coverage, Evidence, Facility, Model, Network, Scenario, Shipment } from './types';

type View = 'command' | 'evidence' | 'science' | 'drive' | 'routes' | 'roads' | 'dispatch' | 'brief' | 'assistant' | 'freshness';
const evidenceNames: Record<string, string> = { openmeteo: 'Open-Meteo forecast', nws_alerts: 'NWS official alerts', ncei_historical: 'NCEI historical observations', fsis_recalls: 'FSIS official recalls', modot: 'MoDOT traveler information' };
const evidenceKinds: Record<string, string> = { openmeteo: 'Weather forecast', nws_alerts: 'Official severe weather warnings', ncei_historical: 'Observed historical weather · see station coverage audit', fsis_recalls: 'Official recall notices · no shipment match asserted', modot: 'Road incident feed · not incorporated in OSRM' };
function SourceStamp({ evidence }: { evidence?: Evidence }) { return <span className="source-stamp">{evidence?.retrieved_at ? `${evidence.fixture ? 'Dated fixture' : evidence.stale ? 'Stale cached response' : 'Cached response'} - retrieved ${new Date(evidence.retrieved_at).toLocaleString('en-US', { timeZone: 'America/Chicago' })} CT` : 'No successful response captured'}</span>; }
function Stat({ label, value, note, icon, alert }: { label: string; value: string | number; note: string; icon: React.ReactNode; alert?: boolean }) { return <div className={`stat ${alert ? 'stat-alert' : ''}`}><div className="stat-top">{label}{icon}</div><strong>{value}</strong><small>{note}</small></div>; }
function ingestionNote(row: any): string {
  if (row.error) return row.error;
  if (row.status === 'ingested') return 'Source schema accepted; no cross-source linkage asserted';
  if (row.status === 'duplicate') return `Duplicate bytes recorded; no additional observations were ingested${row.duplicate_of ? ` (${row.duplicate_of})` : ''}.`;
  if (row.status === 'unrecognized') return row.note ?? 'Unsupported source schema; not ingested or merged.';
  if (row.status === 'conflict') return 'Conflicting exports; select one explicit source snapshot before ingestion.';
  if (row.status === 'failed') return 'Import failed; observations were not accepted. Inspect the exact ingestion report.';
  return 'Import completion is not recorded; schema acceptance has not been established.';
}

export default function App() {
  const driverOnly = new URLSearchParams(window.location.search).get('mode') === 'drive';
  const [view, setView] = useState<View>(driverOnly ? 'drive' : new URLSearchParams(window.location.search).get('mode') === 'rehearsal' ? 'brief' : 'command');
  const loadEpoch = useRef(0);
  const routeEpoch = useRef(0);
  const currentRouteContext = useRef('');
  const [network, setNetwork] = useState<Network>();
  const [coverage, setCoverage] = useState<Coverage[]>([]);
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [model, setModel] = useState<Model>({ status: 'Loading measured evaluation' });
  const [evidence, setEvidence] = useState<Record<string, Evidence>>({});
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [assignments, setAssignments] = useState<Shipment[]>([]);
  const [audit, setAudit] = useState<Audit[]>([]);
  const [selectedId, setSelectedId] = useState('SH11');
  const [freshnessShipmentId, setFreshnessShipmentId] = useState<string>();
  const [driverTrip, setDriverTrip] = useState<{truckId:string;shipmentId:string}>();
  const [route, setRoute] = useState<any>();
  const [proposal, setProposal] = useState<Scenario>();
  const [actor, setActor] = useState('');
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const actionLock = useRef(false);
  const [routeLoading, setRouteLoading] = useState(false);
  const [routeError, setRouteError] = useState('');
  const [recomputeError, setRecomputeError] = useState('');
  const [resetError, setResetError] = useState('');
  const [selectedAlternative, setSelectedAlternative] = useState(0);
  const [mapPlan, setMapPlan] = useState('candidates');
  const [approvalError, setApprovalError] = useState('');
  const [resetOpen, setResetOpen] = useState(false);
  const [focusTarget, setFocusTarget] = useState('');
  const [lastRecompute, setLastRecompute] = useState<{time:string; revision:number; count:number; same:boolean}>();
  const [confirmedEvent, setConfirmedEvent] = useState<{receipt:any;comparison:any}>();
  const [activityOpen, setActivityOpen] = useState(false);
  const [roadJourney, setRoadJourney] = useState<RoadJourneyContext>();
  function navigate(target: View) {
    if (target === 'roads') setRoadJourney(undefined);
    if (target === 'freshness') setFreshnessShipmentId(undefined);
    if (target === 'command' && (view === 'dispatch' || view === 'roads')) setFocusTarget('command-scenarios');
    setView(target);
  }
  function compareShipmentRoad(id: string) {
    const candidate = network?.shipments.find(row => row.id === id);
    const origin = network?.nodes.find(row => row.id === candidate?.origin);
    const destination = network?.nodes.find(row => row.id === candidate?.destination);
    const usable = (point: unknown): point is [number,number] => Array.isArray(point) && point.length === 2 && point.every(value => typeof value === 'number' && Number.isFinite(value)) && Math.abs(point[0]) <= 180 && Math.abs(point[1]) <= 90;
    if (!network || !candidate || !origin || !destination || !usable(origin.coordinates) || !usable(destination.coordinates)) {
      setError('This candidate has no usable journey in the current network. Reload the plan before comparing roads.');
      return;
    }
    setSelectedId(candidate.id);
    setRoadJourney({shipmentId:candidate.id,networkRevision:network.revision,origin:[...origin.coordinates],destination:[...destination.coordinates],originName:origin.name,destinationName:destination.name});
    setView('roads');
  }
  function focusActivity() { const panel=document.getElementById('activity-history'); panel?.scrollIntoView?.({block:'start',behavior:'auto'}); panel?.focus({preventScroll:true}); }
  useEffect(() => { if (activityOpen) focusActivity(); },[activityOpen]);
  function setActionBusy(value: boolean) { actionLock.current = value; setBusy(value); if (value) { setNotice(''); setError(''); } }
  function jump(target: string) { setView('command'); setFocusTarget(target); }
  useEffect(() => {
    if (view !== 'command' || !focusTarget) return;
    const element = document.getElementById(focusTarget);
    if (element) { element.scrollIntoView?.({behavior:'auto', block:'center'}); element.focus({preventScroll:true}); setFocusTarget(''); }
  }, [view, focusTarget, route]);
  const [inventory, setInventory] = useState<{ files?: any[] }>({});
  const [evidenceSummary, setEvidenceSummary] = useState<any[]>([]);
  const load = useCallback(async () => {
    const epoch = ++loadEpoch.current;
    if (driverOnly) {
      try { const current = await api<Network>('/network'); if (epoch === loadEpoch.current) { setNetwork(current); setError(''); } }
      catch(e) { if (epoch === loadEpoch.current) { setNetwork(undefined); setError(`Driver network unavailable: ${String(e)}`); } }
      return;
    }
    const results = await Promise.allSettled([api<Network>('/network'), api<Coverage[]>('/coverage'), api<Facility[]>('/facilities'), api<Model>('/model'), api<Scenario[]>('/scenarios'), api<Shipment[]>('/driver'), api<Audit[]>('/audit'), api<{ files?: any[] }>('/inventory')]);
    if (epoch !== loadEpoch.current) return;
    if (results[0].status === 'rejected') { setNetwork(undefined); setAssignments([]); setScenarios([]); setError(`Backend unavailable: ${results[0].reason.message}. Start FastAPI on port 8000.`); return {okay:false}; }
    setNetwork(results[0].value); setError('');
    const setters = [setCoverage, setFacilities, setModel, setScenarios, setAssignments, setAudit, setInventory] as ((v: any) => void)[];
    const empty = [[], [], {status:'Measured evaluation unavailable'}, [], [], [], {files:[]}];
    const names = ['source coverage','facility directory','model evaluation','scenario results','driver assignments','audit trail','raw inventory'];
    const failed: string[] = [];
    results.slice(1).forEach((result, i) => { setters[i](result.status === 'fulfilled' ? result.value : empty[i]); if (result.status === 'rejected') failed.push(names[i]); });
    if (failed.length) setError(`Some application data is unavailable: ${failed.join(', ')}. Prior results were cleared; retry before acting.`);
    const sources = await Promise.allSettled(Object.keys(evidenceNames).map(async key => [key, await api<Evidence>(`/evidence/${key}${key === 'fsis_recalls' ? '?limit=20' : ''}`)] as const));
    if (epoch !== loadEpoch.current) return;
    setEvidence(Object.fromEntries(sources.filter(r => r.status === 'fulfilled').map(r => r.value)));
    api<any[]>('/evidence-summary').then(value => { if (epoch === loadEpoch.current) setEvidenceSummary(value); }).catch(() => {});
    return {okay:failed.length === 0, revision:results[0].value.revision, scenarios:results[4].status === 'fulfilled' ? results[4].value : []};
  }, [driverOnly]);
  useEffect(() => { load(); }, [load]);
  const previousView = useRef(view);
  useEffect(() => { if (previousView.current === 'drive' && view !== 'drive') load(); previousView.current = view; }, [view, load]);
  useEffect(() => { if (typeof window.matchMedia === 'function' && window.matchMedia('(max-width:700px)').matches) document.querySelector<HTMLElement>('.sidebar nav button.active')?.scrollIntoView?.({block:'nearest',inline:'center'}); },[view]);
  async function act(fn: () => Promise<unknown>, success: string, approval = false, reset = false) {
    if (actionLock.current) return;
    setActionBusy(true); setError(''); setNotice(''); if (approval) setApprovalError('');
    try { await fn(); setNotice(success); await load(); }
    catch (e) { const message = e instanceof Error ? e.message : String(e); setError(message); if (approval) setApprovalError(message); if (reset) setResetError(message); }
    finally { setActionBusy(false); }
  }
  async function refreshApplication() {
    if (actionLock.current) return;
    setActionBusy(true); setError(''); setNotice(''); setRecomputeError('');
    const fingerprint = (rows:Scenario[]) => JSON.stringify(rows.map(row => [row.scenario,row.solver_status,row.total_logistics_cost,row.unmet_demand_kg,row.shipments.map(trip => [trip.id,trip.lot_id])]));
    try {
      const result = await load();
      if (result?.okay && result.scenarios && result.revision !== undefined) {
        const same = fingerprint(scenarios) === fingerprint(result.scenarios);
        const time = new Date().toLocaleTimeString('en-US',{timeZone:'America/Chicago'});
        setLastRecompute({time,revision:result.revision,count:result.scenarios.length,same});
        setNotice(`Recomputed ${result.scenarios.length} response plans at revision ${result.revision}. ${same ? 'Totals and selected trips match the previous results.' : 'Updated results are ready to review.'} No plan was approved.`);
      } else setRecomputeError('The full comparison could not be recomputed. Some network or scenario data is unavailable; reload before proposing an action.');
    } catch(e) { const message=e instanceof Error ? e.message : String(e); setError(message); setRecomputeError(message); }
    finally { setActionBusy(false); }
  }
  const selected = network?.shipments.find(s => s.id === selectedId) ?? network?.shipments[0];
  const routeContextKey = JSON.stringify([selected?.id,selected?.origin,selected?.destination,network?.revision]);
  currentRouteContext.current = routeContextKey;
  const offlineRehearsal = !!(network?.runtime?.isolated && network.runtime.offline);
  const excursions = network?.shipments.filter(s => s.temperature_c > 4) ?? [];
  const totalSuccessful = coverage.filter(s => s.success).length;
  const telemetry = network?.telemetry.filter(t => t.shipment_id === selected?.id).map(t => ({ time: t.timestamp.slice(11, 16), temperature: t.temperature_c })) ?? [];
  const forecast = evidence.openmeteo?.payload?.hourly;
  const forecastData = forecast?.time?.slice(0, 36).map((t: string, i: number) => ({ time: t.slice(11, 16), temperature: forecast.temperature_2m?.[i] })) ?? [];
  const recalls = recallRows(evidence.fsis_recalls?.payload);
  const alertFeatures = evidence.nws_alerts?.payload?.features ?? [];
  const reviewAlerts = [
    ...excursions.map(s => ({ title: `${s.id} · cargo temperature ${s.temperature_c}°C`, body: `${s.truck_id} → ${s.destination}. Simulated excursion; dispatcher review required.`, color: 'amber', shipmentId:s.id })),
    ...(network?.lots.filter(l => l.held).map(l => ({ title: `${l.id} · active precautionary hold`, body: 'Excluded from dispatch in every scenario.', color: 'red', target:'dispatch' as View })) ?? []),
    ...alertFeatures.slice(0, 2).map((f: any) => ({ title: `NWS · ${f.properties?.event ?? 'weather alert'}`, body: f.properties?.areaDesc ?? 'Review official alert geometry and timing.', color: 'amber', target:'evidence' as View })),
  ];
  useEffect(() => { setRoute((previous: any) => previous?.shipmentId && previous.contextKey !== currentRouteContext.current ? undefined : previous); }, [routeContextKey]);
  async function computeRoute() {
    if (!network || !selected) return;
    const origin = network.nodes.find(n => n.id === selected.origin), destination = network.nodes.find(n => n.id === selected.destination);
    if (!origin || !destination) return;
    if (actionLock.current) return;
    const epoch = ++routeEpoch.current; const contextKey = routeContextKey; setActionBusy(true); setRouteLoading(true); setError(''); setNotice(''); setRouteError(''); setRoute(undefined);
    try { const result = await api<any>('/route', {coordinates:[origin.coordinates,destination.coordinates],alternatives:true});
      if (epoch !== routeEpoch.current || contextKey !== currentRouteContext.current) return;
      if (!hasUsableRoadRoutes(result)) throw new Error('No usable route geometry was returned. No route or assignment changed; retry the route request.');
      setSelectedAlternative(0);
      setRoute({...result, contextKey, shipmentId:selected.id, networkRevision:network.revision, displayLabel:`Requested route for ${selected.id}: ${origin.name} to ${destination.name}`});
      setFocusTarget('command-route-result');
      setNotice(`Route response loaded for ${selected.id}. Review geometry and commercial vehicle limitations.`);
    } catch(e) { if (epoch === routeEpoch.current && contextKey === currentRouteContext.current) { setError(String(e)); setRouteError(e instanceof Error ? e.message : String(e)); } } finally { setActionBusy(false); setRouteLoading(false); }
  }
  async function refreshSource(key: string, title: string) {
    if (actionLock.current) return;
    setActionBusy(true); setError(''); setNotice('');
    try { const response = await api<any>(`/refresh/${key}?summary=true`,{}); await load();
      if (response.status === 'failed') setError(`${title}: ${response.error ?? 'request failed'}`);
      else if (response.stale || response.refresh_error) setError(`${title}: refresh unavailable; showing the dated cached response. ${response.refresh_error ?? 'Read the source age before use.'}`);
      else setNotice(`${title} source check completed. Read the response retrieval time and coverage.`);
    } catch(e) { setError(String(e)); } finally { setActionBusy(false); }
  }
  const mapOverlay = mapPlan === 'approved' ? {label:'Current approved assignments',scope:'approved' as const,shipments:assignments} : mapPlan === 'candidates' ? {label:'All candidate shipments',scope:'candidate' as const,shipments:network?.shipments ?? []} : {label:`Scenario ${mapPlan}: proposed allocation`,scope:'scenario' as const,shipments:scenarios.find(row => row.scenario === mapPlan)?.shipments ?? []};
  const approvedSelected = assignments.find(row => row.id === selected?.id);
  return <div className={`app-shell ${driverOnly ? 'driver-only' : ''}`}>
    {!driverOnly && <aside className="sidebar">
      <div className="brand"><div className="brand-symbol"><ShieldCheck size={25} strokeWidth={1.6} /></div><div>AEGIS<small>SUPPLY CHAIN INTELLIGENCE</small></div></div>
      <div className="workspace-label">OPERATIONS WORKSPACE</div>
      <nav aria-label="Main navigation">
        <button className={view === 'command' ? 'active' : ''} onClick={() => setView('command')}><Gauge size={19} /> Command center <ChevronRight size={14} /></button>
        <button className={view === 'freshness' ? 'active' : ''} onClick={() => navigate('freshness')}><Snowflake size={19} /> Save the Load</button>
        <button className={view === 'routes' ? 'active' : ''} onClick={() => setView('routes')}><Route size={19} /> Route laboratory</button>
        <button className={view === 'roads' ? 'active' : ''} onClick={() => navigate('roads')}><MapPin size={19} /> Road intelligence</button>
        <button className={view === 'dispatch' ? 'active' : ''} onClick={() => setView('dispatch')}><ClipboardCheck size={19} /> Dispatcher desk</button>
        <button className={view === 'drive' ? 'active' : ''} onClick={() => setView('drive')}><Smartphone size={19} /> AEGIS Drive</button>
        <button className={view === 'assistant' ? 'active' : ''} onClick={() => setView('assistant')}><ShieldCheck size={19} /> Evidence assistant</button>
        <button className={view === 'science' ? 'active' : ''} onClick={() => setView('science')}><Activity size={19} /> Model evaluation</button>
        <button className={view === 'brief' ? 'active' : ''} onClick={() => setView('brief')}><ArrowDownToLine size={19} /> Project brief</button>
        <button className={view === 'evidence' ? 'active' : ''} onClick={() => setView('evidence')}><Database size={19} /> Sources & evidence</button>
      </nav>
      <div className="sidebar-note"><span className="eyebrow">MISSOURI PILOT</span><strong>A clearer view.<br />A considered response.</strong><p>Regional poultry distribution<br />Research demonstrator</p><div><i className="live-dot" /> Deterministic scenario</div></div>
      <div className="sidebar-footer"><span className="avatar">MO</span><div>Regional operations<small>Local development · seed {network?.seed ?? '20261026'}</small></div></div>
    </aside>}
    <main>
      {!driverOnly && <header className="topbar"><span><span className="breadcrumb">AEGIS</span><ChevronRight size={13} /> {view === 'freshness' ? 'Freshness and rescue planning' : view === 'brief' ? 'Team status and presentation' : view === 'routes' ? 'Farm & fleet planning' : view === 'roads' ? 'Independent road evidence' : view === 'assistant' ? 'Cited operational explanations' : view === 'dispatch' ? 'Dispatcher review' : view === 'drive' ? 'Driver workspace' : view === 'science' ? 'Scientific validation' : view === 'evidence' ? 'Data provenance' : 'Command center'}</span><div><span className="environment-badge">SIMULATED OPERATIONS</span><button aria-label="Reload application data" className="icon-button" disabled={busy} onClick={() => void refreshApplication()}><RefreshCw size={17} /></button><button className="icon-button" aria-label="Open review queue" onClick={() => jump("command-review-queue")}><Bell size={18} /></button><button className="secondary small" id="open-activity-history" aria-label="Open activity history" aria-controls="activity-history" aria-expanded={activityOpen} onClick={() => { if (activityOpen) focusActivity(); else setActivityOpen(true); }}>Recent activity</button><span className="avatar">OP</span></div></header>}
      <div className="content"><RuntimeBanner runtime={network?.runtime} requestedRehearsal={!!network && new URLSearchParams(window.location.search).get('mode') === 'rehearsal'} />
        {!driverOnly && <div className="page-heading"><div><div className="eyebrow">{view === 'drive' ? 'AEGIS DRIVE' : 'ADAPTIVE EARLY-WARNING & GUIDANCE'}</div><h1>{view === 'freshness' ? 'Save the Load' : view === 'brief' ? 'Know what works. Show the evidence.' : view === 'routes' ? 'Test the journey ahead' : view === 'roads' ? 'Inspect the road ahead' : view === 'assistant' ? 'Understand the evidence behind a decision' : view === 'dispatch' ? 'Turn reports into reviewed action' : view === 'command' ? 'Regional command center' : view === 'evidence' ? 'Evidence with a clear origin' : view === 'science' ? 'Measured model performance' : 'Your assigned journey'}</h1><p>{view === 'freshness' ? 'Follow captured temperature exposure, compare FEFO picks and review a closer recipient before changing the simulated plan.' : view === 'brief' ? 'Your maintained feature register, executed checks and downloadable presentation brief.' : view === 'routes' ? 'Single-farm dispatch and multi-location fleets · Simulated operations, explicit assumptions, inspectable routes.' : view === 'assistant' ? 'Read-only answers grounded in a captured network and dated evidence. Human decisions stay in their existing workflows.' : view === 'roads' ? 'Explore Missouri and Iowa official road events, compare alternatives, and inspect coverage before any operational decision.' : view === 'dispatch' ? 'Driver reports, human-approved holds, and versioned trip instructions in one shared workflow.' : view === 'command' ? 'Missouri poultry network · Monitor conditions. Compare responses. Keep people in control.' : view === 'drive' ? 'Park safely before using this interface. Assignments appear only after dispatcher approval.' : view === 'science' ? 'A retrospective feasibility study of selected FSIS poultry samples. No consumer illness probability.' : 'Public source responses, coverage gaps, retrieval times, and supplied data.'}</p></div><div className="date-block"><span>{view === 'freshness' ? 'EXPOSURE HISTORY' : 'SCENARIO REFERENCE DATE'}</span><strong>{view === 'freshness' ? 'See observation times' : 'October 26, 2026'}</strong></div></div>}
        {!driverOnly && <WorkspaceGuide view={view} onNavigate={navigate} />}
        {!driverOnly && activityOpen && <div id="activity-history" tabIndex={-1} style={{scrollMarginTop:90}}><ActivityTimeline onClose={() => { setActivityOpen(false); document.getElementById('open-activity-history')?.focus(); }} onNavigate={target => { setActivityOpen(false); setView(target); }} onSelectShipment={id => { setActivityOpen(false); setView('command'); if (network?.shipments.some(row => row.id === id)) { setSelectedId(id); setFocusTarget('command-trip-detail'); } else setNotice(`Recorded trip ${id} is not present in the current network. Its historical audit entry remains available.`); }} /></div>}
        {error && <div role="alert" className="feedback error"><TriangleAlert size={18} />{error}<button onClick={() => setError('')} aria-label="Dismiss error"><X size={16} /></button></div>}
        {notice && <div role="status" className="feedback success"><CheckCircle2 size={18} />{notice}<button onClick={() => setNotice('')} aria-label="Dismiss notification"><X size={16} /></button></div>}
        {!driverOnly && confirmedEvent && view === 'command' && <aside className="panel command-confirmed-event" aria-label="Confirmed event receipt"><div><strong>Confirmed: {confirmedEvent.comparison.event_label} on {confirmedEvent.comparison.shipment_id}</strong><p>Applied at network revision {confirmedEvent.receipt.revision}; {confirmedEvent.receipt.assignments_removed} approved assignments were removed. This is a captured result, not a new action.</p>{!network && <p role="alert">The event was applied, but the current network is unavailable. The confirmed receipt is preserved here. Reload application data before applying another event.</p>}</div><div className="command-result-actions"><button className="secondary small" onClick={() => downloadCaptured(`aegis-confirmed-event-${confirmedEvent.comparison.shipment_id}.json`,{stage:'applied',comparison:confirmedEvent.comparison,receipt:confirmedEvent.receipt})}>Export confirmed event JSON</button><button className="text-button" onClick={() => setConfirmedEvent(undefined)}>Dismiss confirmed receipt</button></div></aside>}
        {!network && <div className="empty-state"><Radio size={30} /><h2>Connecting to the local backend</h2><p>Run <code>python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000</code>.</p><button onClick={() => load()}>Retry connection</button></div>}
        {view === 'brief' && <ProjectBrief onNavigate={navigate} />}
        {network && view === 'command' && <>
          <DeliveryOutlook network={network} onInspectShipment={id => { setSelectedId(id); jump('command-trip-detail'); }} onNavigate={navigate} onReviewPlans={() => jump('command-scenarios')} onCompareShipmentRoad={compareShipmentRoad} onReloadNetwork={load} />
          <div className="stats-grid"><Stat label="NETWORK SHIPMENTS" value={network.shipments.length} note={`${network.nodes.filter(n => n.kind === 'destination').length} destinations · all simulated`} icon={<Truck size={20} />} /><Stat label="COLD-CHAIN REVIEW" value={excursions.length} note="Simulated cargo excursions > 4°C" icon={<Snowflake size={20} />} alert /><Stat label="APPROVED ASSIGNMENTS" value={assignments.length} note={`${assignments.filter(s => s.acknowledged).length} acknowledged by simulated drivers`} icon={<ClipboardCheck size={20} />} /><Stat label="PUBLIC ENDPOINT PROBES" value={`${totalSuccessful}/${coverage.length}`} note="HTTP success; data coverage differs" icon={<Radio size={20} />} /></div>
          <div className="operations-grid"><section className="panel map-panel" id="command-network-map" tabIndex={-1}><div className="panel-heading"><div><h2>Distribution network</h2><span>20 fictional locations across Missouri</span></div><span className="pill green"><i className="live-dot" /> Seed {network.seed}</span></div><div className="command-map-controls"><label>Show allocation on map<select aria-label="Map allocation" value={mapPlan} onChange={event => setMapPlan(event.target.value)}><option value="candidates">All {network.shipments.length} candidate shipments</option><option value="approved">Current approved assignments ({assignments.length})</option>{scenarios.map(row => <option key={row.scenario} value={row.scenario}>Scenario {row.scenario}: {row.shipments.length} proposed trips</option>)}</select></label><p>Allocation links show which candidates a plan selects. Request a road route separately to see road geometry.</p></div><NetworkMap selectedAlternative={selectedAlternative} planOverlay={mapOverlay} network={network} facilities={facilities} weather={evidence.nws_alerts} roads={evidence.modot} route={route} selected={selected} onSelect={setSelectedId} /><div className="map-footer"><MapPin size={14} /><span>OpenStreetMap base map · internet required for tiles</span><span>Real source layers + explicitly simulated entities</span></div></section>
          <section className="panel review-panel" id="command-review-queue" tabIndex={-1}><div className="panel-heading"><div><h2>Review queue</h2><span>Evidence prompts a human decision</span></div><span className="count-badge">{reviewAlerts.length}</span></div><div className="review-list">{reviewAlerts.slice(0, 5).map((a, i) => <div className="review-item" key={i}><span className={`review-icon ${a.color}`}><TriangleAlert size={16} /></span><div><strong>{a.title}</strong><p>{a.body}</p><span className="tiny">{a.title.startsWith('NWS') ? 'Official dated evidence' : 'SIMULATED · OPERATIONAL REVIEW'}</span><button className="text-button command-review-action" onClick={() => { if ('shipmentId' in a && a.shipmentId) { setSelectedId(a.shipmentId); jump('command-trip-detail'); } else if ('target' in a && a.target) setView(a.target); }}>{'shipmentId' in a ? `Inspect ${a.shipmentId}` : 'target' in a && a.target === 'dispatch' ? 'Open lot review' : 'Inspect official evidence'}<ArrowRight size={13} /></button></div></div>)}</div><div className="queue-footnote"><ShieldCheck size={16} /> Predictive scores never impose a mandatory hold.</div></section></div>
          <div className="detail-grid"><section className="panel" id="command-trip-detail" tabIndex={-1}><div className="panel-heading"><div><h2>Cold-chain & trip detail</h2><span>Simulated cargo temperature</span></div><select aria-label="Select shipment" value={selected?.id} disabled={busy} onChange={e => setSelectedId(e.target.value)}>{network.shipments.map(s => <option key={s.id}>{s.id}</option>)}</select></div>{selected && <><div className="trip-summary"><div><small>CANDIDATE TRUCK</small><strong>{selected.truck_id}</strong></div><div><small>DESTINATION</small><strong>{selected.destination}</strong></div><div><small>CARGO</small><strong>{selected.quantity_kg} kg</strong></div><div><small>TEMPERATURE</small><strong className={selected.temperature_c > 4 ? 'text-amber' : ''}>{selected.temperature_c}°C</strong></div></div><p className="command-context-badge">{approvedSelected ? `Approved assignment exists for ${selected.id}: truck ${approvedSelected.truck_id}, lot ${approvedSelected.lot_id}. Candidate lot shown below: ${selected.lot_id}.` : `${selected.id} is a candidate trip. It has no current approved driver assignment.`}</p><div className="chart"><ResponsiveContainer width="100%" height={155}><AreaChart data={telemetry}><defs><linearGradient id="temperatureFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#d4a04c" stopOpacity={.25} /><stop offset="100%" stopColor="#d4a04c" stopOpacity={0} /></linearGradient></defs><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="time" tick={{ fontSize: 10 }} minTickGap={30} /><YAxis tick={{ fontSize: 10 }} unit="°" domain={[0, 12]} /><Tooltip /><Area type="monotone" dataKey="temperature" stroke="#bb8738" strokeWidth={2} fill="url(#temperatureFill)" /></AreaChart></ResponsiveContainer></div><p className="command-chart-note">Chart: seeded historical simulation trace. The current reading above may include an injected event; the chart is not a live sensor stream.</p><button className="secondary small" disabled={busy} onClick={() => {setFreshnessShipmentId(selected.id);setView('freshness');}}>Model this lot’s shelf life<ArrowRight size={14}/></button><div className="route-detail"><div><Route size={16} /><span>{fixed(selected.estimated_hours, 1)}h estimated · {Math.round(selected.estimated_distance_km)} km<br /><small>OD estimate: haversine × 1.25 at 65 km/h</small></span></div><button className="secondary small" disabled={busy} onClick={() => void computeRoute()}>{routeLoading ? 'Finding road route…' : 'Request road route'} <ArrowRight size={14} /></button></div>{routeError && <p role="alert" className="feedback error">{routeError}</p>}<p className="source-note">{route ? route.fallback ? 'A labeled estimated fallback is shown for this candidate.' : 'A requested road comparison is shown for this candidate.' : 'No road route has been requested for this candidate yet. Dashed links are estimated connections.'} Driving profile does not validate commercial vehicle restrictions or current MoDOT closures. No truck-safe claim.</p></>}</section>
          <section className="panel"><div className="panel-heading"><div><h2>Weather exposure</h2><span>Columbia, Missouri · forecast, not cargo readings</span></div><CloudSun size={22} className="muted-icon" /></div>{forecastData.length ? <><div className="weather-summary"><strong>{forecastData[0]?.temperature ?? '—'}<span>°C</span></strong><div>First forecast timestep<br /><small>{forecast?.time?.[0]?.replace('T', ' ')} · America/Chicago</small></div></div><div className="chart"><ResponsiveContainer width="100%" height={135}><AreaChart data={forecastData}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="time" minTickGap={55} tick={{ fontSize: 10 }} /><YAxis unit="°" tick={{ fontSize: 10 }} /><Tooltip /><Area dataKey="temperature" stroke="#5f8b80" fill="#eaf2ed" strokeWidth={2} /></AreaChart></ResponsiveContainer></div></> : <div className="empty-inline">Forecast unavailable. Refresh the source in Evidence.</div>}<SourceStamp evidence={evidence.openmeteo} /><div className="coverage-warning"><TriangleAlert size={14} /> Historical NOAA station coverage is audited in Sources & evidence. No validated weather-to-FSIS model join is established.</div></section></div>
          {routeLoading && <p role="status" className="command-loading">Finding a road route for {selected?.id}. An estimated fallback will be clearly labeled if the routing service is unavailable.</p>}
          {route && <CommandRouteReview route={route} selected={selected} selectedAlternative={selectedAlternative} onSelect={setSelectedAlternative} onShowMap={() => jump('command-network-map')} />}
          <section className="panel scenario-panel" id="command-scenarios" tabIndex={-1}><div className="panel-heading"><div><div className="eyebrow">HUMAN-IN-THE-LOOP RESPONSE</div><h2>Compare operational scenarios</h2><span>One-wave OR-Tools allocation · simulated costs and demand · hard safety constraints</span></div><button className="secondary small" disabled={busy} onClick={() => void refreshApplication()}><RefreshCw size={14} /> {busy ? 'Working…' : 'Recompute'}</button></div><div className="table-scroll"><table><thead><tr><th>Response scenario</th><th>Logistics cost</th><th>Unmet demand</th><th>Delays</th><th>Waste*</th><th>Affected</th><th>Review</th><th>Violations</th><th>Solver</th><th>Inspect result</th></tr></thead><tbody>{scenarios.map(s => <tr key={s.scenario}><td><span className="scenario-letter">{s.scenario}</span><strong>{s.name}</strong></td><td>${formatNumber(s.total_logistics_cost)}</td><td>{formatNumber(s.unmet_demand_kg)} kg</td><td>{s.delayed_shipments}</td><td>{s.food_waste_kg} kg</td><td>{s.affected_shipments}</td><td>{s.review_priority_count}</td><td>{s.constraint_violations ?? '—'}</td><td><span className={`pill ${s.feasible ? 'green' : 'red'}`}>{s.solver_status}</span></td><td><button className="text-button" disabled={busy || !s.feasible} aria-label={`Review scenario ${s.scenario}`} onClick={() => { setActor(''); setReason(''); setApprovalError(''); void act(async () => setProposal(await api<Scenario>(`/proposals/${s.scenario}`, {})), 'Proposal prepared for review.'); }}>Review <ArrowRight size={14} /></button><button className="text-button" aria-label={`Show scenario ${s.scenario} allocation on map`} onClick={() => { setMapPlan(s.scenario); jump('command-network-map'); }}>Show on map<MapPin size={13} /></button></td></tr>)}</tbody></table></div>{recomputeError && <p role="alert" className="feedback error">{recomputeError}</p>}<div className="command-inline-status" role="status">{lastRecompute ? `Last computation ${lastRecompute.time} CT · revision ${lastRecompute.revision} · ${lastRecompute.count} response plans. ${lastRecompute.same ? 'Totals and selected trips match the previous run; nothing was approved.' : 'Updated comparison produced; review it before approval.'}` : `Computed response plans for network revision ${network.revision}. Review opens the proposed assignments; Show on map only changes the display.`}</div><div className="scenario-note">*No expiry during the six-hour planning horizon; unsent stock remains inventory. Scenario C proposes holds for approval. D substitutes eligible simulated lots; alternative road routes require separate review.</div></section>
          <EventImpactPanel onConfirmed={(receipt, comparison) => setConfirmedEvent({receipt, comparison})} network={network} selected={selected} disabled={busy} onBusyChange={setActionBusy} onApplied={async () => { const refreshed = await load(); if (!refreshed?.okay) throw new Error('Network refresh incomplete'); setNotice('Simulated event applied. Recomputed plans are ready; no new assignment was approved.'); }} onCompare={() => jump('command-scenarios')} />
          <div className="command-result-actions"><button className="secondary" disabled={busy} onClick={() => { setResetError(''); setResetOpen(true); }}>Reset demo</button><span>Restores the seeded network and clears approved assignments after confirmation.</span></div>
        </>}
        {view === 'routes' && <RouteLab />}
        {view === 'freshness' && <FreshnessLab initialShipmentId={freshnessShipmentId} onNetworkChanged={async () => { await load(); }} onOpenDrive={trip => {setDriverTrip(trip);navigate('drive');}} />}
        {view === 'roads' && <RoadIntelligence onNavigate={navigate} initialJourney={roadJourney} currentNetworkRevision={network?.revision} />}
        {view === 'assistant' && <EvidenceAssistant onNavigate={navigate} initialShipmentId={selected?.id} />}
        {view === 'dispatch' && <DispatcherDesk onNavigate={navigate} onChange={async () => { await load(); }} />}
        {network && view === 'command' && <ScenarioDetails scenarios={scenarios} />}
        {view === 'science' && <ModelTimingCard />}
        {view === 'science' && <ModelErrorAnalysis model={model} />}
        {view === 'evidence' && <>
          <FoodAccessContext />
          <DataExplorer />
          <NOAACoverageCard />
          <section className="panel"><div className="panel-heading"><div><h2>Source-specific ingestion</h2><span>CDC surveillance and outbreak evidence remain separate from FSIS sampling outcomes</span></div></div><div className="table-scroll"><table><thead><tr><th>Supplied export</th><th>Evidence layer</th><th>Rows ingested</th><th>Validation</th></tr></thead><tbody>{evidenceSummary.map((s, i) => <tr key={i}><td className="wrap-cell">{s.file}</td><td>{s.source ?? 'Unrecognized'}</td><td>{s.rows == null ? '—' : formatNumber(s.rows)}</td><td className="wrap-cell">{ingestionNote(s)}</td></tr>)}</tbody></table></div></section>
          <div className="evidence-grid">{Object.entries(evidenceNames).map(([key, title]) => <section className="panel source-card" key={key}><div className="source-card-top"><Database size={21} /><span className={`pill ${evidence[key]?.payload && !evidence[key]?.stale ? 'green' : 'amber'}`}>{evidence[key]?.stale ? 'Stale response - review age' : evidence[key]?.payload ? 'Dated response available' : 'Coverage gap'}</span></div><h2>{title}</h2><p>{evidenceKinds[key]}</p><SourceStamp evidence={evidence[key]} /><p className="source-note">{evidence[key]?.coverage_warning ?? (key === 'ncei_historical' ? 'This dated station probe is separate from the bounded multi-station coverage audit above. No validated joining to FSIS observations.' : key === 'fsis_recalls' ? 'Official notices are displayed separately. Simulated lots lack real traceability fields for verified recall matching.' : 'Cached source evidence may be stale. Read timestamps before operational use.')}</p><div className="source-actions">{evidence[key]?.source_url && <a href={evidence[key].source_url} target="_blank" rel="noreferrer">Open official response <ArrowRight size={13} /></a>}<button className="text-button" disabled={busy || offlineRehearsal} title={offlineRehearsal ? "Live refresh is disabled in this offline rehearsal" : "Check this public source"} onClick={() => refreshSource(key, title)}><RefreshCw size={13} /> Refresh</button></div></section>)}</div>
          <section className="panel"><div className="panel-heading"><div><h2>Official recall notices</h2><span>No asserted match to simulated lots or shipments</span></div><SourceStamp evidence={evidence.fsis_recalls} /></div>{evidence.fsis_recalls?.truncated && <p className="source-note padded">Showing a bounded preview of the first {evidence.fsis_recalls.returned_records} of {evidence.fsis_recalls.total_records} provider records in provider order; the list below displays six. The full response remains available at the official source.</p>}{recalls.length ? <div className="recall-list">{recalls.slice(0, 6).map((r, i) => <div key={i}><span className="recall-index">{String(i + 1).padStart(2, '0')}</span><div><strong dangerouslySetInnerHTML={undefined}>{String(r.title ?? r.field_title ?? r.recall_title ?? r.name ?? 'Official FSIS recall notice').replace(/<[^>]*>/g, '')}</strong><p>{String(r.field_recall_date ?? r.recall_date ?? r.date ?? r.field_recall_number ?? 'See official response for date and affected products')}</p>{(r.url || r.field_recall_url) && <a href={r.url ?? r.field_recall_url} target="_blank" rel="noreferrer">Read official notice</a>}</div></div>)}</div> : <div className="empty-inline">Recall response unavailable or schema unrecognized. See the dated raw response in the source card.</div>}</section>
          <section className="panel"><div className="panel-heading"><div><h2>Connectivity evidence</h2><span>Catalog reachability is distinct from validated data ingestion</span></div><a className="download-link" href="/api/coverage" target="_blank" rel="noreferrer"><ArrowDownToLine size={15} /> JSON evidence</a></div><div className="table-scroll"><table><thead><tr><th>Source</th><th>Test status</th><th>HTTP</th><th>Latency</th><th>Content type</th><th>Last probe / failure</th></tr></thead><tbody>{coverage.map(c => <tr key={c.id}><td><strong>{c.id}</strong></td><td><span className={`pill ${c.success ? 'green' : 'red'}`}>{c.success ? 'HTTP success' : 'Failed'}</span></td><td>{c.http_status ?? '—'}</td><td>{c.latency_ms}ms</td><td>{c.content_type || '—'}</td><td className="wrap-cell">{c.failure ?? c.tested_at}</td></tr>)}</tbody></table></div></section>
          <section className="panel"><div className="panel-heading"><div><h2>Supplied data inventory</h2><span>Raw files preserved unchanged · {inventory.files?.length ?? 0} files inventoried</span></div><a className="download-link" href="/api/inventory" target="_blank" rel="noreferrer"><ArrowDownToLine size={15} /> Full inventory</a></div><div className="table-scroll"><table><thead><tr><th>File</th><th>Size</th><th>Likely source</th><th>Read status</th></tr></thead><tbody>{inventory.files?.map((f: any) => <tr key={f.path}><td className="wrap-cell">{f.filename}</td><td>{fixed(f.size_bytes / 1048576, 1)} MB</td><td>{f.likely_source}</td><td>{f.errors?.length ? f.errors.join('; ') : f.duplicate_of ? 'Duplicate detected' : 'Inspected'}</td></tr>)}</tbody></table></div><p className="source-note padded">CDC BEAM human surveillance, NORS historical outbreaks, and FSIS sampling remain separate evidence layers. Unrecognized files are inventoried without merging.</p></section>
        </>}
        {view === 'science' && <section className="science-view"><div className="coverage-warning large"><TriangleAlert size={19} /><div><strong>{model.status}</strong><p>{model.feature_availability ?? 'Run scripts/ingest_fsis.py and scripts/train_model.py to obtain measured evaluation.'}</p></div></div><div className="stats-grid"><Stat label="TRAINING SAMPLES" value={formatNumber(model.training_rows)} note={`Training ends ${model.training_end?.slice(0, 10) ?? '—'}`} icon={<Database size={20} />} /><Stat label="VALIDATION SAMPLES" value={formatNumber(model.validation_rows)} note={`${model.validation_start?.slice(0, 10) ?? '—'} → ${model.validation_end?.slice(0, 10) ?? '—'}`} icon={<ClipboardCheck size={20} />} /><Stat label="BASELINE BRIER" value={fixed(model.baseline?.brier)} note="Lower is better · measured holdout loss" icon={<Activity size={20} />} /><Stat label="LOGISTIC BRIER" value={fixed(model.logistic_regression?.brier)} note="90-day temporal embargo" icon={<Gauge size={20} />} /></div><section className="panel"><div className="panel-heading"><div><h2>Chronological holdout comparison</h2><span>{model.target}</span></div></div><div className="table-scroll"><table><thead><tr><th>Estimator</th><th>Brier</th><th>95% week-block CI</th><th>PR-AUC (AP)</th><th>ROC-AUC</th><th>Precision @ 0.5</th><th>Recall @ 0.5</th></tr></thead><tbody>{[['Historical prevalence', model.baseline], ['Logistic regression', model.logistic_regression]].map(([name, metric]: any) => <tr key={name}><td><strong>{name}</strong></td><td>{fixed(metric?.brier)}</td><td>{metric?.brier_week_block_bootstrap_95_ci?.map((n: number) => fixed(n)).join('–') ?? '—'}</td><td>{fixed(metric?.pr_auc_average_precision)}</td><td>{fixed(metric?.roc_auc)}</td><td>{fixed(metric?.precision_at_0_5)}</td><td>{fixed(metric?.recall_at_0_5)}</td></tr>)}</tbody></table></div></section><div className="detail-grid"><section className="panel"><div className="panel-heading"><div><h2>Calibration</h2><span>Predicted and observed selected-sample positivity</span></div></div><div className="chart"><ResponsiveContainer width="100%" height={260}><LineChart data={model.logistic_regression?.calibration.predicted.map((p, i) => ({ predicted: p, observed: model.logistic_regression!.calibration.observed[i], ideal: p })) ?? []}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="predicted" tickFormatter={n => fixed(n, 2)} /><YAxis tickFormatter={n => fixed(n, 2)} /><Tooltip /><Line dataKey="ideal" stroke="#c1c9c3" strokeDasharray="5 5" dot={false} /><Line dataKey="observed" stroke="#226c56" strokeWidth={2} /></LineChart></ResponsiveContainer></div></section><section className="panel science-notes"><h2>Interpretation & limitations</h2><p><strong>Operational selection:</strong> {model.operational_selection ?? 'Not established'}</p><ul>{model.limitations?.map(l => <li key={l}>{l}</li>)}</ul><h3>Feature coefficients</h3>{Object.entries(model.coefficients ?? {}).map(([k, v]) => <div className="coefficient" key={k}><code>{k}</code><span>{fixed(v)}</span></div>)}<p className="source-note">Coefficients describe fitted associations. They do not establish causes or regulatory findings.</p></section></div></section>}
        {network && view === 'drive' && <DriverWorkspace initialTruckId={driverTrip?.truckId} initialShipmentId={driverTrip?.shipmentId} network={network} onChanged={async () => { await load(); }} />}
        {!driverOnly && <footer className="page-footer"><ShieldCheck size={14} /><span>AEGIS · NAFSI SENSD Student Data Challenge</span><span>Simulation is explicit. Evidence is traceable. Decisions require people.</span></footer>}
      </div>
    </main>
    {resetOpen && <div className="modal-backdrop"><section role="dialog" aria-modal="true" aria-labelledby="reset-title" className="approval-modal"><h2 id="reset-title">Reset the simulated network?</h2><p>This restores the deterministic seed, clears all {assignments.length} approved assignments and advances the network revision. Existing proposals become stale. Raw data and public evidence stay unchanged.</p>{resetError && <p role="alert" className="feedback error">Reset did not complete: {resetError}</p>}<div className="modal-actions"><button className="secondary" disabled={busy} onClick={() => setResetOpen(false)}>Keep current network</button><button disabled={busy} onClick={() => void act(async () => { await api('/demo/reset', {}); setResetOpen(false); setRoute(undefined); setLastRecompute(undefined); }, 'Demo reset to deterministic initial state.', false, true)}>Confirm reset simulation</button></div></section></div>}
    {proposal && <div className="modal-backdrop"><section role="dialog" aria-modal="true" aria-labelledby="approval-title" className="approval-modal"><button className="modal-close icon-button" aria-label="Close proposal" disabled={busy} onClick={() => setProposal(undefined)}><X size={20} /></button><span className="eyebrow">DISPATCHER DECISION</span><h2 id="approval-title">Review scenario {proposal.scenario}</h2><p>{proposal.name} · {proposal.shipments.length} proposed assignments</p><div className="approval-facts"><div><small>LOGISTICS COST</small><strong>${formatNumber(proposal.total_logistics_cost)}</strong></div><div><small>UNMET DEMAND</small><strong>{proposal.unmet_demand_kg} kg</strong></div><div><small>SAFETY VIOLATIONS</small><strong>{proposal.constraint_violations}</strong></div></div><p>{proposal.proposed_hold_lots.length ? `Approval places precautionary holds on: ${proposal.proposed_hold_lots.join(', ')}.` : 'No new lot holds proposed.'}</p><p className="source-note">{proposal.limitations}</p><details className="command-proposed-trips"><summary>Inspect {proposal.shipments.length} proposed assignments and lots</summary><div className="table-scroll"><table><thead><tr><th>Trip</th><th>Truck</th><th>Lot</th><th>Destination</th><th>Load</th></tr></thead><tbody>{proposal.shipments.map(trip => <tr key={trip.id}><td>{trip.id}</td><td>{trip.truck_id}</td><td>{trip.lot_id}{network?.shipments.find(row => row.id === trip.id)?.lot_id !== trip.lot_id ? ' · substituted' : ''}</td><td>{trip.destination}</td><td>{trip.quantity_kg} kg</td></tr>)}</tbody></table></div></details>{approvalError && <p role="alert" className="feedback error command-approval-error">Approval did not complete: {approvalError}</p>}<label className="field">Dispatcher name<input value={actor} onChange={e => setActor(e.target.value)} placeholder="Your name" /></label><label className="field">Reason for approval<textarea rows={3} value={reason} onChange={e => setReason(e.target.value)} placeholder="Record the evidence and operational rationale…" /></label><div className="coverage-warning"><ShieldCheck size={17} /> Approval updates simulated driver assignments and creates an audit entry. Safety constraints are rechecked against the current network revision.</div><div className="modal-actions"><button className="secondary" disabled={busy} onClick={() => setProposal(undefined)}>Keep under review</button><button disabled={busy || actor.trim().length < 2 || reason.trim().length < 5} onClick={() => act(async () => { await api(`/proposals/${proposal.id}/approve`, { actor, reason }); setProposal(undefined); setReason(''); }, 'Scenario approved. Driver assignments updated and audit recorded.', true)}><Check size={16} /> {busy ? 'Publishing approved plan…' : 'Approve simulated plan'}</button></div></section></div>}
  </div>;
}
