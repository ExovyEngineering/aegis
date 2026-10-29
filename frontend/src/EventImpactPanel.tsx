import { useEffect, useRef, useState } from 'react';
import { ArrowDownToLine, FlaskConical, RefreshCw } from 'lucide-react';
import { api } from './api';
import { downloadCaptured } from './CommandRouteReview';
import type { Network, Shipment } from './types';
import './CommandWorkflow.css';

const events = [
  ['road_closure', 'Road closure', 'Adds two hours to this candidate’s planning duration. It does not alter the road geometry or create an official incident.'],
  ['severe_weather', 'Severe weather', 'Adds a simulated two-hour planning delay. Public weather evidence and route geometry stay separate.'],
  ['delivery_delay', 'Delivery delay', 'Adds two hours to the planning duration and reduces the deadline margin.'],
  ['refrigeration_fault', 'Refrigeration fault', 'Sets this cargo reading to 9°C and makes its shared truck ineligible for allocation.'],
  ['temperature_excursion', 'Cargo temperature excursion', 'Sets the current simulated cargo reading to 9°C and raises review priority. This alone does not impose a hold.'],
  ['inventory_shortage', 'Inventory shortage', 'Sets the original shared lot’s available inventory to zero. Other candidates using that lot can be affected.'],
] as const;
const scenarioIds = ['A', 'B', 'C', 'D'];
const display = (value: unknown) => typeof value === 'boolean' ? (value ? 'Yes' : 'No') : String(value ?? 'Not recorded');
const signed = (value: number, unit = '') => `${value > 0 ? '+' : ''}${value.toLocaleString('en-US')}${unit}`;
const strings = (value: unknown) => Array.isArray(value) && value.every(item => typeof item === 'string');
function validPreview(value: any, event: string, shipment: string, revision: number) {
  return value?.simulation === true && value.read_only === true && value.operational_state_modified === false &&
    value.event === event && value.shipment_id === shipment && value.network_revision === revision &&
    /^[a-f0-9]{64}$/.test(value.preview_id) && typeof value.event_label === 'string' && value.shipment?.id === shipment && Array.isArray(value.shipment.changes) && value.shipment.changes.every((row: any) => typeof row?.field === 'string' && typeof row.label === 'string' && [row.before,row.after].every(item => ['string','number','boolean'].includes(typeof item)) && (row.delta === null || Number.isFinite(row.delta))) &&
    Array.isArray(value.scenarios) && value.scenarios.length === 4 && value.scenarios.every((row: any, index: number) =>
      row.scenario === scenarioIds[index] && row.before && row.after && row.delta &&
      ['total_logistics_cost', 'unmet_demand_kg', 'selected_shipments'].every(key =>
        Number.isFinite(row.before[key]) && Number.isFinite(row.after[key]) && Number.isFinite(row.delta[key])) &&
      strings(row.added_shipments) && strings(row.removed_shipments) && Array.isArray(row.lot_changes) && strings(row.proposed_hold_lots_added) && strings(row.proposed_hold_lots_removed) && typeof row.name === 'string' && typeof row.after.solver_status === 'string') &&
    Number.isInteger(value.assignments?.would_be_invalidated) && value.assignments.would_be_invalidated >= 0 &&
    value.route_effects?.geometry_changed === false && value.route_effects.stop_order_changed === false &&
    Array.isArray(value.resource_effects) && value.resource_effects.every((row: any) => typeof row?.kind === 'string' && typeof row.id === 'string' && typeof row.field === 'string' && strings(row.candidate_shipments)) && strings(value.limitations);
}

