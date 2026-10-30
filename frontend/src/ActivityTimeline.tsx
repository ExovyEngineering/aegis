import { useEffect, useRef, useState } from 'react';
import { ArrowDownToLine, ArrowRight, Clock3, RefreshCw, X } from 'lucide-react';
import { api } from './api';
import { downloadCaptured } from './CommandRouteReview';
import type { WorkspaceView } from './WorkspaceGuide';
import './ActivityTimeline.css';

interface ActivityRecord {
  id: number; timestamp: string | null; actor: string; action: string;
  action_label: string; summary: string; scope: string; payload: Record<string, unknown> | null;
  payload_error: string | null; payload_sha256: string | null; explicit_shipment_id: string | null;
  timestamp_raw?: string | null; metadata_errors?: string[]; payload_bytes?: number | null; payload_prefix_sha256?: string | null;
  suggested_view: WorkspaceView | null; citation: { label: string; path: string };
}
interface ActivityPage {
  available: boolean; records: ActivityRecord[]; actions: { id: string; label: string }[];
  snapshot_latest_id: number; snapshot_id: string; total_matching: number; next_cursor: string | null;
  read_only: true; operational_state_modified: false; generated_at: string; limitations: string[];
  filters: { action: string | null; shipment_id: string | null }; returned_records: number;
}
interface Filters { action: string; shipment: string }
interface Capture { filters: Filters; pages: ActivityPage[] }
interface Props {
  onNavigate?: (view: WorkspaceView) => void;
  onSelectShipment?: (id: string) => void;
  initialShipmentId?: string;
  onClose?: () => void;
}
const destinations: WorkspaceView[] = ['command', 'dispatch', 'drive', 'routes', 'brief'];
const viewNames: Partial<Record<WorkspaceView, string>> = { command: 'Command', dispatch: 'Dispatcher desk', drive: 'AEGIS Drive', routes: 'Route laboratory', brief: 'Project brief' };
const integer = (value: unknown, min = 0): value is number => typeof value === 'number' && Number.isSafeInteger(value) && value >= min;
const text = (value: unknown, max = 20000): value is string => typeof value === 'string' && value.length <= max;
const hash = (value: unknown) => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const nullableText = (value: unknown, max = 20000) => value === null || text(value, max);
const shipment = (value: unknown): value is string => typeof value === 'string' && /^[A-Za-z0-9_.-]{1,64}$/.test(value);
function recordValid(value: any): value is ActivityRecord {
  return value && integer(value.id, 1) && nullableText(value.timestamp, 300) && text(value.actor, 2048) && text(value.action, 2048)
    && text(value.action_label, 1000) && text(value.summary, 10000) && text(value.scope, 3000)
    && (value.payload === null || typeof value.payload === 'object' && !Array.isArray(value.payload))
    && nullableText(value.payload_error, 3000) && (value.payload_sha256 === null || hash(value.payload_sha256))
    && (value.timestamp_raw === undefined || nullableText(value.timestamp_raw, 3000))
    && (value.metadata_errors === undefined || Array.isArray(value.metadata_errors) && value.metadata_errors.length <= 20 && value.metadata_errors.every((item: unknown) => text(item, 3000)))
    && (value.payload_bytes === undefined || value.payload_bytes === null || integer(value.payload_bytes))
    && (value.payload_prefix_sha256 === undefined || value.payload_prefix_sha256 === null || hash(value.payload_prefix_sha256))
    && (value.explicit_shipment_id === null || shipment(value.explicit_shipment_id))
    && (value.suggested_view === null || destinations.includes(value.suggested_view))
    && value.citation && text(value.citation.label, 1000) && text(value.citation.path, 3000);
}
function pageValid(value: any): value is ActivityPage {
  if (!value || value.available !== true || value.read_only !== true || value.operational_state_modified !== false
    || !integer(value.snapshot_latest_id) || !hash(value.snapshot_id) || !integer(value.total_matching)
    || !Array.isArray(value.records) || value.records.length > 25 || !value.records.every(recordValid)
    || !Array.isArray(value.actions) || value.actions.length > 100 || !value.actions.every((row: any) => row && text(row.id, 100) && row.id.length > 0 && text(row.label, 1000))
    || new Set(value.actions.map((row: any) => row.id)).size !== value.actions.length
    || !nullableText(value.next_cursor, 4096) || value.next_cursor === '' || !text(value.generated_at, 300)
    || !integer(value.returned_records) || value.returned_records !== value.records.length
    || !value.filters || !nullableText(value.filters.action, 100) || !nullableText(value.filters.shipment_id, 64)
    || !Array.isArray(value.limitations) || value.limitations.length > 50 || !value.limitations.every((item: any) => text(item, 5000))) return false;
  if (value.total_matching < value.records.length || value.records.some((row: ActivityRecord, index: number) => row.id > value.snapshot_latest_id || index > 0 && row.id >= value.records[index - 1].id)) return false;
  return value.records.length > 0 || value.next_cursor === null;
}
function clock(value: string | null) {
  if (value === null) return 'Time not recorded';
  return /(?:Z|[+-]\d{2}:\d{2})$/i.test(value) && Number.isFinite(Date.parse(value))
    ? `${new Date(value).toLocaleString('en-US', { timeZone: 'America/Chicago' })} CT`
    : `Time not verified: ${value}`;
}
function payloadText(value: Record<string, unknown> | null) {
  try { const encoded = JSON.stringify(value, null, 2); return encoded.length <= 131072 ? encoded : 'Captured payload exceeds the client display limit.'; }
  catch { return 'Captured payload cannot be displayed as JSON.'; }
}

