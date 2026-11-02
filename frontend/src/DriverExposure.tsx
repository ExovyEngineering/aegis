import { useEffect, useRef, useState } from 'react';
import { Route, ShieldCheck, Snowflake, TriangleAlert } from 'lucide-react';
import { api, fixed } from './api';
import type { Network, Shipment } from './types';
import type { ColdChainResult, LabRoute } from './RouteLab';
import RouteLabMap from './RouteLabMap';

interface ExposureResponse extends ColdChainResult { shipment_id: string; network_revision: number; ambient_provenance?: string; advisories?: { type: string }[] }

export default function DriverExposure({ shipment, network, disabled = false }: { shipment: Shipment; network: Network; disabled?: boolean }) {
  const [exposureSnapshot, setExposure] = useState<{ key: string; value: ExposureResponse }>();
  const [routeSnapshot, setRoute] = useState<{ key: string; value: any }>();
  const [failure, setFailure] = useState<{ key: string; message: string }>();
  const [busy, setBusy] = useState(false);
  const contextKey = JSON.stringify([shipment.id, shipment.origin, shipment.destination, shipment.truck_id, network.revision]);
  const currentContext = useRef(contextKey);
  const exposureRequest = useRef(0);
  const routeRequest = useRef(0);
  const routePending = useRef(false);
  currentContext.current = contextKey;
  const exposure = exposureSnapshot?.key === contextKey ? exposureSnapshot.value : undefined;
  const route = routeSnapshot?.key === contextKey ? routeSnapshot.value : undefined;
  const error = failure?.key === contextKey ? failure.message : '';
  const origin = network.nodes.find(n => n.id === shipment.origin);
  const destination = network.nodes.find(n => n.id === shipment.destination);
  useEffect(() => {
    const request = ++exposureRequest.current;
    let active = true;
    routeRequest.current++; routePending.current = false;
    setRoute(undefined); setFailure(undefined); setExposure(undefined); setBusy(false);
    api<ExposureResponse>(`/shipments/${shipment.id}/exposure`).then(result => {
      if (!active || request !== exposureRequest.current || currentContext.current !== contextKey) return;
      if (result.shipment_id !== shipment.id || result.network_revision !== network.revision) {
        setFailure({ key: contextKey, message: 'Trip or network changed while loading. Refresh the approved trip before reviewing this projection.' });
        return;
      }
      setExposure({ key: contextKey, value: result });
    }).catch(e => {
      if (active && request === exposureRequest.current && currentContext.current === contextKey) setFailure({ key: contextKey, message: e instanceof Error ? e.message : String(e) });
    });
    return () => { active = false; exposureRequest.current++; routeRequest.current++; routePending.current = false; };
  }, [contextKey, shipment.id, network.revision]);
  useEffect(() => {
    if (disabled) { routeRequest.current++; routePending.current = false; setRoute(undefined); setBusy(false); }
  }, [disabled]);
  async function requestRoute() {
    if (!origin || !destination || disabled || routePending.current) return;
    const request = ++routeRequest.current;
    routePending.current = true; setBusy(true); setFailure(undefined); setRoute(undefined);
    try {
      const result = await api<any>('/route', { coordinates: [origin.coordinates, destination.coordinates], alternatives: true });
      if (request !== routeRequest.current || currentContext.current !== contextKey) return;
      if (!Array.isArray(result.payload?.routes) || !result.payload.routes.length) throw new Error('Route response did not contain a usable route. Retry while parked.');
      setRoute({ key: contextKey, value: result });
    }
    catch (e) { if (request === routeRequest.current && currentContext.current === contextKey) setFailure({ key: contextKey, message: e instanceof Error ? e.message : String(e) }); }
    finally { if (request === routeRequest.current && currentContext.current === contextKey) { routePending.current = false; setBusy(false); } }
  }
  const primary = route?.payload?.routes?.[0];
  const mapRoute: LabRoute[] = primary ? [{ truck_id: shipment.truck_id, origin_id: shipment.origin, stop_ids: [shipment.destination], distance_m: primary.distance, duration_seconds: primary.duration, load_kg: shipment.quantity_kg, geometry: primary.geometry, fallback: route.fallback }] : [];
  return <section className="panel driver-exposure"><div className="panel-heading"><div><h2>{shipment.id} · trip advisories</h2><span>Review while parked · dispatcher-approved trip</span></div><Snowflake size={21} className="muted-icon" /></div>
    {error && <div role="alert" className="coverage-warning"><TriangleAlert size={16} />Trip advisory unavailable: {error}</div>}
    {exposure && <><div className="driver-projection"><div><span>SIMULATED CURRENT CARGO</span><strong>{shipment.temperature_c}°C</strong></div><div><span>ILLUSTRATIVE JOURNEY MAXIMUM</span><strong>{fixed(exposure.max_temperature_c, 1)}°C</strong></div><span className={`pill ${exposure.status === 'review' ? 'amber' : 'green'}`}>{exposure.status === 'review' ? 'Dispatcher review requested' : 'Within assumed temperature target'}</span></div><p className="source-note padded">{exposure.provenance}. {exposure.ambient_provenance}.</p></>}
    <div className="driver-route-action"><button className="secondary" disabled={disabled || busy || !origin || !destination} onClick={requestRoute}><Route size={16} />{busy ? 'Requesting route…' : 'Review trip route while parked'}</button><p>{disabled ? 'Route requests are locked in driving focus. Park safely before reviewing alternatives.' : 'This displays a route comparison for the approved trip. It does not change your assignment or authorize a detour.'}</p></div>
    {primary && <><RouteLabMap nodes={[origin!, destination!]} routes={mapRoute} /><p className="source-note padded">{route.fallback ? 'Estimated fallback connection; not road geometry.' : 'OSRM ordinary driving route.'} {fixed(primary.distance / 1000, 1)} km · {Math.round(primary.duration / 60)} min travel estimate. Commercial vehicle restrictions require validation.</p><div className="coverage-warning"><TriangleAlert size={16} /><div><strong>{route.road_review?.alternatives?.some((a: any) => a.review_required) ? 'Route requires dispatcher review' : 'Commercial vehicle validation required'}</strong><p>{route.road_review?.warning ?? 'Current disruption coverage has not been verified.'}</p></div></div></>}
    <div className="coverage-warning"><ShieldCheck size={16} />Cargo projections use uncalibrated assumptions. Report an incident and await dispatcher instructions; no automatic safety decision is made.</div>
  </section>;
}
