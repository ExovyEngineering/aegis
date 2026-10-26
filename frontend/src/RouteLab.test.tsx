import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import RouteLab from './RouteLab';
import { api } from './api';

vi.mock('./RouteLabMap', () => ({ default: () => <div>Farm and fleet route test map</div> }));
vi.mock('./api', async original => ({ ...await original<object>(), api: vi.fn() }));
vi.mock('recharts', () => {
  const Chart = ({ children }: { children?: React.ReactNode }) => <svg>{children}</svg>;
  const Wrapper = ({ children }: { children?: React.ReactNode }) => <div>{children}</div>;
  return { AreaChart: Chart, ResponsiveContainer: Wrapper, Area: () => null, Line: () => null, ReferenceLine: () => null, CartesianGrid: () => null, Tooltip: () => null, XAxis: () => null, YAxis: () => null };
});
const nodes = [{ id: 'FARM1', name: 'Fictional farm', kind: 'farm', coordinates: [-92.4, 39] }, { id: 'FD01', name: 'Fictional stop', kind: 'destination', coordinates: [-92.3, 39.1] }];
const result = {
  preset: { id: 'farm', name: 'Single-farm dispatch', nodes, stops: [{ id: 'FD08', held: true, eligible: true }], trucks: [{ id: 'FT01', capacity_kg: 1500 }] },
  routes: [{ truck_id: 'FT01', origin_id: 'FARM1', stop_ids: ['FD01'], distance_m: 45000, duration_seconds: 4200, load_kg: 300, capacity_kg: 1500, fallback: true, cold_chain: { status: 'review', max_temperature_c: 9, time_above_threshold_minutes: 32, provenance: 'simulated cargo projection', assumptions: ['Uncalibrated physical model'], projection: [{ elapsed_minutes: 0, temperature_c: 2.5, lower_c: 2.5, upper_c: 2.5 }, { elapsed_minutes: 70, temperature_c: 9, lower_c: 7, upper_c: 11 }] } }],
  solver_status: 'FEASIBLE', feasible: true, summary: { total_distance_m: 45000, total_duration_seconds: 4200, total_cost: 113, unserved_stops: ['FD08'], unmet_demand_kg: 300, constraint_violations: 0 }, provenance: 'Simulated farm exercise', limitations: ['Does not dispatch or modify assignments'],
};
describe('Route laboratory', () => {
  it('sends farm constraints and explicit exposure assumptions without creating assignments', async () => {
    vi.mocked(api).mockImplementation(async path => path === '/route-lab' ? result as any : [] as any);
    render(<RouteLab />);
    fireEvent.change(screen.getByLabelText('Available trucks'), { target: { value: '2' } });
    fireEvent.change(screen.getByLabelText('Additional road delay (minutes)'), { target: { value: '60' } });
    fireEvent.click(screen.getByLabelText(/Simulate refrigeration failure/));
    fireEvent.click(screen.getByRole('button', { name: 'Test dispatch plan' }));
    await screen.findByText('Farm and fleet route test map');
    expect(api).toHaveBeenCalledWith('/route-lab', { preset: 'farm', routing: 'estimated', truck_count: 2, truck_capacity_kg: 1500, max_route_hours: 8, refrigeration_fault: true, ambient_temperature_c: 30, delay_minutes: 60 });
    expect(screen.getByText('Estimated travel')).toBeInTheDocument();
    expect(screen.getByText('300 kg unmet demand')).toBeInTheDocument();
    expect(screen.getByText(/Unserved stop IDs: FD08. Held\/recalled\/ineligible exclusions: FD08 \(held\)/)).toBeInTheDocument();
    expect(screen.getByText(/Projected cargo temperature, not observed telemetry/)).toBeInTheDocument();
    expect(screen.getByText(/Does not dispatch or modify assignments/)).toBeInTheDocument();
    expect(vi.mocked(api).mock.calls.some(([path]) => path.startsWith('/proposals/') || path.startsWith('/driver'))).toBe(false);
    fireEvent.change(screen.getByLabelText('Ambient temperature assumption (°C)'), { target: { value: '35' } });
    expect(screen.getByText(/Inputs changed/)).toBeInTheDocument();
  });
  it('normalizes full API preset inventories and enables multi-location fleet testing', async () => {
    vi.mocked(api).mockImplementation(async path => path === '/operations/presets' ? [{ id: 'regional', name: 'Multi-location fleet', description: 'Two simulated origins', origins: [{}, {}], trucks: Array.from({ length: 8 }, () => ({})), stops: Array.from({ length: 15 }, () => ({})), simulation: true }] as any : result as any);
    render(<RouteLab />);
    const regional = await screen.findByRole('button', { name: /Multi-location fleet Two simulated origins/ });
    fireEvent.click(regional);
    expect(screen.getByLabelText('Available trucks')).toHaveValue(8);
    fireEvent.change(screen.getByLabelText('Capacity per truck (kg)'), { target: { value: '6000' } });
    expect(screen.getByRole('button', { name: 'Test dispatch plan' })).toBeDisabled();
    fireEvent.change(screen.getByLabelText('Capacity per truck (kg)'), { target: { value: '2000' } });
    fireEvent.click(screen.getByRole('button', { name: 'Test dispatch plan' }));
    await waitFor(() => expect(api).toHaveBeenCalledWith('/route-lab', expect.objectContaining({ preset: 'regional', truck_count: 8, truck_capacity_kg: 2000 })));
  });
});
