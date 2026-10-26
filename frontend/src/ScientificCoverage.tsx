import { useEffect, useState } from 'react';
import { CalendarCheck, Database, ShieldCheck, TriangleAlert } from 'lucide-react';
import { api, fixed, formatNumber } from './api';

interface MetricCoverage { numeric_days: number; quality_pass_days: number; flagged_days: number; missing_days: number }
interface NOAAStation { city: string; station_id: string; station_name: string; latitude: number; longitude: number; distance_to_city_km: number; expected_days: number; observed_days: number; missing_days: number; metric_coverage: Record<string, MetricCoverage>; retrieved_at?: string; status: string; error?: string }
interface NOAACoverage { status?: string; provenance?: string; start_date?: string; end_date?: string; station_count?: number; requested_station_count?: number; expected_station_days?: number; observed_station_days?: number; coverage_fraction?: number; metric_coverage_fraction?: number; missing_metric_values?: number; stations?: NOAAStation[]; limitations?: string[]; model_join_status?: string }
interface TimingAudit { status?: string; strict_split?: { training_snapshot_cutoff?: string; training_rows?: number; validation_rows?: number; validation_start?: string; validation_end?: string }; snapshot_release_verified?: boolean; feature_availability?: string; limitations?: string[]; snapshot_baseline?: { brier: number; pr_auc_average_precision?: number; roc_auc?: number } | null; calendar_logistic?: { brier: number; pr_auc_average_precision?: number; roc_auc?: number } | null }

export function NOAACoverageCard() {
  const [coverage, setCoverage] = useState<NOAACoverage>();
  const [error, setError] = useState('');
  useEffect(() => { api<NOAACoverage>('/noaa-coverage').then(setCoverage).catch(e => setError(e.message)); }, []);
  const datePercent = coverage?.coverage_fraction == null ? null : coverage.coverage_fraction * 100;
  const metricPercent = coverage?.metric_coverage_fraction == null ? null : coverage.metric_coverage_fraction * 100;
  return <section className="panel scientific-coverage"><div className="panel-heading"><div><div className="eyebrow">OBSERVED HISTORICAL WEATHER</div><h2>NOAA coverage audit</h2><span>{coverage?.start_date && coverage?.end_date ? `${coverage.start_date} through ${coverage.end_date} · daily station observations` : 'Coverage report is not yet available'}</span></div><Database size={23} className="muted-icon" /></div>
    {error && <div className="coverage-warning"><TriangleAlert size={16} />Coverage report unavailable: {error}</div>}
    {coverage?.stations?.length ? <>
      <div className="coverage-facts"><div><span>VERIFIED STATIONS</span><strong>{coverage.station_count} / {coverage.requested_station_count}</strong></div><div><span>DATE-ROW COVERAGE</span><strong>{fixed(datePercent, 1)}%</strong><small>{formatNumber(coverage.observed_station_days)} / {formatNumber(coverage.expected_station_days)} station-days</small></div><div><span>METRIC COVERAGE</span><strong>{fixed(metricPercent, 2)}%</strong><small>{formatNumber(coverage.missing_metric_values)} missing metric values</small></div><div><span>REPORT STATUS</span><strong className="coverage-status">{coverage.status}</strong></div></div>
      <div className="table-scroll"><table><thead><tr><th>City / actual station</th><th>Verified coordinates</th><th>Station-days</th><th>Missing metrics</th><th>Quality flags</th><th>Retrieval</th></tr></thead><tbody>{coverage.stations.map(station => <tr key={station.station_id}><td><strong>{station.city}</strong><br />{station.station_id}<br /><span className="wrap-cell">{station.station_name}</span></td><td>{fixed(station.latitude, 4)}, {fixed(station.longitude, 4)}<br />{fixed(station.distance_to_city_km, 1)} km from city</td><td>{station.observed_days} / {station.expected_days}<br />{station.missing_days} missing days</td><td>{Object.entries(station.metric_coverage ?? {}).map(([metric, count]) => <div key={metric}>{metric}: {count.missing_days} missing</div>)}</td><td>{Object.entries(station.metric_coverage ?? {}).map(([metric, count]) => <div key={metric}>{metric}: {count.flagged_days} flagged</div>)}</td><td className="wrap-cell">{station.error ?? (station.retrieved_at ? new Date(station.retrieved_at).toLocaleString('en-US', { timeZone: 'America/Chicago' }) + ' CT' : station.status)}</td></tr>)}</tbody></table></div>
      <div className="coverage-warning"><TriangleAlert size={16} /><div><strong>Complete date rows do not establish complete variables.</strong><p>{coverage.model_join_status ?? 'No validated weather-to-FSIS linkage is established.'}</p></div></div>
      {coverage.limitations?.length ? <ul className="lab-assumptions">{coverage.limitations.map(limitation => <li key={limitation}>{limitation}</li>)}</ul> : null}
    </> : !error && <p className="padded source-note">No verified historical coverage report captured. The existing station/week response remains a separate dated probe.</p>}
  </section>;
}

export function ModelTimingCard() {
  const [audit, setAudit] = useState<TimingAudit>();
  const [error, setError] = useState('');
  useEffect(() => { api<TimingAudit>('/model-timing').then(setAudit).catch(e => setError(e.message)); }, []);
  return <section className="panel scientific-coverage"><div className="panel-heading"><div><div className="eyebrow">WHEN FEATURES WERE AVAILABLE</div><h2>Snapshot timing audit</h2><span>Separate from the original retrospective 90-day-lag study</span></div><CalendarCheck size={23} className="muted-icon" /></div>
    {error ? <div className="coverage-warning"><TriangleAlert size={16} />Timing audit unavailable: {error}</div> : <>
      <div className="coverage-warning"><ShieldCheck size={16} /><div><strong>{audit?.status ?? 'No timing audit captured'}</strong><p>{audit?.feature_availability ?? 'Actual per-result publication timestamps have not been established.'}</p></div></div>
      {audit?.strict_split && <div className="coverage-facts"><div><span>TRAINING SNAPSHOT CUTOFF</span><strong className="date-value">{audit.strict_split.training_snapshot_cutoff ?? '—'}</strong></div><div><span>TRAINING SAMPLES</span><strong>{formatNumber(audit.strict_split.training_rows)}</strong></div><div><span>LATER SAMPLES</span><strong>{formatNumber(audit.strict_split.validation_rows)}</strong></div><div><span>PUBLIC RELEASE VERIFIED</span><strong>{audit.snapshot_release_verified ? 'Yes' : 'No'}</strong></div></div>}
      {audit?.snapshot_baseline && <div className="table-scroll"><table><thead><tr><th>Snapshot-aligned estimator</th><th>Brier score</th><th>PR-AUC (AP)</th><th>ROC-AUC</th><th>Later sample window</th></tr></thead><tbody>{[['Historical prevalence', audit.snapshot_baseline], ['Calendar-only logistic', audit.calendar_logistic]].map(([name, metric]: any) => metric ? <tr key={name}><td><strong>{name}</strong></td><td>{fixed(metric.brier, 5)}</td><td>{fixed(metric.pr_auc_average_precision)}</td><td>{fixed(metric.roc_auc)}</td><td>{audit.strict_split?.validation_start ?? '—'} to {audit.strict_split?.validation_end ?? '—'}</td></tr> : null)}</tbody></table></div>}
      {audit?.limitations?.length ? <ul className="lab-assumptions">{audit.limitations.map(limitation => <li key={limitation}>{limitation}</li>)}</ul> : null}
    </>}
  </section>;
}
