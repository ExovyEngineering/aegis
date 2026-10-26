import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { api } from './api';
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
    vi.mocked(api).mockImplementation(async (path: string) => {
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
    expect(screen.getByRole('button', { name: 'Send to dispatcher' })).toBeDisabled();
  });
});
