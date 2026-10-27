import { useCallback, useEffect, useRef, useState } from 'react';
import { ClipboardCheck, RefreshCw, TriangleAlert } from 'lucide-react';
import { api } from './api';

type Status = 'blocked' | 'review_required' | 'ready_for_review';
interface Check { id: string; label: string; category: 'hard_constraint' | 'workflow'; status: 'pass' | 'blocked' | 'review_required'; detail: string }
interface AssignmentReview { shipment_id: string; truck_id: string; lot_id: string; status: Status; checks: Check[]; blockers: string[]; reviews_required: string[] }
interface Readiness { network_revision: number; checked_at: string; summary: {total_assignments: number; blocked: number; review_required: number; ready_for_review: number}; assignments: AssignmentReview[]; limitations: string[] }
const labels = { blocked: 'Blocked by a constraint', review_required: 'Review outstanding', ready_for_review: 'Listed checks passed' };

export default function DispatchReadiness({ networkRevision, refreshKey = '' }: {networkRevision: number; refreshKey?: string}) {
  const [snapshot, setSnapshot] = useState<Readiness>();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [filter, setFilter] = useState<Status | 'all'>('all');
  const [selected, setSelected] = useState('');
  const epoch = useRef(0);
  const load = useCallback(async () => {
    const request = ++epoch.current;
    setBusy(true);
    try {
      const result = await api<Readiness>('/readiness');
      if (request !== epoch.current) return;
      if (!Array.isArray(result.assignments) || !result.summary) throw new Error('Readiness checks are unavailable. Refresh before reviewing.');
      setSnapshot(result); setError('');
    } catch(e) {
      if (request !== epoch.current) return;
      setSnapshot(undefined); setError(e instanceof Error ? e.message : String(e));
    } finally { if (request === epoch.current) setBusy(false); }
  }, []);
  useEffect(() => { setSnapshot(undefined); load(); const timer = window.setInterval(load, 15000); return () => { epoch.current++; window.clearInterval(timer); }; }, [load, networkRevision, refreshKey]);
  const current = snapshot?.network_revision === networkRevision ? snapshot : undefined;
  const rows = current?.assignments.filter(row => filter === 'all' || row.status === filter) ?? [];
  const chosen = rows.find(row => row.shipment_id === selected) ?? rows[0];
  return <section className="panel readiness-panel" aria-label="Dispatch readiness review">
    <div className="panel-heading"><div><h2>Dispatch readiness review</h2><span>Constraint checks and outstanding acknowledgments for approved simulated trips</span></div><button className="secondary small" disabled={busy} onClick={load}><RefreshCw size={14} />Refresh readiness</button></div>
    <div className="padded">
      {error && <p role="alert" className="feedback error"><TriangleAlert size={16} />{error}</p>}
      {snapshot && !current && <p role="alert" className="coverage-warning">Network changed between the desk and checklist. Refresh the desk and readiness before relying on these checks.</p>}
      {busy && !current && !error && <p role="status">Checking the approved assignments…</p>}
      {current && <>
        <div className="readiness-counts"><div><strong>{current.summary.total_assignments}</strong><span>Approved trips</span></div><div><strong>{current.summary.blocked}</strong><span>Constraint blocks</span></div><div><strong>{current.summary.review_required}</strong><span>Review outstanding</span></div><div><strong>{current.summary.ready_for_review}</strong><span>Listed checks passed</span></div></div>
        {current.assignments.length > 0 ? <>
          <div className="planning-actions"><label className="field">Readiness status<select aria-label="Readiness status" value={filter} onChange={e => setFilter(e.target.value as Status | 'all')}><option value="all">All approved trips</option>{Object.entries(labels).map(([value,label]) => <option key={value} value={value}>{label}</option>)}</select></label><label className="field">Trip to inspect<select aria-label="Trip readiness" value={chosen?.shipment_id ?? ''} onChange={e => setSelected(e.target.value)}>{rows.length ? rows.map(row => <option key={row.shipment_id} value={row.shipment_id}>{row.shipment_id} · {row.truck_id} · {labels[row.status]}</option>) : <option value="">No trips match this status</option>}</select></label></div>
          {chosen ? <div className="readiness-detail"><p><ClipboardCheck size={17} /><strong>{chosen.shipment_id} · {chosen.truck_id} · lot {chosen.lot_id}</strong><span className={`pill ${chosen.status === 'ready_for_review' ? 'green' : 'amber'}`}>{labels[chosen.status]}</span></p><div className="table-scroll"><table><thead><tr><th>Check</th><th>Result</th><th>Evidence</th></tr></thead><tbody>{chosen.checks.map(check => <tr key={check.id}><td><strong>{check.label}</strong><small className="source-note">{check.category === 'hard_constraint' ? 'Hard eligibility / resource check' : 'Operational workflow'}</small></td><td><span className={`pill ${check.status === 'pass' ? 'green' : 'amber'}`}>{check.status.replaceAll('_',' ')}</span></td><td className="wrap-cell">{check.detail}</td></tr>)}</tbody></table></div></div> : <p>No approved trips match this status.</p>}
        </> : <p>No approved trips to inspect. Review and approve a scenario in Command first.</p>}
        <p className="source-note">Checked {new Date(current.checked_at).toLocaleString('en-US',{timeZone:'America/Chicago'})} CT · network revision {current.network_revision}. This read-only checklist does not dispatch, certify food safety, or validate a commercial-truck route.</p>
        <details><summary>Scope of these checks</summary><ul>{current.limitations.map((limit,i) => <li key={i}>{limit}</li>)}</ul></details>
      </>}
    </div>
  </section>;
}
