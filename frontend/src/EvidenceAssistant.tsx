import { useCallback, useEffect, useRef, useState } from 'react';
import { Activity, ArrowDownToLine, ArrowRight, BookOpen, ClipboardCheck, Database, RefreshCw, ShieldCheck, TriangleAlert, Truck } from 'lucide-react';
import { api } from './api';
import './EvidenceAssistant.css';

export type AssistantView = 'command' | 'evidence' | 'science' | 'drive' | 'routes' | 'roads' | 'dispatch' | 'brief';
type QuestionId = 'scenario_compare' | 'shipment_review' | 'model_limits' | 'source_coverage' | 'driver_workflow' | 'next_actions';
interface Citation { id: string; label: string; path: string; retrieved_at?: string | null; sha256?: string | null }
export interface AssistantFact {
  id: string; title: string; text: string; category: string; provenance: string;
  citations: Citation[]; uncertainty: string[]; shipment_id?: string;
}
interface Engine { mode: 'deterministic'; label: string; llm_used: false }
interface Question { id: QuestionId; label: string; prompt: string }
interface Shipment { id: string; label?: string; origin?: string; destination?: string; lot_id?: string; truck_id?: string }
export interface AssistantContext {
  snapshot_id: string; network_revision: number; generated_at: string; engine: Engine;
  questions: Question[]; facts: AssistantFact[]; limitations: string[]; shipments?: Shipment[];
}
interface AskRequest { question_id: QuestionId; expected_snapshot_id: string; shipment_id?: string }
interface Interpretation { question_id: QuestionId; mode: 'rules' | 'ollama_topic_selection'; llm_routing_used: boolean; prompt_version: string; warning?: string; fallback_reason?: string; requested_model?: string; reported_model?: string }
interface TopicEngine { configured: boolean; provider: 'ollama_loopback' | 'none'; label: string; model?: string | null; operational_data_sent: false; quality_evaluation: string; warning?: string | null }
interface AssistantAnswer {
  snapshot_id: string; network_revision: number; generated_at: string; engine: Engine;
  question_id: QuestionId; shipment_id: string | null;
  answer: { title: string; summary: string; items: AssistantFact[] };
  suggested_views: { view: AssistantView; label: string }[];
  limitations: string[]; operational_state_modified: false;
  interpretation?: Interpretation;
}
interface Captured { response: AssistantAnswer; question: Question; shipment?: Shipment; prompt?: string }

