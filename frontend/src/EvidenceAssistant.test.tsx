import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import EvidenceAssistant from './EvidenceAssistant';
import { api } from './api';

vi.mock('./api', () => ({ api: vi.fn() }));
const catalog = [
  ['scenario_compare', 'Compare responses', 'Compare cost, unmet demand and feasibility.'],
  ['shipment_review', 'Review a shipment', 'Inspect a simulated shipment and its current constraints.'],
  ['model_limits', 'Understand the model', 'Why was the historical baseline retained?'],
  ['source_coverage', 'Inspect source coverage', 'Which evidence is dated or unavailable?'],
  ['driver_workflow', 'Understand driver workflow', 'What needs parked acknowledgment and human review?'],
  ['next_actions', 'Find next review steps', 'What remains open before presenting?'],
] as const;
const engine = { mode: 'deterministic', label: 'Deterministic evidence summary', llm_used: false };
const noModel = { configured: false, provider: 'none', label: 'Rules only', model: null, operational_data_sent: false, quality_evaluation: 'No actual model evaluation.' };
const citation = { id: 'source-network', label: 'Captured simulation', path: 'network snapshot', retrieved_at: '2026-10-29T17:00:00Z', sha256: 'a'.repeat(64) };
const facts = catalog.map(([id]) => ({ id: `${id}-fact`, title: `${id} evidence`, text: `Unit-test captured ${id} evidence.`, category: id, provenance: 'Unit-test server-authored fact, not a real operational finding.', citations: [citation], uncertainty: ['Simulated evidence does not certify product safety.'] }));
const shipmentFacts = [
  { ...facts[1], id: 'shipment-SH01', title: 'SH01 constraints', shipment_id: 'SH01', text: 'Unit-test shipment SH01 is held.' },
  { ...facts[1], id: 'shipment-SH02', title: 'SH02 constraints', shipment_id: 'SH02', text: 'Unit-test shipment SH02 requires review.' },
];
function snapshot(overrides: any = {}) {
  return structuredClone({ snapshot_id: 'snapshot-a', network_revision: 7, generated_at: '2026-10-29T17:00:00Z', engine, questions: catalog.map(([id, label, prompt]) => ({ id, label, prompt })), facts: [...facts, ...shipmentFacts], limitations: ['CDC and FSIS remain separate.', 'No automatic hold or dispatch.'], shipments: [{ id: 'SH01', label: 'SH01 · T01' }, { id: 'SH02', label: 'SH02 · T02' }], ...overrides });
}
function answer(body: any, overrides: any = {}) {
  const selected = body.question_id === 'shipment_review' ? shipmentFacts.filter(fact => fact.shipment_id === body.shipment_id) : facts.filter(fact => fact.category === body.question_id);
  return structuredClone({ snapshot_id: body.expected_snapshot_id, network_revision: 7, generated_at: '2026-10-29T17:01:00Z', engine, question_id: body.question_id, shipment_id: body.shipment_id ?? null, answer: { title: 'Captured explanation', summary: 'A bounded answer based on the captured evidence.', items: selected }, suggested_views: [{ view: 'command', label: 'Open Command for review' }], limitations: ['Read-only explanation, not a decision.'], operational_state_modified: false, ...overrides });
}
function deferred<T>() { let resolve!: (value: T) => void; let reject!: (reason: Error) => void; const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; }
async function mount(onNavigate?: (view: any) => void) {
  let view!: ReturnType<typeof render>;
  await act(async () => { view = render(<EvidenceAssistant onNavigate={onNavigate} />); });
  return view;
}
async function ask() { await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Get answer' })); }); }
const normal = async (path: string, body: any) => {
  if (path === '/assistant/context') return snapshot();
  if (path === '/assistant/engine') return noModel;
  if (path === '/assistant/ask') return answer(body);
  if (path === '/assistant/interpret') {
    const request = { ...body, question_id: 'model_limits', shipment_id: undefined };
    return answer(request, { interpretation: { question_id: 'model_limits', mode: 'rules', llm_routing_used: false, prompt_version: 'test-router-v1' } });
  }
  throw new Error('Unexpected API path: ' + path);
};
beforeEach(() => { vi.mocked(api).mockReset(); vi.mocked(api).mockImplementation(async (path, body) => normal(path, body)); });

it('offers six bounded topics and clearly identifies deterministic read-only facts', async () => {
  await mount();
  for (const [, label] of catalog) expect(screen.getByRole('button', { name: new RegExp(label) })).toBeInTheDocument();
  expect(screen.getByText('READ-ONLY HELP')).toBeInTheDocument();
  expect(screen.getByText(/Guided questions use no language model/)).toBeInTheDocument();
  expect(screen.getByText(/No Ollama topic selector is configured/)).toBeInTheDocument();
  expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
  expect(vi.mocked(api).mock.calls.every(([path]) => ['/assistant/context', '/assistant/engine'].includes(path))).toBe(true);
});

it.each(catalog.filter(([id]) => id !== 'shipment_review'))('captures the %s guided topic without operational writes', async (id, label) => {
  await mount();await act(async()=>{fireEvent.click(screen.getByRole('button', { name: new RegExp(label) }));});
  expect(api).toHaveBeenCalledWith('/assistant/ask', { question_id: id, expected_snapshot_id: 'snapshot-a' });
  const briefing = screen.getByRole('region', { name: 'Captured evidence briefing' });
  expect(within(briefing).getByText(`Unit-test captured ${id} evidence.`)).toBeInTheDocument();
  expect(vi.mocked(api).mock.calls.filter(([, body]) => body !== undefined).every(([path]) => path === '/assistant/ask')).toBe(true);
});

it('submits the selected simulated shipment and explains that exact captured trip', async () => {
  await mount();await act(async()=>{fireEvent.click(screen.getByRole('button', { name: /Review a shipment/ }));});
  fireEvent.change(screen.getByRole('combobox', { name: 'Simulated shipment to review' }), { target: { value: 'SH02' } });await ask();
  expect(api).toHaveBeenCalledWith('/assistant/ask', { question_id: 'shipment_review', shipment_id: 'SH02', expected_snapshot_id: 'snapshot-a' });
  expect(screen.getByRole('article', { name: 'SH02 constraints' })).toHaveTextContent('Unit-test shipment SH02 requires review.');
  expect(screen.queryByRole('article', { name: 'SH01 constraints' })).not.toBeInTheDocument();
});

it('exposes source path, retrieval, checksum and uncertainty with each fact', async () => {
  await mount();await ask();
  const fact = screen.getByRole('article', { name: 'scenario_compare evidence' });
  expect(within(fact).getByText('Interpretation limits')).toBeInTheDocument();
  fireEvent.click(within(fact).getByText('Sources & provenance (1)'));
  expect(within(fact).getByText('Captured simulation')).toBeVisible();
  expect(within(fact).getByText('network snapshot')).toBeVisible();
  expect(within(fact).getByText(new RegExp('SHA-256: ' + 'a'.repeat(64)))).toBeVisible();
  expect(within(fact).getByText(/Source retrieval:.*CT/)).toBeVisible();
  expect(within(fact).getByText('Simulated evidence does not certify product safety.')).toBeVisible();
});

it('allows navigation only through the provided view callback', async () => {
  const navigate = vi.fn();await mount(navigate);await ask();
  expect(navigate).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Open Command for review' }));expect(navigate).toHaveBeenCalledWith('command');
  expect(screen.getByText(/These buttons navigate only/)).toBeInTheDocument();
});

it('marks a delayed answer as a previous request if inputs changed while it ran', async () => {
  const pending = deferred<any>();vi.mocked(api).mockImplementation(async (path, body) => path === '/assistant/ask' ? pending.promise : normal(path, body));
  await mount();fireEvent.click(screen.getByRole('button', { name: 'Get answer' }));
  fireEvent.change(screen.getByLabelText('Your evidence question'),{target:{value:'What can the model predict?'}});
  await act(async () => { pending.resolve(answer({ question_id: 'scenario_compare', expected_snapshot_id: 'snapshot-a' })); });
  expect(screen.getByRole('region', { name: 'Captured evidence briefing' })).toHaveTextContent('Compare responses');
  expect(screen.getByText(/briefing below belongs to the previous request/)).toBeInTheDocument();
  expect(screen.getByLabelText('Your evidence question')).toHaveValue('What can the model predict?');
});

it('invalidates an outstanding explanation when context is reloaded', async () => {
  const pending = deferred<any>();let loads = 0;
  vi.mocked(api).mockImplementation(async (path, body) => {
    if (path === '/assistant/context') return snapshot({ snapshot_id: ++loads === 1 ? 'snapshot-a' : 'snapshot-b', network_revision: loads === 1 ? 7 : 8 });
    return path === '/assistant/ask' ? pending.promise : normal(path, body);
  });
  await mount();fireEvent.click(screen.getByRole('button', { name: 'Get answer' }));
  await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Reload evidence context' })); });
  await act(async () => { pending.resolve(answer({ question_id: 'scenario_compare', expected_snapshot_id: 'snapshot-a' })); });
  expect(screen.queryByRole('region', { name: 'Captured evidence briefing' })).not.toBeInTheDocument();
  expect(screen.getByText(/Revision 8/)).toBeInTheDocument();
});

it('prevents duplicate requests before the first explanation resolves', async () => {
  const pending = deferred<any>();vi.mocked(api).mockImplementation(async (path, body) => path === '/assistant/ask' ? pending.promise : normal(path, body));
  await mount();const button = screen.getByRole('button', { name: 'Get answer' });
  act(() => { fireEvent.click(button);fireEvent.click(button); });
  expect(vi.mocked(api).mock.calls.filter(([path]) => path === '/assistant/ask')).toHaveLength(1);
  expect(button).toBeDisabled();
  await act(async () => { pending.resolve(answer({ question_id: 'scenario_compare', expected_snapshot_id: 'snapshot-a' })); });
});

it('clears stale context after a rejected snapshot and requires an explicit reload', async () => {
  vi.mocked(api).mockImplementation(async (path, body) => { if (path === '/assistant/ask') throw new Error('409: Evidence snapshot changed'); return normal(path, body); });
  await mount();await ask();
  expect(screen.getByRole('alert')).toHaveTextContent('Evidence snapshot changed');
  expect(screen.getByRole('alert')).toHaveTextContent('Reload evidence context before asking again');
  expect(screen.queryByRole('button', { name: 'Get answer' })).not.toBeInTheDocument();
  expect(vi.mocked(api).mock.calls.filter(([path]) => path === '/assistant/context')).toHaveLength(1);
  await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Reload evidence context' })); });
  expect(screen.getByRole('button', { name: 'Get answer' })).toBeEnabled();
});

it.each(['changed fact', 'wrong question', 'wrong snapshot', 'write flag', 'unknown navigation'])('rejects a response with %s rather than showing unsupported claims', async fault => {
  vi.mocked(api).mockImplementation(async (path, body) => {
    if (path !== '/assistant/ask') return normal(path, body);
    const value = answer(body);
    if (fault === 'changed fact') value.answer.items[0].text = 'Invented answer outside captured evidence';
    if (fault === 'wrong question') value.question_id = 'model_limits';
    if (fault === 'wrong snapshot') value.snapshot_id = 'different-snapshot';
    if (fault === 'write flag') value.operational_state_modified = true;
    if (fault === 'unknown navigation') value.suggested_views[0].view = 'approve';
    return value;
  });
  await mount();await ask();expect(screen.getByRole('alert')).toHaveTextContent('did not match');
  expect(screen.queryByRole('region', { name: 'Captured evidence briefing' })).not.toBeInTheDocument();
});

it('reports missing or invalid context without fabricating evidence', async () => {
  vi.mocked(api).mockImplementation(async (path, body) => path === '/assistant/context' ? { ...snapshot(), facts: [] } : normal(path, body));
  await mount();expect(screen.getByRole('alert')).toHaveTextContent('unsupported schema');
  expect(screen.queryByRole('button', { name: 'Get answer' })).not.toBeInTheDocument();
});

it('permits unknown citation checksums without inventing a hash', async () => {
  const context = snapshot();context.facts.forEach((fact: any) => { fact.citations[0].sha256 = null; });
  vi.mocked(api).mockImplementation(async (path, body: any) => {
    if (path === '/assistant/context') return context;
    if (path === '/assistant/ask') return answer(body, { answer: { title: 'Captured explanation', summary: 'Unknown hashes remain unknown.', items: [context.facts[0]] } });
    return normal(path, body);
  });
  await mount();await ask();const fact = screen.getByRole('article', { name: 'scenario_compare evidence' });
  fireEvent.click(within(fact).getByText('Sources & provenance (1)'));expect(within(fact).queryByText(/SHA-256/)).not.toBeInTheDocument();
});

it('matches typed wording using rules by default and omits prompt text from export', async () => {
  let exported!: Blob;
  Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: vi.fn((blob: Blob) => { exported = blob;return 'blob:test-answer'; }) });
  Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: vi.fn() });
  const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
  await mount();fireEvent.change(screen.getByRole('textbox', { name: 'Your evidence question' }), { target: { value: 'Why was the historical baseline selected?' } });
  await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Ask AEGIS' })); });
  expect(api).toHaveBeenCalledWith('/assistant/interpret', { prompt: 'Why was the historical baseline selected?', expected_snapshot_id: 'snapshot-a', allow_model: false, shipment_id: 'SH01' });
  expect(screen.getByText('RULE-BASED TOPIC MATCH')).toBeInTheDocument();
  expect(within(screen.getByRole('region', { name: 'Captured evidence briefing' })).getByText('Why was the historical baseline selected?')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Export captured answer JSON' }));
  const body = await new Promise<string>((resolve, reject) => { const reader = new FileReader();reader.onload = () => resolve(String(reader.result));reader.onerror = reject;reader.readAsText(exported); });
  const value = JSON.parse(body);
  expect(value.response.question_id).toBe('model_limits');expect(value.question.id).toBe('model_limits');
  expect(JSON.stringify(value)).not.toContain('Why was the historical baseline selected?');
  expect(value.response.interpretation.mode).toBe('rules');click.mockRestore();
});

