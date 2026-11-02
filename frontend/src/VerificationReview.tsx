import { useEffect, useState } from 'react';
import { api } from './api';
import type { Shipment } from './types';
const labels = {temperature_history_reviewed: 'Reviewed simulated temperature history', packaging_condition_reviewed: 'Reviewed packaging-condition scenario', simulated_lot_identity_reviewed: 'Reviewed simulated lot identity and assignment'};
const emptyChecks = () => ({temperature_history_reviewed:false, packaging_condition_reviewed:false, simulated_lot_identity_reviewed:false});
export function VerificationStatus({ shipment }: { shipment: Shipment }) {
  if (!shipment.verification_required) return null;
  return <div className="coverage-warning"><div><strong>Targeted verification: {shipment.verification_status === 'complete' ? 'review complete' : shipment.verification_status === 'review_required' ? 'further review required' : 'pending dispatcher review'}</strong><p>{shipment.verification_status === 'complete' ? 'A dispatcher recorded the scenario review. This is not product-safety certification or an official recall clearance.' : 'Do not treat assignment acknowledgment as verification or permission for onward movement. Contact the dispatcher while parked.'}</p>{shipment.verification_review && <p className="source-note">{shipment.verification_review.actor} · {shipment.verification_review.reason} · review v{shipment.verification_version}</p>}</div></div>;
}
export default function VerificationReview({ assignments, revision, actor, reason, onSaved }: {assignments: Shipment[]; revision: number; actor: string; reason: string; onSaved: () => Promise<void>}) {
  const required = assignments.filter(s => s.verification_required);
  const [sid, setSid] = useState('');
  const selected = required.find(s => s.id === sid) ?? required[0];
  const [checks, setChecks] = useState(emptyChecks);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => { setChecks(emptyChecks()); }, [selected?.id, selected?.verification_version, revision]);
  async function save(outcome: string) { if (!selected) return; setBusy(true); setError(''); try { await api(`/dispatch/assignments/${selected.id}/verification`, {actor, reason, expected_network_revision:revision, expected_verification_version:selected.verification_version ?? 0, outcome, checks}); await onSaved(); } catch(e) { setError(String(e)); await onSaved().catch(() => {}); } finally { setBusy(false); } }
  const identified = actor.trim().length >= 2 && reason.trim().length >= 5;
  return <section className="panel"><div className="panel-heading"><div><h2>Targeted verification review</h2><span>Record the review requested by scenario B</span></div></div><div className="editor-body">{!selected ? <p>No currently approved trip requests targeted verification. Scenario B can propose this requirement for simulated excursions.</p> : <><label className="field">Trip requiring verification<select aria-label="Trip requiring verification" value={selected.id} onChange={e => setSid(e.target.value)}>{required.map(s => <option key={s.id}>{s.id}</option>)}</select></label><VerificationStatus shipment={selected} />{Object.entries(labels).map(([key,label]) => <label className="lab-checkbox" key={key}><input type="checkbox" checked={checks[key as keyof typeof checks]} onChange={e => setChecks({...checks,[key]:e.target.checked})} /><span>{label}</span></label>)}<div className="planning-actions"><button disabled={busy || !identified || !Object.values(checks).every(Boolean)} onClick={() => save('complete')}>Record verification review complete</button><button className="secondary" disabled={busy || !identified} onClick={() => save('review_required')}>Record further review required</button></div><p className="source-note">Uses the decision identity and reason at left. This records a simulated checklist, not laboratory testing or verified product traceability. A further-review outcome does not automatically hold stock; use explicit human lot controls if needed.</p></>}{error && <p role="alert" className="feedback error">{error}</p>}</div></section>;
}
