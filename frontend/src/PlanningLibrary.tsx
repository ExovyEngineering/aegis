import { useEffect, useState } from 'react';
import { api, fixed, formatNumber } from './api';

interface Project { id: string; name: string; version: number; run_id: string; updated_at: string }
interface SavedRun { request: any; result: any; checksum: string; created_at: string }
interface Detail extends Project { run: SavedRun; viewed_version: number; history: { version: number; name: string }[] }

export default function PlanningLibrary({ runId, changed, onLoad }: { runId?: string; changed: boolean; onLoad: (request: any, result: any) => void }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [name, setName] = useState('My route experiment');
  const [current, setCurrent] = useState<Detail>();
  const [selected, setSelected] = useState<string[]>([]);
  const [comparison, setComparison] = useState<Detail[]>([]);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const refresh = () => api<Project[]>('/planning/projects').then(setProjects);
  useEffect(() => { refresh().catch(e => setError(String(e))); }, []);
  async function act(fn: () => Promise<void>) { setBusy(true); setError(''); setMessage(''); try { await fn(); } catch (e) { setError(String(e)); } finally { setBusy(false); } }
  async function open(id: string, version?: number) {
    const value = await api<Detail>(`/planning/projects/${id}${version ? `?version=${version}` : ''}`);
    setCurrent(value); setName(value.name); onLoad(value.run.request, value.run.result);
    setMessage(`Opened saved version ${value.viewed_version}. Source timestamps describe that saved run.`);
  }
  const sameOperation = comparison.length === 2 && JSON.stringify({ preset: comparison[0].run.request.preset, custom: comparison[0].run.request.custom_operation }) === JSON.stringify({ preset: comparison[1].run.request.preset, custom: comparison[1].run.request.custom_operation });
  return <section className="panel planning-library" aria-label="Saved route experiments">
    <div className="panel-heading"><div><h2>Saved route experiments</h2><span>Persistent local projects, version history and inspectable comparisons</span></div><span className="pill amber">NO DISPATCH</span></div>
    <div className="padded">
      <p>Save a completed run before leaving the laboratory. Unsaved editor changes remain temporary. Opening a project replaces the editor and displayed result with that saved snapshot.</p>
      <div className="planning-actions"><label className="field">Experiment name<input maxLength={100} value={name} onChange={e => setName(e.target.value)} /></label>
        <button disabled={busy || !runId || changed || name.trim().length < 2} onClick={() => act(async () => { const p = await api<Project>('/planning/projects', { name, run_id: runId }); await refresh(); setCurrent(await api<Detail>(`/planning/projects/${p.id}`)); setMessage('Experiment saved locally. No driver assignments changed.'); })}>Save as new project</button>
        {current && <button className="secondary" disabled={busy || !runId || changed || name.trim().length < 2} onClick={() => act(async () => { const p = await api<Project>(`/planning/projects/${current.id}/update`, { name, run_id: runId, expected_version: current.version }); await refresh(); setCurrent(await api<Detail>(`/planning/projects/${p.id}`)); setMessage(`Saved version ${p.version}; earlier versions retained.`); })}>Save next version</button>}
      </div>
      {changed && <p className="coverage-warning">Run the edited inputs before saving; the previous result has different assumptions.</p>}
      {error && <p role="alert" className="feedback error">{error}</p>}{message && <p role="status" className="feedback success">{message}</p>}
      {!projects.length && <p className="source-note">No saved projects yet. Run a plan, then save it here.</p>}
      <div className="table-scroll"><table><thead><tr><th>Compare</th><th>Project</th><th>Version / saved</th><th>Actions</th></tr></thead><tbody>{projects.map(p => <tr key={p.id}><td><input type="checkbox" aria-label={`Compare ${p.name}`} checked={selected.includes(p.id)} disabled={!selected.includes(p.id) && selected.length >= 2} onChange={e => { setComparison([]); setSelected(e.target.checked ? [...selected, p.id] : selected.filter(id => id !== p.id)); }} /></td><td>{p.name}</td><td>v{p.version}<br />{new Date(p.updated_at).toLocaleString()}</td><td><button className="text-button" disabled={busy} onClick={() => act(() => open(p.id))}>Open project</button></td></tr>)}</tbody></table></div>
      {current && <div className="planning-actions"><label className="field">Saved version<select aria-label="Saved project version" value={current.viewed_version} disabled={busy} onChange={e => act(() => open(current.id, Number(e.target.value)))}>{current.history.map(h => <option key={h.version} value={h.version}>Version {h.version} · {h.name}</option>)}</select></label><a className="secondary" href={`/api/planning/runs/${current.run.result.run_id}`} download="aegis-experiment.json">Export snapshot JSON</a><a className="secondary" href={`/api/planning/runs/${current.run.result.run_id}/stops.csv`}>Export stop sequence CSV</a></div>}
      <button className="secondary" disabled={busy || selected.length !== 2} onClick={() => act(async () => { setComparison(await Promise.all(selected.map(id => api<Detail>(`/planning/projects/${id}`)))); })}>Compare selected experiments</button>
      {comparison.length === 2 && <div className="planning-comparison"><h3>Saved experiment comparison</h3><p className="source-note">{sameOperation ? 'Same saved operation definition; review differences in fleet, timing, travel source and stress assumptions below.' : 'Different operation definitions: costs and demand are descriptive, not a controlled performance comparison.'} These saved results are not refreshed live.</p><div className="table-scroll"><table><thead><tr><th>Measure</th>{comparison.map(p => <th key={p.id}>{p.name} · v{p.version}</th>)}</tr></thead><tbody>{[
        ['Operation', (p: Detail) => p.run.request.preset], ['Available trucks', (p: Detail) => p.run.request.preset === 'custom' ? p.run.request.custom_operation.trucks.length : p.run.request.truck_count ?? 'preset'], ['Capacity per truck', (p: Detail) => p.run.request.preset === 'custom' ? p.run.request.custom_operation.trucks.map((t: any) => `${t.id}: ${t.capacity_kg} kg`).join('; ') : `${p.run.request.truck_capacity_kg ?? 'preset'} kg`], ['Travel requested', (p: Detail) => p.run.request.routing], ['Ambient assumption', (p: Detail) => `${p.run.request.ambient_temperature_c}°C`], ['Added delay', (p: Detail) => `${p.run.request.delay_minutes} min`], ['Refrigeration fault', (p: Detail) => p.run.request.refrigeration_fault ? 'simulated fault' : 'normal assumption'], ['Route limit', (p: Detail) => `${p.run.request.max_route_hours} h`], ['Simulated cost', (p: Detail) => `$${formatNumber(p.run.result.summary.total_cost)}`], ['Unmet demand', (p: Detail) => `${p.run.result.summary.unmet_demand_kg} kg`], ['Distance', (p: Detail) => `${fixed(p.run.result.summary.total_distance_m / 1000, 1)} km`], ['Solver', (p: Detail) => p.run.result.solver_status], ['Checked violations', (p: Detail) => p.run.result.summary.constraint_violations], ['Travel / geometry fallback', (p: Detail) => p.run.result.routes.some((r: any) => r.fallback) ? 'some estimated fallback' : 'no fallback reported'], ['Run timestamp', (p: Detail) => p.run.created_at],
      ].map(([label, value]) => <tr key={String(label)}><td>{String(label)}</td>{comparison.map(p => <td key={p.id}>{(value as (p: Detail) => string)(p)}</td>)}</tr>)}</tbody></table></div></div>}
      <p className="source-note">Stored in this local application's SQLite database. No cloud accounts, shared tenancy or approved dispatch are created. JSON includes original assumptions, results, retrieval timestamps where supplied, and a SHA-256 checksum.</p>
    </div>
  </section>;
}
