import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import PlanningLibrary from './PlanningLibrary';
import { api } from './api';
vi.mock('./api', async () => ({ ...await vi.importActual('./api'), api: vi.fn() }));
const project = {id: 'p1', name: 'Farm baseline', version: 1, run_id: 'r1', updated_at: '2026-10-26T12:00:00Z'};
const detail = {...project, viewed_version: 1, history: [{version: 1, name: 'Farm baseline'}], run: {request: {preset: 'farm'}, result: {run_id: 'r1', routes: []}}};
beforeEach(() => { vi.mocked(api).mockReset(); });
it('loads exact saved inputs/results instead of recomputing or dispatching', async () => {
  vi.mocked(api).mockImplementation(async path => path === '/planning/projects' ? [project] : detail as any);
  const load = vi.fn();render(<PlanningLibrary changed={false} onLoad={load} />);
  fireEvent.click(await screen.findByText('Open project'));
  await waitFor(() => expect(load).toHaveBeenCalledWith(detail.run.request, detail.run.result));
  expect(screen.getByText('Export snapshot JSON')).toHaveAttribute('href','/api/planning/runs/r1');
});
it('prevents saving unrun or changed inputs and rejects fabricated result submission', async () => {
  vi.mocked(api).mockResolvedValue([]);
  const {rerender}=render(<PlanningLibrary changed={false} onLoad={vi.fn()} />);
  expect(screen.getByText('Save as new project')).toBeDisabled();
  rerender(<PlanningLibrary changed={true} runId="r1" onLoad={vi.fn()} />);
  expect(screen.getByText('Save as new project')).toBeDisabled();
  rerender(<PlanningLibrary changed={false} runId="r1" onLoad={vi.fn()} />);
  vi.mocked(api).mockImplementation(async (path, body) => path === '/planning/projects/p1' ? detail : path === '/planning/projects' ? (body ? project : [project]) : [] as any);
  fireEvent.click(screen.getByText('Save as new project'));
  await waitFor(() => expect(api).toHaveBeenCalledWith('/planning/projects',{name:'My route experiment',run_id:'r1'}));
});
