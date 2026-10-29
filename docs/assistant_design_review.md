# Operations evidence assistant: design review

October 29, 2026. This document records a proposed bounded stretch increment,
reviewed against the existing implementation. It is not evidence that the
assistant, a language model, an external provider or its evaluation has run.
Executed implementation and validation must be recorded separately by the
implementing team. The user's renewed request authorizes further stretch work;
the genuine Kiro, author/rubric and timed human-presentation gates remain open.

## Useful first scope

The assistant should help a teammate find and interpret existing evidence. A
person should be able to ask about a scenario tradeoff without manually joining
several screens, while still seeing exactly which values and limitations support
the answer. It must not introduce a second dispatch or approval workflow.

| Supported topic | Useful question | Permitted evidence and answer boundary |
| --- | --- | --- |
| Current operation | What needs review in this simulated network? | Current held/recalled/eligible lot flags, simulated excursions, assignment count and network revision; no illness probabilities |
| Compare responses | How do A and D differ in cost and unmet demand? | Plans computed from the same copied network; explicit numeric deltas, feasibility and independent constraint review; no universal best-plan claim |
| Explain a response | Why is a shipment excluded from scenario C? | Direct eligibility blocks and joint allocation nonselection from `review_plan`; these are not counterfactual or causal proofs of solver choice |
| Approved-trip readiness | What remains outstanding on this approved assignment? | The existing thirteen hard-constraint and three workflow diagnostics from the same network/assignment snapshot; passing does not authorize departure |
| Measured science | Did the fitted model outperform the baseline? | Saved model results, target, units, holdout and availability limitations; no invented run date, accuracy or consumer illness probability |
| Source coverage | Which evidence is dated, missing or incomplete? | Captured source metadata, report errors and NOAA coverage; connectivity success is not complete data coverage or a new provider request |
| Workflow meaning | What does holding, releasing or reporting a concern do? | Reviewed workflow definitions; human approvals and driver safeguards remain explicit |

Start with a visible question catalog and typed parameters such as scenario A-D
and a current shipment ID. If free text is offered, unsupported questions should
be identified explicitly and lead to the supported choices. Keyword matching is
not an LLM. Do not attach fabricated confidence percentages to intent matching.

The current repository has no configured LLM credentials for this increment.
A working deterministic evidence explainer must be labeled accordingly. A local
or cloud LLM adapter, if added later, needs separate genuine configuration,
request evidence, bounded evaluation and provider/fallback provenance. Merely
including an adapter does not demonstrate working LLM integration.

## Snapshot and citation contract

1. Validate the runtime profile before reading state. Misconfigured rehearsal
   settings must not bypass the existing isolation guard.
2. Read an existing SQLite database using `mode=ro`, a read transaction and
   `query_only`. Obtain network, revision and approved-assignment rows together;
   copy them, close the transaction promptly, and compute any scenario outside
   that read lock. Missing or unsupported state should be explicit; answering a
   question should not create, seed or migrate an operator database.
3. The shared `backend.main.db()` context currently performs schema creation,
   state initialization and commit. It is not a strict read-only entry point.
   Reuse pure calculation functions rather than assuming that context is a
   no-write reader.
4. Read each allowlisted report into one bounded byte buffer. Hash and parse
   those same bytes. Reject malformed/nonfinite JSON and validate the fields
   actually used; do not independently hash one version and display another.
5. Report files have independent production times. One network transaction plus
   several report snapshots is not a globally atomic point-in-time snapshot.
   Retain the network revision, report hashes and each available source time.
6. Give every authored fact a stable identifier within the captured answer.
   Cite facts by source identity, snapshot hash and relevant metadata. Answer
   text should come from those verified facts or fixed interpretation rules.
7. Return a captured-at time, evidence digest, engine/version and explicit
   unavailable/stale sources. Existing live-view links should explain that
   opening them can show newer state than the captured answer.
8. A downloaded answer should retain its facts, citations, parameters and
   digest. Downloading or copying it must not create an audit/approval record.

An illustrative response includes `answer_type`, `engine`, `engine_version`,
`captured_at`, `network_revision`, `snapshot_sha256`, `facts`, `citations`,
`limitations` and an empty `actions_performed` list. If expected revision is
accepted from the UI, a mismatch should be rejected or clearly returned as a
different captured context, never silently presented as the selected old trip.

## Interpretation rules inherited from the core

- All logistics, costs, inventory, fuel and cargo telemetry remain simulated.
  Real source coordinates do not establish a supply contract or traceability.
- Scenarios use one-wave allocation over fixed candidate trips. Scenario D
  permits interchangeable simulated lot substitution; it does not reroute a
  truck. Road alternatives belong to the separate route-review tools.
- Scenario B may publish approved assignments that still require targeted
  verification. Driver acknowledgment does not complete that checklist.
- Scenario C proposes lot-level precautionary holds based on the current
  illustrative excursion rule. Computing or explaining it does not impose a
  hold; the existing human approval records that decision.
