import { describe, expect, it } from 'vitest';
import { connectionOverlay, readCoordinate, routePaths, selectedRoutePath, shipmentCoordinates } from './networkMapModel';
import type { Network } from './types';

const network = (): Network => ({
  seed: 1, revision: 0, provenance: 'simulated',
  nodes: [{ id: 'DC1', kind: 'dc', name: 'Fictional DC', coordinates: [-92.3, 38.9] }, { id: 'D01', kind: 'destination', name: 'Fictional stop', coordinates: [-90.2, 38.6] }],
  shipments: [1, 2].map(index => ({ id: `SH0${index}`, origin: 'DC1', destination: 'D01', truck_id: `T0${index}`, lot_id: 'L01', quantity_kg: 400, temperature_c: 2, deadline_hours: 6, estimated_hours: 2, estimated_distance_km: 130, review_priority: 'routine' })),
  trucks: [], lots: [], telemetry: [], events: [],
});
const path = (coordinates: unknown = [[-92.3, 38.9], [-90.2, 38.6]], overrides = {}) => ({ geometry: { type: 'LineString', coordinates }, distance: 130000, duration: 7200, ...overrides });

describe('Command map coordinate and alternative selection', () => {
  it('preserves longitude/latitude order without swapping or coercing input', () => {
    expect(readCoordinate([-92.3, 38.9])).toEqual([-92.3, 38.9]);
    expect(readCoordinate([-180, -90])).toEqual([-180, -90]);
    expect(readCoordinate([180, 90, 100])).toEqual([180, 90]);
    for (const value of [null, {}, [], [0], ['-92.3', 38.9], [0, NaN], [Infinity, 0], [181, 0], [0, 91], [0, -91], [-181, 0]]) expect(readCoordinate(value)).toBeUndefined();
  });

  it('rejects the entire malformed path instead of drawing around bad vertices', () => {
    const wrapper = { payload: { routes: [path([[-92.3, 38.9], [NaN, 38.7], [-90.2, 38.6]]), path([[-92.3, 38.9]]), path(undefined, { geometry: { type: 'Polygon', coordinates: [[-92.3, 38.9], [-90.2, 38.6]] } }), path()] } };
    expect(routePaths(wrapper).map(row => row.index)).toEqual([3]);
    expect(routePaths({ payload: { routes: [null, false, {}] } })).toEqual([]);
    for (const value of [null, [], {}, { payload: [] }, { payload: { routes: {} } }]) expect(routePaths(value)).toEqual([]);
  });

  it('preserves provider alternative indexes and can select beyond the old first-three display', () => {
    const paths = routePaths({ payload: { routes: [path(), path(null), path(), path()] } });
    expect(paths.map(row => row.index)).toEqual([0, 2, 3]);
    expect(selectedRoutePath(paths, 3)?.index).toBe(3);
    expect(selectedRoutePath(paths, 2)?.index).toBe(2);
    expect(selectedRoutePath(paths)?.index).toBe(0);
  });

  it('chooses the first valid geometry when the requested alternative cannot render', () => {
    const paths = routePaths({ payload: { routes: [path(null), path()] } });
    for (const requested of [0, -1, 99, 1.5, NaN, Infinity]) expect(selectedRoutePath(paths, requested)?.index).toBe(1);
    expect(selectedRoutePath([], 0)).toBeUndefined();
  });

  it('leaves unavailable metrics explicit while retaining usable geometry', () => {
    const [result] = routePaths({ payload: { routes: [path(undefined, { distance: -1, duration: '7200' })] } });
    expect(result.distanceM).toBeNull();
    expect(result.durationSeconds).toBeNull();
    expect(routePaths({ payload: { routes: [path(undefined, { distance: 0, duration: 0 })] } })[0]).toMatchObject({ distanceM: 0, durationSeconds: 0 });
  });

  it('does not alias or change provider geometry while deriving a map path', () => {
    const wrapper = { payload: { routes: [path()] } };
    const original = JSON.stringify(wrapper);
    const paths = routePaths(wrapper);
    paths[0].coordinates[0][0] = 0;
    expect(JSON.stringify(wrapper)).toBe(original);
  });
});

describe('Display-only allocation overlays', () => {
  it('defaults to all candidates and resolves selected origin/destination', () => {
    const source = network();
    expect(connectionOverlay(source)).toMatchObject({ scope: 'candidate', label: 'All candidate shipments', requestedCount: 2 });
    expect(connectionOverlay(source).connections.map(row => row.shipment.id)).toEqual(['SH01', 'SH02']);
    expect(shipmentCoordinates(source.nodes, source.shipments[0])).toEqual([[-92.3, 38.9], [-90.2, 38.6]]);
    expect(shipmentCoordinates(source.nodes)).toBeUndefined();
  });

  it('shows only proposed rows and preserves scenario-D substituted lot without rerouting', () => {
    const source = network(), original = JSON.stringify(source);
    const proposed = { ...source.shipments[1], lot_id: 'L02' };
    const overlay = connectionOverlay(source, { label: 'Scenario D', scope: 'scenario', shipments: [proposed] });
    expect(overlay.connections).toHaveLength(1);
    expect(overlay.connections[0].shipment).toMatchObject({ id: 'SH02', lot_id: 'L02' });
    expect(overlay.connections[0].coordinates).toEqual(shipmentCoordinates(source.nodes, source.shipments[1]));
    expect(JSON.stringify(source)).toBe(original);
  });

  it('does not fall back to candidates when approved assignment set is empty', () => {
    expect(connectionOverlay(network(), { label: 'Approved assignments', scope: 'approved', shipments: [] })).toEqual({ scope: 'approved', label: 'Approved assignments', connections: [], requestedCount: 0 });
  });

  it('counts but does not draw duplicate, unknown or invalid endpoint connections', () => {
    const source = network();
    const rows = [source.shipments[0], source.shipments[0], { ...source.shipments[1], origin: 'UNKNOWN' }];
    expect(connectionOverlay(source, { label: 'Review set', scope: 'scenario', shipments: rows })).toMatchObject({ requestedCount: 3, connections: [{ shipment: source.shipments[0] }] });
    source.nodes[1].coordinates = [-90.2, Infinity];
    expect(shipmentCoordinates(source.nodes, source.shipments[0])).toBeUndefined();
    expect(connectionOverlay(source).connections).toEqual([]);
  });

  it('copies display endpoints so a map projection cannot change network locations', () => {
    const source = network(), before = JSON.stringify(source);
    connectionOverlay(source).connections[0].coordinates[0][0] = 0;
    expect(JSON.stringify(source)).toBe(before);
  });
});
