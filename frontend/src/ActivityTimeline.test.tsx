import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import ActivityTimeline from './ActivityTimeline';
import { api } from './api';

vi.mock('./api', () => ({ api: vi.fn() }));
const actions = [{ id: 'event', label: 'Simulated event' }, { id: 'approve', label: 'Plan approval' }, { id: 'incident', label: 'Driver incident report' }];
const identifier = 'a'.repeat(64);
function record(id: number, overrides: any = {}) {
  return { id, timestamp: '2026-10-29T20:00:00+00:00', timestamp_raw: '2026-10-29T20:00:00+00:00', actor: 'Unit-test self-declared actor', action: 'event', action_label: 'Simulated event', summary: `Recorded test event ${id}.`, scope: 'Recorded simulated activity; current state may differ', payload: { shipment_id: 'SH11', event: 'delivery_delay' }, payload_error: null, payload_sha256: 'b'.repeat(64), payload_prefix_sha256: null, payload_bytes: 53, metadata_errors: [], explicit_shipment_id: 'SH11', suggested_view: 'command', citation: { label: `Internal audit row ${id}`, path: `audit/${id}` }, ...overrides };
}
function page(overrides: any = {}) {
  const rows = overrides.records ?? [record(5), record(4, { action: 'approve', action_label: 'Plan approval', summary: 'A simulated plan approval was recorded.', explicit_shipment_id: null, payload: { scenario: 'A' } })];
  return structuredClone({ available: true, records: rows, actions, snapshot_latest_id: 5, snapshot_id: identifier, total_matching: 3, next_cursor: 'opaque-older-page', read_only: true, operational_state_modified: false, generated_at: '2026-10-29T20:05:00+00:00', filters: { action: null, shipment_id: null }, returned_records: rows.length, limitations: ['This is not an authenticated or tamper-proof ledger.', 'Missing historical effects are not reconstructed.'], ...overrides });
}
function deferred<T>() { let resolve!: (value: T) => void; let reject!: (reason: Error) => void; const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; }
async function mount(props: Parameters<typeof ActivityTimeline>[0] = {}) {
  let view!: ReturnType<typeof render>;
  await act(async () => { view = render(<ActivityTimeline {...props} />); });
  return view;
}
beforeEach(() => { vi.mocked(api).mockReset(); vi.mocked(api).mockResolvedValue(page() as any); });

it('loads actual captured records and explains the limits of absence, identity and history', async () => {
  await mount();
  expect(api).toHaveBeenCalledWith('/activity?limit=25');
  expect(screen.getByRole('heading', { name: 'Activity history' })).toBeInTheDocument();
  expect(screen.getByText(/Actor names are self-declared/)).toBeInTheDocument();
  expect(screen.getByText(/empty history does not mean a button failed/)).toBeInTheDocument();
  expect(screen.getByText('2 of 3 matching records loaded')).toBeInTheDocument();
  expect(screen.getAllByRole('article')).toHaveLength(2);
  expect(screen.getByRole('article', { name: 'Audit record 4' })).toHaveTextContent('no explicit shipment ID recorded');
  expect(vi.mocked(api).mock.calls.every(([,body]) => body === undefined)).toBe(true);
});

it('keeps draft filters separate from the captured page until explicitly applied', async () => {
  await mount();
  fireEvent.change(screen.getByRole('combobox', { name: 'Recorded action' }), { target: { value: 'approve' } });
  expect(screen.getByText(/Filter inputs changed/)).toBeInTheDocument();
  expect(screen.getByRole('article', { name: 'Audit record 5' })).toBeInTheDocument();
  expect(api).toHaveBeenCalledTimes(1);
  expect(screen.getByRole('button', { name: 'Load older activity' })).toBeDisabled();
  vi.mocked(api).mockResolvedValueOnce(page({ records: [record(4, { action: 'approve', explicit_shipment_id: null })], filters: { action: 'approve', shipment_id: null }, total_matching: 1, next_cursor: null }) as any);
  await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Apply activity filters' })); });
  expect(api).toHaveBeenLastCalledWith('/activity?limit=25&action=approve');
  expect(screen.queryByRole('article', { name: 'Audit record 5' })).not.toBeInTheDocument();
  expect(screen.getByText('Filters: approve · all explicit shipment IDs')).toBeInTheDocument();
});