it('requires explicit opt-in before requesting configured local model topic selection', async () => {
  vi.mocked(api).mockImplementation(async (path, body: any) => {
    if (path === '/assistant/engine') return { ...noModel, configured: true, provider: 'ollama_loopback', label: 'Configured local topic selector', model: 'local-test-model' };
    if (path === '/assistant/interpret') return answer({ ...body, question_id: 'model_limits', shipment_id: undefined }, { interpretation: { question_id: 'model_limits', mode: body.allow_model ? 'ollama_topic_selection' : 'rules', llm_routing_used: body.allow_model, prompt_version: 'test-router-v1' } });
    return normal(path, body);
  });
  await mount();const checkbox = screen.getByRole('checkbox', { name: /Use the configured Ollama service/ });expect(checkbox).not.toBeChecked();
  fireEvent.change(screen.getByRole('textbox', { name: 'Your evidence question' }), { target: { value: 'Explain the model baseline' } });
  await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Ask AEGIS' })); });
  expect(vi.mocked(api).mock.calls.filter(([path]) => path === '/assistant/interpret')[0][1]).toMatchObject({ allow_model: false });
  fireEvent.click(checkbox);await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Ask AEGIS' })); });
  expect(vi.mocked(api).mock.calls.filter(([path]) => path === '/assistant/interpret')[1][1]).toMatchObject({ allow_model: true });
  expect(screen.getByText('LLM TOPIC SELECTION ONLY')).toBeInTheDocument();
  expect(screen.getByText(/All factual wording below remains server-authored and cited/)).toBeInTheDocument();
});

