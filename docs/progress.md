# Progress and acceptance evidence

Session date: October 26, 2026, America/Chicago. This document distinguishes implementation from verification. Test and frontend-build results must be updated only from executed commands.

## Latest: decision depth and team planning brief

October 26 feature-depth release:

- Persistent route projects: immutable server-side runs and checksums, saved
  versions, historical reopening, two-project comparison and JSON/CSV exports.
  Unsaved edits remain temporary; saved plans cannot dispatch or change stock.
- Independent scenario checks expose actual resource sums, selected shipments and
  exclusion reasons. Approval rejects altered candidate quantities and invalid
  eligibility even if a faulty solver returns the same result twice.
- Source explorer: recognized FSIS, NORS, BEAM and establishment tables remain
  separate, with bounded pagination, literal filters, schema, derived-file hashes,
  page null counts and explicit errors for missing/corrupt sources.
- Scenario-B verification checklist: identified review, rationale, context and
  version guards. Driver acknowledgment is separate; completion neither certifies
  safety nor changes stock disposition automatically.
- Measured state-level holdout error analysis is now inspectable in Model evaluation.
- Project brief: maintained feature register, change history, dated verification
  logs and a regenerated 10-page PDF/Markdown with presentation narrative and limits.
  The CI workflow regenerates a downloadable brief and verification artifact.
- Latest local checks: **189 pytest tests, 31 Vitest tests and production build
  passed**. **36 isolated Chrome checks** and **23 loopback HTTP checks** passed.
  Four upstream Python deprecation warnings remain. Browser screenshots and results
  are in `reports/browser_qa/depth/`; no uncaught JavaScript or app HTTP failures.
- All 42 original raw hashes remain unchanged. Scripted demos use isolated state.
  Public providers were not re-probed in this feature session; dated source
  coverage must not be interpreted as new live connectivity evidence.
- Development verification encountered a Windows shared pytest-temp permission
  failure; the runner now uses workspace-local temporary storage. Failed and
  successful local verification records/logs are retained separately. Chrome QA
  also prompted explicit dropdown names and proper waits for asynchronously loaded
  status. The final recorded browser run passed.
- Remaining P0 gates: real Kiro sign-in/task execution, final rubric/report author
  review and timed presentation. Publication timing, NOAA gaps, commercial truck
  restrictions, authentication and physical sensing remain explicit limitations.

## Implemented and measured

October 26 operational feature extension:

- Custom route planning now edits 1–3 origins, 1–20 stops and 1–10 trucks, with strict numeric/reference validation, per-stop shelf life and service-completion deadlines. User-entered data stays labeled as planning assumptions; custom experiments cannot publish assignments.
- Dispatcher desk connects new driver reports to identified review/resolution, explicit lot hold/release decisions and versioned trip instructions. Holds remove affected assignments; release cannot bypass recall status or recreate assignments. Exact-version driver acknowledgment is separate from original trip acknowledgment. Historical reporting context and audit records are retained.
- Validation: 164 backend tests, 23 frontend tests and production build pass. An isolated actual-Chrome workflow passed 50 checks, including negative coordinate editing, non-first-trip incident selection, stale instruction rejection, hold/release and desktop/mobile layout. Evidence and eight screenshots: `reports/browser_qa/operations/`. Four upstream Python deprecation warnings and the cosmetic browser-default favicon 404 remain; no app JavaScript/resource failures occurred.
- The isolated scripted workflow is `scripts/operations_demo.py`; it does not modify the operator database. Custom editor drafts are currently in-memory and are not saved across reload/navigation. Saved route/account storage is not claimed. Scientific coverage/timing limits and actual Kiro-task evidence remain unchanged.

- Read-only audit and manifest generated from 42 supplied raw files with zero recorded read errors, zero exact duplicate hashes, streaming JSON missingness and date ranges, and separate table schemas/counts. Workbook row dimensions remain declared rather than exact parsed counts.
- API registry, Google Sheets CSV, bounded sequential probe, and dated public-response caches.
- In the saved second probe, all 18 registry requests returned HTTP success. Several are catalogs/documentation rather than data feeds. The subsequent full MoDOT adapter queried 18 incident layers with no reported layer errors.
- 78,607 FSIS raw-poultry primary rows ingested; NORS, five BEAM exports, and 175 Missouri directory coordinates processed separately.
- Four deterministic OR-Tools allocation scenarios; persistent proposals, approval, assignments, events, acknowledgments, incidents, and audit trail.
- Initial seed solver results were OPTIMAL for all four scenarios: A cost 3,018 / unmet 2,300 kg; B cost 3,093 / unmet 2,300 kg; C cost 2,838 / unmet 2,700 kg; D cost 2,904 / unmet 1,900 kg. Costs are simulated dollars.
- Geometry intersection/proximity review compares OSRM alternatives against queried MoDOT point/line features using a 250-meter buffer. It produces dispatcher-review signals without truck-safe claims.
- Earlier foundation-stage verification: 114 passing tests, with four upstream deprecation warnings. Frontend TypeScript/Vite build passes and twelve Vitest checks include map teardown regressions. `reports/validation.json` records the latest final counts.
- Uvicorn served the built UI, four assets and twelve JSON endpoints (17 real HTTP checks). Actual Chrome desktop/mobile QA passed 26 checks: map tiles, farm/fleet routes, capacity shortages, refrigeration fault projection, approval and driver acknowledgment/reporting. Nine inspected screenshots and results are in `reports/browser_qa/final/`. No uncaught JavaScript errors or application resource failures remain; a cosmetic default favicon 404 was observed.
- Accelerated isolated demo completed event injection, changed scenario results, approval of 13 simulated assignments, acknowledgment, incident reporting and audit history (`reports/demo_results.json`). The operator database was not modified by this script.
- Measured retrospective model holdout: 23,472 samples, August 29, 2025–June 30, 2026. Baseline Brier 0.0885558; logistic Brier 0.0885944; logistic ROC-AUC 0.4980. The logistic model shows no useful improvement over prevalence in this evaluation. Operational choice remains the transparent historical estimator.

