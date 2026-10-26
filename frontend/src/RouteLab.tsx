import PlanningLibrary from './PlanningLibrary';
import { useEffect, useState } from 'react';
import { ArrowRight, FlaskConical, MapPin, Route, ShieldCheck, Snowflake, TriangleAlert, Truck } from 'lucide-react';
import { Area, AreaChart, CartesianGrid, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api, fixed, formatNumber } from './api';
import RouteLabMap from './RouteLabMap';
import { routingSourceLabels, type RoutingSources } from './routingProvenance';
import CustomOperationEditor, { customOperationErrors, newPlanningOperation, operationFromPreset, type CustomOperation } from './CustomOperationEditor';

export interface LabNode { id: string; name: string; kind: string; coordinates: [number, number]; demand_kg?: number }
export interface ColdChainResult { status?: string; max_temperature_c?: number; threshold_c?: number; time_above_threshold_minutes?: number; provenance?: string; assumptions?: string[]; projection?: { elapsed_minutes: number; temperature_c: number; lower_c: number; upper_c: number }[] }
export interface LabRoute extends RoutingSources { truck_id: string; origin_id: string; stop_ids: string[]; distance_m: number; duration_seconds: number; load_kg: number; capacity_kg?: number; geometry?: { type: string; coordinates: number[][] }; fallback?: boolean; provenance?: string; cold_chain?: ColdChainResult; road_review?: any; stops?: any[] }
interface Preset { id: string; name: string; description: string; origins: number; trucks: number; stops: number; simulation: boolean }
interface LabResult { run_id?: string; preset: { id: string; name: string; nodes: LabNode[]; stops?: { id: string; held?: boolean; recalled?: boolean; eligible?: boolean }[]; trucks: { id: string; capacity_kg: number }[] }; routes: LabRoute[]; solver_status: string; feasible: boolean; summary: { total_distance_m: number; total_duration_seconds: number; total_cost: number; unserved_stops: string[]; constraint_violations: number; served_demand_kg?: number; unmet_demand_kg?: number }; provenance: string; limitations: string[] | string; warnings?: string[] }
const defaultPresets: Preset[] = [
  { id: 'farm', name: 'Single farm dispatch', description: 'One simulated farm sending refrigerated trucks to nearby delivery stops.', origins: 1, trucks: 3, stops: 8, simulation: true },
  { id: 'regional', name: 'Multi-location fleet', description: 'A simulated regional fleet serving destinations from more than one dispatch location.', origins: 2, trucks: 8, stops: 15, simulation: true },
];

