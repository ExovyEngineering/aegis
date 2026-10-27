import { useCallback, useEffect, useRef, useState } from 'react';
import { ArrowRight, Check, Fuel, LockKeyhole, MapPin, MessageSquare, Navigation, RefreshCw, ShieldCheck, Snowflake, Truck, TriangleAlert } from 'lucide-react';
import { api, fixed } from './api';
import type { Network, Shipment } from './types';
import DriverInstruction from './DriverInstruction';
import DriverExposure from './DriverExposure';
import { VerificationStatus } from './VerificationReview';

interface Focus { mode: 'locked' | 'driving' | 'parked'; version: number; parked_until: string | null; interaction_allowed: boolean; provenance: string }
interface DriveSnapshot { truck_id: string; network_revision: number; focus: Focus; assignments: Shipment[]; vehicle: {fuel_percent: number; fuel_liters: number; tank_capacity_liters: number; estimated_range_km: number; consumption_l_per_100km: number; coordinates: number[]; position_label: string; observed_at: string; provenance: string; simulation: boolean}; events: {type: string; shipment_id: string}[]; limitations?: string[] }

export default function DriverWorkspace({ network, onChanged }: {network: Network; onChanged: () => Promise<void>}) {
  const [truckId, setTruckId] = useState('T01');
  const [shipmentId, setShipmentId] = useState('');
  const [snapshot, setSnapshot] = useState<DriveSnapshot>();
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [healthy, setHealthy] = useState(false);
  const [panel, setPanel] = useState<'none' | 'route' | 'report' | 'instructions'>('none');
  const [description, setDescription] = useState('');
  const [clock, setClock] = useState(Date.now());
  const generation = useRef(0);
  const load = useCallback(async () => {
    const epoch = ++generation.current;
    try {
      const response = await api<DriveSnapshot>(`/drive/${truckId}`);
      if (epoch !== generation.current) return;
      if (!response?.focus || !Array.isArray(response.assignments)) throw new Error('Driver snapshot is incomplete. Refresh before interacting.');
      setSnapshot(response); setHealthy(true);
    } catch(e) {
      if (epoch !== generation.current) return;
      setSnapshot(undefined); setHealthy(false); setError(e instanceof Error ? e.message : String(e));
    }
  }, [truckId]);
  useEffect(() => { setSnapshot(undefined); setHealthy(false); setPanel('none'); setDescription(''); setError(''); load(); const timer = window.setInterval(load, 15000); return () => { generation.current++; window.clearInterval(timer); }; }, [load]);
  useEffect(() => { const timer = window.setInterval(() => setClock(Date.now()), 1000); return () => window.clearInterval(timer); }, []);
  const parkedUntil = snapshot?.focus.parked_until ? Date.parse(snapshot.focus.parked_until) : 0;
  const parked = healthy && !!snapshot?.focus.interaction_allowed && snapshot.focus.mode === 'parked' && parkedUntil > clock;
  useEffect(() => { if (!parked) { setPanel('none'); setDescription(''); } }, [parked]);
  const current = snapshot?.assignments.find(s => s.id === shipmentId) ?? snapshot?.assignments[0];
  const destination = network.nodes.find(n => n.id === current?.destination);
  const origin = network.nodes.find(n => n.id === current?.origin);
  const vehicle = snapshot?.vehicle;
  const minutesLeft = Math.min(10, Math.max(0, Math.ceil((parkedUntil - clock) / 60000)));
  async function action(fn: () => Promise<unknown>, success: string, notifyParent = true) {
    setBusy(true); setError(''); setNotice('');
    try { await fn(); await load(); if (notifyParent) await onChanged(); setNotice(success); }
    catch(e) { await load(); setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }
  const focus = (mode: 'parked' | 'driving') => action(() => api(`/drive/${truckId}/focus`, {mode, expected_version:snapshot?.focus.version ?? 0, parked_confirmation:mode === 'parked'}), mode === 'parked' ? 'Parked-use controls enabled temporarily. Lock them before moving.' : 'Read-only focus enabled. Reporting and acknowledgments are locked.', false);
  const quickReport = (kind: string) => current && action(() => api(`/drive/${truckId}/quick-report`, {shipment_id:current.id,kind,expected_network_revision:snapshot?.network_revision}), 'Incident submitted for dispatcher review. This did not send an emergency call or change your route.');
  return <section className={`drive-workspace ${parked ? 'is-parked' : 'is-locked'}`} aria-label="AEGIS Drive workspace">
    <header className="drive-header"><div className="drive-wordmark"><ShieldCheck size={27} /><div>AEGIS <strong>DRIVE</strong><small>SIMULATED DRIVER WORKSPACE</small></div></div><span className={`drive-mode ${parked ? 'parked' : ''}`}><i />{parked ? 'PARKED USE' : 'READ-ONLY FOCUS'}</span></header>
    {error && <div role="alert" className="drive-feedback error"><TriangleAlert size={18} />{error}<button disabled={busy} onClick={() => { setError(''); load(); }}>Retry driver data</button></div>}
    {notice && <p role="status" className="drive-feedback">{notice}</p>}
    <div className="drive-focus-bar"><LockKeyhole size={22} /><div><strong>{parked ? `Parked confirmation · up to ${minutesLeft} min remaining` : 'Eyes on the road. Controls are locked.'}</strong><p>{parked ? 'Use only while safely parked. Lock before moving; confirmation expires automatically.' : 'No typing, reports or acknowledgments until you confirm you are safely parked.'}</p></div><button disabled={busy || !snapshot} onClick={() => focus(parked ? 'driving' : 'parked')}>{parked ? 'Lock for driving' : 'Confirm safely parked'}</button></div>
    <div className="drive-hero-grid"><section className="drive-destination"><div className="drive-section-label"><Navigation size={17} />{current ? 'CURRENT ASSIGNED DESTINATION' : 'AWAITING DISPATCHER ASSIGNMENT'}<span>{truckId}</span></div><h2>{current ? destination?.name ?? current.destination : 'Ready for a reviewed plan'}</h2><p>{current ? `${current.id} · lot ${current.lot_id} · ${current.quantity_kg} kg simulated cargo` : 'A dispatcher must approve a scenario before a trip appears. No route or load is invented here.'}</p><div className="drive-travel"><div><strong>{current ? fixed(current.estimated_hours,1) : '—'}<span> h</span></strong><small>PLANNED TRAVEL FROM ORIGIN</small></div><div><strong>{current ? fixed(current.estimated_distance_km,0) : '—'}<span> km</span></strong><small>ESTIMATED DISTANCE</small></div></div><div className="drive-journey-strip"><span><i />{origin?.name ?? 'Dispatch origin'}</span><ArrowRight size={20} /><span><MapPin size={15} />{destination?.name ?? 'Destination pending'}</span></div><p className="drive-quiet">Dispatch plan, not live remaining ETA. No GPS progress or navigation is inferred.</p></section>
      <div className="drive-gauges"><section className="drive-gauge fuel"><div className="drive-section-label"><Fuel size={18} />FUEL SCENARIO</div><div className="drive-fuel-display"><svg viewBox="0 0 120 80" aria-hidden="true"><path d="M15 65 A45 45 0 0 1 105 65" pathLength="100" className="gauge-track" /><path d="M15 65 A45 45 0 0 1 105 65" pathLength="100" className="gauge-value" strokeDasharray={`${vehicle?.fuel_percent ?? 0} 100`} /></svg><strong>{vehicle ? Math.round(vehicle.fuel_percent) : '—'}<span>%</span></strong></div><p>{vehicle ? `${fixed(vehicle.fuel_liters,0)} / ${vehicle.tank_capacity_liters} L · ${fixed(vehicle.estimated_range_km,0)} km assumed range` : 'Vehicle snapshot unavailable'}</p><small>DETERMINISTIC SIMULATION · NO FUEL SENSOR</small></section>
      <section className={`drive-gauge cargo ${current && current.temperature_c > 4 ? 'cargo-review' : ''}`}><div className="drive-section-label"><Snowflake size={18} />CARGO TEMPERATURE</div><strong className="drive-temperature">{current ? fixed(current.temperature_c,1) : '—'}<span>°C</span></strong><p>{current ? current.temperature_c > 4 ? 'Simulated excursion · dispatcher review' : 'Simulated cargo reading' : 'No approved cargo assignment'}</p><small>{current ? 'DEMO REVIEW LEVEL > 4°C · NOT PRODUCT DISPOSITION' : 'TELEMETRY IS SIMULATED'}</small></section></div></div>
    <div className="drive-status-strip"><span><Check size={17} />{current ? 'Dispatcher approved' : 'No approved assignments'}</span><span className={current?.acknowledged ? 'done' : ''}><Check size={17} />{current?.acknowledged ? 'Assignment acknowledged' : 'Acknowledgment pending'}</span><span><ShieldCheck size={17} />{current?.verification_required ? current.verification_status === 'complete' ? 'Verification review complete' : 'Verification review pending' : 'Routine review'}</span></div>
    <div className="drive-location"><MapPin size={17} /><div><strong>{vehicle?.position_label ?? 'Position unavailable'}</strong><p>{vehicle ? `Scenario snapshot ${new Date(vehicle.observed_at).toLocaleString()} · ${vehicle.coordinates.map(n => fixed(n,4)).join(', ')} (longitude, latitude)` : 'No successful driver snapshot captured.'}</p></div><span>SIMULATED POSITION · NOT LIVE GPS</span></div>
    <div className="drive-primary-actions"><button disabled={!parked || !current || busy} onClick={() => setPanel(panel === 'route' ? 'none' : 'route')}><Navigation size={22} />Trip route<span>Review alternatives while parked</span></button><button disabled={!parked || !current || busy} onClick={() => setPanel(panel === 'instructions' ? 'none' : 'instructions')}><MessageSquare size={22} />Dispatch instructions<span>{current?.instruction_revision && !current.instruction_acknowledged ? 'New version to acknowledge' : 'Approved trip and acknowledgments'}</span></button><button disabled={!parked || !current || busy} onClick={() => setPanel(panel === 'report' ? 'none' : 'report')}><TriangleAlert size={22} />Report an issue<span>Recorded in the dispatcher inbox</span></button></div>
    {parked && <section className="drive-parked-tools"><div className="drive-selector-row"><label className="field">Simulated driver truck<select aria-label="Simulated driver truck" value={truckId} disabled={busy} onChange={e => { if (e.target.value === truckId) return; setHealthy(false); setSnapshot(undefined); setTruckId(e.target.value); setShipmentId(''); }}>{network.trucks.map(t => <option key={t.id}>{t.id}</option>)}</select></label>{snapshot && snapshot.assignments.length > 1 && <label className="field">Trip for advisories and incident reporting<select aria-label="Trip for advisories and incident reporting" value={current?.id} disabled={busy} onChange={e => { setShipmentId(e.target.value); setPanel('none'); setDescription(''); }}>{snapshot.assignments.map(s => <option key={s.id} value={s.id}>{s.id} → {s.destination}</option>)}</select></label>}<button className="secondary" disabled={busy} onClick={() => load()}><RefreshCw size={16} /> Refresh driver data</button></div><p>Each demo vehicle has its own expiring parked confirmation; changing vehicles reloads that vehicle's focus status. This is a local demonstration, not authenticated driver identity.</p></section>}
    {parked && current && panel === 'instructions' && <section className="panel drive-detail-panel"><div className="panel-heading"><div><h2>Dispatcher-approved trip instructions</h2><span>{current.id} · {truckId} · lot {current.lot_id}</span></div></div><div className="padded"><p className="driver-instruction">{current.instruction}</p><DriverInstruction shipment={current} onAcknowledged={async () => { await load(); await onChanged(); }} /><VerificationStatus shipment={current} /><button disabled={busy || current.acknowledged} onClick={() => action(() => api(`/driver/${current.id}/acknowledge`,{expected_network_revision:snapshot?.network_revision}),`${current.id} assignment acknowledged.`)}><Check size={16} />{current.acknowledged ? 'Assignment acknowledged' : 'Acknowledge assignment'}</button><p className="source-note">Acknowledgment is not permission to disregard holds, verification requirements or road restrictions.</p></div></section>}
    {parked && current && panel === 'report' && <section className="panel drive-detail-panel"><div className="panel-heading"><div><h2>Report while safely parked</h2><span>Reporting for {current.id} · {truckId} · {current.destination}</span></div></div><div className="padded"><div className="drive-quick-reports">{[['refrigeration','Refrigeration concern'],['road_delay','Road delay'],['vehicle_issue','Vehicle issue'],['cargo_issue','Cargo concern']].map(([kind,label]) => <button key={kind} className="secondary" disabled={busy} onClick={() => quickReport(kind)}>{label}</button>)}</div><label className="field">Report a driver incident<textarea value={description} maxLength={2000} rows={3} onChange={e => setDescription(e.target.value)} placeholder="Optional detail, only while parked" /></label><button disabled={busy || description.trim().length < 5} onClick={() => action(async () => { await api('/driver/incident',{shipment_id:current.id,description,expected_network_revision:snapshot?.network_revision}); setDescription(''); },'Incident submitted for dispatcher review.')}><TriangleAlert size={16} />Send to dispatcher</button><p className="source-note">Quick reports create a simulated operational report for the dispatcher. They do not call emergency services, reroute the truck, or impose a lot hold.</p></div></section>}
    {parked && current && panel === 'route' && <DriverExposure key={`${truckId}-${current.id}`} shipment={current} network={{...network,revision:snapshot?.network_revision ?? network.revision}} disabled={!parked} />}
    {!!snapshot?.events.length && <section className="drive-advisories"><h3>Assigned-trip scenario advisories</h3>{snapshot.events.map((e,i) => <p key={i}><TriangleAlert size={16} />{e.shipment_id} · {e.type.replaceAll('_',' ')} · simulated event</p>)}</section>}
    {!current && snapshot && <p className="drive-empty">No approved assignments. Ask the dispatcher to review and approve a plan in Command.</p>}
    <footer className="drive-disclosure"><ShieldCheck size={17} /><p>This interface does not detect actual motion or verify that you are parked. Fuel, position and cargo values are simulated; no physical sensor is connected. Park safely before interacting. Road geometry and projections require dispatcher review.</p><a href="/?mode=drive">Open dedicated driver view</a></footer>
  </section>;
}
