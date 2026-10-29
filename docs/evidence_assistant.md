# Read-only evidence assistant

This increment was authorized by the October 29 request to continue stretch
features. Human Kiro, author/rubric review and presentation gates remain open.

October 29, 2026. The core assistant is a deterministic explanation workspace.
It summarizes captured operational fields, recalculated scenario tradeoffs and
dated scientific/source reports. It does not use an LLM, contact a public
provider or perform an operational action. Any optional model intent router is
a separate capability and must retain its own truthful configuration/evaluation
labels; it cannot change the facts described here.

## Questions supported by the core

| Topic | Useful question | Evidence used |
| --- | --- | --- |
| Compare response scenarios | What do the four responses cost and leave unmet? | All four actual optimization results from one captured simulated network |
| Review a shipment | What needs inspection for this candidate/current assignment? | Candidate lot/truck/timing fields, actual approved assignment fields and explicit simulation limits |
| Explain model performance | Did the historical model improve on the baseline? | Saved cohort counts, Brier/ROC-AUC results and availability boundaries |
| Explain source coverage | Which saved checks failed, and what weather coverage is absent? | Dated registry probe records and NOAA coverage report |
| Explain driver handoff | What do approval, acknowledgment and verification mean? | Captured assignment counts and the implemented human/parked-use workflow |
| Find next review steps | Where can I inspect the supporting evidence? | Read-only navigation to existing Command, Sources, Science, Dispatcher, Drive or handbook views |

These are bounded questions. The core does not accept arbitrary action names,
SQL, source paths, a free-form model prompt or a request to change a disposition.
It never produces a fabricated accuracy percentage or a consumer illness
probability. CDC BEAM, NORS and FSIS sampling retain distinct meanings.

## Optional wording-to-topic router

`POST /api/assistant/interpret` accepts a 5–400 character question, the expected
snapshot hash, optional selected shipment and an explicit `allow_model` flag.
Deterministic rules select one of the same six topics. A selected topic is shown
to the user, who can choose the appropriate guided question when matching is
ambiguous. Unrelated/action requests are rejected rather than executed. This is
not general chat, autonomous advice or a new predictive model.

`GET /api/assistant/engine` reports configuration without probing a provider or
claiming successful inference. By default no model is configured or called.
To opt into an already installed service, a technical teammate can explicitly
set the following outside Git:

```text
AEGIS_ASSISTANT_OLLAMA_ENABLED=1
AEGIS_ASSISTANT_OLLAMA_MODEL=<explicit installed model:tag>
AEGIS_ASSISTANT_OLLAMA_URL=http://127.0.0.1:11434
```

The browser still requires an opt-in checkbox for the request. Only that
question and fixed topic descriptions are sent. No network records, report
payloads, actor names, incident text or operational tools are supplied. The
connector permits explicit HTTP loopback addresses/ports, rejects credentials,
paths/queries/redirects and cloud-tagged model names, and disables environment
proxies. A loopback address does not independently certify how the service runs
its model; review that service's settings. No model is downloaded automatically.