interface Props { network: Network; selected?: Shipment; disabled: boolean; onBusyChange: (value: boolean) => void; onApplied: () => Promise<unknown>; onCompare: () => void; onConfirmed?: (receipt: any, comparison: any) => void }
export default function EventImpactPanel({ network, selected, disabled, onBusyChange, onApplied, onCompare, onConfirmed }: Props) {
  const [event, setEvent] = useState('temperature_excursion');
  const [preview, setPreview] = useState<any>();
  const [applied, setApplied] = useState<any>();
  const [consent, setConsent] = useState(false);
  const [pending, setPending] = useState<'preview' | 'apply' | ''>('');
  const [error, setError] = useState('');
  const epoch = useRef(0); const locked = useRef(false); const mounted = useRef(true);
  const key = JSON.stringify([event, selected?.id, network.revision]);
  const current = useRef(key); current.current = key;
  useEffect(() => { setConsent(false); }, [key]);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; epoch.current++; }; }, []);
  const matches = !!preview && preview.event === event && preview.shipment_id === selected?.id && preview.network_revision === network.revision;
  async function produce() {
    if (disabled || locked.current || !selected) return;
    const requestKey = key; const token = ++epoch.current; locked.current = true; onBusyChange(true);
    setPending('preview'); setError(''); setConsent(false); setPreview(undefined); setApplied(undefined);
    try {
      const result = await api<any>('/events/preview', { event, shipment_id: selected.id, expected_network_revision: network.revision });
      if (!mounted.current || token !== epoch.current) return;
      if (current.current !== requestKey) { setError('The selection or network changed during calculation. No event was applied; produce a fresh preview for the current shipment.'); return; }
      if (!validPreview(result, event, selected.id, network.revision)) throw new Error('The event comparison did not match the requested simulation. Reload the network and preview again.');
      setPreview(result);
    } catch (reason) { if (mounted.current && token === epoch.current && current.current === requestKey) setError(reason instanceof Error ? reason.message : String(reason)); }
    finally { locked.current = false; onBusyChange(false); if (mounted.current) setPending(''); }
  }
  async function apply() {
    if (disabled || locked.current || !matches || !consent || !selected) return;
    locked.current = true; onBusyChange(true); setPending('apply'); setError('');
    try {
      const result = await api<any>('/events', { event, shipment_id: selected.id, expected_network_revision: preview.network_revision, preview_id: preview.preview_id });
      if (result?.operational_state_modified !== true || result.assignments_invalidated !== true || result.network_revision_before !== preview.network_revision || result.preview_id !== preview.preview_id || result.revision !== preview.network_revision + 1 || result.assignments_removed !== preview.assignments.would_be_invalidated) throw new Error('The server response could not verify this event receipt. Reload the network before taking another action.');
      if (mounted.current) { setApplied(result); setConsent(false); }
      onConfirmed?.(result, preview);
      try { await onApplied(); }
      catch { if (mounted.current) setError('The simulated event was applied, but the refreshed network could not be loaded completely. The confirmed receipt is preserved below. Reload application data before another action.'); }
    } catch (reason) { if (mounted.current) { setError(reason instanceof Error ? reason.message : String(reason)); setConsent(false); setPreview(undefined); } }
    finally { locked.current = false; onBusyChange(false); if (mounted.current) setPending(''); }
  }
  return <section className="panel event-impact-panel" aria-labelledby="event-impact-heading">
    <div className="panel-heading"><div><div className="eyebrow">SIMULATED WHAT-IF EXPERIMENT</div><h2 id="event-impact-heading">Preview a disruption before applying it</h2><span>Compute the effect on {selected?.id ?? 'a candidate shipment'}, shared resources and all four response plans.</span></div><FlaskConical size={23} /></div>
    <p className="command-explanation">First produce a read-only comparison. Apply it separately if you want to change the current simulation. Neither step creates a real incident or automatically reroutes a truck.</p>
    <div className="event-impact-controls"><label className="field">Event type<select aria-label="Event type" value={event} disabled={disabled || !!pending} onChange={change => setEvent(change.target.value)}>{events.map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label><button disabled={disabled || !!pending || !selected} onClick={() => void produce()}><RefreshCw size={15} />{pending === 'preview' ? 'Computing impact…' : 'Preview event impact'}</button></div>
    <p className="command-explanation">{events.find(([id]) => id === event)?.[2]}</p>
    {error && <p role="alert" className="feedback error">{error}</p>}
    {pending === 'preview' && <p role="status" className="command-inline-status">Computing the actual before/after simulation and four constrained allocation results. No event has been applied.</p>}
    {!preview && !pending && !error && <p className="event-impact-empty">No impact result yet. Choose an event and click <strong>Preview event impact</strong> to generate the comparison.</p>}
    {preview && <div className="event-impact-comparison">
      {applied ? <div role="status" className="event-impact-applied"><strong>Simulated event applied to {preview.shipment_id}.</strong> Network revision {applied.revision}; {applied.assignments_removed} approved assignments removed. The comparison below records the inputs used for that action. <button className="secondary small" disabled={disabled || !!pending} onClick={onCompare}>Compare refreshed response plans</button></div> : <div role="status" className="command-inline-status"><strong>Preview produced for {preview.shipment_id} · revision {preview.network_revision}.</strong> No event, hold or assignment has been changed.</div>}
      {!matches && !applied && <p className="coverage-warning">The selected event, shipment or network changed. This is an older comparison; produce a fresh preview before applying.</p>}
      <h3>{preview.event_label}: direct changes</h3>
      {preview.shipment.changes.length ? <div className="table-scroll"><table><thead><tr><th>Planning field</th><th>Before</th><th>After</th><th>Change</th></tr></thead><tbody>{preview.shipment.changes.map((row: any) => <tr key={row.field}><td>{row.label}{row.unit ? ` (${row.unit})` : ''}</td><td>{display(row.before)}</td><td>{display(row.after)}</td><td>{typeof row.delta === 'number' ? signed(row.delta) : 'State changed'}</td></tr>)}</tbody></table></div> : <p className="coverage-warning">These direct values are already at this event's modeled setting. Applying it would still record another event, advance the revision and clear every approved assignment.</p>}
      <p className="coverage-warning event-route-scope"><strong>Road geometry and stop order stay unchanged.</strong> {preview.route_effects.explanation}</p>
      <h3>Allocation outcomes: before → after</h3><p className="event-impact-details">These are newly computed one-wave solver results, not proposed or approved dispatches. Cost is simulated dollars. The same total can still involve different shipments or lots.</p>
      <div className="table-scroll"><table><thead><tr><th>Scenario</th><th>Selected trips</th><th>Logistics cost</th><th>Unmet demand</th><th>Solver after event</th><th>Changed trip choices</th></tr></thead><tbody>{preview.scenarios.map((row: any) => <tr key={row.scenario}><td><strong>{row.scenario}: {row.name}</strong></td><td>{row.before.selected_shipments} → {row.after.selected_shipments}</td><td>${row.before.total_logistics_cost.toLocaleString('en-US')} → ${row.after.total_logistics_cost.toLocaleString('en-US')}<br /><small>{signed(row.delta.total_logistics_cost)} simulated dollars</small></td><td>{row.before.unmet_demand_kg.toLocaleString('en-US')} → {row.after.unmet_demand_kg.toLocaleString('en-US')} kg<br /><small>{signed(row.delta.unmet_demand_kg, ' kg')}</small></td><td>{row.after.solver_status} · {row.after.constraint_violations ?? 'unavailable'} constraint violations</td><td>{row.added_shipments.length} added · {row.removed_shipments.length} removed · {row.lot_changes.length} lot changes</td></tr>)}</tbody></table></div>
      <details className="event-impact-details"><summary>Inspect changed shipments, resources and limitations</summary>{preview.resource_effects.map((row: any, index: number) => <p key={index}>{row.kind} {row.id}: {row.field} {display(row.before)} → {display(row.after)}. Shared candidates: {row.candidate_shipments.join(', ')}.</p>)}{preview.scenarios.map((row: any) => <p key={row.scenario}>Scenario {row.scenario}: added {row.added_shipments.join(', ') || 'none'}; removed {row.removed_shipments.join(', ') || 'none'}; lot substitutions {row.lot_changes.map((item: any) => JSON.stringify(item)).join('; ') || 'none'}. Proposed new holds: {row.proposed_hold_lots_added.join(', ') || 'none'}; removed proposed holds: {row.proposed_hold_lots_removed.join(', ') || 'none'}.</p>)}<ul>{preview.limitations.map((limit: string, index: number) => <li key={index}>{limit}</li>)}</ul><p>Preview SHA-256: <span className="checksum">{preview.preview_id}</span></p></details>
      {!applied && <><p className="coverage-warning">Applying this event will remove <strong>all {preview.assignments.would_be_invalidated} approved assignments</strong>, including unrelated trips. Holds and recall flags remain enforced. A fresh plan needs separate human approval.</p><label className="event-impact-consent"><input type="checkbox" checked={consent} disabled={!matches || disabled || !!pending} onChange={change => setConsent(change.target.checked)} />I intend to change this simulation and clear all approved assignments.</label><button disabled={!matches || !consent || disabled || !!pending} onClick={() => void apply()}>{pending === 'apply' ? 'Applying simulated event…' : 'Apply previewed event'}</button></>}
      <div className="command-result-actions"><button className="secondary small" onClick={() => downloadCaptured(`aegis-event-impact-${preview.shipment_id}.json`, { stage: applied ? 'applied' : 'preview', comparison: preview, receipt: applied ?? null })}><ArrowDownToLine size={14} /> Export event impact JSON</button><span>Captured {applied ? 'applied-event receipt' : 'read-only preview'}</span></div>
    </div>}
  </section>;
}
