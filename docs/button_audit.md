# Action audit - October 27, 2026

This is executed coverage, not a guarantee of future external availability or
every possible combination of inputs. Current results and timestamps live in the
linked artifacts; browser mutations used only the isolated port8001 database.

| Area | Actions and failure paths exercised | Evidence |
|---|---|---|
| Command map | Five layer toggles, zoom controls, selected-shipment routes, road review | `reports/browser_qa/controls/results.json`, `reports/browser_qa/drive/results.json` |
| Scenario response | A/B/C/D proposal review, close/keep-under-review, identity requirement, C human-approved holds, hard exclusions and allocation arithmetic | `reports/browser_qa/controls/results.json`, `tests/test_plan_review.py` |
| Simulator | All six events, reset, recompute, assignment invalidation | `reports/browser_qa/controls/results.json` |
| Route laboratory | Farm/regional/custom controls, invalid coordinates, capacity/timing/eligibility, late-run and changed-input guards | `reports/browser_qa/operations/results.json`, `frontend/src/RouteLabRace.test.tsx` |
| Saved planning | Save, next version, reopen historical inputs/results, compare and JSON/CSV exports; stale update rejection | `reports/browser_qa/depth/results.json`, `tests/test_planning_library.py` |
| Sources | Pagination, literal filters/clear, schemas/nulls; all five Refresh buttons and actual provider actions | `reports/browser_qa/controls/results.json`, `reports/source_actions.json` |
| Source failure handling | Stale/partial nested MoDOT responses, malformed caches, bounded recall previews, large-body summaries, retained retrieval timestamps | `tests/test_adapters_audit.py`, `tests/test_evidence_limits.py`, `frontend/src/App.test.tsx` |
| Dispatcher desk | Incident review/resolution, hold/release, targeted verification, versioned instruction, stale decisions | `reports/browser_qa/operations/results.json`, `reports/browser_qa/depth/results.json` |
| Drive | Dedicated entry, destination/fuel/cargo, no bulk evidence requests, parked confirmation, expiry/locked API rejection, all quick reports/free text, selected-trip context, acknowledgments and route view | `reports/browser_qa/drive/results.json`, `tests/test_drive_integration.py` |
| Science and brief | Measured group-error table, model/timing/coverage panels, PDF and Markdown, pending gates visible | `reports/browser_qa/depth/results.json`, `tests/test_project_brief.py` |
| USDA county context | County selection/comparison, historical definitions, missing/suppressed grocery observations, CSV download and source hash | `reports/browser_qa/readiness/results.json`, `tests/test_usda_ingestion.py`, `tests/test_food_context.py` |
| Source import identity | Eight semantic identities, input-file hashes, displayed row snapshot integrity, conflicts and corrupt-file continuation | `reports/browser_qa/readiness/results.json`, `reports/ingestion_verification.json`, `tests/test_ingestion_identity.py` |
| Readiness diagnostics | Empty state, status filter, per-trip checks, refresh, parked acknowledgment, three verification checks, exact instruction revision and hold/removal | `reports/browser_qa/readiness/results.json`, `tests/test_readiness.py`, `frontend/src/DispatchReadiness.test.tsx` |

Corrected findings include stale assignments surviving partial reloads, requested
routes being replaced by reference routes, stale fallback being called a refresh
success, old trip responses replacing current context, late run results becoming
saveable beside edited inputs, lot-ID validation drift, oversized recall transfers
and partially published generated JSON. The cosmetic favicon404 is also resolved.

Driver parked confirmation is a self-declaration, checked by the server for up to
ten minutes; it is not vehicle-motion sensing or prevention of other device use.
Verified source freshness is separate from complete historical coverage, product
traceability and commercial-truck routing validation. Genuine Kiro execution,
author/rubric review and a timed team presentation remain pending.

Drive submits its displayed network revision with trip acknowledgments and both
report forms. Stale same-ID reassignment actions are rejected before audit,
incident or acknowledgment writes; current-context requests succeed. Older
revisionless clients remain compatible in the local prototype. Evidence:
`tests/test_driver_action_context.py`.
