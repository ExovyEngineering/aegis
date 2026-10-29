import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import EventImpactPanel from './EventImpactPanel';
import { api } from './api';
import { downloadCaptured } from './CommandRouteReview';
import type { Network, Shipment } from './types';

vi.mock('./api', () => ({ api: vi.fn() }));
vi.mock('./CommandRouteReview', () => ({ downloadCaptured: vi.fn() }));

// Explicit unit-test transport fixtures, not operational observations or solver measurements.
const candidate: Shipment = { id: 'SH11', origin: 'DC1', destination: 'D01', lot_id: 'L01', truck_id: 'T01', quantity_kg: 300, temperature_c: 3.5, deadline_hours: 6, estimated_hours: 2, estimated_distance_km: 120, review_priority: 'routine' };
const network: Network = { seed: 20261026, revision: 7, provenance: 'Unit-test simulation', nodes: [], trucks: [], lots: [], shipments: [candidate], telemetry: [], events: [] };
const previewId = 'a'.repeat(64);
function comparison(event = 'temperature_excursion', shipment = 'SH11', revision = 7) {
  const state = { origin: 'DC1', destination: 'D01', truck_id: 'T01', lot_id: 'L01', quantity_kg: 300, estimated_hours: 2, estimated_distance_km: 120, deadline_hours: 6, temperature_c: 3.5, review_priority: 'routine', routing_provenance: 'Unit-test estimate', deadline_margin_hours: 4, lot_inventory_kg: 1500, lot_held: false, lot_recalled: false, lot_eligible: true, truck_eligible: true, truck_refrigerated: true, direct_exclusions: [] };
  const summary = { total_logistics_cost: 250, unmet_demand_kg: 100, delayed_shipments: 0, affected_shipments: 0, review_priority_count: 0, food_waste_kg: 0, selected_shipments: 2, supplied_kg: 600, solver_status: 'OPTIMAL', feasible: true, constraint_violations: 0, constraint_review_passed: true, proposed_hold_lots: [], selected_ids: ['SH11', 'SH12'], selected_lots: { SH11: 'L01', SH12: 'L02' }, verification_required_ids: [] };
  return structuredClone({ network_revision: revision, snapshot_id: 'b'.repeat(64), preview_id: previewId, generated_at: '2026-10-29T18:00:00Z', event, event_label: 'Unit-test simulated disruption', shipment_id: shipment, simulation: true, read_only: true, operational_state_modified: false, requires_explicit_apply: true,
    shipment: { id: shipment, before: state, after: { ...state, temperature_c: 9, review_priority: 'high' }, changes: [{ field: 'temperature_c', label: 'Simulated cargo temperature', unit: '°C', before: 3.5, after: 9, delta: 5.5 }, { field: 'review_priority', label: 'Operational review priority', unit: null, before: 'routine', after: 'high', delta: null }] },
    route_effects: { geometry_changed: false, distance_changed: false, stop_order_changed: false, duration_change_hours: 0, explanation: 'Unit-test event does not compute road geometry or publish a driver route.' }, resource_effects: [], candidate_effects: [{ shipment_id: shipment, before_exclusions: [], after_exclusions: [], note: 'Unit-test original-lot checks only' }], assignments: { current_count: 3, would_be_invalidated: 3, explanation: 'All three unit-test assignments would be cleared only by explicit apply.' },
    scenarios: ['A', 'B', 'C', 'D'].map(scenario => ({ scenario, name: `Unit-test scenario ${scenario}`, before: summary, after: summary, delta: { total_logistics_cost: 0, unmet_demand_kg: 0, delayed_shipments: 0, affected_shipments: 0, review_priority_count: 0, food_waste_kg: 0, selected_shipments: 0, supplied_kg: 0 }, added_shipments: [], removed_shipments: [], lot_changes: [], proposed_hold_lots_added: [], proposed_hold_lots_removed: [], verification_added: [], verification_removed: [] })), limitations: ['Unit-test simulation; not physical sensing.', 'One-wave allocations do not dispatch or reroute.'], next_steps: ['Inspect the captured comparison, then separately apply if intended.'] });
}
function receipt(overrides: Record<string, unknown> = {}) { return { revision: 8, network_revision_before: 7, assignments_invalidated: true, assignments_removed: 3, preview_id: previewId, operational_state_modified: true, ...overrides }; }
function deferred<T>() { let resolve!: (value: T) => void; let reject!: (reason: Error) => void; const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; }
function mount(overrides: Record<string, any> = {}) {
  const props = { network, selected: candidate, disabled: false, onBusyChange: vi.fn(), onApplied: vi.fn().mockResolvedValue(undefined), onCompare: vi.fn(), ...overrides };
  return { ...render(<EventImpactPanel {...props} />), props };
}
async function preview() { await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Preview event impact' })); }); }
function consent() { fireEvent.click(screen.getByRole('checkbox', { name: 'I intend to change this simulation and clear all approved assignments.' })); }
async function apply() { await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Apply previewed event' })); }); }
beforeEach(() => {
  vi.mocked(api).mockReset(); vi.mocked(downloadCaptured).mockReset();
  vi.mocked(api).mockImplementation(async (path, body: any): Promise<any> => {
    if (path === '/events/preview') return comparison(body.event, body.shipment_id, body.expected_network_revision);
    if (path === '/events') return receipt();
    throw new Error('Unexpected mocked endpoint: ' + path);
  });
});

it('produces a read-only result and four comparisons without applying an event', async () => {
  const view = mount();
  expect(api).not.toHaveBeenCalled();
  expect(screen.getByText(/No impact result yet/)).toBeInTheDocument();
  await preview();
  expect(api).toHaveBeenCalledExactlyOnceWith('/events/preview', { event: 'temperature_excursion', shipment_id: 'SH11', expected_network_revision: 7 });
  expect(screen.getByText(/No event, hold or assignment has been changed/)).toBeInTheDocument();
  expect(screen.getByText('Road geometry and stop order stay unchanged.')).toBeInTheDocument();
  const table = screen.getAllByRole('table')[1];
  expect(within(table).getAllByRole('row')).toHaveLength(5);
  expect(screen.getByRole('button', { name: 'Apply previewed event' })).toBeDisabled();
  expect(view.props.onBusyChange.mock.calls).toEqual([[true], [false]]);
  expect(view.props.onApplied).not.toHaveBeenCalled();
});

it('requires consent and submits the exact preview identity and network revision', async () => {
  const pending = deferred<any>();
  const view = mount();
  await preview();
  fireEvent.click(screen.getByRole('button', { name: 'Apply previewed event' }));
  expect(api).toHaveBeenCalledTimes(1);
  consent();
  vi.mocked(api).mockReturnValueOnce(pending.promise);
  await apply();
  expect(api).toHaveBeenLastCalledWith('/events', { event: 'temperature_excursion', shipment_id: 'SH11', expected_network_revision: 7, preview_id: previewId });
  expect(screen.getByRole('button', { name: 'Applying simulated event…' })).toBeDisabled();
  expect(screen.queryByText('Simulated event applied to SH11.')).not.toBeInTheDocument();
  expect(view.props.onApplied).not.toHaveBeenCalled();
  await act(async () => { pending.resolve(receipt()); });
  expect(view.props.onApplied).toHaveBeenCalledTimes(1);
  expect(screen.getByText('Simulated event applied to SH11.')).toBeInTheDocument();
  expect(screen.getByText(/Network revision 8; 3 approved assignments removed/)).toBeInTheDocument();
  expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Compare refreshed response plans' }));
  expect(view.props.onCompare).toHaveBeenCalledTimes(1);
  expect(api).toHaveBeenCalledTimes(2);
});

it.each(['event', 'shipment', 'network'] as const)('marks an old comparison stale and resets consent after %s changes', async change => {
  const view = mount(); await preview(); consent();
  expect(screen.getByRole('button', { name: 'Apply previewed event' })).toBeEnabled();
  if (change === 'event') fireEvent.change(screen.getByRole('combobox', { name: 'Event type' }), { target: { value: 'road_closure' } });
  if (change === 'shipment') view.rerender(<EventImpactPanel {...view.props} selected={{ ...candidate, id: 'SH12' }} />);
  if (change === 'network') view.rerender(<EventImpactPanel {...view.props} network={{ ...network, revision: 8 }} />);
  expect(screen.getByText(/This is an older comparison/)).toBeInTheDocument();
  expect(screen.getByRole('checkbox')).not.toBeChecked();
  expect(screen.getByRole('checkbox')).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Apply previewed event' })).toBeDisabled();
  expect(api).toHaveBeenCalledTimes(1);
});

it('clears the old comparison immediately and keeps failure visible when a new preview fails', async () => {
  mount(); await preview(); consent();
  const pending = deferred<any>(); vi.mocked(api).mockReturnValueOnce(pending.promise);
  await preview();
  expect(screen.getByRole('status')).toHaveTextContent('No event has been applied');
  expect(screen.queryByRole('button', { name: 'Apply previewed event' })).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Export event impact JSON' })).not.toBeInTheDocument();
  await act(async () => { pending.reject(new Error('409 Network changed; reload and preview again')); });
  expect(screen.getByRole('alert')).toHaveTextContent('409 Network changed');
  expect(screen.queryByText(/Preview produced for/)).not.toBeInTheDocument();
  expect(api).toHaveBeenCalledTimes(2);
  expect(vi.mocked(api).mock.calls.every(([path]) => path === '/events/preview')).toBe(true);
});

it.each([
  ['event identity', (value: any) => { value.event = 'road_closure'; }],
  ['shipment identity', (value: any) => { value.shipment_id = 'SH12'; }],
  ['network revision', (value: any) => { value.network_revision = 8; }],
  ['preview checksum', (value: any) => { value.preview_id = 'not-a-hash'; }],
  ['operational mutation claim', (value: any) => { value.operational_state_modified = true; }],
  ['nonfinite scenario result', (value: any) => { value.scenarios[0].after.total_logistics_cost = NaN; }],
  ['resource schema', (value: any) => { delete value.resource_effects; }],
  ['proposed hold schema', (value: any) => { delete value.scenarios[0].proposed_hold_lots_added; }],
] as const)('rejects a malformed or mismatched preview: %s', async (_name, modify) => {
  const invalid = comparison(); modify(invalid); vi.mocked(api).mockResolvedValueOnce(invalid);
  const view = mount(); await preview();
  expect(screen.getByRole('alert')).toHaveTextContent(/did not match|invalid|unsupported/i);
  expect(screen.queryByRole('button', { name: 'Apply previewed event' })).not.toBeInTheDocument();
  expect(view.props.onApplied).not.toHaveBeenCalled();
  expect(api).toHaveBeenCalledTimes(1);
});

it('shows a failed apply without optimistic receipt or retained consent', async () => {
  const view = mount(); await preview(); consent();
  const pending = deferred<any>(); vi.mocked(api).mockReturnValueOnce(pending.promise);
  await apply();
  expect(screen.queryByText('Simulated event applied to SH11.')).not.toBeInTheDocument();
  await act(async () => { pending.reject(new Error('409 Preview is stale; no event was applied')); });
  expect(screen.getByRole('alert')).toHaveTextContent('409 Preview is stale');
  expect(screen.queryByText('Simulated event applied to SH11.')).not.toBeInTheDocument();
  expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
  expect(view.props.onApplied).not.toHaveBeenCalled();
  await preview();
  expect(screen.getByRole('checkbox')).not.toBeChecked();
  expect(screen.getByRole('button', { name: 'Apply previewed event' })).toBeDisabled();
});

it.each([
  ['wrong preview', { preview_id: 'c'.repeat(64) }],
  ['wrong revision', { revision: 99 }],
  ['wrong original revision', { network_revision_before: 6 }],
  ['unconfirmed mutation', { operational_state_modified: false }],
  ['unconfirmed assignment invalidation', { assignments_invalidated: false }],
  ['noninteger removed count', { assignments_removed: 2.5 }],
  ['negative removed count', { assignments_removed: -1 }],
  ['mismatched removed count', { assignments_removed: 2 }],
] as const)('does not present an unverified apply receipt: %s', async (_name, override) => {
  const view = mount(); await preview(); consent(); vi.mocked(api).mockResolvedValueOnce(receipt(override)); await apply();
  expect(screen.getByRole('alert')).toHaveTextContent(/could not verify|receipt/i);
  expect(screen.queryByText('Simulated event applied to SH11.')).not.toBeInTheDocument();
  expect(view.props.onApplied).not.toHaveBeenCalled();
});

it('retains a confirmed applied receipt if only the subsequent network refresh fails', async () => {
  const view = mount({ onApplied: vi.fn().mockRejectedValue(new Error('Refresh network unavailable')) });
  await preview(); consent(); await apply();
  expect(view.props.onApplied).toHaveBeenCalledTimes(1);
  expect(screen.getByText('Simulated event applied to SH11.')).toBeInTheDocument();
  expect(screen.getByRole('alert')).toHaveTextContent(/applied|refresh/i);
  expect(screen.queryByRole('button', { name: 'Apply previewed event' })).not.toBeInTheDocument();
});

it('discloses repeated no-change events and every assignment that apply would remove', async () => {
  const repeat = comparison(); repeat.shipment.changes = []; vi.mocked(api).mockResolvedValueOnce(repeat);
  mount(); await preview();
  expect(screen.getByText(/already at this event's modeled setting/)).toHaveTextContent('advance the revision and clear every approved assignment');
  expect(screen.getByText('all 3 approved assignments')).toBeInTheDocument();
  expect(screen.getByText(/including unrelated trips/)).toBeInTheDocument();
  expect(api).toHaveBeenCalledTimes(1);
});

it('exports the captured preview and actual receipt as distinct stages without another request', async () => {
  mount(); await preview();
  fireEvent.click(screen.getByRole('button', { name: 'Export event impact JSON' }));
  expect(downloadCaptured).toHaveBeenNthCalledWith(1, 'aegis-event-impact-SH11.json', { stage: 'preview', comparison: comparison(), receipt: null });
  expect(api).toHaveBeenCalledTimes(1);
  consent(); await apply();
  fireEvent.click(screen.getByRole('button', { name: 'Export event impact JSON' }));
  expect(downloadCaptured).toHaveBeenNthCalledWith(2, 'aegis-event-impact-SH11.json', { stage: 'applied', comparison: comparison(), receipt: receipt() });
  expect(api).toHaveBeenCalledTimes(2);
});

it('ignores a delayed preview after the selected shipment changes', async () => {
  const pending = deferred<any>(); vi.mocked(api).mockReturnValueOnce(pending.promise);
  const view = mount(); await preview();
  view.rerender(<EventImpactPanel {...view.props} selected={{ ...candidate, id: 'SH12' }} />);
  await act(async () => { pending.resolve(comparison()); });
  expect(screen.queryByText(/Preview produced for SH11/)).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Apply previewed event' })).not.toBeInTheDocument();
  expect(screen.getByRole('alert')).toHaveTextContent('selection or network changed during calculation');
  expect(view.props.onBusyChange).toHaveBeenLastCalledWith(false);
  expect(view.props.onApplied).not.toHaveBeenCalled();
});

it.each(['resolve', 'reject'] as const)('does not publish an obsolete preview after unmount: %s', async outcome => {
  const pending = deferred<any>(); vi.mocked(api).mockReturnValueOnce(pending.promise);
  const view = mount(); await preview(); view.unmount();
  await act(async () => { if (outcome === 'resolve') pending.resolve(comparison()); else pending.reject(new Error('Late unit-test failure')); });
  expect(view.props.onApplied).not.toHaveBeenCalled();
  expect(view.props.onBusyChange.mock.calls).toEqual([[true], [false]]);
  expect(api).toHaveBeenCalledTimes(1);
  expect(downloadCaptured).not.toHaveBeenCalled();
});

it('prevents overlapping preview requests and disables controls while computing', async () => {
  const pending = deferred<any>(); vi.mocked(api).mockReturnValueOnce(pending.promise);
  mount();
  await act(async () => { const button = screen.getByRole('button', { name: 'Preview event impact' }); fireEvent.click(button); fireEvent.click(button); });
  expect(api).toHaveBeenCalledTimes(1);
  expect(screen.getByRole('button', { name: 'Computing impact…' })).toBeDisabled();
  expect(screen.getByRole('combobox', { name: 'Event type' })).toBeDisabled();
  await act(async () => { pending.resolve(comparison()); });
  expect(screen.getByRole('button', { name: 'Preview event impact' })).toBeEnabled();
});

it('submits an approved apply only once and refreshes parent state if it completes after unmount', async () => {
  const pending = deferred<any>();
  const view = mount(); await preview(); consent(); vi.mocked(api).mockReturnValueOnce(pending.promise);
  await act(async () => { const button = screen.getByRole('button', { name: 'Apply previewed event' }); fireEvent.click(button); fireEvent.click(button); });
  expect(vi.mocked(api).mock.calls.filter(([path]) => path === '/events')).toHaveLength(1);
  expect(view.props.onApplied).not.toHaveBeenCalled();
  view.unmount();
  await act(async () => { pending.resolve(receipt()); });
  expect(view.props.onApplied).toHaveBeenCalledTimes(1);
  expect(view.props.onBusyChange.mock.calls).toEqual([[true], [false], [true], [false]]);
  expect(downloadCaptured).not.toHaveBeenCalled();
});

it('requires a selected shipment and respects the shared busy state', () => {
  const view = mount({ selected: undefined });
  expect(screen.getByRole('button', { name: 'Preview event impact' })).toBeDisabled();
  view.rerender(<EventImpactPanel {...view.props} selected={candidate} disabled />);
  expect(screen.getByRole('button', { name: 'Preview event impact' })).toBeDisabled();
  expect(screen.getByRole('combobox', { name: 'Event type' })).toBeDisabled();
  expect(api).not.toHaveBeenCalled();
});
