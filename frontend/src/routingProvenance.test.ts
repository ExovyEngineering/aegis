import { expect, it } from 'vitest';
import { routingSourceLabels } from './routingProvenance';

it('keeps estimated journey metrics separate from successful OSRM geometry', () => {
  const labels = routingSourceLabels({ fallback: true, travel_time_fallback: true, distance_fallback: true, geometry_fallback: false });
  expect(labels.travel).toBe('Estimated travel');
  expect(labels.geometryEstimated).toBe(false);
  expect(labels.detail).toContain('geometry: OSRM');
});
it('does not relabel OSRM journey metrics when geometry falls back', () => {
  const labels = routingSourceLabels({ fallback: true, travel_time_fallback: false, distance_fallback: false, geometry_fallback: true });
  expect(labels.travel).toBe('OSRM travel');
  expect(labels.geometryEstimated).toBe(true);
});