export default function RouteLab() {
  const [presets, setPresets] = useState(defaultPresets);
  const [templates, setTemplates] = useState<any[]>([]);
  const [customOperation, setCustomOperation] = useState<CustomOperation>(newPlanningOperation);
  const [preset, setPreset] = useState('farm');
  const [routing, setRouting] = useState('estimated');
  const [ambient, setAmbient] = useState(30);
  const [delay, setDelay] = useState(0);
  const [fault, setFault] = useState(false);
  const [truckCount, setTruckCount] = useState(3);
  const [capacity, setCapacity] = useState(1500);
  const [maxHours, setMaxHours] = useState(8);
  const [result, setResult] = useState<LabResult>();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [selectedTruck, setSelectedTruck] = useState('');
  const [changed, setChanged] = useState(false);
  useEffect(() => { api<any[]>('/operations/presets').then(data => { if (Array.isArray(data) && data.length) { setTemplates(data.filter(p => Array.isArray(p.origins) && Array.isArray(p.stops) && Array.isArray(p.trucks))); setPresets(data.map(p => ({ ...p, origins: Array.isArray(p.origins) ? p.origins.length : p.origins, trucks: Array.isArray(p.trucks) ? p.trucks.length : p.trucks, stops: Array.isArray(p.stops) ? p.stops.length : p.stops }))); } }).catch(() => {}); }, []);
  function change(fn: () => void) { fn(); setChanged(!!result); }
  async function run() {
    setBusy(true); setError('');
    try {
      const fleet = preset === 'custom' ? { custom_operation: customOperation } : { truck_count: truckCount, truck_capacity_kg: capacity };
      const output = await api<LabResult>('/route-lab', { preset, routing, ...fleet, max_route_hours: maxHours, refrigeration_fault: fault, ambient_temperature_c: ambient, delay_minutes: delay });
      setResult(output); setSelectedTruck(output.routes[0]?.truck_id ?? ''); setChanged(false);
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }
  const selected = result?.routes.find(route => route.truck_id === selectedTruck);
  const cold = selected?.cold_chain;
  const selectedPreset = presets.find(p => p.id === preset);
  const customErrors = preset === 'custom' ? customOperationErrors(customOperation) : [];
  const excludedStops = result?.preset.stops?.filter(stop => stop.held || stop.recalled || stop.eligible === false) ?? [];
  const limitations = result ? (Array.isArray(result.limitations) ? result.limitations : [result.limitations]) : [];
  return <section className="route-lab" aria-label="Route laboratory">
    <div className="lab-intro"><span className="lab-intro-icon"><FlaskConical size={23} /></span><div><strong>From one farm to a regional fleet.</strong><p>Test simulated dispatch plans, inspect truck routes, and explore how delays and refrigeration faults affect an illustrative cargo-temperature projection.</p></div><span className="pill amber">PLANNING SANDBOX</span></div>
    <PlanningLibrary runId={result?.run_id} changed={changed} onLoad={(request, output) => {
      setPreset(request.preset); if (request.custom_operation) setCustomOperation(request.custom_operation);
      setRouting(request.routing); setTruckCount(request.truck_count ?? 3); setCapacity(request.truck_capacity_kg ?? 1500);
      setMaxHours(request.max_route_hours); setAmbient(request.ambient_temperature_c); setDelay(request.delay_minutes); setFault(request.refrigeration_fault);
      setResult(output); setSelectedTruck(output.routes[0]?.truck_id ?? ''); setChanged(false);
    }} />
    <div className="lab-configuration">
      <section className="panel lab-controls"><div className="eyebrow">01 · DEFINE THE EXERCISE</div><h2>Operational scale</h2>
        <div className="preset-options">{presets.map(p => <button key={p.id} aria-pressed={preset === p.id} className={`preset-option ${preset === p.id ? 'selected' : ''}`} onClick={() => change(() => { setPreset(p.id); setTruckCount(p.trucks); })}><span className="preset-icon">{p.id === 'farm' ? <MapPin size={20} /> : <Truck size={20} />}</span><span><strong>{p.name}</strong><small>{p.description}</small></span></button>)}</div>
        <button aria-pressed={preset === 'custom'} className={`preset-option custom-preset ${preset === 'custom' ? 'selected' : ''}`} onClick={() => change(() => { if (preset !== 'custom') { const template = templates.find(p => p.id === preset); if (template) setCustomOperation(operationFromPreset(template)); } setPreset('custom'); })}><span className="preset-icon"><MapPin size={20} /></span><span><strong>Your operation</strong><small>Edit locations, stock, deliveries and individual trucks.</small></span></button>
        <div className="preset-facts"><span><strong>{preset === 'custom' ? customOperation.origins.length : selectedPreset?.origins ?? '—'}</strong> origins</span><span><strong>{preset === 'custom' ? customOperation.trucks.length : truckCount}</strong> trucks</span><span><strong>{preset === 'custom' ? customOperation.stops.length : selectedPreset?.stops ?? '—'}</strong> stops</span></div>
        {preset === 'custom' ? <p className="source-note">Set each truck’s origin and capacity in the operation editor. Changes remain planning inputs and do not dispatch trucks.</p> : <div className="lab-fleet-inputs"><label className="field">Available trucks<input type="number" min={1} max={10} value={truckCount} onChange={e => change(() => setTruckCount(Number(e.target.value)))} /></label><label className="field">Capacity per truck (kg)<input type="number" min={100} max={5000} step={100} value={capacity} onChange={e => change(() => setCapacity(Number(e.target.value)))} /></label></div>}<label className="field">Maximum route duration (hours)<input type="number" min={0.25} max={16} step={0.25} value={maxHours} onChange={e => change(() => setMaxHours(Number(e.target.value)))} /></label><label className="field">Travel-time source<select value={routing} onChange={e => change(() => setRouting(e.target.value))}><option value="estimated">Offline estimated travel</option><option value="osrm">Public OSRM road service</option></select></label>
        <p className="source-note">Estimated travel uses a documented distance factor. OSRM requests are cached and can fall back visibly. Neither source validates commercial truck restrictions.</p>
        <div className="lab-control-divider" /><div className="eyebrow">02 · STRESS THE PLAN</div>
        <label className="field">Ambient temperature assumption (°C)<input type="number" min={-30} max={55} step={1} value={ambient} onChange={e => change(() => setAmbient(Number(e.target.value)))} /></label>
        <label className="field">Additional road delay (minutes)<input type="number" min={0} max={360} step={15} value={delay} onChange={e => change(() => setDelay(Number(e.target.value)))} /></label>
        <label className="lab-checkbox"><input type="checkbox" checked={fault} onChange={e => change(() => setFault(e.target.checked))} /><span>Simulate refrigeration failure<small>A scenario assumption, not a live sensor diagnosis.</small></span></label>
        <button className="lab-run" disabled={busy || customErrors.length > 0 || (preset !== 'custom' && (truckCount < 1 || truckCount > 10 || capacity < 100 || capacity > 5000)) || maxHours < 0.25 || maxHours > 16 || ambient < -30 || ambient > 55 || delay < 0 || delay > 360} onClick={run}>{busy ? 'Computing dispatch plan…' : 'Test dispatch plan'}<ArrowRight size={16} /></button>
        <p className="source-note">This exercise does not create driver assignments or alter stock. Dispatch still requires the Command approval workflow.</p>
      </section>
      <div className="lab-results">
        {preset === 'custom' && <CustomOperationEditor value={customOperation} templates={templates} onChange={operation => change(() => setCustomOperation(operation))} />}
        {error && <div role="alert" className="feedback error"><TriangleAlert size={18} />{error}</div>}
        {changed && <div className="coverage-warning lab-change-warning"><TriangleAlert size={16} />Inputs changed. The results below describe the previous run; test the plan again to update them.</div>}
        {!result ? <section className="panel lab-empty"><Route size={36} /><h2>A route plan you can inspect.</h2><p>Select the scale of the operation, choose travel data, and run the test. Each truck’s stops, load, journey and temperature projection will appear here.</p><div><span>Capacity & timing constraints</span><span>Source provenance</span><span>No automatic dispatch</span></div></section> : <>
          <div className="lab-summary"><div><span>SOLVER STATUS</span><strong className={result.feasible ? 'text-green' : 'text-amber'}>{result.solver_status}</strong></div><div><span>TRAVEL DISTANCE</span><strong>{fixed(result.summary.total_distance_m / 1000, 1)}<small> km</small></strong></div><div><span>SIMULATED COST</span><strong>${formatNumber(result.summary.total_cost)}</strong></div><div><span>UNSERVED STOPS</span><strong>{result.summary.unserved_stops.length}</strong></div></div>
          <div className="coverage-warning lab-unserved"><TriangleAlert size={16} /><div><strong>{formatNumber(result.summary.unmet_demand_kg)} kg unmet demand</strong><p>Unserved stop IDs: {result.summary.unserved_stops.join(', ') || 'none'}.{excludedStops.length > 0 && <> Held/recalled/ineligible exclusions: {excludedStops.map(stop => `${stop.id} (${stop.recalled ? 'recalled' : stop.held ? 'held' : 'ineligible'})`).join(', ')}.</>}</p><p>Excluded or unserved deliveries remain unmet demand; they are not dispatched or assumed to be food waste.</p></div></div>
          <section className="panel lab-map-panel"><div className="panel-heading"><div><h2>{result.preset.name}</h2><span>{result.preset.id === 'custom' ? 'User-entered locations; trips, demand and safety flags are planning assumptions' : 'Fictional origins, trucks, deliveries and demand'}</span></div><span className="pill amber">SIMULATED LOGISTICS</span></div><RouteLabMap nodes={result.preset.nodes} routes={result.routes} /><p className="source-note padded">{result.provenance}</p></section>
          <section className="panel"><div className="panel-heading"><div><h2>Truck-by-truck plan</h2><span>Review loads, stops, timing and source before considering dispatch</span></div><span className={`pill ${result.summary.constraint_violations ? 'red' : 'green'}`}>{result.summary.constraint_violations} violations</span></div><div className="table-scroll"><table><thead><tr><th>Truck / origin</th><th>Stop sequence</th><th>Load</th><th>Journey</th><th>Travel source</th><th>Exposure / road review</th><th /></tr></thead><tbody>{result.routes.map(route => <tr key={route.truck_id}><td><strong>{route.truck_id}</strong><br />{route.origin_id}</td><td className="wrap-cell">{route.stop_ids.join(' → ') || 'No stops assigned'}</td><td>{route.load_kg} / {route.capacity_kg ?? '—'} kg</td><td>{fixed(route.distance_m / 1000, 1)} km<br />{Math.round(route.duration_seconds / 60)} min</td><td><span className={`pill ${route.fallback ? 'amber' : 'green'}`}>{routingSourceLabels(route).travel}</span><small className="source-note">{routingSourceLabels(route).detail}</small></td><td>{route.cold_chain?.status === 'review' ? <span className="pill amber">Review projection</span> : 'Inspect assumptions'}<div className="lab-road-count">{route.road_review?.alternatives?.length ? `${route.road_review.alternatives.reduce((count: number, item: any) => count + (item.nearby_events?.length ?? 0), 0)} nearby MoDOT geometries` : 'Road coverage unverified'}</div></td><td><button className="text-button" onClick={() => setSelectedTruck(route.truck_id)}>Inspect <ArrowRight size={13} /></button></td></tr>)}</tbody></table></div></section>
          {selected && <section className="panel lab-cold-chain"><div className="panel-heading"><div><div className="eyebrow">ILLUSTRATIVE PHYSICAL MODEL</div><h2>{selected.truck_id} · cold-chain exposure</h2><span>Projected cargo temperature, not observed telemetry or a validated food-safety forecast</span></div><Snowflake size={22} /></div>{cold ? <><div className="lab-cold-facts"><div><span>INITIAL CARGO</span><strong>{fixed(cold.projection?.[0]?.temperature_c, 1)}°C</strong></div><div><span>PROJECTED FINAL</span><strong>{fixed(cold.projection?.at(-1)?.temperature_c, 1)}°C</strong></div><div><span>TIME ABOVE REVIEW LEVEL</span><strong>{fixed(cold.time_above_threshold_minutes, 0)} min</strong></div></div>{!!cold.projection?.length && <div className="chart"><ResponsiveContainer width="100%" height={200}><AreaChart data={cold.projection?.map(point => ({ ...point, sensitivity: [point.lower_c, point.upper_c] }))}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="elapsed_minutes" unit=" min" tick={{ fontSize: 10 }} /><YAxis unit="°C" tick={{ fontSize: 10 }} /><Tooltip /><Area dataKey="sensitivity" name="Parameter sensitivity range" stroke="none" fill="#f0dfbc" /><Line type="monotone" dataKey="temperature_c" name="Illustrative cargo temperature" stroke="#ac7a34" strokeWidth={2} dot={false} /><ReferenceLine y={cold.threshold_c ?? 4} stroke="#a85f42" strokeDasharray="4 4" label="Review level" /></AreaChart></ResponsiveContainer></div>}<p className="source-note padded">{cold.provenance}. Shaded ranges show sensitivity to assumed thermal parameters; they are not confidence intervals.</p>{cold.assumptions?.length && <ul className="lab-assumptions">{cold.assumptions.map(a => <li key={a}>{a}</li>)}</ul>}</> : <p className="padded source-note">No cargo-temperature projection was returned for this route.</p>}<div className="coverage-warning"><ShieldCheck size={16} />A temperature projection prompts human review. It does not establish product safety, illness probability or an automatic hold.</div></section>}
          <section className="panel lab-limitations">{selected?.road_review && <div className="coverage-warning"><TriangleAlert size={15} /><div><strong>{selected.road_review.stale || !selected.road_review.coverage_complete ? 'Road coverage is stale or incomplete' : 'Independent road geometry screening'}</strong><p>{selected.road_review.warning}</p>{selected.road_review.modot_retrieved_at && <p>MoDOT retrieval: {new Date(selected.road_review.modot_retrieved_at).toLocaleString('en-US', { timeZone: 'America/Chicago' })} CT.</p>}</div></div>}<h2>What this run establishes</h2><ul>{limitations.map((limitation, i) => <li key={i}>{limitation}</li>)}</ul>{result.warnings?.map((warning, i) => <p key={i} className="coverage-warning"><TriangleAlert size={15} />{warning}</p>)}</section>
        </>}
      </div>
    </div>
  </section>;
}
