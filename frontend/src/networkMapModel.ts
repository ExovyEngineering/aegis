import type { Coordinates, Network, Node, Shipment } from './types';

export interface PlanOverlay {
  label: string;
  scope: 'candidate' | 'scenario' | 'approved';
  shipments: Shipment[];
}

export interface RoutePath {
  index: number;
  coordinates: Coordinates[];
  distanceM: number | null;
  durationSeconds: number | null;
}

export interface ShipmentConnection { shipment: Shipment; coordinates: Coordinates[] }

/** Read GeoJSON longitude/latitude explicitly; never swap or coerce values. */
export function readCoordinate(value: unknown): Coordinates | undefined {
  if (!Array.isArray(value) || value.length < 2) return undefined;
  const [longitude, latitude] = value;
  if (typeof longitude !== 'number' || typeof latitude !== 'number'
      || !Number.isFinite(longitude) || !Number.isFinite(latitude)
      || longitude < -180 || longitude > 180 || latitude < -90 || latitude > 90) return undefined;
  return [longitude, latitude];
}

const record = (value: unknown): value is Record<string, unknown> => !!value && typeof value === 'object' && !Array.isArray(value);
const metric = (value: unknown): number | null => typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value : null;

/** Keep original alternative indexes so a missing geometry cannot relabel one. */
export function routePaths(wrapper: unknown): RoutePath[] {
  if (!record(wrapper) || !record(wrapper.payload) || !Array.isArray(wrapper.payload.routes)) return [];
  return wrapper.payload.routes.flatMap((value: unknown, index: number): RoutePath[] => {
    if (!record(value) || !record(value.geometry) || value.geometry.type !== 'LineString'
        || !Array.isArray(value.geometry.coordinates) || value.geometry.coordinates.length < 2) return [];
    const coordinates = value.geometry.coordinates.map(readCoordinate);
    if (coordinates.some(point => point === undefined)) return [];
    return [{ index, coordinates: coordinates as Coordinates[], distanceM: metric(value.distance), durationSeconds: metric(value.duration) }];
  });
}

export function selectedRoutePath(paths: RoutePath[], requested = 0): RoutePath | undefined {
  return (Number.isInteger(requested) && requested >= 0 ? paths.find(path => path.index === requested) : undefined) ?? paths[0];
}

export function shipmentCoordinates(nodes: Node[], shipment?: Shipment): Coordinates[] | undefined {
  if (!shipment) return undefined;
  const origin = readCoordinate(nodes.find(node => node.id === shipment.origin)?.coordinates);
  const destination = readCoordinate(nodes.find(node => node.id === shipment.destination)?.coordinates);
  return origin && destination ? [origin, destination] : undefined;
}

/** A display-only projection. No assignments, original rows or geometry are changed. */
export function connectionOverlay(network: Network, overlay?: PlanOverlay) {
  const scope = overlay?.scope ?? 'candidate';
  const label = overlay?.label ?? 'All candidate shipments';
  const shipments = overlay?.shipments ?? network.shipments;
  const seen = new Set<string>();
  const connections = shipments.flatMap((shipment): ShipmentConnection[] => {
    const coordinates = shipmentCoordinates(network.nodes, shipment);
    if (seen.has(shipment.id) || !coordinates) return [];
    seen.add(shipment.id);
    return [{ shipment, coordinates }];
  });
  return { scope, label, connections, requestedCount: shipments.length };
}