const questionIds: QuestionId[] = ['scenario_compare', 'shipment_review', 'model_limits', 'source_coverage', 'driver_workflow', 'next_actions'];
const views: AssistantView[] = ['command', 'evidence', 'science', 'drive', 'routes', 'roads', 'dispatch', 'brief'];
const icons = { scenario_compare: Activity, shipment_review: Truck, model_limits: BookOpen, source_coverage: Database, driver_workflow: ClipboardCheck, next_actions: ShieldCheck };
const isText = (value: unknown, maximum = 20000): value is string => typeof value === 'string' && value.length <= maximum;
const texts = (value: unknown): value is string[] => Array.isArray(value) && value.length <= 100 && value.every(item => isText(item));
const engineValid = (value: any): value is Engine => value && value.mode === 'deterministic' && value.llm_used === false && isText(value.label, 300);
const topicEngineValid = (value: any): value is TopicEngine => value && typeof value.configured === 'boolean' && ['ollama_loopback', 'none'].includes(value.provider) && (!value.configured || value.provider === 'ollama_loopback') && isText(value.label, 1000) && (value.model == null || isText(value.model, 1000)) && value.operational_data_sent === false && isText(value.quality_evaluation, 3000) && (value.warning == null || isText(value.warning, 3000));
const revisionValid = (value: unknown): value is number => typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;
const citationValid = (value: any): value is Citation => value && isText(value.id, 300) && isText(value.label, 1000) && isText(value.path, 3000) && (value.retrieved_at == null || isText(value.retrieved_at, 200)) && (value.sha256 == null || typeof value.sha256 === 'string' && /^[a-f0-9]{64}$/.test(value.sha256));
const factValid = (value: any): value is AssistantFact => value && isText(value.id, 300) && value.id.length > 0 && isText(value.title, 1000) && isText(value.text) && isText(value.category, 300) && isText(value.provenance, 3000) && Array.isArray(value.citations) && value.citations.length > 0 && value.citations.length <= 20 && value.citations.every(citationValid) && texts(value.uncertainty) && (value.shipment_id === undefined || isText(value.shipment_id, 300));
function contextValid(value: any): value is AssistantContext {
  return value && isText(value.snapshot_id, 300) && value.snapshot_id.length > 0 && revisionValid(value.network_revision) && isText(value.generated_at, 200) && engineValid(value.engine)
    && Array.isArray(value.questions) && value.questions.length === questionIds.length && value.questions.every((item: any) => item && questionIds.includes(item.id) && isText(item.label, 1000) && isText(item.prompt, 3000))
    && new Set(value.questions.map((item: Question) => item.id)).size === questionIds.length
    && Array.isArray(value.facts) && value.facts.length > 0 && value.facts.length <= 1200 && value.facts.every(factValid) && new Set(value.facts.map((item: AssistantFact) => item.id)).size === value.facts.length
    && texts(value.limitations) && (value.shipments === undefined || Array.isArray(value.shipments) && value.shipments.length <= 200 && value.shipments.every((item: any) => item && isText(item.id, 300) && item.id.length > 0 && (item.label === undefined || isText(item.label, 1000))) && new Set(value.shipments.map((item: Shipment) => item.id)).size === value.shipments.length);
}
function canonical(value: any): string {
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (value && typeof value === 'object') return '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + canonical(value[key])).join(',') + '}';
  return JSON.stringify(value);
}
function answerValid(value: any, request: AskRequest, context: AssistantContext): value is AssistantAnswer {
  if (!value || value.snapshot_id !== request.expected_snapshot_id || value.network_revision !== context.network_revision || value.question_id !== request.question_id || value.shipment_id !== (request.shipment_id ?? null)
      || !isText(value.generated_at, 200) || !engineValid(value.engine) || value.operational_state_modified !== false || !value.answer || !isText(value.answer.title, 1000) || !isText(value.answer.summary)
      || !Array.isArray(value.answer.items) || !value.answer.items.length || value.answer.items.length > 200 || !value.answer.items.every(factValid) || !texts(value.limitations)
      || !Array.isArray(value.suggested_views) || value.suggested_views.length > 20 || !value.suggested_views.every((item: any) => item && views.includes(item.view) && isText(item.label, 1000))) return false;
  const facts = new Map(context.facts.map(fact => [fact.id, fact]));
  return new Set(value.answer.items.map((fact: AssistantFact) => fact.id)).size === value.answer.items.length
    && value.answer.items.every((fact: AssistantFact) => facts.has(fact.id) && canonical(fact) === canonical(facts.get(fact.id)));
}
const timestamp = (value?: string | null) => {
  if (!value) return 'Not supplied';
  return /(?:Z|[+-]\d{2}:\d{2})$/i.test(value) && Number.isFinite(Date.parse(value))
    ? `${new Date(value).toLocaleString('en-US', { timeZone: 'America/Chicago' })} CT`
    : `${value} (timezone not verified)`;
};
const message = (error: unknown) => error instanceof Error ? error.message : String(error);
const interpretationValid = (value: any): value is Interpretation => value && questionIds.includes(value.question_id) && ['rules', 'ollama_topic_selection'].includes(value.mode) && typeof value.llm_routing_used === 'boolean' && value.llm_routing_used === (value.mode === 'ollama_topic_selection') && isText(value.prompt_version, 1000) && ['warning', 'fallback_reason', 'requested_model', 'reported_model'].every(key => value[key] === undefined || value[key] === null || isText(value[key], 3000));

