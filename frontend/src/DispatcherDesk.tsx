import VerificationReview from './VerificationReview';
import DispatchReadiness from './DispatchReadiness';
import { useCallback, useEffect, useRef, useState } from 'react';
import { ClipboardCheck, MessageSquare, RefreshCw, ShieldCheck, TriangleAlert } from 'lucide-react';
import { api } from './api';
import type { Shipment } from './types';

interface DispatchIncident { id: string; shipment_id: string; description: string; status: 'open' | 'in_review' | 'resolved'; version: number; reported_at: string; reported_network_revision?: number; reporting_assignment?: { lot_id?: string; truck_id?: string; origin?: string; destination?: string }; review?: { actor?: string; reason?: string; timestamp?: string } }
interface DispatchLot { id: string; held: boolean; recalled: boolean; eligible: boolean; inventory_kg: number }
interface DispatchSnapshot { network_revision: number; lots: DispatchLot[]; incidents: DispatchIncident[]; assignments: Shipment[] }

export default function DispatcherDesk({ onChange }: { onChange?: () => Promise<void> }) {
  const [snapshot, setSnapshot] = useState<DispatchSnapshot>();
  const [actor, setActor] = useState('');
  const [reason, setReason] = useState('');
  const [instruction, setInstruction] = useState('');
  const [assignmentId, setAssignmentId] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const loadEpoch = useRef(0);
  const load = useCallback(async () => {
    const epoch = ++loadEpoch.current;
    try {
      const data = await api<DispatchSnapshot>('/dispatch');
      if (epoch !== loadEpoch.current) return;
      if (!Array.isArray(data.assignments) || !Array.isArray(data.lots) || !Array.isArray(data.incidents)) throw new Error('Dispatcher snapshot is incomplete. Refresh before acting.');
      setSnapshot(data); setError('');
      setAssignmentId(previous => data.assignments.some(a => a.id === previous) ? previous : data.assignments[0]?.id ?? '');
    } catch(e) {
      if (epoch !== loadEpoch.current) return;
      setSnapshot(undefined); setAssignmentId('');
      setError(e instanceof Error ? e.message : String(e));
      throw e;
    }
  }, []);
  useEffect(() => { load().catch(() => {}); const timer = window.setInterval(() => { load().catch(() => {}); }, 15000); return () => { loadEpoch.current++; window.clearInterval(timer); }; }, [load]);
  const identified = !!snapshot && actor.trim().length >= 2 && reason.trim().length >= 5;
  const selectedAssignment = snapshot?.assignments.find(a => a.id === assignmentId);
  async function act(path: string, body: unknown, success: string) {
    setBusy(true); setError(''); setNotice('');
    try { await api(path, body); await load(); await onChange?.(); setNotice(success); }
    catch (e) { await load().catch(() => {}); setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }
  return <section className="dispatcher-desk" aria-label="Dispatcher desk">
    <div className="lab-intro"><span className="lab-intro-icon"><ClipboardCheck size={23} /></span><div><strong>Close the loop with the people in the field.</strong><p>Review driver reports, approve lot holds and issue versioned instructions to already approved assignments. Every decision records an identity and reason.</p></div><span className="pill amber">SIMULATED OPERATIONS</span></div>
    {error && <div role="alert" className="feedback error"><TriangleAlert size={18} />{error} <button className="text-button" onClick={() => load().catch(e => setError(String(e)))}>Refresh desk</button></div>}
    {notice && <div role="status" className="feedback success"><ShieldCheck size={18} />{notice}</div>}
    <div className="dispatch-layout">
      <aside className="panel dispatch-identity"><div className="eyebrow">HUMAN REVIEW</div><h2>Decision record</h2><p className="source-note">Complete these fields before changing a hold, reviewing a report or sending an instruction. Identity is self-declared in this local demonstrator.</p><label className="field">Reviewing dispatcher<input autoComplete="name" value={actor} maxLength={100} onChange={e => setActor(e.target.value)} placeholder="Dispatcher name" /></label><label className="field">Decision reason<textarea value={reason} maxLength={1000} rows={4} onChange={e => setReason(e.target.value)} placeholder="Record the evidence and decision rationale" /></label><div className="coverage-warning"><ShieldCheck size={16} /><span>Predictive scores do not create mandatory holds. Recalled or held lots remain excluded from dispatch.</span></div><p className="source-note">Network revision: {snapshot?.network_revision ?? '—'}. The desk checks for new driver reports every 15 seconds. Stale decisions are rejected and the current state is reloaded.</p><button className="secondary" disabled={busy} onClick={() => load().catch(e => setError(String(e)))}><RefreshCw size={14} /> Refresh desk</button></aside>
      <div className="dispatch-panels">
        {snapshot && <DispatchReadiness networkRevision={snapshot.network_revision} refreshKey={snapshot.assignments.map(a => `${a.id}:${a.acknowledged}:${a.instruction_revision}:${a.instruction_acknowledged}:${a.verification_version}`).join('|')} />}
        <VerificationReview assignments={snapshot?.assignments ?? []} revision={snapshot?.network_revision ?? 0} actor={actor} reason={reason} onSaved={async () => { await load(); await onChange?.(); }} />
        <section className="panel"><div className="panel-heading"><div><h2>Driver incident inbox</h2><span>Reports are operational evidence, not verified food-safety findings</span></div><span className="count-badge">{snapshot?.incidents.filter(i => i.status !== 'resolved').length ?? 0}</span></div>
          {!snapshot?.incidents.length ? <div className="empty-inline"><MessageSquare size={24} /><h3>No reports in the current inbox</h3><p>Approved trips can submit an incident from AEGIS Drive. Earlier audit-only reports remain in the audit trail.</p></div> : <div className="dispatch-incidents">{snapshot.incidents.map(incident => <article className="dispatch-incident" key={incident.id}><div className="dispatch-incident-title"><strong>{incident.shipment_id}</strong><span className={`pill ${incident.status === 'resolved' ? 'green' : 'amber'}`}>{incident.status.replaceAll('_', ' ')}</span></div><p>{incident.description}</p><small>Reported {new Date(incident.reported_at).toLocaleString('en-US', { timeZone: 'America/Chicago' })} CT · review version {incident.version}</small>{incident.review?.reason && <p className="source-note">Latest review: {incident.review.actor} · {incident.review.reason}</p>}<div className="dispatch-actions"><button className="secondary small" disabled={busy || !identified || incident.status !== 'open'} onClick={() => act(`/dispatch/incidents/${incident.id}/review`, { actor, reason, status: 'in_review', expected_version: incident.version }, `${incident.shipment_id} incident is under review.`)}>Start review</button><button className="small" disabled={busy || !identified || incident.status === 'resolved'} onClick={() => act(`/dispatch/incidents/${incident.id}/review`, { actor, reason, status: 'resolved', expected_version: incident.version }, `${incident.shipment_id} incident resolved with an audit record.`)}>Resolve report</button></div></article>)}</div>}
        </section>
        <section className="panel"><div className="panel-heading"><div><h2>Lot hold controls</h2><span>Only an explicit dispatcher decision changes a precautionary hold</span></div></div><div className="table-scroll"><table><thead><tr><th>Lot</th><th>Inventory</th><th>Current status</th><th>Human response</th></tr></thead><tbody>{snapshot?.lots.map(lot => <tr key={lot.id}><td><strong>{lot.id}</strong></td><td>{lot.inventory_kg} kg</td><td><span className={`pill ${lot.recalled || lot.held ? 'amber' : 'green'}`}>{lot.recalled ? 'Recalled — blocked' : lot.held ? 'Held — blocked' : lot.eligible ? 'Eligible' : 'Ineligible'}</span></td><td><button className={lot.held ? 'secondary small' : 'small'} aria-label={`${lot.held ? 'Release hold on' : 'Place hold on'} ${lot.id}`} disabled={busy || !identified || lot.recalled} onClick={() => act(`/dispatch/lots/${lot.id}/${lot.held ? 'release' : 'hold'}`, { actor, reason, expected_network_revision: snapshot.network_revision }, lot.held ? `${lot.id} hold released. Regenerate and approve a plan before dispatch.` : `${lot.id} held. Affected assignments were removed and earlier proposals require review.`)}>{lot.held ? 'Release hold' : 'Place hold'}</button></td></tr>)}</tbody></table></div><p className="source-note padded">A hold removes affected approved assignments. Releasing a hold does not recreate assignments or override a recall. Review and approve a fresh scenario before rescheduling.</p></section>
        <section className="panel dispatch-instructions"><div className="panel-heading"><div><h2>Dispatcher-approved instructions</h2><span>Send a recorded message to an already approved simulated trip</span></div></div><div className="editor-body">{!snapshot?.assignments.length ? <div className="empty-inline"><h3>No approved trips available</h3><p>Approve a response scenario in Command before sending trip instructions.</p></div> : <><label className="field">Approved trip for instruction<select value={assignmentId} onChange={e => setAssignmentId(e.target.value)}>{snapshot.assignments.map(a => <option key={a.id} value={a.id}>{a.id} · {a.truck_id} → {a.destination}</option>)}</select></label>{selectedAssignment && <div className="dispatch-current-instruction"><strong>Current instruction</strong><p>{selectedAssignment.instruction}</p><span className="source-stamp">Version {selectedAssignment.instruction_revision ?? 0} · {selectedAssignment.instruction_revision ? selectedAssignment.instruction_acknowledged ? 'Driver acknowledged' : 'Driver acknowledgment pending' : 'Initial assignment instruction'}</span></div>}<label className="field">New dispatcher instruction<textarea rows={3} maxLength={2000} value={instruction} onChange={e => setInstruction(e.target.value)} placeholder="Write concise instructions for review while parked" /></label><button disabled={busy || !identified || instruction.trim().length < 3 || !selectedAssignment} onClick={() => act(`/dispatch/assignments/${assignmentId}/instruction`, { actor, reason, instruction, expected_instruction_revision: selectedAssignment?.instruction_revision ?? 0, expected_network_revision: snapshot.network_revision }, 'Instruction approved and published. The driver must acknowledge this version.')}><MessageSquare size={15} /> Approve and send instruction</button><p className="source-note">This sends text within the simulated app; it does not change the route, inventory, eligibility or lot disposition. New versions require their own driver acknowledgment.</p></>}</div></section>
      </div>
    </div>
  </section>;
}
