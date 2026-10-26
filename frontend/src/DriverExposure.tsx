import { useEffect, useState } from 'react';
import { Route, ShieldCheck, Snowflake, TriangleAlert } from 'lucide-react';
import { api, fixed } from './api';
import type { Network, Shipment } from './types';
import type { ColdChainResult, LabRoute } from './RouteLab';
import RouteLabMap from './RouteLabMap';

export default function DriverExposure({ shipment, network }: { shipment: Shipment; network: Network }) {
  const [exposure, setExposure] = useState<ColdChainResult & { ambient_provenance?: string; advisories?: { type: string }[] }>();
  const [route, setRoute] = useState<any>();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const origin = network.nodes.find(n => n.id === shipment.origin);
  const destination = network.nodes.find(n => n.id === shipment.destination);
  useEffect(() => {
    setRoute(undefined); setError(''); setExposure(undefined);
    api<any>(`/shipments/${shipment.id}/exposure`).then(setExposure).catch(e => setError(e.message));
  }, [shipment.id, network.revision]);
  async function requestRoute() {
    if (!origin || !destination) return;
    setBusy(true); setError('');
    try { setRoute(await api('/route', { coordinates: [origin.coordinates, destination.coordinates], alternatives: true })); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }
  const primary = route?.payload?.routes?.[0];
  const mapRoute: LabRoute[] = primary ? [{ truck_id: shipment.truck_id, origin_id: shipment.origin, stop_ids: [shipment.destination], distance_m: primary.distance, duration_seconds: primary.duration, load_kg: shipment.quantity_kg, geometry: primary.geometry, fallback: route.fallback }] : [];
  return <section className="panel driver-exposure"><div className="panel-heading"><div><h2>{shipment.id} · trip advisories</h2><span>Review while parked · dispatcher-approved trip</span></div><Snowflake size={21} className="muted-icon" /></div>
    {error && <div className="coverage-warning"><TriangleAlert size={16} />Trip advisory unavailable: {error}</div>}
    {exposure && <><div className="driver-projection"><div><span>SIMULATED CURRENT CARGO</span><strong>{shipment.temperature_c}°C</strong></div><div><span>ILLUSTRATIVE JOURNEY MAXIMUM</span><strong>{fixed(exposure.max_temperature_c, 1)}°C</strong></div><span className={`pill ${exposure.status === 'review' ? 'amber' : 'green'}`}>{exposure.status === 'review' ? 'Dispatcher review requested' : 'Within assumed temperature target'}</span></div><p className="source-note padded">{exposure.provenance}. {exposure.ambient_provenance}.</p></>}
    <div className="driver-route-action"><button className="secondary" disabled={busy || !origin || !destination} onClick={requestRoute}><Route size={16} />{busy ? 'Requesting route…' : 'Review trip route while parked'}</button><p>This displays a route comparison for the approved trip. It does not change your assignment or authorize a detour.</p></div>
    {primary && <><RouteLabMap nodes={[origin!, destination!]} routes={mapRoute} /><p className="source-note padded">{route.fallback ? 'Estimated fallback connection; not road geometry.' : 'OSRM ordinary driving route.'} {fixed(primary.distance / 1000, 1)} km · {Math.round(primary.duration / 60)} min travel estimate. Commercial vehicle restrictions require validation.</p><div className="coverage-warning"><TriangleAlert size={16} /><div><strong>{route.road_review?.alternatives?.some((a: any) => a.review_required) ? 'Route requires dispatcher review' : 'Commercial vehicle validation required'}</strong><p>{route.road_review?.warning ?? 'Current disruption coverage has not been verified.'}</p></div></div></>}
    <div className="coverage-warning"><ShieldCheck size={16} />Cargo projections use uncalibrated assumptions. Report an incident and await dispatcher instructions; no automatic safety decision is made.</div>
  </section>;
}