it('shows a local model failure fallback as rules rather than model success', async () => {
  vi.mocked(api).mockImplementation(async (path, body) => path === '/assistant/interpret' ? answer({ ...body as any, question_id: 'model_limits', shipment_id: undefined }, { interpretation: { question_id: 'model_limits', mode: 'rules', llm_routing_used: false, prompt_version: 'test-router-v1', warning: 'Local topic selector unavailable; rules were used.', fallback_reason: 'Unit-test connection refused' } }) : normal(path, body));
  await mount();fireEvent.change(screen.getByRole('textbox', { name: 'Your evidence question' }), { target: { value: 'Explain the model baseline' } });
  await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Ask AEGIS' })); });
  expect(screen.getByText('RULE-BASED TOPIC MATCH')).toBeInTheDocument();
  expect(screen.getByText('Unit-test connection refused')).toBeInTheDocument();
  expect(screen.queryByText('LLM TOPIC SELECTION ONLY')).not.toBeInTheDocument();
});

it('blocks unsupported or action-like requests without showing an operational result', async () => {
  vi.mocked(api).mockImplementation(async (path, body) => { if (path === '/assistant/interpret') throw new Error('Read-only assistant cannot dispatch or approve actions');return normal(path, body); });
  await mount();fireEvent.change(screen.getByRole('textbox', { name: 'Your evidence question' }), { target: { value: 'Dispatch every truck immediately' } });
  await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Ask AEGIS' })); });
  expect(screen.getByRole('alert')).toHaveTextContent('cannot dispatch or approve');
  expect(screen.queryByRole('region', { name: 'Captured evidence briefing' })).not.toBeInTheDocument();
});

it('ignores a context response that arrives after unmount', async () => {
  const pending = deferred<any>();vi.mocked(api).mockImplementation(async (path, body) => path === '/assistant/context' ? pending.promise : normal(path, body));
  const view = render(<EvidenceAssistant />);expect(screen.getByRole('status')).toHaveTextContent('Capturing the current network');view.unmount();
  await act(async () => { pending.resolve(snapshot()); });expect(screen.queryByRole('region', { name: 'Evidence assistant' })).not.toBeInTheDocument();
});
