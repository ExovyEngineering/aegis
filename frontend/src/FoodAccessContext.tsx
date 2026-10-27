import { useCallback, useEffect, useRef, useState } from 'react';
import { ArrowDownToLine, Database, RefreshCw, TriangleAlert } from 'lucide-react';
import { api } from './api';

interface Variable { code: string; label: string; unit: string; year: number; sheet: string; denominator: string; definition: string; documentation_url?: string }
interface County { FIPS: string; State: string; County: string; county_display_name: string; [key: string]: string | number | null }
interface Context { status: string; provider: string; source_url: string; documentation_url: string; source_file: {filename: string; sha256: string}; ingested_at: string; release_note: string; geography: {county_count: number}; variables: Variable[]; records: County[]; limitations: string[]; integrity_verified: boolean }
const value = (number: unknown) => typeof number === 'number' && Number.isFinite(number) ? number.toLocaleString('en-US',{maximumFractionDigits:2}) : 'Missing / suppressed';

export default function FoodAccessContext() {
  const [data, setData] = useState<Context>();
  const [fips, setFips] = useState('29019');
  const [compareFips, setCompareFips] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const epoch = useRef(0);
  const load = useCallback(async()=>{
    const request = ++epoch.current;setBusy(true);
    try {
      const result = await api<Context>('/food-access');
      if (request !== epoch.current) return;
      if (result.status !== 'available' || !result.integrity_verified || !Array.isArray(result.records) || !Array.isArray(result.variables)) throw new Error('Verified USDA county context is unavailable. Re-run the source-specific importer.');
      setData(result);setError('');
    } catch(e) { if (request === epoch.current) {setData(undefined);setError(e instanceof Error ? e.message : String(e));} }
    finally {if (request === epoch.current) setBusy(false);}
  },[]);
  useEffect(()=>{load();return()=>{epoch.current++;};},[load]);
  const counties = [...(data?.records ?? [])].sort((a,b)=>a.county_display_name.localeCompare(b.county_display_name));
  const county = counties.find(c=>c.FIPS === fips) ?? counties[0];
  const comparison = counties.find(c=>c.FIPS === compareFips);
  return <section className="panel food-context" aria-label="Historical USDA food access context">
    <div className="panel-heading"><div><h2>Food access across Missouri</h2><span>USDA historical county context · separate from food-safety evidence</span></div><Database size={21}/></div>
    <div className="padded">
      <p className="coverage-warning">County-level access and retail measures help describe the operating region. They do not rate a farm, identify an outbreak, establish current demand, or change shipment eligibility.</p>
      {error && <div role="alert" className="feedback error"><TriangleAlert size={17}/>{error}<button className="secondary small" disabled={busy} onClick={load}>Retry USDA context</button></div>}
      {busy && <p role="status">Reading the checked USDA county extract…</p>}
      {data && county && <>
        <div className="food-context-toolbar"><label className="field">USDA county<select aria-label="USDA county" value={county.FIPS} onChange={e=>setFips(e.target.value)}>{counties.map(c=><option value={c.FIPS} key={c.FIPS}>{c.county_display_name} · {c.FIPS}</option>)}</select></label><label className="field">Compare USDA county<select aria-label="Compare USDA county" value={compareFips} onChange={e=>setCompareFips(e.target.value)}><option value="">No comparison</option>{counties.map(c=><option value={c.FIPS} key={c.FIPS}>{c.county_display_name} · {c.FIPS}</option>)}</select></label><a className="button-link secondary" href="/api/food-access.csv" download><ArrowDownToLine size={15}/>Download county CSV</a><button className="secondary small" disabled={busy} onClick={load}><RefreshCw size={14}/>Recheck local extract</button></div>
        <p><strong>{county.county_display_name}</strong> · county FIPS {county.FIPS}{comparison && <> compared with <strong>{comparison.county_display_name}</strong> · {comparison.FIPS}</>}. Values displayed to two decimal places where needed; exports retain numeric source precision.</p>
        <div className="food-metric-grid">{data.variables.map(variable=><article className="food-metric" key={variable.code}><span className="eyebrow">{variable.year} · {variable.sheet}</span><h3>{variable.label}</h3><strong>{value(county[variable.code])}</strong><span>{variable.unit}</span>{comparison && <p className="food-comparison">{comparison.county_display_name}: <b>{value(comparison[variable.code])}</b></p>}<details><summary>Definition and denominator</summary><p>{variable.definition}</p><p>Denominator: {variable.denominator || 'No denominator; a count as documented by the source.'}</p><code>{variable.code}</code></details></article>)}</div>
        <p className="source-note">{data.geography.county_count} Missouri counties / county-equivalents · {data.release_note}. Historical vintages differ by measure. Missing or suppressed values remain null; they are never substituted with zero.</p>
        <details><summary>Source provenance and interpretation limits</summary><p>{data.provider} · <a href={data.source_url} target="_blank" rel="noreferrer">Official source</a> · <a href={data.documentation_url} target="_blank" rel="noreferrer">Documentation</a></p><p>{data.source_file.filename}. Imported {new Date(data.ingested_at).toLocaleString('en-US',{timeZone:'America/Chicago'})} CT. The derived-file checksum was checked before serving these values.</p><p className="checksum">Original SHA-256: {data.source_file.sha256}</p><ul>{data.limitations.map((item,i)=><li key={i}>{item}</li>)}</ul></details>
      </>}
    </div>
  </section>;
}
