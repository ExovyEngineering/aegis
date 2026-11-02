import type { ReactNode } from 'react';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from './api';
import { ChallengeReadiness, FoodSecurityStudy, IntegratedModelStudy } from './ChallengeEvidence';

vi.mock('./api', () => ({ api: vi.fn() }));
vi.mock('recharts', () => {
  const Frame = ({ children }: { children?: ReactNode }) => <div>{children}</div>;
  return {
    ResponsiveContainer: Frame,
    LineChart: ({ children, data }: { children?: ReactNode; data?: unknown }) => <div data-testid="captured-model-series"><output>{JSON.stringify(data)}</output>{children}</div>,
    CartesianGrid: () => null, Legend: () => null, Tooltip: () => null, XAxis: () => null, YAxis: () => null,
    Line: ({ dataKey, connectNulls }: { dataKey?: string; connectNulls?: boolean }) => <span data-testid={`line-${dataKey}`} data-connect-nulls={String(connectNulls)} />,
  };
});

const modelReport = () => ({
  status: 'Conditional retrospective study; prospective skill unestablished',
  target: 'Selected Missouri FSIS sample positivity', horizon_days: 7,
  operational_activation_allowed: false,
  primary_split: { training_rows: 255, validation_rows: 171, validation_start: '2026-01-05', validation_end: '2026-06-23' },
  models: {
    baseline: { metrics: { brier: 0, pr_auc_average_precision: null, roc_auc: null, brier_week_block_bootstrap_95_ci: null } },
    fsis_cdc: { metrics: { brier: .11265, pr_auc_average_precision: .1664, roc_auc: .5995 } },
    core_integrated: { metrics: { brier: null, pr_auc_average_precision: undefined, roc_auc: null, confusion_at_0_1: { tp: 5, fp: 17, tn: 30, fn: 6 } } },
  },
  ablations: [{ added_domain: 'NOAA ambient context', brier_change: -.0002, interpretation: 'Paired interval includes zero; added value not established' }],
  timeseries: [{ month: '2026-01', positive_fraction: .1, core_integrated_mean: null, baseline_mean: .08 }],
  availability_assumptions: { beam: { assumed_lag_days: 90 }, noaa: { assumed_lag_days: 7 } },
  limitations: ['CDC records remain contextual predictors, never FSIS outcome labels.'],
});

const policy = (id: string, name: string, distributed: number, unmet: number) => ({
  policy_id: id, policy_name: name, solver_status: 'OPTIMAL',
  metrics: { distributed_kg: distributed, unmet_demand_kg: unmet, min_demand_service_fraction: null,
    projected_quality_budget_exposure_kg: null, held_or_recalled_dispatched_kg: 0,
    total_estimated_shipment_hours: 3.25, total_estimated_distance_km: 21.5 },
  constraint_review: { passed: true },
  demand_service: [{ destination_id: `${id}-destination`, demand_kg: 500, distributed_kg: distributed, service_fraction: null }],
  proposed_actions: [{ action: 'review_candidate_allocation', shipment_ids: [`${id}-shipment`], requires_human_approval: true }],
  requires_human_approval: true,
});

const decisionReport = () => ({
  simulation: true, requires_human_approval: true, operator_state_modified: false,
  objective: 'Preserve eligible food volume and compare destination demand service.',
  scenarios: [
    { id: 'baseline', name: 'Captured baseline', assumptions: ['Fixed baseline assumptions'], policies: [policy('rule-a', 'Captured first-feasible baseline', 321, 679), policy('quality-a', 'Captured quality baseline', 456, 544)] },
    { id: 'scarcity', name: 'Captured scarcity', assumptions: ['Only the captured scarcity capacities apply'], policies: [policy('rule-b', 'Captured first-feasible scarcity', 123, 877), policy('balanced-b', 'Captured balanced scarcity', 234, 766)] },
  ],
  policy_definitions: [{ id: 'rule', name: 'Feasible input-order rule', logic: 'Shared constraints apply to every policy.' }],
  limitations: ['Human approval is required. This study creates no holds or dispatch assignments.', 'Quality exposure is a simulation estimate, not measured waste or pathogen risk.'],
});

const readinessReport = () => ({
  generated_at: '2026-11-02T00:00:00Z', release_status: 'Software demonstrated; team evidence remains open',
  tasks: [{ id: 'Task 3', title: 'Food safety and food security', status: 'Demonstrated simulation', summary: 'Compare food volume and service.',
    implemented: ['Three feasible policy comparisons'], remaining: ['Prospective risk-to-action validation'], menu: 'science',
    artifacts: [{ label: 'Captured decision-study JSON', name: 'decision-study.json' }] }],
  limitations: ['No task status is a claim of prospective validation.'],
});

