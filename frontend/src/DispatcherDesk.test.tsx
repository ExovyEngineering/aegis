import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import DispatcherDesk from './DispatcherDesk';
import { api } from './api';
vi.mock('./api', () => ({ api: vi.fn() }));
vi.mock('./DispatchReadiness',()=>({default:()=>null}));
const snapshot = { network_revision: 7, lots: [{ id: 'L01', held: true, recalled: false, eligible: true, inventory_kg: 1500 }, { id: 'L02', held: false, recalled: false, eligible: true, inventory_kg: 1500 }, { id: 'L03', held: true, recalled: true, eligible: true, inventory_kg: 100 }], incidents: [{ id: 'I1', shipment_id: 'SH01', description: 'Refrigeration alarm while parked', status: 'open', version: 2, reported_at: '2026-10-26T10:00:00Z' }], assignments: [{ id: 'SH01', truck_id: 'T01', destination: 'D01', instruction: 'Previous reviewed instruction', instruction_revision: 4, instruction_acknowledged: false }] };
beforeEach(() => { vi.mocked(api).mockReset(); vi.mocked(api).mockImplementation(async path => path === '/dispatch' ? snapshot as any : {} as any); });
function identify() { fireEvent.change(screen.getByLabelText('Reviewing dispatcher'), { target: { value: 'Dispatcher Taylor' } }); fireEvent.change(screen.getByLabelText('Decision reason'), { target: { value: 'Reviewed the reported cargo condition' } }); }
it('requires identity/reason for hold decisions and cannot release a recalled lot', async () => {
  render(<DispatcherDesk />);
  const hold = await screen.findByRole('button', { name: 'Place hold on L02' });
  expect(hold).toBeDisabled();
  identify();
  expect(screen.getByRole('button', { name: 'Release hold on L03' })).toBeDisabled();
  fireEvent.click(hold);
  await waitFor(() => expect(api).toHaveBeenCalledWith('/dispatch/lots/L02/hold', { actor: 'Dispatcher Taylor', reason: 'Reviewed the reported cargo condition', expected_network_revision: 7 }));
  expect(await screen.findByText(/L02 held. Affected assignments/)).toBeInTheDocument();
});
it('reviews an incident using the version displayed to the dispatcher', async () => {
  render(<DispatcherDesk />);
  await screen.findByText('Refrigeration alarm while parked');
  identify(); fireEvent.click(screen.getByRole('button', { name: 'Start review' }));
  await waitFor(() => expect(api).toHaveBeenCalledWith('/dispatch/incidents/I1/review', { actor: 'Dispatcher Taylor', reason: 'Reviewed the reported cargo condition', status: 'in_review', expected_version: 2 }));
});
it('sends approved instructions with both network and current instruction revisions', async () => {
  render(<DispatcherDesk />);
  await screen.findByText('Previous reviewed instruction');
  identify(); fireEvent.change(screen.getByLabelText('New dispatcher instruction'), { target: { value: 'Remain parked and await cargo review' } });
  fireEvent.click(screen.getByRole('button', { name: 'Approve and send instruction' }));
  await waitFor(() => expect(api).toHaveBeenCalledWith('/dispatch/assignments/SH01/instruction', { actor: 'Dispatcher Taylor', reason: 'Reviewed the reported cargo condition', instruction: 'Remain parked and await cargo review', expected_instruction_revision: 4, expected_network_revision: 7 }));
});
it('surfaces a rejected stale decision and reloads the current desk instead of reporting success', async () => {
  vi.mocked(api).mockImplementation(async path => { if (path.endsWith('/hold')) throw new Error('Network changed; refresh the desk'); return snapshot as any; });
  render(<DispatcherDesk />); await screen.findByText('Refrigeration alarm while parked');
  identify(); fireEvent.click(screen.getByRole('button', { name: 'Place hold on L02' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Network changed');
  expect(screen.queryByRole('status')).not.toBeInTheDocument();
  expect(vi.mocked(api).mock.calls.filter(([path]) => path === '/dispatch').length).toBeGreaterThan(1);
});
it('removes stale actionable data when a desk refresh fails', async () => {
  render(<DispatcherDesk />); await screen.findByText('Refrigeration alarm while parked'); identify();
  vi.mocked(api).mockRejectedValueOnce(new Error('Desk unavailable'));
  fireEvent.click(screen.getByRole('button',{name:'Refresh desk'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('Desk unavailable');
  expect(screen.queryByRole('button',{name:'Place hold on L02'})).not.toBeInTheDocument();
  expect(screen.queryByText('Refrigeration alarm while parked')).not.toBeInTheDocument();
});
it('clears a transient loading error after a successful desk retry',async()=>{
  vi.mocked(api).mockRejectedValueOnce(new Error('Temporary desk outage'));
  render(<DispatcherDesk/>);
  expect(await screen.findByRole('alert')).toHaveTextContent('Temporary desk outage');
  fireEvent.click(screen.getAllByRole('button',{name:'Refresh desk'})[0]);
  expect(await screen.findByText('Refrigeration alarm while parked')).toBeInTheDocument();
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});
