import type { ReactNode } from 'react';
import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import RoadIntelligence from './RoadIntelligence';
import { api } from './api';

vi.mock('./api', () => ({ api: vi.fn() }));
vi.mock('./MapViewport', () => ({ default: () => null }));
vi.mock('react-leaflet', () => ({
  MapContainer: ({ children }: { children: ReactNode }) => <div data-testid="road-map">{children}</div>,
  CircleMarker: ({ children, center }: { children: ReactNode; center: number[] }) => <div data-testid="road-map-marker" data-center={JSON.stringify(center)}>{children}</div>,
  Polyline: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  Popup: () => null, TileLayer: () => null,
}));

const event = { id: 'event-1', source_id: 'iowa_dot', title: 'Bridge work on I-35', description: 'A provider-reported lane restriction.', geometry: { type: 'Point', coordinates: [-93.6, 41.3] }, route_name: 'I-35', updated_at: '2026-10-28T10:00:00Z', starts_at: null, ends_at: null, properties: { source_id: 1 } };
const iowa = { id: 'iowa_dot', name: 'Iowa DOT 511', state: 'IA', provider: 'Iowa DOT', available: true, fixture: true, stale: true, retrieved_at: '2026-10-28T10:05:00Z', source_url: 'https://example.iowa.gov/FeatureServer', coverage_complete: true, event_count: 2, unusable_geometry_count: 1, returned_event_count: 2, events_truncated: false, warning: 'The feed is an independent snapshot.', events: [event, { ...event, id: 'event-2', title: 'County road notice', geometry: null }] };
const missouri = { ...iowa, id: 'modot', name: 'MoDOT road events', state: 'MO', provider: 'MoDOT', available: false, fixture: false, coverage_complete: false, event_count: 0, unusable_geometry_count: 0, error: 'ConnectError: provider unavailable', events: [] };
const snapshot = { generated_at: '2026-10-28T11:00:00Z', offline: false, sources: [iowa, missouri], examples: [{ id: 'columbia-desmoines', name: 'Columbia to Des Moines', origin: [-92.3341, 38.9517], destination: [-93.625, 41.5868] }], limitations: ['No full-route geographic coverage is established.'] };
const request = { origin: [-92.3341, 38.9517], destination: [-93.625, 41.5868], routing: 'estimated', buffer_m: 250 };
function comparison(overrides = {}) {
  return { compared_at: '2026-10-28T11:05:00Z', request, sources: [iowa, missouri], alternatives: [{ index: 0, distance_m: 400000, duration_seconds: 18000, geometry: { type: 'LineString', coordinates: [request.origin, request.destination] }, fallback: true, review_required: true, reviews: [{ source_id: iowa.id, source_name: iowa.name, coverage_complete: true, stale: true, nearby_event_count: 1, hits_truncated: false, unusable_geometry_count: 1, nearby_events: [{ ...event, proximity_m: 22.3 }] }, { source_id: missouri.id, source_name: missouri.name, coverage_complete: false, stale: true, unusable_geometry_count: 0, nearby_events: [] }] }], limitations: ['Proximity does not confirm a road closure.'], ...overrides };
}
function deferred<T>() { let resolve!: (value: T) => void; let reject!: (error: Error) => void; const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; }
async function ready() { render(<RoadIntelligence />); await screen.findByRole('button', { name: 'Inspect IA events' }); }
beforeEach(() => { vi.mocked(api).mockReset(); vi.mocked(api).mockResolvedValue(snapshot); });