beforeEach(() => { vi.mocked(api).mockReset(); });

describe('integrated research evidence', () => {
  it('keeps CDC and weather context distinct from FSIS labels and consequential actions', async () => {
    vi.mocked(api).mockResolvedValue(modelReport());
    render(<IntegratedModelStudy />);
    expect(await screen.findByText('RESEARCH EVALUATION')).toBeInTheDocument();
    await screen.findByRole('cell', { name: 'Historical prevalence' });
    expect(screen.getByText(/Regional human surveillance and weather are contextual features/)).toHaveTextContent('not linked illness/food samples or proof of causation');
    expect(screen.getByText(/These results cannot approve or hold a lot/)).toBeInTheDocument();
    expect(screen.getByText(/never FSIS outcome labels/)).toBeInTheDocument();
    expect(screen.getByRole('cell', { name: 'FSIS + BEAM' })).toBeInTheDocument();
    expect(screen.getByText(/Paired interval includes zero; added value not established/)).toBeInTheDocument();
    fireEvent.click(screen.getByText('Availability assumptions, calibration and error consequences'));
    expect(screen.getAllByText(/Neither is a count of consumer illnesses/).length).toBe(3);
    expect(vi.mocked(api).mock.calls).toEqual([['/challenge/integrated-model']]);
    expect(screen.queryByRole('button', { name: /activate|approve|hold|dispatch/i })).not.toBeInTheDocument();
  });

  it('renders missing metrics as unavailable while preserving actual zeros and chart gaps', async () => {
    vi.mocked(api).mockResolvedValue(modelReport());
    render(<IntegratedModelStudy />);
    const baseline = (await screen.findByRole('cell', { name: 'Historical prevalence' })).closest('tr')!;
    expect(within(baseline).getByText('0')).toBeInTheDocument();
    expect(within(baseline).getAllByText('Not available')).toHaveLength(3);
    const integrated = screen.getByRole('cell', { name: 'FSIS + BEAM + NOAA' }).closest('tr')!;
    expect(within(integrated).getAllByText('Not available')).toHaveLength(4);
    expect(within(integrated).queryByText('0')).not.toBeInTheDocument();
    expect(screen.getByTestId('captured-model-series')).toHaveTextContent('"core_integrated_mean":null');
    expect(screen.getByTestId('line-core_integrated_mean')).toHaveAttribute('data-connect-nulls', 'false');
  });
});

describe('captured food-security policies', () => {
  it('scenario selection binds the displayed quantities to the captured policy rows', async () => {
    vi.mocked(api).mockResolvedValue(decisionReport());
    render(<FoodSecurityStudy />);
    const firstRow = (await screen.findByRole('cell', { name: 'Captured first-feasible baseline' })).closest('tr')!;
    expect(within(firstRow).getByText('321')).toBeInTheDocument();
    expect(within(firstRow).getByText('679')).toBeInTheDocument();
    expect(within(firstRow).getAllByText('Not available')).toHaveLength(2);
    expect(within(firstRow).getByText('0')).toBeInTheDocument();
    fireEvent.change(screen.getByRole('combobox', { name: 'Food-security study scenario' }), { target: { value: 'scarcity' } });
    expect(screen.queryByText('Captured first-feasible baseline')).not.toBeInTheDocument();
    const scarcityRow = screen.getByRole('cell', { name: 'Captured balanced scarcity' }).closest('tr')!;
    expect(within(scarcityRow).getByText('234')).toBeInTheDocument();
    expect(within(scarcityRow).getByText('766')).toBeInTheDocument();
    expect(screen.getByText('Only the captured scarcity capacities apply')).toBeInTheDocument();
    expect(vi.mocked(api).mock.calls).toEqual([['/challenge/decision-study']]);
  });

  it('exports captured comparisons without dispatch or mutation calls and makes review limits clear', async () => {
    vi.mocked(api).mockResolvedValue(decisionReport());
    render(<FoodSecurityStudy />);
    await screen.findByRole('cell', { name: 'Captured first-feasible baseline' });
    expect(screen.getByText('SIMULATED POLICY STUDY')).toBeInTheDocument();
    expect(screen.getByText(/not a verified population-vulnerability score/)).toBeInTheDocument();
    expect(screen.getByText(/Human approval is required/)).toBeInTheDocument();
    expect(screen.getByText(/not measured waste or pathogen risk/)).toBeInTheDocument();
    const download = screen.getByRole('link', { name: 'Download comparison CSV' });
    expect(download).toHaveAttribute('href', '/api/challenge/artifacts/decision-study.csv');
    download.addEventListener('click', event => event.preventDefault());
    fireEvent.click(download);
    fireEvent.click(screen.getByText('Policy logic, destination service and review actions'));
    expect(screen.getAllByText(/"requires_human_approval": true/)).toHaveLength(2);
    expect(screen.queryByRole('button', { name: /dispatch|approve|hold|activate/i })).not.toBeInTheDocument();
    expect(vi.mocked(api).mock.calls).toEqual([['/challenge/decision-study']]);
  });
});