it('trims the explicit shipment filter and accepts only matching recorded IDs', async () => {
  await mount();
  fireEvent.change(screen.getByRole('textbox', { name: 'Explicit shipment ID' }), { target: { value: '  SH11  ' } });
  vi.mocked(api).mockResolvedValueOnce(page({ records: [record(5)], filters: { action: null, shipment_id: 'SH11' }, total_matching: 1, next_cursor: null }) as any);
  await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Apply activity filters' })); });
  expect(api).toHaveBeenLastCalledWith('/activity?limit=25&shipment_id=SH11');
  expect(screen.getByText(/Shipment filtering matches an explicitly recorded/)).toBeInTheDocument();
  expect(screen.getByText('Filters: all actions · SH11')).toBeInTheDocument();
});

it('rejects invalid shipment input without requesting or changing history', async () => {
  await mount();
  fireEvent.change(screen.getByRole('textbox', { name: 'Explicit shipment ID' }), { target: { value: '../SH11/?all=1' } });
  expect(screen.getByRole('button', { name: 'Apply activity filters' })).toBeDisabled();
  expect(screen.getByText(/Use letters, digits, underscores/)).toBeInTheDocument();
  expect(api).toHaveBeenCalledTimes(1);
});

it('seeds an optional initial shipment filter without inferring it from related lot or plan records', async () => {
  vi.mocked(api).mockResolvedValue(page({ records: [record(5)], total_matching: 1, next_cursor: null, filters: { action: null, shipment_id: 'SH11' } }) as any);
  await mount({ initialShipmentId: 'SH11' });
  expect(api).toHaveBeenCalledWith('/activity?limit=25&shipment_id=SH11');
  expect(screen.getByRole('textbox', { name: 'Explicit shipment ID' })).toHaveValue('SH11');
});

