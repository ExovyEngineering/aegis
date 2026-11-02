import { useState } from 'react';
import { formatNumber } from './api';
import type { Scenario } from './types';

export default function ScenarioDetails({ scenarios }: { scenarios: Scenario[] }) {
  const [choice, setChoice] = useState('A');
  const [tab, setTab] = useState('resources');
  const scenario = scenarios.find(s => s.scenario === choice);
  const baseline = scenarios.find(s => s.scenario === 'A');
  const review = scenario?.review;
  if (!scenario || !review) return null;
  return <section className="panel scenario-details" aria-label="Scenario decision details"><div className="panel-heading"><div><h2>Look inside the decision</h2><span>Selected shipments, exclusions, resource use and independent constraint checks</span></div><label className="field">Inspect scenario<select aria-label="Inspect scenario" value={choice} onChange={e => setChoice(e.target.value)}>{scenarios.map(s => <option key={s.scenario} value={s.scenario}>{s.scenario} · {s.name}</option>)}</select></label></div>
    <div className="padded"><p><strong>{review.passed ? 'Independent checks passed' : 'Independent checks failed'}.</strong> {review.method}</p>{baseline && <p>Compared with baseline A: simulated cost change <strong>${formatNumber(scenario.total_logistics_cost - baseline.total_logistics_cost)}</strong>; unmet demand change <strong>{formatNumber(scenario.unmet_demand_kg - baseline.unmet_demand_kg)} kg</strong>. Lower cost can reflect fewer deliveries.</p>}
    <div className="planning-actions">{['resources', 'shipments', 'exclusions'].map(t => <button className={tab === t ? '' : 'secondary'} key={t} aria-pressed={tab === t} onClick={() => setTab(t)}>{t === 'resources' ? 'Resource utilization' : t === 'shipments' ? 'Proposed shipments' : 'Excluded candidates'}</button>)}</div>
    {tab === 'resources' && <div className="table-scroll"><table><thead><tr><th>Resource</th><th>ID</th><th>Planned</th><th>Limit / demand</th><th>Remaining / unmet</th></tr></thead><tbody>{review.resources.map(r => <tr key={r.kind+r.id}><td>{r.kind}</td><td>{r.id}</td><td>{r.used_kg} kg</td><td>{r.limit_kg} kg</td><td>{r.remaining_kg} kg</td></tr>)}</tbody></table></div>}
    {tab === 'shipments' && <div className="table-scroll"><table><thead><tr><th>Shipment / lot</th><th>Truck</th><th>Origin → destination</th><th>Load</th><th>Verification</th></tr></thead><tbody>{scenario.shipments.map(s => <tr key={s.id}><td>{s.id} / {s.lot_id}</td><td>{s.truck_id}</td><td>{s.origin} → {s.destination}</td><td>{s.quantity_kg} kg</td><td>{s.verification_required ? 'required before onward movement' : 'routine review'}</td></tr>)}</tbody></table></div>}
    {tab === 'exclusions' && <><p className="source-note">{review.exclusion_note}</p><div className="table-scroll"><table><thead><tr><th>Candidate</th><th>Destination / quantity</th><th>Reason</th></tr></thead><tbody>{review.excluded_shipments.map(s => <tr key={s.shipment_id}><td>{s.shipment_id}</td><td>{s.destination} / {s.quantity_kg} kg</td><td className="wrap-cell">{s.reasons.join('; ')}</td></tr>)}</tbody></table></div></>}
    {!!review.violations.length && <p role="alert">{review.violations.join('; ')}</p>}<p className="source-note">All quantities, commercial relationships and costs are simulated. Proposed scenario C holds need explicit approval. Unsent stock is not automatically food waste.</p></div></section>;
}