describe('five-task readiness', () => {
  it('separates software, research and missing team evidence and navigates without mutating', async () => {
    vi.mocked(api).mockResolvedValue(readinessReport());
    const navigate = vi.fn();
    render(<ChallengeReadiness onNavigate={navigate} />);
    await screen.findByRole('heading', { name: /Task 3.*Food safety and food security/ });
    expect(screen.getByText(/Software checks, retrospective science and actual team\/Kiro evidence have separate statuses/)).toBeInTheDocument();
    fireEvent.click(screen.getByText('What is implemented and what remains'));
    expect(screen.getByText('Prospective risk-to-action validation')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Captured decision-study JSON' })).toHaveAttribute('href', '/api/challenge/artifacts/decision-study.json');
    fireEvent.click(screen.getByRole('button', { name: 'Open related workspace' }));
    expect(navigate).toHaveBeenCalledWith('science');
    expect(vi.mocked(api).mock.calls).toEqual([['/challenge']]);
  });
});

describe('unavailable and malformed evidence', () => {
  it.each([
    ['readiness', ChallengeReadiness, { tasks: null }],
    ['model', IntegratedModelStudy, { models: null, primary_split: {} }],
    ['decision', FoodSecurityStudy, { scenarios: [] }],
  ])('shows an explicit schema error for unavailable %s evidence', async (_name, Component, payload) => {
    vi.mocked(api).mockResolvedValue(payload);
    render(<Component />);
    expect(await screen.findByRole('alert')).toHaveTextContent(/schema|no recorded scenarios/i);
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it.each([ChallengeReadiness, IntegratedModelStudy, FoodSecurityStudy])('shows a failed read without inventing successful evidence', async Component => {
    vi.mocked(api).mockRejectedValue(new Error('Recorded source artifact is unavailable'));
    render(<Component />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Recorded source artifact is unavailable');
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    expect(vi.mocked(api).mock.calls).toHaveLength(1);
    expect(vi.mocked(api).mock.calls[0]).toHaveLength(1);
  });

  it.each([
    ['readiness task', ChallengeReadiness, { ...readinessReport(), tasks: [{}] }],
    ['model row', IntegratedModelStudy, { ...modelReport(), models: { broken: null } }],
    ['model metrics', IntegratedModelStudy, { ...modelReport(), models: { broken: { metrics: 'unsupported' } } }],
    ['calibration row', IntegratedModelStudy, { ...modelReport(), models: { broken: { metrics: { calibration: [null] } } } }],
    ['time-series row', IntegratedModelStudy, { ...modelReport(), timeseries: [null] }],
    ['scenario row', FoodSecurityStudy, { ...decisionReport(), scenarios: [{}] }],
    ['policy metrics', FoodSecurityStudy, { ...decisionReport(), scenarios: [{ id: 'bad', name: 'Malformed values', policies: [{ ...policy('bad', 'Malformed', 1, 2), metrics: { distributed_kg: { invented: 0 } } }] }] }],
    ['constraint approval', FoodSecurityStudy, { ...decisionReport(), scenarios: [{ id: 'bad', name: 'Malformed review', policies: [{ ...policy('bad', 'Malformed', 1, 2), constraint_review: { passed: 'false' } }] }] }],
  ])('rejects a malformed nested %s instead of crashing or claiming a valid report', async (_name, Component, payload) => {
    vi.mocked(api).mockResolvedValue(payload);
    render(<Component />);
    expect(await screen.findByRole('alert')).toHaveTextContent(/schema|no recorded scenarios|unavailable/i);
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('keeps the fixed human-review and contextual-score warnings visible when evidence is unavailable', async () => {
    vi.mocked(api).mockResolvedValue({ ...decisionReport(), requires_human_approval: false, limitations: [] });
    render(<FoodSecurityStudy />);
    expect(await screen.findByRole('alert')).toHaveTextContent(/unsupported schema/);
    expect(screen.getByText('Human approval required. This read-only study cannot dispatch shipments or create holds.')).toBeVisible();
    expect(screen.getByText(/does not estimate causal pathogen-risk reduction/)).toBeVisible();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('rejects research evidence claiming operational activation', async () => {
    vi.mocked(api).mockResolvedValue({ ...modelReport(), operational_activation_allowed: true });
    render(<IntegratedModelStudy />);
    expect(await screen.findByRole('alert')).toHaveTextContent(/unsupported schema/);
    expect(screen.getByText('RESEARCH EVALUATION')).toBeVisible();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });
});
