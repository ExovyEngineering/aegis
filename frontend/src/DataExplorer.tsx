import { useEffect, useState } from 'react';
import { api, formatNumber } from './api';
interface Source { id: string; name: string; status: string; rows?: number; note: string; columns?: {name: string; type: string}[]; sha256?: string; error?: string }
interface Page { rows: Record<string, unknown>[]; columns: string[]; offset: number; returned_rows: number; matching_rows: number; next_offset: number | null; page_null_counts: Record<string, number>; provenance: string }
export default function DataExplorer() {
  const [catalog, setCatalog] = useState<Source[]>([]);
  const [source, setSource] = useState('fsis_poultry');
  const [field, setField] = useState('');
  const [query, setQuery] = useState('');
  const [page, setPage] = useState<Page>();
  const [applied, setApplied] = useState<{field: string; contains: string}>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => { api<Source[]>('/data/catalog').then(setCatalog).catch(e => setError(String(e))); }, []);
  async function load(identity: string, offset = 0, filter?: {field: string; contains: string}) {
    setBusy(true); setError('');
    try { const params = new URLSearchParams({offset: String(offset), limit: '25', ...(filter ?? {})}); setPage(await api<Page>(`/data/${identity}?${params}`)); setApplied(filter); }
    catch (e) { setError(String(e)); setPage(undefined); } finally { setBusy(false); }
  }
  useEffect(() => { setField(''); setQuery(''); setPage(undefined); load(source); }, [source]);
  const selected = catalog.find(s => s.id === source);
  return <section className="panel data-explorer" aria-label="Ingested data explorer"><div className="panel-heading"><div><h2>Inspect the underlying evidence</h2><span>Real ingested rows, original column names and explicit source separation</span></div></div><div className="padded">
    <label className="field">Dataset<select aria-label="Dataset" value={source} disabled={busy} onChange={e => setSource(e.target.value)}>{catalog.length ? catalog.map(s => <option key={s.id} value={s.id} disabled={s.status !== 'available'}>{s.name} · {s.status === 'available' ? `${formatNumber(s.rows)} rows` : s.status}</option>) : <option value="fsis_poultry">FSIS raw-poultry samples</option>}</select></label>
    <p className="coverage-warning">{selected?.note ?? 'These sources remain separate evidence layers; no supplier or shipment linkage is inferred.'}</p>
    <div className="planning-actions"><label className="field">Filter column<select aria-label="Filter column" value={field} disabled={busy} onChange={e => setField(e.target.value)}><option value="">Choose a source column</option>{selected?.columns?.map(c => <option key={c.name}>{c.name}</option>)}</select></label><label className="field">Contains text<input maxLength={100} value={query} onChange={e => setQuery(e.target.value)} placeholder="Literal text, case insensitive" /></label><button disabled={busy || !field || !query.trim()} onClick={() => load(source, 0, {field, contains: query.trim()})}>Apply source filter</button><button className="secondary" disabled={busy} onClick={() => { setQuery(''); load(source); }}>Clear filter</button></div>
    {error && <p role="alert" className="feedback error">{error}</p>}{busy && <p role="status">Reading a bounded page of source rows…</p>}
    {page && <><p>{formatNumber(page.matching_rows)} matching rows. Showing {page.returned_rows ? page.offset + 1 : 0}–{page.offset + page.returned_rows}. Missing cells are shown explicitly as ∅.</p><div className="table-scroll explorer-table"><table><thead><tr>{page.columns.map(c => <th key={c}>{c}<small className="source-note">{page.page_null_counts[c]} null on this page</small></th>)}</tr></thead><tbody>{page.rows.map((row, i) => <tr key={i}>{page.columns.map(c => <td key={c}>{row[c] == null ? <span className="muted">∅</span> : String(row[c])}</td>)}</tr>)}</tbody></table></div><div className="planning-actions"><button className="secondary" disabled={busy || page.offset === 0} onClick={() => load(source, Math.max(0, page.offset - 25), applied)}>Previous rows</button><button className="secondary" disabled={busy || page.next_offset == null} onClick={() => load(source, page.next_offset!, applied)}>Next rows</button></div><p className="source-note">{page.provenance} Browser pagination is capped at 10,000 rows; use the source-specific scripts for full analysis.</p></>}
    {selected?.sha256 && <details><summary>Schema and derived-file integrity</summary><p className="checksum">SHA-256: {selected.sha256}</p><ul>{selected.columns?.map(c => <li key={c.name}><code>{c.name}</code> · {c.type}</li>)}</ul></details>}
  </div></section>;
}