function FactCard({ fact }: { fact: AssistantFact }) {
  return <article className="assistant-fact" aria-label={fact.title}>
    <div className="assistant-fact-heading"><span className="eyebrow">{fact.category.replaceAll('_', ' ')}</span><span className="assistant-fact-id">{fact.id}</span></div>
    <h3>{fact.title}</h3><p className="assistant-fact-text">{fact.text}</p>
    {fact.uncertainty.length > 0 && <div className="assistant-fact-limits"><strong>Interpretation limits</strong><ul>{fact.uncertainty.map((limit, index) => <li key={index}>{limit}</li>)}</ul></div>}
    <details className="assistant-provenance"><summary>Sources & provenance ({fact.citations.length})</summary><p>{fact.provenance}</p><ol>{fact.citations.map((citation, index) => <li key={`${citation.id}-${index}`}><strong>{citation.label}</strong><code>{citation.path}</code>{citation.retrieved_at && <span>Source retrieval: {timestamp(citation.retrieved_at)}</span>}{citation.sha256 && <span className="assistant-source-hash">SHA-256: {citation.sha256}</span>}</li>)}</ol></details>
  </article>;
}

export default function EvidenceAssistant({ onNavigate }: { onNavigate?: (view: AssistantView) => void }) {
  const [context, setContext] = useState<AssistantContext>();
  const [topicEngine, setTopicEngine] = useState<TopicEngine>();
  const [prompt, setPrompt] = useState('');
  const [allowModel, setAllowModel] = useState(false);
  const [questionId, setQuestionId] = useState<QuestionId>('scenario_compare');
  const [shipmentId, setShipmentId] = useState('');
  const [captured, setCaptured] = useState<Captured>();
  const [loading, setLoading] = useState(false);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState('');
  const [changed, setChanged] = useState(false);
  const loadEpoch = useRef(0), askEpoch = useRef(0), inputRevision = useRef(0);
  const loadingRef = useRef(false), askingRef = useRef(false);
  const contextId = useRef('');

  const load = useCallback(async () => {
    if (loadingRef.current) return;
    loadingRef.current = true;
    const epoch = ++loadEpoch.current;
    askEpoch.current++; askingRef.current = false; contextId.current = '';
    setLoading(true); setAsking(false); setError(''); setContext(undefined); setTopicEngine(undefined); setAllowModel(false); setCaptured(undefined); setChanged(false);
    try {
      const [contextResponse, engineResponse] = await Promise.allSettled([api<AssistantContext>('/assistant/context'), api<TopicEngine>('/assistant/engine')]);
      if (epoch !== loadEpoch.current) return;
      if (contextResponse.status === 'rejected') throw contextResponse.reason;
      const response = contextResponse.value;
      if (!contextValid(response)) throw new Error('The evidence context has an unsupported schema. No explanation or source success was inferred.');
      contextId.current = response.snapshot_id; setContext(response);
      setTopicEngine(engineResponse.status === 'fulfilled' && topicEngineValid(engineResponse.value) ? engineResponse.value : undefined);
      setQuestionId(current => response.questions.some(question => question.id === current) ? current : response.questions[0].id);
      setShipmentId(current => response.shipments?.some(shipment => shipment.id === current) ? current : response.shipments?.[0]?.id ?? '');
    } catch (reason) { if (epoch === loadEpoch.current) setError(message(reason)); }
    finally { if (epoch === loadEpoch.current) { loadingRef.current = false; setLoading(false); } }
  }, []);
  useEffect(() => {
    void load();
    return () => { loadEpoch.current++; askEpoch.current++; loadingRef.current = false; askingRef.current = false; contextId.current = ''; };
  }, [load]);
  function change(action: () => void) {
    inputRevision.current++; action(); setChanged(!!captured || asking);
  }
  const question = context?.questions.find(item => item.id === questionId);
  const shipment = context?.shipments?.find(item => item.id === shipmentId);
  async function ask(interpret = false) {
    if (!context || !question || loadingRef.current || askingRef.current || (!interpret && questionId === 'shipment_review' && !shipment) || (interpret && (prompt.trim().length < 5 || prompt.trim().length > 400))) return;
    askingRef.current = true; setAsking(true); setError('');
    const epoch = ++askEpoch.current, revision = inputRevision.current;
    const request: AskRequest = { question_id: question.id, expected_snapshot_id: context.snapshot_id, ...(question.id === 'shipment_review' && shipment ? { shipment_id: shipment.id } : {}) };
    const requestedQuestion = { ...question }, requestedShipment = shipment, requestedPrompt = prompt.trim();
    try {
      const response = await api<AssistantAnswer>(interpret ? '/assistant/interpret' : '/assistant/ask', interpret ? {
        prompt: requestedPrompt, expected_snapshot_id: context.snapshot_id, allow_model: !!(topicEngine?.configured && allowModel), ...(shipment ? { shipment_id: shipment.id } : {}),
      } : request);
      if (epoch !== askEpoch.current || contextId.current !== request.expected_snapshot_id) return;
      const resolvedQuestion = interpret ? context.questions.find(item => item.id === response.question_id) : requestedQuestion;
      const expected: AskRequest = interpret ? { question_id: response.question_id, expected_snapshot_id: request.expected_snapshot_id, ...(response.question_id === 'shipment_review' && requestedShipment ? { shipment_id: requestedShipment.id } : {}) } : request;
      if (!resolvedQuestion || (interpret && (!interpretationValid(response.interpretation) || response.interpretation.question_id !== response.question_id)) || !answerValid(response, expected, context)) throw new Error('The answer did not match its question, captured evidence or read-only contract. Reload evidence context before asking again.');
      setCaptured({ response, question: resolvedQuestion, shipment: response.question_id === 'shipment_review' ? requestedShipment : undefined, ...(interpret ? { prompt: requestedPrompt } : {}) }); setChanged(revision !== inputRevision.current);
      if (interpret && revision === inputRevision.current) setQuestionId(resolvedQuestion.id);
    } catch (reason) {
      if (epoch !== askEpoch.current) return;
      contextId.current = ''; setContext(undefined); setCaptured(undefined); setChanged(false);
      setError(`${message(reason)} Reload evidence context before asking again. No operational action was taken.`);
    } finally { if (epoch === askEpoch.current) { askingRef.current = false; setAsking(false); } }
  }
  function exportAnswer() {
    if (!captured) return;
    try {
      const output = { format: 'aegis-evidence-briefing-v1', question: captured.question, shipment: captured.shipment ?? null, response: captured.response,
        notice: 'A captured deterministic explanation of dated evidence and simulated operations. Typed question text is omitted from this export. This export does not approve, hold, release or dispatch anything.' };
      const url = URL.createObjectURL(new Blob([JSON.stringify(output, null, 2)], { type: 'application/json' }));
      const anchor = document.createElement('a'); anchor.href = url; anchor.download = `AEGIS-evidence-${captured.question.id}-${captured.response.snapshot_id.slice(0, 12)}.json`;
      document.body.appendChild(anchor); anchor.click(); anchor.remove(); window.setTimeout(() => URL.revokeObjectURL(url), 0);
    } catch (reason) { setError(`The captured answer could not be exported: ${message(reason)}`); }
  }

  return <section className="evidence-assistant" aria-label="Evidence assistant">
    <div className="assistant-intro"><span className="assistant-intro-icon"><BookOpen size={26} /></span><div><div className="eyebrow">READ-ONLY OPERATIONS BRIEFING</div><h2>Understand the evidence behind a response</h2><p>Choose a question, inspect the captured facts and follow their sources. Every explanation retains the distinction between public evidence, simulated operations and scientific limits.</p></div><span className="pill amber">DETERMINISTIC FACTS</span></div>
    <div className="assistant-toolbar"><div><span className="pill">READ ONLY</span>{context && <span className="source-stamp">Revision {context.network_revision} · {context.facts.length} captured facts</span>}</div><button className="secondary" disabled={loading} onClick={() => void load()}><RefreshCw size={15} />{loading ? 'Loading evidence context…' : 'Reload evidence context'}</button></div>
    {error && <div role="alert" className="feedback error"><TriangleAlert size={18} />{error}</div>}
    {loading && <p role="status" className="assistant-loading">Capturing the current network and saved evidence…</p>}
    {!loading && !context && !error && <p className="assistant-empty">Evidence context is unavailable. Reload before asking a question.</p>}
    {context && <>
      <div className="assistant-context-note"><ShieldCheck size={18} /><div><strong>{context.engine.label}</strong><p>Server-authored facts from one captured context. No language model generates these facts. Guided questions use no language model. This screen does not refresh public feeds, train a model, approve a plan or change inventory.</p><span>Captured {timestamp(context.generated_at)} · snapshot <code>{context.snapshot_id}</code></span></div></div>
      <div className="assistant-workbench">
        <section className="panel assistant-questions" aria-label="Guided evidence questions"><div className="panel-heading"><div><h2>What would you like to understand?</h2><span>Six bounded questions with inspectable evidence</span></div></div><div className="padded">
          <div className="assistant-question-grid">{context.questions.map(item => { const Icon = icons[item.id]; return <button key={item.id} aria-pressed={questionId === item.id} className={`assistant-question ${questionId === item.id ? 'selected' : ''}`} onClick={() => change(() => setQuestionId(item.id))}><Icon size={19} /><span><strong>{item.label}</strong><small>{item.prompt}</small></span></button>; })}</div>
          {(!!context.shipments?.length || questionId === 'shipment_review') && <label className="field">Simulated shipment to review<select aria-label="Simulated shipment to review" value={shipmentId} onChange={event => change(() => setShipmentId(event.target.value))}>{context.shipments?.length ? context.shipments.map(item => <option key={item.id} value={item.id}>{item.label ?? item.id}</option>) : <option value="">No simulated shipments available</option>}</select><small>Used only when the explanation concerns a shipment.</small></label>}
          <button className="assistant-ask" disabled={asking || loading || !question || (questionId === 'shipment_review' && !shipment)} onClick={() => void ask()}>{asking ? 'Capturing a cited explanation…' : 'Explain captured evidence'}<ArrowRight size={16} /></button>
          <p className="source-note">Questions only read the current snapshot. To make a decision, navigate to the appropriate workspace and complete its existing human approval steps.</p>
          <div className="assistant-intent"><h3>Find an explanation</h3><label className="field">Your evidence question<textarea aria-label="Your evidence question" value={prompt} minLength={5} maxLength={400} rows={3} placeholder="For example: Why was the historical baseline selected?" onChange={event => change(() => setPrompt(event.target.value))} /></label><p className="source-note">Maps your wording to one of the six supported topics. It cannot carry out instructions or answer beyond captured evidence.</p>
            {topicEngine?.configured ? <><label className="assistant-model-opt-in"><input type="checkbox" checked={allowModel} onChange={event => change(() => setAllowModel(event.target.checked))} /><span>Use the configured Ollama service for topic selection only<small>Only this question text and the fixed topic catalog are sent. Operational records and captured evidence are not sent.</small></span></label><p className="source-note">{topicEngine.label}{topicEngine.model ? ` · ${topicEngine.model}` : ''}. {topicEngine.quality_evaluation}</p>{topicEngine.warning && <p className="source-note">{topicEngine.warning}</p>}</> : <p className="source-note">{topicEngine ? 'No Ollama topic selector is configured. Question matching uses deterministic rules.' : 'Optional model configuration is unavailable. Guided questions and rule-based matching remain available.'}</p>}
            <button className="secondary assistant-interpret" disabled={asking || loading || prompt.trim().length < 5 || prompt.trim().length > 400} onClick={() => void ask(true)}>Interpret question<ArrowRight size={14} /></button>
          </div>
        </div></section>
        <div className="assistant-answer-area">
          {changed && <div className="coverage-warning" role="status"><TriangleAlert size={16} />Question, shipment or topic-selection preference changed. The briefing below belongs to the previous request; ask again to explain the current selection.</div>}
          {!captured ? <section className="panel assistant-answer-empty"><BookOpen size={34} /><h2>A briefing you can verify</h2><p>Choose a guided question and capture its explanation. Facts, source paths, retrieval times and interpretation limits will appear together.</p><span>Simulated logistics · dated evidence · human decisions</span></section> : <section className="panel assistant-answer" aria-label="Captured evidence briefing">
            <div className="panel-heading"><div><div className="eyebrow">CAPTURED DETERMINISTIC ANSWER</div><h2>{captured.response.answer.title}</h2><span>{captured.question.label}{captured.shipment ? ` · ${captured.shipment.label ?? captured.shipment.id}` : ''}</span></div><button className="secondary small" onClick={exportAnswer}><ArrowDownToLine size={14} />Export captured answer JSON</button></div>
            <div className="padded">{captured.prompt && <p className="assistant-captured-prompt"><strong>Your captured question</strong>{captured.prompt}<small>Shown locally for context; omitted from the JSON export.</small></p>}{captured.response.interpretation && <div className="assistant-routing-note"><span className="pill amber">{captured.response.interpretation.llm_routing_used ? 'LLM TOPIC SELECTION ONLY' : 'RULE-BASED TOPIC MATCH'}</span><p>Matched topic: {captured.question.label}. All factual wording below remains server-authored and cited.</p>{captured.response.interpretation.warning && <p>{captured.response.interpretation.warning}</p>}{captured.response.interpretation.fallback_reason && <p>{captured.response.interpretation.fallback_reason}</p>}<small>Prompt version: {captured.response.interpretation.prompt_version}{captured.response.interpretation.requested_model ? ` · requested model: ${captured.response.interpretation.requested_model}` : ''}{captured.response.interpretation.reported_model ? ` · reported model: ${captured.response.interpretation.reported_model}` : ''}</small></div>}<p className="assistant-answer-summary">{captured.response.answer.summary}</p><p className="source-note">Answer captured {timestamp(captured.response.generated_at)} · revision {captured.response.network_revision} · snapshot <code>{captured.response.snapshot_id}</code>.</p><div className="assistant-facts">{captured.response.answer.items.map(fact => <FactCard key={fact.id} fact={fact} />)}</div>
              {onNavigate && captured.response.suggested_views.length > 0 && <div className="assistant-navigation"><h3>Continue reviewing in the app</h3><div>{captured.response.suggested_views.map((item, index) => <button key={`${item.view}-${index}`} className="secondary" onClick={() => onNavigate(item.view)}>{item.label}<ArrowRight size={14} /></button>)}</div><p className="source-note">These buttons navigate only. They do not approve a proposal, hold or release a lot, dispatch a truck or submit a driver report.</p></div>}
              <details className="assistant-answer-limits"><summary>Scope and limitations of this captured answer</summary><ul>{captured.response.limitations.map((limit, index) => <li key={index}>{limit}</li>)}</ul></details>
            </div>
          </section>}
        </div>
      </div>
      <details className="panel assistant-context-limits"><summary>Evidence context and scientific boundaries</summary><ul>{context.limitations.map((limit, index) => <li key={index}>{limit}</li>)}</ul><p>Sampling positivity is not consumer illness probability. CDC and FSIS remain separate evidence. A predictive score or explanation does not create a mandatory hold.</p></details>
    </>}
  </section>;
}