- `food_waste_kg` is zero under the current one-wave expiry assumption. Unmet
  demand and unsent inventory are separate quantities, not zero or invented
  waste.
- `review_plan` gives direct blocks or joint resource/cost nonselection. Its
  own documentation says it is not a causal solver explanation or optimality
  proof; assistant wording must preserve that distinction.
- Readiness has thirteen constraint checks and three human-workflow checks.
  Ready for review is not safety certification, physical dispatch or legal
  authorization to depart.
- The saved primary sampling study retained the historical prevalence baseline
  because the fitted model did not establish useful advantage. Its collection
  date plus 90-day availability is assumed, not verified publication timing.
  No model-run timestamp should be invented from the handbook's check date.
- NOAA observations, historical reanalysis, forecasts and simulated cargo are
  separate evidence types. CDC evidence stays separate from FSIS outcomes.

## Read-only and data boundaries

The answer path must never call proposal creation, approval, lot hold/release,
assignment acknowledgment, incident submission, reset, simulator, source refresh
or training methods. It should have no tool capable of executing arbitrary
paths, SQL, shell commands or outbound messages. Opening a suggested workspace
is different from submitting its action.

Allowlist the report paths used for answers. A question containing a path, URL,
SQL expression or instructions to read `.env` must not influence file access.
Use bounded requests and finite numeric validation; boolean, string, NaN and
infinite values are not valid substitutes for measured numeric metrics.
Missing outcomes are unavailable, never zero. Missing, invalid, naive or
implausibly future retrieval timestamps must not produce a fresh-source claim.

Do not send actor names, audit identities, arbitrary incident descriptions,
instructions, credentials or raw private database payloads to an optional
external model. Provider text and user questions are untrusted data, not
instructions. Render them as text in the browser, never raw HTML.

An optional LLM can select/reorder allowlisted fact IDs; unknown, duplicate,
over-limit or malformed selections should be rejected with a labeled fallback.
Server-authored simulation/scientific limitations must remain mandatory even if
the model omits them. A selection-only model should be described as AI-selected
evidence, not generative clinical or regulatory advice. Model, prompt/schema and
fact-version metadata need to survive in the captured answer. Genuine local
provider tests and factual-grounding evaluation remain distinct from mocks.

If a local endpoint is supported, restrict it to an explicitly configured
loopback service and refuse redirects; arbitrary user URLs must not become an
SSRF channel. Do not silently use a cloud service, discover credentials from a
different account integration, install a model, or infer authorization for a
paid request from a configured key alone. Offline rehearsal must not call a
model or mutable provider cache.

## Verification matrix

| Case | Required observed behavior |
| --- | --- |
| Seeded A-D comparison | Numbers equal pure solver outputs from the same captured network; no metrics fabricated |
| Delayed or refrigeration-fault scenario | Answer changes with that network revision and retains its source context |
| Scenario D explanation | States lot substitution on fixed trips; never promises closure avoidance |
| Proposed C hold | Explanation leaves lot/assignment/proposal/audit state unchanged |
| Existing held/recalled stock | Explanation and citations preserve hard exclusions; never suggest override |
| Readiness pending/complete | All appropriate hard/workflow states match `build_readiness`; no departure authorization |
| Unknown shipment/scenario/question | Explicit unsupported/unavailable response; no guessed identity or hallucinated answer |
| Model values absent, corrupt or nonfinite | Exact missing/invalid evidence state; no default accuracy or zero-filled metric |
| Weak model result | Historical baseline remains selected; positivity is not illness probability |
| Source timestamp missing, naive, old or future | Conservative stale/unverified label, preserving actual raw metadata |
| Concurrent source replacement | Each citation hash matches the exact bytes parsed for that fact |
| Network changes during answer | Response retains captured revision; UI marks a prior answer when current context differs |
| Injection in question/provider text | No file, network, SQL, approval or shell action; plain-text rendering |
| Request to approve/hold/dispatch | Refuses execution and points to the existing human workflow |
| Optional model unavailable/invalid | Clearly identified deterministic fallback, with no invented provider success |
| Offline isolated rehearsal | No model/provider/cache refresh; dated evidence and deterministic answer still useful |
| Missing database | No database creation, directory initialization or false seeded snapshot |
| Answer/export browser path | Current selection retained, obsolete responses ignored, JSON digest exact, no hidden write controls |
| Preservation check | Operator SQLite/sidecars and all raw observations remain unchanged through answering/export |

Evaluate representative catalog, unsupported, stale, injection and numeric cases
as separate executable cases. Report actual counts and failed cases with dated
artifacts. A passing unit suite alone does not establish real model connectivity,
scientific validity or a completed human presentation.

## Review outcome

The bounded deterministic scope is useful and consistent with the existing
human-controlled core if the boundaries above are implemented and measured.
Neither a new feature nor this design review closes the remaining P0 human or
scientific gates. Implementation status must remain planned until its own code,
tests, browser checks and provenance records actually exist.