The connector uses the official [Ollama chat protocol](https://docs.ollama.com/api/chat)
with a JSON-schema topic enum and nonstreaming response. It accepts only one
supported topic identifier. Tool calls, extra output claims, duplicate keys,
nonfinite/malformed output, incomplete responses, identity mismatch or excessive
response size are rejected. Requests use bounded connection/read timeouts, a
32 KiB response limit, no automatic retries and one concurrent model selection.
Errors fall back visibly to rules when those rules support the question.
Offline rehearsal blocks the model call even if a client forges the opt-in flag.

All resulting evidence sentences still come from the captured server facts;
neither a model topic nor a model error can rewrite them. The response reports
`interpretation.llm_routing_used` separately from the deterministic fact engine.
The snapshot is rechecked after interpretation to reject a context that changed
during a delayed request. Questions are not stored in SQLite, and typed question
text is omitted from the default briefing export.

Configuration and mocked transport tests are not actual-model quality evidence.
No actual configured model inference has been recorded for this increment.
The working/default assistant is deterministic; model evaluation remains open.

## Snapshot and citation contract

`backend/evidence_assistant.py` exposes:

- `capture_context(db_path, root=ROOT)` to capture and explain current local
  state. Either argument may be a callable, allowing the application factory to
  resolve its configured runtime without rebinding a global database.
- `answer_from_context(context, question_id, shipment_id=None)` to select exact
  existing fact objects from that context. It cannot add a new numerical claim
  or invoke an action.
- `create_assistant_router(db_path, root=ROOT)` for the HTTP routes below.

The database is opened with SQLite `mode=ro`, `query_only=ON` and
`trusted_schema=OFF`. A `BEGIN` read transaction covers the network and all
approved assignments. The main application's schema-initializing `db()` context
is never used. A missing database, missing required table, unsupported state,
oversized record or malformed JSON fails explicitly; it does not seed a demo.
Normal SQLite read coordination may access existing WAL/shared-memory state;
this is not a promise of an immutable filesystem under concurrent writers.
There are no schema/data commits or action-audit entries from the assistant.

The model evaluation, timing audit, NOAA coverage and API-status reports are
read independently with a 1 MiB bound per report. The exact byte snapshot is
hashed and parsed together. Nonfinite values, duplicate JSON keys, corrupt
files and unsupported report shapes are explicit unavailable evidence. A
malformed report does not erase usable information from the other reports.
There is no global transaction across independently refreshed report files and
no claim that provider observations share one timestamp.

Every fact has an ID, title, server-authored text, category, provenance,
citations and an uncertainty list. Citations carry a relative source path and
its checksum when captured. A missing checksum is omitted, not invented.
Verified timezone-aware source-check timestamps are retained separately; naive,
invalid or implausibly future timestamps are not treated as verified retrieval
times. These saved checks are never labeled new or currently live successes.

Oversized reports are unavailable; their full-file checksum/size is left
unknown. A bounded prefix checksum is labeled separately and is never presented
as a full report hash. Derived context responses are bounded to 2 MiB.

The `snapshot_id` is a SHA-256 over captured input checksums and the derived
facts/metadata. The changing generation clock is excluded so an unchanged
context remains usable. A changed network revision, approved assignment,
acknowledgment, supported captured report byte or reported fact changes the
identifier. Unread portions of an oversized unavailable report are not hashed.
An expected
older identifier is rejected before answering. No automatic retry performs an
action; this endpoint has no such action capability in the first place.

## HTTP routes

`GET /api/assistant/context` returns the current `snapshot_id`, revision,
generation time, deterministic engine label, six-question catalog, shipment
roster, cited facts, scenario summaries, input snapshot metadata and limitations.
It does not create a conversation, proposal or new audit record.

`POST /api/assistant/ask` accepts:

```json
{
  "question_id": "shipment_review",
  "shipment_id": "SH03",
  "expected_snapshot_id": "<64 lowercase hexadecimal characters>"
}
```

The shipment ID is required for `shipment_review` and rejected for other topics,
so it cannot be silently ignored. A known but unavailable trip is not replaced
by the first candidate. Unsupported inputs return 422, an unknown shipment 404,
a changed expected snapshot 409, and unavailable operational evidence 503.

An answer echoes its question/shipment selection, snapshot, revision and engine.
`answer.items` contains the identical fact objects from `context.facts`, allowing
the UI to verify both their identities and full content. Suggested views are
allowlisted navigation labels, not tools or executable instructions. The answer
states `operational_state_modified: false`.

## Operational and scientific interpretation

Scenario numbers are recomputed from the captured simulation, using the current
one-wave optimizer. A result is not stored as a proposal or approved assignment.
An infeasible result is described as unusable rather than advertising its empty
selection as a cheap plan. Scenario B verification remains separate from driver
acknowledgment; C candidate holds still require explicit approval; D substitutes
eligible lots on fixed trips and does not automatically reroute trucks.

Shipment review distinguishes the original candidate lot from the lot in an
actual alternative-supply assignment. Single-candidate flags are not a complete
aggregate plan review or departure authorization. Held/recalled/ineligible
records and temperature excursions prompt inspection, never a silent override
or mandatory model-imposed hold. Cargo values, fleet relationships and costs
remain simulated.

Model comparisons require supported target/cohort fields and matching holdout
sizes. Metrics are read from the recorded artifact, not generated or trained by
the assistant. Missing publication dates remain missing; a reporting-lag
assumption does not verify historical feature availability. NOAA date rows,
numeric/quality coverage, forecasts, reanalysis and cargo telemetry are distinct.
Neither a saved HTTP success nor the assistant's explanation certifies source
coverage, scientific validity, truck restrictions or product safety.

## Verification

`tests/test_evidence_assistant.py` exercises read-only SQL and byte preservation,
no provider calls, no seeding, exact cited fact selection, stable/stale snapshots,
assignment changes without a network revision, candidate/assigned-lot separation,
corrupt/missing/oversized reports, unsupported metrics, invalid actions and paths,
offline runtime guards and solver failures. The focused implementation run
passed 43 tests; later full-suite/browser evidence must be read from its own
dated reports. No real local/cloud model use or model accuracy is established by
these deterministic engine tests.