it('shows dated, incomplete and failed sources without claiming clear roads', async () => {
  await ready();
  expect(screen.getByText('DATED FIXTURE')).toBeInTheDocument();
  expect(screen.getByText('UNAVAILABLE')).toBeInTheDocument();
  expect(screen.getByText('ConnectError: provider unavailable')).toBeInTheDocument();
  expect(screen.getByText('1 records lack usable geometry for screening.')).toBeInTheDocument();
  expect(screen.getByTestId('road-map')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Inspect MO events' }));
  expect(screen.getByText('This feed is unavailable. No road-clear conclusion can be drawn.')).toBeInTheDocument();
});

it('inspects provider text and timestamps and filters the bounded source preview', async () => {
  await ready();
  fireEvent.click(screen.getByRole('button', { name: /Bridge work on I-35/ }));
  const detail = screen.getByRole('article', { name: 'Road event detail' });
  expect(within(detail).getByText('A provider-reported lane restriction.')).toBeInTheDocument();
  expect(within(detail).getByText('Provider update')).toBeInTheDocument();
  expect(within(detail).getByText('Source retrieval')).toBeInTheDocument();
  fireEvent.change(screen.getByRole('searchbox', { name: 'Filter captured road events' }), { target: { value: 'county' } });
  const list = screen.getByLabelText('Captured event list');
  expect(within(list).queryByRole('button', { name: /Bridge work/ })).not.toBeInTheDocument();
  fireEvent.click(within(list).getByRole('button', { name: /County road notice/ }));
  expect(screen.getByText('Unavailable; excluded from proximity screening')).toBeInTheDocument();
});

it('reports absent filtered rows without inferring a road-clear result', async () => {
  await ready();
  fireEvent.change(screen.getByRole('searchbox', { name: 'Filter captured road events' }), { target: { value: 'not-an-event' } });
  expect(screen.getByText('No listed events match this view. This does not establish clear roads or full coverage.')).toBeInTheDocument();
});

it('retries a failed load and rejects malformed coverage instead of rendering invented results', async () => {
  vi.mocked(api).mockRejectedValueOnce(new Error('Backend unavailable'));
  render(<RoadIntelligence />);
  expect(await screen.findByRole('alert')).toHaveTextContent('Backend unavailable');
  vi.mocked(api).mockResolvedValueOnce({ ...snapshot, sources: [{ ...iowa, event_count: -1 }] });
  fireEvent.click(screen.getByRole('button', { name: 'Retry road evidence' }));
  expect(await screen.findByText(/unsupported schema/)).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Inspect IA events' })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Retry road evidence' }));
  expect(await screen.findByRole('button', { name: 'Inspect IA events' })).toBeInTheDocument();
});