it('loads older rows only from the same snapshot and preserves descending order', async () => {
  await mount();
  vi.mocked(api).mockResolvedValueOnce(page({ records: [record(2)], next_cursor: null }) as any);
  await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Load older activity' })); });
  expect(api).toHaveBeenLastCalledWith('/activity?limit=25&cursor=opaque-older-page');
  expect(screen.getAllByRole('article').map(item => item.getAttribute('aria-label'))).toEqual(['Audit record 5', 'Audit record 4', 'Audit record 2']);
  expect(screen.getByText('3 of 3 matching records loaded')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Load older activity' })).toBeDisabled();
  expect(screen.getByText('End of this captured history.')).toBeInTheDocument();
});

it.each([
  ['snapshot changed', { snapshot_id: 'c'.repeat(64), records: [record(2)] }],
  ['latest ID changed', { snapshot_latest_id: 6, records: [record(2)] }],
  ['row duplicated', { records: [record(4)] }],
  ['newer row substituted', { records: [record(5)] }],
  ['matching total changed', { total_matching: 4, records: [record(2)] }],
])('blocks pagination when %s without discarding prior captured evidence', async (_name, overrides) => {
  await mount(); vi.mocked(api).mockResolvedValueOnce(page(overrides) as any);
  await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Load older activity' })); });
  expect(await screen.findByRole('alert')).toHaveTextContent(/changed|captured snapshot/);
  expect(screen.getAllByRole('article')).toHaveLength(2);
  expect(screen.getByRole('button', { name: 'Load older activity' })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Export captured activity JSON' })).toBeEnabled();
});

it('requires explicit refresh after a paging failure and then replaces the captured view', async () => {
  await mount(); vi.mocked(api).mockRejectedValueOnce(new Error('Captured activity changed; reload'));
  await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Load older activity' })); });
  expect(screen.getByRole('alert')).toHaveTextContent('Captured activity changed');
  vi.mocked(api).mockResolvedValueOnce(page({ records: [record(6)], snapshot_latest_id: 6, total_matching: 1, next_cursor: null, snapshot_id: 'd'.repeat(64) }) as any);
  await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Refresh activity' })); });
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  expect(screen.queryByRole('article', { name: 'Audit record 5' })).not.toBeInTheDocument();
  expect(screen.getByRole('article', { name: 'Audit record 6' })).toBeInTheDocument();
});

it.each([
  ['early end of history', { records: [record(5)], total_matching: 3, next_cursor: null }],
  ['cursor after all rows', { records: [record(5)], total_matching: 1, next_cursor: 'extra-page' }],
])('rejects incoherent first-page counts: %s', async (_name, overrides) => {
  vi.mocked(api).mockResolvedValueOnce(page(overrides) as any);await mount();
  expect(screen.getByRole('alert')).toHaveTextContent('captured record count');
  expect(screen.queryByRole('article')).not.toBeInTheDocument();
});

it('does not append a page that would exceed the captured matching-record total', async () => {
  await mount();vi.mocked(api).mockResolvedValueOnce(page({records:[record(2),record(1)],next_cursor:null}) as any);
  await act(async()=>{fireEvent.click(screen.getByRole('button',{name:'Load older activity'}));});
  expect(screen.getByRole('alert')).toHaveTextContent('captured record count');
  expect(screen.getAllByRole('article')).toHaveLength(2);
});

it('refresh uses captured filters rather than silently applying an edited draft', async () => {
  await mount();
  fireEvent.change(screen.getByRole('combobox', { name: 'Recorded action' }), { target: { value: 'approve' } });
  await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Refresh activity' })); });
  expect(api).toHaveBeenLastCalledWith('/activity?limit=25');
  expect(screen.getByText(/Filter inputs changed/)).toBeInTheDocument();
  expect(screen.getByText('Filters: all actions · all explicit shipment IDs')).toBeInTheDocument();
});

it('preserves the captured view after a failed filter request without mislabeling it as fresh', async () => {
  await mount();
  fireEvent.change(screen.getByRole('combobox', { name: 'Recorded action' }), { target: { value: 'approve' } });
  vi.mocked(api).mockRejectedValueOnce(new Error('Activity history unavailable'));
  await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Apply activity filters' })); });
  expect(screen.getByRole('alert')).toHaveTextContent('previous captured records remain');
  expect(screen.getByText('Filters: all actions · all explicit shipment IDs')).toBeInTheDocument();
  expect(screen.getAllByRole('article')).toHaveLength(2);
});

it('reports initial unavailability and retries without inventing an empty success', async () => {
  vi.mocked(api).mockRejectedValueOnce(new Error('No audit schema'));
  await mount();
  expect(screen.getByRole('alert')).toHaveTextContent('No audit schema');
  expect(screen.queryByText(/No recorded actions match/)).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Export captured activity JSON' })).not.toBeInTheDocument();
  await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Refresh activity' })); });
  expect(screen.getAllByRole('article')).toHaveLength(2);
});

it('shows a valid empty snapshot as empty recorded evidence rather than a product failure', async () => {
  vi.mocked(api).mockResolvedValueOnce(page({ records: [], returned_records: 0, total_matching: 0, next_cursor: null, snapshot_latest_id: 0 }) as any);
  await mount();
  expect(screen.getByText('0 of 0 matching records loaded')).toBeInTheDocument();
  expect(screen.getByText(/No recorded actions match this captured view/)).toBeInTheDocument();
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});

it.each([
  ['writes indicated', { operational_state_modified: true }],
  ['not read-only', { read_only: false }],
  ['unavailable success', { available: false }],
  ['invalid snapshot', { snapshot_id: 'missing' }],
  ['bad actions', { actions: [null] }],
  ['duplicate actions', { actions: [actions[0], actions[0]] }],
  ['bad limitations', { limitations: [false] }],
  ['unexpected navigation', { records: [record(5, { suggested_view: 'external-script' })] }],
  ['malformed citation', { records: [record(5, { citation: null })] }],
  ['bad metadata', { records: [record(5, { metadata_errors: [false] })] }],
  ['bad payload shape', { records: [record(5, { payload: [] })] }],
  ['duplicate IDs', { records: [record(5), record(5)] }],
  ['ascending IDs', { records: [record(4), record(5)] }],
  ['unexpected return count', { returned_records: 10 }],
  ['too many records', { records: Array.from({length:26},(_,i)=>record(30-i)), snapshot_latest_id:30,total_matching:26 }],
  ['unusable empty cursor', { next_cursor: '' }],
])('rejects malformed activity response: %s', async (_name, overrides) => {
  vi.mocked(api).mockResolvedValueOnce(page(overrides) as any); await mount();
  expect(screen.getByRole('alert')).toHaveTextContent('bounded read-only contract');
  expect(screen.queryByRole('article')).not.toBeInTheDocument();
});

it('rejects a response for different filters even if its rows are otherwise valid', async () => {
  vi.mocked(api).mockResolvedValueOnce(page({ filters: { action: 'approve', shipment_id: null } }) as any);
  await mount(); expect(screen.getByRole('alert')).toHaveTextContent('did not match the requested filters');
});

it('rejects a shipment-filtered response containing records without that explicit shipment ID', async () => {
  vi.mocked(api).mockResolvedValueOnce(page({ filters: { action: null, shipment_id: 'SH11' } }) as any);
  await mount({ initialShipmentId: 'SH11' }); expect(screen.getByRole('alert')).toHaveTextContent('did not match the requested filters');
});

it('shows corrupted or oversized raw evidence explicitly and labels a prefix hash correctly', async () => {
  vi.mocked(api).mockResolvedValueOnce(page({ records: [record(5, { payload: null, payload_error: 'Payload exceeds the 32768-byte inspection bound; full bytes were not read', payload_sha256: null, payload_prefix_sha256: 'f'.repeat(64), payload_bytes: 100000 })], total_matching: 1, next_cursor: null }) as any);
  await mount(); const row = screen.getByRole('article', { name: 'Audit record 5' });
  fireEvent.click(within(row).getByText('Inspect the recorded evidence'));
  expect(within(row).getByText(/Payload unavailable/)).toHaveTextContent('full bytes were not read');
  expect(within(row).getByText(/Inspected prefix SHA-256 \(not the full payload\)/)).toBeInTheDocument();
  expect(within(row).getByText('Stored payload size: 100,000 bytes.')).toBeInTheDocument();
  expect(within(row).queryByText(/Stored payload SHA-256/)).not.toBeInTheDocument();
});

it('preserves a naive original timestamp and metadata error without claiming a verified time zone', async () => {
  vi.mocked(api).mockResolvedValueOnce(page({ records: [record(5, { timestamp: null, timestamp_raw: '2026-10-29 14:00:00', metadata_errors: ['Timestamp lacks an explicit time zone'] })], total_matching: 1, next_cursor: null }) as any);
  await mount(); const row = screen.getByRole('article', { name: 'Audit record 5' });
  expect(within(row).getByText(/Time not verified: 2026-10-29 14:00:00/)).toBeInTheDocument();
  fireEvent.click(within(row).getByText('Inspect the recorded evidence'));
  expect(within(row).getByText('Timestamp lacks an explicit time zone')).toBeInTheDocument();
  expect(within(row).getByText('2026-10-29 14:00:00')).toBeInTheDocument();
});

it('keeps unrecognized recorded actions inspectable without inventing a destination or historical effect', async () => {
  vi.mocked(api).mockResolvedValueOnce(page({ records: [record(5, { action: 'old_unknown_action', action_label: 'Unrecognized recorded action', summary: 'An unrecognized local audit action was recorded.', suggested_view: null, explicit_shipment_id: null })], total_matching: 1, next_cursor: null }) as any);
  await mount({ onNavigate: vi.fn(), onSelectShipment: vi.fn() });
  const row = screen.getByRole('article', { name: 'Audit record 5' });
  expect(within(row).getByText('Unrecognized recorded action')).toBeInTheDocument();
  expect(within(row).queryByRole('button')).not.toBeInTheDocument();
});

it('accepts bounded 2048-character actor and unrecognized action metadata that the backend can legitimately return', async () => {
  const actor='Actor-'+ 'a'.repeat(2042);const action='x'.repeat(2048);
  vi.mocked(api).mockResolvedValueOnce(page({records:[record(5,{actor,action,action_label:'Unrecognized recorded action',summary:'An unrecognized local audit action was recorded.',suggested_view:null})],total_matching:1,next_cursor:null}) as any);
  await mount();const row=screen.getByRole('article',{name:'Audit record 5'});
  expect(within(row).getByText(actor)).toBeInTheDocument();
  fireEvent.click(within(row).getByText('Inspect the recorded evidence'));
  expect(within(row).getByText(action)).toBeInTheDocument();
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});

it.each(['actor','action'])('rejects %s metadata exceeding the aligned 2048-character display bound',async field=>{
  vi.mocked(api).mockResolvedValueOnce(page({records:[record(5,{[field]:'x'.repeat(2049)})],total_matching:1,next_cursor:null}) as any);
  await mount();expect(screen.getByRole('alert')).toHaveTextContent('bounded read-only contract');
});

it('navigation callbacks inspect existing workspaces without posting an operational action', async () => {
  const navigate=vi.fn();const select=vi.fn();const close=vi.fn();
  await mount({onNavigate:navigate,onSelectShipment:select,onClose:close});
  const row=screen.getByRole('article',{name:'Audit record 5'});
  fireEvent.click(within(row).getByRole('button',{name:'Open Command'}));
  fireEvent.click(within(row).getByRole('button',{name:'Inspect shipment SH11'}));
  fireEvent.click(screen.getByRole('button',{name:'Close activity history'}));
  expect(navigate).toHaveBeenCalledWith('command');expect(select).toHaveBeenCalledWith('SH11');expect(close).toHaveBeenCalledOnce();
  expect(api).toHaveBeenCalledTimes(1);
});

it('exports the loaded snapshot and captured filters, excluding unapplied draft filter changes', async () => {
  const originalBlob=globalThis.Blob;const blobs:any[]=[];
  vi.stubGlobal('Blob',class {constructor(parts:any[], options:any){blobs.push({parts,options});}});
  const create=vi.fn(()=> 'blob:test-activity');const revoke=vi.fn();
  const priorCreate=URL.createObjectURL;const priorRevoke=URL.revokeObjectURL;
  URL.createObjectURL=create;URL.revokeObjectURL=revoke;
  const click=vi.spyOn(HTMLAnchorElement.prototype,'click').mockImplementation(()=>{});
  try {
    await mount();fireEvent.change(screen.getByRole('textbox',{name:'Explicit shipment ID'}),{target:{value:'SH99'}});
    fireEvent.click(screen.getByRole('button',{name:'Export captured activity JSON'}));
    const exported=JSON.parse(blobs[0].parts[0]);
    expect(exported.filters).toEqual({action:'',shipment:''});expect(exported.pages[0].snapshot_id).toBe(identifier);
    expect(exported.pages[0].records.map((row:any)=>row.id)).toEqual([5,4]);
    expect(exported.operational_state_modified).toBe(false);expect(exported.read_only).toBe(true);
    expect(click).toHaveBeenCalledOnce();expect(api).toHaveBeenCalledTimes(1);
  } finally {vi.stubGlobal('Blob',originalBlob);URL.createObjectURL=priorCreate;URL.revokeObjectURL=priorRevoke;click.mockRestore();}
});

it('prevents duplicate page requests while loading', async () => {
  await mount();const waiting=deferred<any>();vi.mocked(api).mockReturnValueOnce(waiting.promise);
  fireEvent.click(screen.getByRole('button',{name:'Load older activity'}));
  fireEvent.click(screen.getByRole('button',{name:'Loading older activity…'}));
  expect(api).toHaveBeenCalledTimes(2);
  expect(screen.getByRole('button',{name:'Refresh activity'})).toBeDisabled();
  await act(async()=>waiting.resolve(page({records:[record(2)],next_cursor:null})));
  expect(screen.getAllByRole('article')).toHaveLength(3);
});

it('ignores a delayed response after the panel is unmounted', async () => {
  const waiting=deferred<any>();vi.mocked(api).mockReturnValueOnce(waiting.promise);
  const view=render(<ActivityTimeline/>);expect(api).toHaveBeenCalledTimes(1);view.unmount();
  await act(async()=>waiting.resolve(page()));expect(screen.queryByRole('article')).not.toBeInTheDocument();
});
