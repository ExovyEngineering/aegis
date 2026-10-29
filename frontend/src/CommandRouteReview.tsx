import { ArrowDownToLine, MapPin } from 'lucide-react';
import type { Shipment } from './types';
import './CommandWorkflow.css';

export function hasUsableRoadRoutes(value: any): boolean {
  const routes = value?.payload?.routes;
  return Array.isArray(routes) && routes.length > 0 && routes.length <= 10 && routes.every((route: any) =>
    Number.isFinite(route?.distance) && route.distance >= 0 && Number.isFinite(route?.duration) && route.duration >= 0 &&
    route.geometry?.type === 'LineString' && Array.isArray(route.geometry.coordinates) &&
    route.geometry.coordinates.length >= 2 && route.geometry.coordinates.length <= 150000 &&
    route.geometry.coordinates.every((point: any) => Array.isArray(point) && point.length >= 2 &&
      Number.isFinite(point[0]) && Math.abs(point[0]) <= 180 && Number.isFinite(point[1]) && Math.abs(point[1]) <= 90));
}

export function downloadCaptured(name: string, value: unknown) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' }));
  const link = document.createElement('a'); link.href = url; link.download = name; link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

interface Props { route: any; selected?: Shipment; selectedAlternative: number; onSelect: (index: number) => void; onShowMap: () => void }
export default function CommandRouteReview({ route, selected, selectedAlternative, onSelect, onShowMap }: Props) {
  const routes = hasUsableRoadRoutes(route) ? route.payload.routes : [];
  const current = routes[selectedAlternative];
  const isSelectedTrip = !!route.shipmentId && route.shipmentId === selected?.id;
  return <section className="panel command-route-result" id="command-route-result" tabIndex={-1} aria-labelledby="command-route-heading">
    <div className="panel-heading"><div><div className="eyebrow">COMPUTED TRAVEL COMPARISON</div><h2 id="command-route-heading">Route alternatives &amp; road review</h2><span>{route.displayLabel}</span></div><span className={`pill ${route.fallback ? 'amber' : 'green'}`}>{route.fallback ? 'Estimated fallback' : 'OSRM driving geometry'}</span></div>
    {!isSelectedTrip && <p className="coverage-warning">This is a separate reference route. Request a road route for the selected candidate shipment to compare that trip.</p>}
    {current ? <>
      <div className="command-route-summary" role="status"><strong>Alternative {selectedAlternative + 1} is selected for the map</strong><span>{(current.distance / 1000).toFixed(1)} km · {Math.round(current.duration / 60)} min of {route.fallback ? 'estimated' : 'ordinary-driving'} travel</span><button className="secondary small" onClick={onShowMap}><MapPin size={14} /> Focus route map</button></div>
      <p className="command-explanation">Selecting an alternative changes this comparison's map highlight. Enable the Route geometry layer if it is hidden. It does not replace the candidate's fixed planning estimate, change stop order, approve a plan or send a driver instruction. Public routing excludes the simulated event delays and does not incorporate the displayed MoDOT incidents.</p>
      {isSelectedTrip && <p className="command-explanation">Command's current planning input for {selected?.id}: {Math.round((selected?.estimated_hours ?? 0) * 60)} min and {selected?.estimated_distance_km.toFixed(1)} km. The road-service result above is a separate estimate; differences are not a verified time saving.</p>}
      <div className="table-scroll"><table><thead><tr><th>Map selection</th><th>Distance</th><th>Travel estimate</th><th>Nearby MoDOT records</th><th>Review</th></tr></thead><tbody>{routes.map((item: any, index: number) => {
        const reviewed = route.road_review?.alternatives?.find((row: any) => row.alternative_index === index);
        return <tr key={index} aria-selected={index === selectedAlternative}><td><button className={index === selectedAlternative ? 'small' : 'secondary small'} aria-pressed={index === selectedAlternative} onClick={() => onSelect(index)}>Highlight alternative {index + 1}</button></td><td>{(item.distance / 1000).toFixed(1)} km</td><td>{Math.round(item.duration / 60)} min</td><td>{reviewed ? reviewed.nearby_events.length : 'Not evaluated'}</td><td>{reviewed?.review_required ? 'Dispatcher review required' : 'Truck restrictions unverified'}</td></tr>;
      })}</tbody></table></div>
      <div className="command-result-actions"><button className="secondary small" onClick={() => downloadCaptured(`aegis-route-${route.shipmentId ?? 'reference'}.json`, { ...route, captured_export: true, selected_alternative: selectedAlternative, operational_state_modified: false })}><ArrowDownToLine size={14} /> Export route comparison JSON</button><span>Captured comparison only · no dispatch</span></div>
    </> : <p role="alert" className="feedback error">No usable route geometry is available. Request the selected trip again to produce a route or a labeled estimate.</p>}
    <p className="coverage-warning">{route.road_review?.warning ?? 'OSRM excludes current closures and commercial vehicle restrictions. A route is not certified for a truck.'}</p>
    <p className="command-explanation">{route.retrieved_at ? `Route retrieved ${new Date(route.retrieved_at).toLocaleString('en-US', { timeZone: 'America/Chicago' })} CT. ` : 'Route retrieval time is unavailable. '}{route.road_review?.stale ? 'Road evidence is stale; inspect its source age. ' : ''}Proximity can include parallel roads or repeated records. Check timing and restrictions before a separate human decision.</p>
  </section>;
}
