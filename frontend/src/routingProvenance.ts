export interface RoutingSources {
  fallback?: boolean;
  travel_time_fallback?: boolean;
  distance_fallback?: boolean;
  geometry_fallback?: boolean;
}
export function routingSourceLabels(route: RoutingSources) {
  const time = route.travel_time_fallback ?? route.fallback ?? true;
  const distance = route.distance_fallback ?? route.fallback ?? true;
  const geometry = route.geometry_fallback ?? route.fallback ?? true;
  return {
    travel: time && distance ? 'Estimated travel' : !time && !distance ? 'OSRM travel' : 'Mixed travel sources',
    detail: `Time: ${time ? 'estimated' : 'OSRM'} · distance: ${distance ? 'estimated' : 'OSRM'} · geometry: ${geometry ? 'estimated' : 'OSRM'}`,
    geometryEstimated: geometry,
  };
}
