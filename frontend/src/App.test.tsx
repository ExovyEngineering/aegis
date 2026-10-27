import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { api } from './api';
vi.mock('./DataExplorer', () => ({default: () => <div>Bounded data explorer</div>}));
vi.mock('./NetworkMap', () => ({ default: () => <div>Missouri logistics map</div> }));
vi.mock('./api', async importOriginal => ({ ...await importOriginal<object>(), api: vi.fn() }));
vi.mock('recharts', () => {
  const Wrapper = ({ children }: { children?: React.ReactNode }) => <div>{children}</div>;
  const Chart = ({ children }: { children?: React.ReactNode }) => <svg>{children}</svg>;
  return { AreaChart: Chart, LineChart: Chart, ResponsiveContainer: Wrapper, Area: () => null, CartesianGrid: () => null, Line: () => null, Tooltip: () => null, XAxis: () => null, YAxis: () => null };
});
const network = { seed: 20261026, revision: 0, provenance: 'SIMULATION', nodes: [{ id: 'DC1', name: 'Columbia DC', kind: 'dc', coordinates: [-92.3, 38.9] }, { id: 'D01', name: 'Simulated destination', kind: 'destination', coordinates: [-90.2, 38.6] }], trucks: [{ id: 'T01', eligible: true, capacity_kg: 1500 }], lots: [{ id: 'L01', held: true, recalled: false, inventory_kg: 1500 }], shipments: [{ id: 'SH01', origin: 'DC1', destination: 'D01', lot_id: 'L02', truck_id: 'T01', quantity_kg: 400, temperature_c: 2, estimated_hours: 2, estimated_distance_km: 130, deadline_hours: 6 }], telemetry: [], events: [] };
const scenario = { id: 'proposal-1', scenario: 'A', name: 'Baseline distribution', solver_status: 'OPTIMAL', feasible: true, total_logistics_cost: 200, unmet_demand_kg: 100, delayed_shipments: 0, affected_shipments: 0, review_priority_count: 0, food_waste_kg: 0, constraint_violations: 0, proposed_hold_lots: [], shipments: network.shipments, limitations: 'Simulated allocation' };
describe('AEGIS workflow', () => {
  beforeEach(() => {
    window.history.replaceState(null,'','/');
    vi.mocked(api).mockClear();
    vi.mocked(api).mockImplementation(async (path: string) => {
      if (path === '/drive/T01') return {truck_id:'T01',network_revision:0,focus:{mode:'locked',version:0,parked_until:null,interaction_allowed:false},assignments:[],vehicle:{fuel_percent:60,fuel_liters:108,tank_capacity_liters:180,estimated_range_km:380,coordinates:[-92.3,38.9],observed_at:'2026-10-26T08:00:00-05:00',position_label:'Simulated origin'},events:[]} as any;
      if (path === '/network') return network as any;
      if (path === '/scenarios') return [scenario] as any;
      if (path === '/model') return { status: 'Retrospective feasibility only' } as any;
      if (path === '/proposals/A') return scenario as any;
      if (path === '/proposals/proposal-1/approve') return { status: 'approved' } as any;
      if (path.startsWith('/evidence/')) return { status: 'unavailable' } as any;
      if (path === '/inventory') return { files: [] } as any;
      return [] as any;
    });
  });
  it('labels simulation and requires an identified reason before approval', async () => {
    render(<App />);
    expect(await screen.findByText('Missouri logistics map')).toBeInTheDocument();
    expect(screen.getByText('SIMULATED OPERATIONS')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /^Review/ }));
    await screen.findByRole('dialog');
    const approve = screen.getByRole('button', { name: 'Approve simulated plan' });
    expect(approve).toBeDisabled();
    fireEvent.change(screen.getByLabelText('Dispatcher name'), { target: { value: 'Test dispatcher' } });
    fireEvent.change(screen.getByLabelText('Reason for approval'), { target: { value: 'Safety and capacity reviewed' } });
    expect(approve).toBeEnabled();
    fireEvent.click(approve);
    await waitFor(() => expect(api).toHaveBeenCalledWith('/proposals/proposal-1/approve', { actor: 'Test dispatcher', reason: 'Safety and capacity reviewed' }));
    await screen.findByText('Scenario approved. Driver assignments updated and audit recorded.');
  });
  it('shows no driver trip before approval', async () => {
    render(<App />);
    await screen.findByText('Missouri logistics map');
    fireEvent.click(screen.getByRole('button', { name: /AEGIS Drive/ }));
    expect(await screen.findByText('No approved assignments')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Report an issue/ })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Confirm safely parked' })).toBeEnabled();
  });
  it('clears old driver assignments and scenario rows when a partial refresh fails', async () => {
    const normal = vi.mocked(api).getMockImplementation()!;
    let failed = false;
    vi.mocked(api).mockImplementation(async (path,body) => {
      if (failed && (path === '/driver' || path === '/scenarios')) throw new Error('temporarily unavailable');
      if (path === '/driver') return network.shipments as any;
      return normal(path,body);
    });
    render(<App />);await screen.findByText('Missouri logistics map');
    expect(screen.getByText('APPROVED ASSIGNMENTS').closest('.stat')).toHaveTextContent('1');
    failed = true;fireEvent.click(screen.getByRole('button',{name:'Reload application data'}));
    await screen.findByText(/Some application data is unavailable/);
    expect(screen.getByText('APPROVED ASSIGNMENTS').closest('.stat')).toHaveTextContent('0');
    expect(screen.queryByRole('button',{name:/^Review/})).not.toBeInTheDocument();
  });
  it('reports stale fallback as a failed refresh rather than new source success', async () => {
    const normal = vi.mocked(api).getMockImplementation()!;
    vi.mocked(api).mockImplementation(async (path,body) => path.startsWith('/refresh/openmeteo') ? {stale:true,refresh_error:'provider timeout',payload:{}} as any : normal(path,body));
    render(<App />);await screen.findByText('Missouri logistics map');
    fireEvent.click(screen.getByRole('button',{name:'Sources & evidence'}));
    fireEvent.click(screen.getAllByRole('button',{name:'Refresh'})[0]);
    await screen.findByText(/refresh unavailable; showing the dated cached response/);
    expect(screen.queryByText('Open-Meteo forecast refreshed.')).not.toBeInTheDocument();
  });
  it('preserves a requested shipment route across application reloads', async () => {
    const normal = vi.mocked(api).getMockImplementation()!;
    vi.mocked(api).mockImplementation(async (path,body) => {
      if (path === '/route') return {fallback:true,payload:{routes:[]}} as any;
      if (path === '/evidence/osrm_route') return {fallback:false,payload:{routes:[]}} as any;
      return normal(path,body);
    });
    render(<App />);await screen.findByText('Missouri logistics map');
    fireEvent.click(screen.getByRole('button',{name:'Request road route'}));
    await screen.findByText(/Requested route for SH01/);
    fireEvent.click(screen.getByRole('button',{name:'Reload application data'}));
    await waitFor(() => expect(vi.mocked(api).mock.calls.filter(([p]) => p === '/network').length).toBeGreaterThan(1));
    expect(screen.getByText(/Requested route for SH01/)).toBeInTheDocument();
  });
  it('dedicated Drive avoids fetching bulk recall, inventory and model evidence', async () => {
    window.history.replaceState(null,'','/?mode=drive');
    render(<App />);await screen.findByText('No approved assignments');
    expect(screen.queryByRole('navigation',{name:'Main navigation'})).not.toBeInTheDocument();
    expect(vi.mocked(api).mock.calls.every(([path]) => path === '/network' || path.startsWith('/drive/'))).toBe(true);
    window.history.replaceState(null,'','/');
  });
});