## Acceptance matrix

October 26 follow-on implementation:

- Five verified Missouri NOAA stations, January 2025–June 2026: 2,730/2,730 daily rows, nine precipitation values missing. Original bytes, SHA, date labels, units and quality attributes are preserved separately in `data/external/noaa/`. No FSIS weather join is claimed.
- Frozen earlier-snapshot sensitivity study: 57,459 training and 7,754 validation rows; baseline Brier 0.09297314 vs calendar-only logistic 0.09293427. No held-out outcomes update the estimator. Actual public release dates remain unverified, so this is retrospective evidence.
- Farm and multi-depot routing laboratory enforces truck capacity, stock, held/recalled/ineligible exclusions, service times, deadlines and return-to-origin routes without changing approved assignments. Live OSRM farm: 2 routes / 164.611 km / cost 330.46 / unmet 300 kg. Regional: 5 routes / 1,195.783 km / cost 1,924.10 / unmet 500 kg. Both FEASIBLE, zero checked violations, no matrix/geometry fallback. Costs/logistics are simulated.
- Temperature projections expose uncalibrated thermal parameters and sensitivity bands. No failure probability, illness probability or automatic disposition is claimed.
- Priority hierarchy is fixed in `docs/priority_matrix.md`; LLM assistance, account tenancy and live sensors remain P2.

| Requirement | Current evidence / remaining check |
|---|---|
| 1. Documented local startup | README commands; actual Uvicorn HTTP startup and 17 HTTP checks passed |
| 2. Inventory supplied folder | `scripts/audit_data.py`, `reports/data_audit.md`, `data/manifests/inventory.json` |
| 3. Actual coverage/failures | `reports/api_status.json`; React source/evidence display built and smoke-tested |
| 4. Real map with simulated entities | Actual Chrome rendered OSM and separate vector layers; desktop/mobile screenshots verified |
| 5. Working public weather | Open-Meteo and NWS returned JSON successfully; dated cache retained |
| 6. Official recall data/cached fixture | FSIS API returned official JSON; cache records retrieval time |
| 7. MoDOT queried or failure reported | Discovery and 18 incident-layer queries succeeded; cached coverage and timestamps remain visible |
| 8. Route or labeled fallback | OSRM route and table probes succeeded; estimated offline fallback adapter implemented |
| 9. At least three scenarios | A/B/C/D returned OPTIMAL with distinct measured tradeoffs; backend constraint tests passed |
| 10. Inventory/capacity/hold/eligibility | Allocation and route-lab constraints tested; insufficient capacity produces explicit unmet demand |
| 11. Real evaluation results | `reports/model_evaluation.json`, `docs/model_card.md` |
| 12. Human approval | Revision-aware endpoint, backend workflow tests and React approval-dialog test passed |
| 13. Driver assignment update | Actual browser approval, mobile acknowledgment and incident persistence verified in isolated QA database |
| 14. Provenance | Raw manifest, separate evidence tables, cached retrieval timestamps, frozen dated fixtures, explicit simulation labels |
| 15. Deterministic five-minute demo | Fixed seed, manual script and accelerated isolated workflow passed; timed visual rehearsal outstanding |

## Outstanding requirements and risks

Full NOAA historical training-year coverage and a validated weather join remain incomplete; the bounded extract retains precipitation gaps. Actual FSIS per-result availability and public release dates are unavailable. No validated prospective forecast or consumer-illness probability is claimed. Food-security workbooks are audited but not integrated into allocation. Returning multi-stop scheduling exists in the laboratory; dispatch integration and commercial-truck validation remain outstanding. Real recall-to-lot matching lacks genuine traceability. Production account/authentication and live sensors remain P2.

Official Kiro IDE 1.4.26 is now installed in `.tools/kiro/`. Amazon installer/application signatures are Valid, installation returned exit code 0, and the version check returned 1.4.26. Account sign-in and authentic spec execution remain pending; `docs/kiro_handoff.md` provides a concrete unfinished P0 task. Codex-prepared `.kiro/` files are not proof of Kiro execution. The project P0 requirement is preserved; organizer-mandated Kiro use has not been independently verified.

## Next three actions

Night maintenance pass: 114 backend tests and 12 frontend tests pass after fixing whitespace-only approval identity, distinct matrix/distance/geometry fallback labels, and MoDOT fixture fallback in route review. Production frontend rebuilt; the original 26-check browser rehearsal is retained as earlier visual evidence. A local allowlisted reviewer package and SHA manifest now include source, prebuilt UI, derived evidence, fixtures and report/figures while excluding credentials, active databases and original large downloads. The extracted package was verified offline with the installed dependency environment; a fresh dependency installation was not claimed. See `reports/submission_package.json`, `reports/package_verification.json` and `docs/morning_review.md`. Nothing was uploaded.

1. Sign in to installed Kiro, execute the bounded P0 provenance spec task, and retain authentic task/test evidence.
2. Review the draft report/figures against official submission requirements and rehearse the timed five-minute presentation.
3. Resolve source-publication timing and broader NOAA coverage before adding predictive claims or a weather model join; retain the transparent historical baseline.