it('refreshes official feeds with POST and preserves an explicitly old snapshot after failure', async () => {
  await ready();
  vi.mocked(api).mockRejectedValueOnce(new Error('Provider refresh failed'));
  fireEvent.click(screen.getByRole('button', { name: 'Refresh official road feeds' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Provider refresh failed');
  expect(screen.getByText(/previous saved snapshot remains visible/)).toBeInTheDocument();
  expect(api).toHaveBeenLastCalledWith('/road-intelligence/refresh', {});
  expect(screen.getByRole('button', { name: 'Inspect IA events' })).toBeInTheDocument();
});

it('disables provider refresh for a verified offline rehearsal', async () => {
  vi.mocked(api).mockResolvedValueOnce({ ...snapshot, offline: true });
  await ready();
  expect(screen.getByRole('button', { name: 'Refresh official road feeds' })).toBeDisabled();
  expect(screen.getByText(/Offline rehearsal: dated evidence fixtures/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Recheck saved road evidence' }));
  expect(api).toHaveBeenLastCalledWith('/road-intelligence', undefined);
});

it('compares estimated travel by default and separates nearby events from unavailable coverage', async () => {
  await ready();
  vi.mocked(api).mockResolvedValueOnce(comparison());
  fireEvent.click(screen.getByRole('button', { name: 'Compare planning routes' }));
  expect(await screen.findByRole('heading', { name: 'Alternative review' })).toBeInTheDocument();
  expect(api).toHaveBeenLastCalledWith('/road-intelligence/compare', request);
  expect(screen.getByText('ESTIMATED CONNECTION')).toBeInTheDocument();
  expect(screen.getByText('No matching geometry in this captured source and buffer. Unreported events and uncovered roads remain possible.')).toBeInTheDocument();
  expect(screen.getByText(/No alternative is certified truck-safe/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Bridge work on I-35 22 m' }));
  expect(screen.getByRole('article', { name: 'Road event detail' })).toHaveTextContent('A provider-reported lane restriction.');
  expect(screen.getByRole('button', { name: 'Export comparison JSON' })).toBeInTheDocument();
});

it('selects a supplied corridor and validates coordinates, distinct locations and the buffer', async () => {
  await ready();
  fireEvent.change(screen.getByRole('combobox', { name: 'Planning corridor' }), { target: { value: 'columbia-desmoines' } });
  expect(screen.getByRole('spinbutton', { name: 'Destination latitude' })).toHaveValue(41.5868);
  fireEvent.change(screen.getByRole('spinbutton', { name: 'Origin latitude' }), { target: { value: '100' } });
  expect(screen.getByRole('button', { name: 'Compare planning routes' })).toBeDisabled();
  fireEvent.change(screen.getByRole('spinbutton', { name: 'Origin latitude' }), { target: { value: '38.9517' } });
  fireEvent.change(screen.getByRole('spinbutton', { name: 'Event proximity buffer (meters)' }), { target: { value: '' } });
  expect(screen.getByRole('button', { name: 'Compare planning routes' })).toBeDisabled();
  fireEvent.change(screen.getByRole('spinbutton', { name: 'Event proximity buffer (meters)' }), { target: { value: '250' } });
  expect(screen.getByRole('button', { name: 'Compare planning routes' })).toBeEnabled();
});

it('retains original comparison inputs and warns when they change during a pending request', async () => {
  await ready();
  const pending = deferred<ReturnType<typeof comparison>>();
  vi.mocked(api).mockReturnValueOnce(pending.promise);
  fireEvent.click(screen.getByRole('button', { name: 'Compare planning routes' }));
  fireEvent.change(screen.getByRole('spinbutton', { name: 'Origin longitude' }), { target: { value: '-91' } });
  expect(screen.getByRole('button', { name: 'Comparing captured evidence…' })).toBeDisabled();
  await act(async () => { pending.resolve(comparison()); await pending.promise; });
  expect(screen.getByText(/Displayed routes describe the previous comparison/)).toBeInTheDocument();
  expect(screen.getByText(/-92.3341, 38.9517 → -93.625, 41.5868/)).toBeInTheDocument();
  expect(screen.getByRole('spinbutton', { name: 'Origin longitude' })).toHaveValue(-91);
});

it('does not accept mismatched echoed coordinates or malformed map geometry', async () => {
  await ready();
  vi.mocked(api).mockResolvedValueOnce(comparison({ request: { ...request, origin: [-91, 39] } }));
  fireEvent.click(screen.getByRole('button', { name: 'Compare planning routes' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('unsupported or inconsistent response');
  expect(screen.queryByRole('heading', { name: 'Alternative review' })).not.toBeInTheDocument();
  vi.mocked(api).mockResolvedValueOnce(comparison({ alternatives: [{ ...comparison().alternatives[0], geometry: { type: 'LineString', coordinates: [[NaN, 39], [-92, 40]] } }] }));
  fireEvent.click(screen.getByRole('button', { name: 'Compare planning routes' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('unsupported or inconsistent response');
  expect(screen.queryByRole('heading', { name: 'Alternative review' })).not.toBeInTheDocument();
});

it('preserves prior comparison after a failed retry and marks changed inputs', async () => {
  await ready();
  vi.mocked(api).mockResolvedValueOnce(comparison());
  fireEvent.click(screen.getByRole('button', { name: 'Compare planning routes' }));
  await screen.findByRole('heading', { name: 'Alternative review' });
  fireEvent.change(screen.getByRole('combobox', { name: 'Road comparison travel source' }), { target: { value: 'osrm' } });
  vi.mocked(api).mockRejectedValueOnce(new Error('Routing service unavailable'));
  fireEvent.click(screen.getByRole('button', { name: 'Compare planning routes' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Routing service unavailable');
  expect(screen.getByRole('heading', { name: 'Alternative review' })).toBeInTheDocument();
  expect(screen.getByText(/Displayed routes describe the previous comparison/)).toBeInTheDocument();
});

it('exports exactly the captured comparison with a stale-input marker and read-only scope', async () => {
  await ready();
  vi.mocked(api).mockResolvedValueOnce(comparison());
  fireEvent.click(screen.getByRole('button', { name: 'Compare planning routes' }));
  await screen.findByRole('heading', { name: 'Alternative review' });
  fireEvent.change(screen.getByRole('spinbutton', { name: 'Event proximity buffer (meters)' }), { target: { value: '500' } });
  const create = vi.fn().mockReturnValue('blob:comparison');
  const revoke = vi.fn();
  const anchorClick = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
  vi.stubGlobal('URL', class extends URL { static createObjectURL = create; static revokeObjectURL = revoke; });
  fireEvent.click(screen.getByRole('button', { name: 'Export comparison JSON' }));
  expect(create).toHaveBeenCalledOnce();
  expect(create.mock.calls[0][0]).toBeInstanceOf(Blob);
  expect(anchorClick).toHaveBeenCalledOnce();
  await act(async () => { await new Promise(resolve => setTimeout(resolve, 1)); });
  expect(revoke).toHaveBeenCalledWith('blob:comparison');
  vi.unstubAllGlobals(); anchorClick.mockRestore();
});

it('retains Iowa attribution and unconverted provider-time provenance', async () => {
  vi.mocked(api).mockResolvedValueOnce({ ...snapshot, sources: [{ ...iowa, attribution: 'Iowa Department of Transportation, CC BY 4.0', license_url: 'https://creativecommons.org/licenses/by/4.0/', terms_url: 'https://iowadot.gov/terms', provider_latest_record_edit_at: '2026-10-28T10:00:00Z', provider_time_warning: 'Provider event-time zones are unverified.', events: [{ ...event, provider_times: { IssueDate: '10/28/2026 6:00 AM' } }] }] });
  await ready();
  expect(screen.getByText(/Iowa Department of Transportation, CC BY 4.0/)).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Data license' })).toHaveAttribute('href', 'https://creativecommons.org/licenses/by/4.0/');
  expect(screen.getByText(/Latest provider record edit/)).toHaveTextContent('separate from retrieval');
  fireEvent.click(screen.getByRole('button', { name: /Bridge work on I-35/ }));
  expect(screen.getByText('Original provider time values')).toBeInTheDocument();
  expect(screen.getByText(/literal values have not been converted/)).toBeInTheDocument();
});

it('ignores obsolete initial responses after unmount and blocks duplicate compare actions', async () => {
  const pendingLoad = deferred<typeof snapshot>();
  vi.mocked(api).mockReturnValueOnce(pendingLoad.promise);
  const old = render(<RoadIntelligence />); old.unmount();
  await act(async () => { pendingLoad.resolve(snapshot); await pendingLoad.promise; });
  await ready();
  const pending = deferred<ReturnType<typeof comparison>>();
  vi.mocked(api).mockReturnValueOnce(pending.promise);
  const button = screen.getByRole('button', { name: 'Compare planning routes' });
  fireEvent.click(button); fireEvent.click(button);
  expect(vi.mocked(api).mock.calls.filter(call => call[0] === '/road-intelligence/compare')).toHaveLength(1);
  await act(async () => { pending.resolve(comparison()); await pending.promise; });
});

it('draws the selected comparison record instead of an older preview with the same event ID', async () => {
  await ready();
  const newer = { ...event, geometry: { type: 'Point', coordinates: [-93.1, 41.9] }, description: 'Updated captured comparison geometry.' };
  const capturedSource = { ...iowa, retrieved_at: '2026-10-28T12:30:00Z', events: [newer] };
  const alternative = comparison().alternatives[0];
  const captured = comparison({ sources: [capturedSource, missouri], alternatives: [{ ...alternative, reviews: [{ ...alternative.reviews[0], nearby_events: [{ ...newer, proximity_m: 22.3 }] }, alternative.reviews[1]] }] });
  vi.mocked(api).mockResolvedValueOnce(captured);
  fireEvent.click(screen.getByRole('button', { name: 'Compare planning routes' }));
  await screen.findByRole('heading', { name: 'Alternative review' });
  const centers = () => screen.getAllByTestId('road-map-marker').map(marker => marker.getAttribute('data-center'));
  expect(centers()).toContain('[41.3,-93.6]');
  fireEvent.click(screen.getByRole('button', { name: 'Bridge work on I-35 22 m' }));
  expect(centers()).toContain('[41.9,-93.1]');
  expect(centers()).not.toContain('[41.3,-93.6]');
  const detail = screen.getByRole('article', { name: 'Road event detail' });
  expect(detail).toHaveTextContent('COMPARISON SNAPSHOT RECORD');
  expect(detail).toHaveTextContent('Updated captured comparison geometry.');
  expect(detail).toHaveTextContent(new Date(capturedSource.retrieved_at).toLocaleString('en-US', { timeZone: 'America/Chicago' }));
  fireEvent.click(within(screen.getByLabelText('Captured event list')).getByRole('button', { name: /Bridge work on I-35/ }));
  expect(detail).toHaveTextContent('SOURCE PREVIEW RECORD');
  expect(detail).toHaveTextContent('A provider-reported lane restriction.');
  expect(centers()).toContain('[41.3,-93.6]');
  expect(centers()).not.toContain('[41.9,-93.1]');
});

it('opens captured comparison evidence even when the earlier feed preview was unavailable', async () => {
  vi.mocked(api).mockResolvedValueOnce({ ...snapshot, sources: [{ ...iowa, available: false, event_count: 0, events: [], coverage_complete: false }] });
  await ready();
  expect(screen.getByText('This feed is unavailable. No road-clear conclusion can be drawn.')).toBeInTheDocument();
  vi.mocked(api).mockResolvedValueOnce(comparison());
  fireEvent.click(screen.getByRole('button', { name: 'Compare planning routes' }));
  await screen.findByRole('heading', { name: 'Alternative review' });
  fireEvent.click(screen.getByRole('button', { name: 'Bridge work on I-35 22 m' }));
  expect(screen.getByRole('article', { name: 'Road event detail' })).toHaveTextContent('A provider-reported lane restriction.');
  expect(screen.getByText(/Its source retrieval and geometry may differ/)).toBeInTheDocument();
});

it('explains an OSRM fallback with its exact failure rather than hiding the source error', async () => {
  await ready();
  fireEvent.change(screen.getByRole('combobox', { name: 'Road comparison travel source' }), { target: { value: 'osrm' } });
  vi.mocked(api).mockResolvedValueOnce(comparison({ request: { ...request, routing: 'osrm' }, routing_provenance: 'estimated travel; straight-line visualization, not road geometry', routing_error: 'ConnectError: routing provider unavailable', routing_retrieved_at: null, routing_cache: false, routing_stale: false }));
  fireEvent.click(screen.getByRole('button', { name: 'Compare planning routes' }));
  await screen.findByRole('heading', { name: 'Alternative review' });
  expect(screen.getByText('Estimated fallback reason:')).toBeInTheDocument();
  expect(screen.getByText(/ConnectError: routing provider unavailable/)).toBeInTheDocument();
  expect(screen.getByText('estimated travel; straight-line visualization, not road geometry')).toBeInTheDocument();
  expect(screen.getByText(/No provider retrieval timestamp is available for this route/)).toBeInTheDocument();
});

it('shows routing-cache retrieval time and stale refresh failures separately from road-event sources', async () => {
  await ready();
  fireEvent.change(screen.getByRole('combobox', { name: 'Road comparison travel source' }), { target: { value: 'osrm' } });
  vi.mocked(api).mockResolvedValueOnce(comparison({ request: { ...request, routing: 'osrm' }, alternatives: [{ ...comparison().alternatives[0], fallback: false }], routing_provenance: 'OSRM driving route', routing_retrieved_at: '2026-10-27T23:30:00Z', routing_cache: true, routing_stale: true, routing_refresh_error: 'ReadTimeout: routing refresh timed out' }));
  fireEvent.click(screen.getByRole('button', { name: 'Compare planning routes' }));
  await screen.findByRole('heading', { name: 'Alternative review' });
  expect(screen.getByText(/Provider response retrieved/)).toHaveTextContent('A saved response was reused.');
  expect(screen.getByText(/The routing response is stale/)).toBeInTheDocument();
  expect(screen.getByText('Routing refresh failure:')).toBeInTheDocument();
  expect(screen.getByText(/ReadTimeout: routing refresh timed out/)).toBeInTheDocument();
});