export default function ActivityTimeline({ onNavigate, onSelectShipment, initialShipmentId = '', onClose }: Props) {
  const [draftAction, setDraftAction] = useState('');
  const [draftShipment, setDraftShipment] = useState(initialShipmentId);
  const [capture, setCapture] = useState<Capture>();
  const [pending, setPending] = useState<'refresh' | 'older' | ''>('');
  const [error, setError] = useState('');
  const [paginationBlocked, setPaginationBlocked] = useState(false);
  const mounted = useRef(true); const lock = useRef(false); const requestId = useRef(0);
  const activeCapture = useRef(capture); activeCapture.current = capture;
  const pages = capture?.pages ?? []; const first = pages[0]; const last = pages[pages.length - 1];
  const records = pages.flatMap(page => page.records);
  const dirty = !!capture && (draftAction !== capture.filters.action || draftShipment.trim() !== capture.filters.shipment);
  const validShipment = draftShipment.trim() === '' || shipment(draftShipment.trim());
  async function load(filters: Filters, older = false) {
    if (lock.current) return;
    const prior = activeCapture.current;
    if (older && (!prior || !prior.pages[prior.pages.length - 1].next_cursor || paginationBlocked || prior.pages.length >= 10)) return;
    lock.current = true; const token = ++requestId.current; setPending(older ? 'older' : 'refresh'); setError('');
    const query = new URLSearchParams({ limit: '25' });
    if (filters.action) query.set('action', filters.action);
    if (filters.shipment) query.set('shipment_id', filters.shipment);
    if (older) query.set('cursor', prior!.pages[prior!.pages.length - 1].next_cursor!);
    try {
      const response = await api<unknown>(`/activity?${query.toString()}`);
      if (!mounted.current || token !== requestId.current) return;
      if (!pageValid(response)) throw new Error('The activity response did not match its bounded read-only contract. Refresh the history before relying on it.');
      if (response.filters.action !== (filters.action || null) || response.filters.shipment_id !== (filters.shipment || null)
        || response.records.some(row => filters.action && row.action !== filters.action || filters.shipment && row.explicit_shipment_id !== filters.shipment)) throw new Error('The activity response did not match the requested filters. Refresh the history before relying on it.');
      if (older) {
        const captured = prior!.pages[0];
        const previousRecords = prior!.pages.flatMap(page => page.records);
        if (response.snapshot_id !== captured.snapshot_id || response.snapshot_latest_id !== captured.snapshot_latest_id || response.total_matching !== captured.total_matching
          || response.records.some(row => previousRecords.some(previous => previous.id === row.id) || previousRecords.length > 0 && row.id >= previousRecords[previousRecords.length - 1].id)) throw new Error('Activity history changed or the page did not belong to the captured snapshot. Refresh before loading older records.');
        const loaded = previousRecords.length + response.records.length;
        if (loaded > captured.total_matching || response.next_cursor === null && loaded !== captured.total_matching || response.next_cursor !== null && loaded >= captured.total_matching) throw new Error('Activity pagination did not match the captured record count. Refresh before loading older records.');
        setCapture({ filters: prior!.filters, pages: [...prior!.pages, response] });
      } else {
        if (response.next_cursor === null && response.records.length !== response.total_matching || response.next_cursor !== null && response.records.length >= response.total_matching) throw new Error('Activity pagination did not match its captured record count. Refresh the history before relying on it.');
        setCapture({ filters, pages: [response] }); setPaginationBlocked(false);
      }
    } catch (reason) {
      if (mounted.current && token === requestId.current) {
        setError(reason instanceof Error ? reason.message : String(reason));
        if (older) setPaginationBlocked(true);
      }
    } finally { lock.current = false; if (mounted.current && token === requestId.current) setPending(''); }
  }
  useEffect(() => {
    mounted.current = true; void load({ action: '', shipment: initialShipmentId.trim() });
    return () => { mounted.current = false; requestId.current++; lock.current = false; };
  }, []);
  function exportCapture() {
    if (!capture) return;
    downloadCaptured('aegis-captured-activity.json', { scope: 'Captured internal simulated-operations audit history', filters: capture.filters, pages: capture.pages, read_only: true, operational_state_modified: false });
  }
  return <section className="panel activity-timeline" aria-labelledby="activity-history-title">
    <div className="panel-heading"><div><div className="eyebrow">RECORDED INTERNAL ACTIONS</div><h2 id="activity-history-title"><Clock3 size={20} /> Activity history</h2><span>See what was actually recorded across Command, dispatch and Drive.</span></div>{onClose && <button className="icon-button" aria-label="Close activity history" onClick={onClose}><X size={19} /></button>}</div>
    <p className="activity-intro">These are internal audit records for simulated operations. Actor names are self-declared, not authenticated identities. Some read-only comparisons and map changes create no audit record; an empty history does not mean a button failed.</p>
    <div className="activity-filters"><label className="field">Recorded action<select aria-label="Recorded action" value={draftAction} disabled={!!pending} onChange={event => setDraftAction(event.target.value)}><option value="">All recorded actions</option>{first?.actions.map(row => <option key={row.id} value={row.id}>{row.label}</option>)}</select></label><label className="field">Explicit shipment ID<input value={draftShipment} maxLength={64} disabled={!!pending} onChange={event => setDraftShipment(event.target.value)} placeholder="All shipments, or SH11" /></label><button disabled={!!pending || !validShipment} onClick={() => void load({ action: draftAction, shipment: draftShipment.trim() })}>Apply activity filters</button><button className="secondary" disabled={!!pending} onClick={() => void load(capture?.filters ?? { action: '', shipment: initialShipmentId.trim() })}><RefreshCw size={14} />{pending === 'refresh' ? 'Loading activity…' : 'Refresh activity'}</button></div>
    {!validShipment && <p className="activity-warning">Use letters, digits, underscores, dots or hyphens for a shipment ID, or leave it empty.</p>}
    {dirty && <p className="activity-warning">Filter inputs changed. Apply them to produce a new snapshot. The records and export below still use the captured filters.</p>}
    <p className="activity-filter-note">Shipment filtering matches an explicitly recorded top-level shipment ID. Plan-wide approvals or lot decisions are not inferred to belong to a shipment.</p>
    {error && <div role="alert" className="activity-error"><strong>Activity request failed.</strong> {error}{capture && <p>The previous captured records remain below and can still be exported. They are not a fresh result.</p>}</div>}
    {pending && <p role="status" className="activity-status">{pending === 'older' ? 'Loading older records from the same captured history…' : 'Reading recorded activity without changing operations…'}</p>}
    {first && <>
      <div className="activity-snapshot" role="status"><strong>{records.length} of {first.total_matching} matching records loaded</strong><span>Captured through audit #{first.snapshot_latest_id} · {clock(first.generated_at)}</span><span>Filters: {capture!.filters.action || 'all actions'} · {capture!.filters.shipment || 'all explicit shipment IDs'}</span></div>
      {!records.length && <div className="activity-empty">No recorded actions match this captured view. Try all actions, clear the shipment filter, or refresh after a separately approved action.</div>}
      <ol className="activity-records">{records.map(row => <li key={row.id}><article aria-label={`Audit record ${row.id}`}><div className="activity-record-heading"><span className="activity-action">{row.action_label}</span><span>#{row.id} · {clock(row.timestamp ?? row.timestamp_raw ?? null)}</span></div><h3>{row.summary}</h3><p className="activity-record-scope">{row.scope}</p><p className="activity-actor">Recorded actor: <strong>{row.actor}</strong>{row.explicit_shipment_id ? ` · explicit shipment ${row.explicit_shipment_id}` : ' · no explicit shipment ID recorded'}</p>
        <div className="activity-navigation">{row.suggested_view && onNavigate && <button className="text-button" onClick={() => onNavigate(row.suggested_view!)}>Open {viewNames[row.suggested_view]}<ArrowRight size={13} /></button>}{row.explicit_shipment_id && onSelectShipment && <button className="text-button" onClick={() => onSelectShipment(row.explicit_shipment_id!)}>Inspect shipment {row.explicit_shipment_id}<ArrowRight size={13} /></button>}</div>
        <details className="activity-details"><summary>Inspect the recorded evidence</summary><p><strong>Action:</strong> <code>{row.action}</code></p><p><strong>Original timestamp:</strong> <code>{row.timestamp_raw ?? row.timestamp ?? 'Not recorded'}</code></p><p><strong>{row.citation.label}</strong><br /><code>{row.citation.path}</code></p>{row.metadata_errors && row.metadata_errors.length > 0 && <ul>{row.metadata_errors.map((item, index) => <li key={index}>{item}</li>)}</ul>}{row.payload_error ? <p className="activity-payload-error">Payload unavailable: {row.payload_error}</p> : <pre>{payloadText(row.payload)}</pre>}{row.payload_sha256 && <p>Stored payload SHA-256: <span className="checksum">{row.payload_sha256}</span></p>}{row.payload_prefix_sha256 && <p>Inspected prefix SHA-256 (not the full payload): <span className="checksum">{row.payload_prefix_sha256}</span></p>}{row.payload_bytes != null && <p>Stored payload size: {row.payload_bytes.toLocaleString('en-US')} bytes.</p>}<p>Only the recorded fields are evidence. This view does not reconstruct missing past values or certify a current assignment.</p></details>
      </article></li>)}</ol>
      <div className="activity-bottom-actions"><button className="secondary" disabled={!!pending || dirty || paginationBlocked || !last?.next_cursor || pages.length >= 10} onClick={() => void load(capture!.filters, true)}>{pending === 'older' ? 'Loading older activity…' : 'Load older activity'}</button><button className="secondary" onClick={exportCapture}><ArrowDownToLine size={14} /> Export captured activity JSON</button><span>{pages.length >= 10 && last?.next_cursor ? 'Client display limit reached: export these pages and narrow the filters.' : paginationBlocked ? 'Refresh before requesting another page.' : !last?.next_cursor ? 'End of this captured history.' : 'Newer actions require an explicit refresh.'}</span></div>
      <details className="activity-limits"><summary>Snapshot scope and limitations</summary><p>Snapshot SHA-256: <span className="checksum">{first.snapshot_id}</span></p><ul>{first.limitations.map((item, index) => <li key={index}>{item}</li>)}</ul><p>Exports preserve the loaded pages and their active filters. This panel cannot approve, hold, dispatch, acknowledge or replay an action.</p></details>
    </>}
    {!capture && !pending && !error && <p className="activity-empty">Activity history has not been captured yet.</p>}
  </section>;
}
