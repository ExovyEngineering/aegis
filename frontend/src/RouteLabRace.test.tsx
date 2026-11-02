import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import RouteLab from './RouteLab';
import { api } from './api';

vi.mock('./RouteLabMap', () => ({ default: () => <div>Inspectable route map</div> }));
vi.mock('./api', async () => ({ ...await vi.importActual('./api'), api: vi.fn() }));

const result = (id: string, name: string, cost: number) => ({ run_id: id, preset: { id: 'farm', name, nodes: [], stops: [], trucks: [] }, routes: [], solver_status: 'FEASIBLE', feasible: true, summary: { total_distance_m: 1000, total_duration_seconds: 600, total_cost: cost, unserved_stops: [], unmet_demand_kg: 0, constraint_violations: 0 }, provenance: 'Synthetic test fixture', limitations: [] });
const savedRequest = { preset: 'farm', routing: 'estimated', truck_count: 2, truck_capacity_kg: 750, max_route_hours: 4, refrigeration_fault: false, ambient_temperature_c: 20, delay_minutes: 15 };
const project = { id: 'p1', name: 'Saved project record', version: 1, run_id: 'saved-run', updated_at: '2026-10-27T08:00:00Z' };
const saved = { ...project, viewed_version: 1, history: [{ version: 1, name: project.name }], run: { request: savedRequest, result: result('saved-run', 'Saved route plan', 400), created_at: project.updated_at } };
function deferred<T>() { let resolve!: (value: T) => void; let reject!: (value: unknown) => void; const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; }
beforeEach(() => { vi.mocked(api).mockReset(); });

it('keeps inputs edited during a run stale until the edited plan is actually computed', async () => {
  const pending = deferred<any>(); let requests = 0;
  vi.mocked(api).mockImplementation(async (path, body) => {
    if (path === '/route-lab') return ++requests === 1 ? pending.promise : result('edited-run', 'Edited route plan', 200);
    if (path === '/planning/projects') return body ? project : [];
    if (path === '/planning/projects/p1') return saved;
    return [];
  });
  render(<RouteLab />);
  fireEvent.click(screen.getByRole('button', { name: 'Test dispatch plan' }));
  fireEvent.change(screen.getByLabelText('Capacity per truck (kg)'), { target: { value: '900' } });
  expect(screen.getByText(/Inputs changed during the current run/)).toBeInTheDocument();
  await act(async () => pending.resolve(result('prior-input-run', 'Prior input plan', 300)));
  expect(await screen.findByRole('heading', { name: 'Prior input plan' })).toBeInTheDocument();
  expect(screen.getByLabelText('Capacity per truck (kg)')).toHaveValue(900);
  expect(screen.getByRole('button', { name: 'Save as new project' })).toBeDisabled();
  expect(screen.getByText(/The results below describe the previous run/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Test dispatch plan' }));
  expect(await screen.findByRole('heading', { name: 'Edited route plan' })).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Save as new project' }));
  await waitFor(() => expect(api).toHaveBeenCalledWith('/planning/projects', { name: 'My route experiment', run_id: 'edited-run' }));
  expect(vi.mocked(api).mock.calls.find(([path, body]) => path === '/route-lab' && (body as any).truck_capacity_kg === 900)).toBeTruthy();
});

it('does not overwrite an opened saved project with a late computation or its run id', async () => {
  const pending = deferred<any>();
  vi.mocked(api).mockImplementation(async path => {
    if (path === '/route-lab') return pending.promise;
    if (path === '/planning/projects') return [project];
    if (path === '/planning/projects/p1') return saved;
    if (path === '/planning/projects/p1/update') return { ...project, version: 2 };
    return [];
  });
  render(<RouteLab />);
  fireEvent.click(screen.getByRole('button', { name: 'Test dispatch plan' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Open project' }));
  expect(await screen.findByRole('heading', { name: 'Saved route plan' })).toBeInTheDocument();
  expect(screen.getByLabelText('Capacity per truck (kg)')).toHaveValue(750);
  expect(screen.getByRole('button', { name: 'Test dispatch plan' })).toBeEnabled();
  await act(async () => pending.resolve(result('obsolete-run', 'Obsolete route plan', 999)));
  expect(screen.queryByRole('heading', { name: 'Obsolete route plan' })).not.toBeInTheDocument();
  expect(screen.getByRole('heading', { name: 'Saved route plan' })).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Export snapshot JSON' })).toHaveAttribute('href', '/api/planning/runs/saved-run');
  fireEvent.click(screen.getByRole('button', { name: 'Save next version' }));
  await waitFor(() => expect(api).toHaveBeenCalledWith('/planning/projects/p1/update', { name: project.name, run_id: 'saved-run', expected_version: 1 }));
});

it('ignores a failed older run after opening a saved project', async () => {
  const pending = deferred<any>();
  vi.mocked(api).mockImplementation(async path => path === '/route-lab' ? pending.promise : path === '/planning/projects' ? [project] : path === '/planning/projects/p1' ? saved : []);
  render(<RouteLab />);
  fireEvent.click(screen.getByRole('button', { name: 'Test dispatch plan' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Open project' }));
  await screen.findByRole('heading', { name: 'Saved route plan' });
  await act(async () => pending.reject(new Error('Obsolete request failed')));
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  expect(screen.getByRole('heading', { name: 'Saved route plan' })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Test dispatch plan' })).toBeEnabled();
});
