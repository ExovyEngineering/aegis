# AEGIS | Team and presentation brief

Adaptive Early-warning & Guidance for Integrated Supply Chains

Generated October 27, 2026 at 03:00 AM CT. Target submission: November 2, 2026; feature freeze target October 30.

Audience: project teammates, presenters and reviewers. This is an ongoing planning brief, not a certified final submission or regulatory decision.

AEGIS supports a regional Missouri poultry logistics operator. Command combines public evidence with a deterministic simulated network; Drive carries dispatcher-approved simulated assignments and parked-use reporting.

All suppliers/contracts, lots, trucks, shipments, operational costs, demand and cargo telemetry are fictional. Official establishment locations do not establish supply relationships.

Team repository: https://github.com/ExovyEngineering/aegis (private). Start with CONTRIBUTING.md. Use feature branches and reviewed pull requests.

Update this brief: run scripts/verify_project.py after code changes, then scripts/build_project_brief.py. Update config/feature_register.yaml and docs/changelog.md when capabilities or limitations change. No live API requests are performed by the brief compiler.

# P0 | Required submission core

Source inventory and provenance | implemented; bounded coverage

42 original downloads audited; official evidence and simulated logistics remain distinct.

Evidence: reports/data_audit.md

Independent public weather integrations | implemented; historical gaps remain

Open-Meteo forecasts, NWS alerts and bounded NOAA observations have separate provenance. No validated FSIS-weather join.

Evidence: reports/noaa_coverage.json

Measured historical estimator and validation | retrospective baseline implemented; prospective validity unproven

Chronological evaluation, baseline, calibration and uncertainty. Logistic model did not establish useful improvement.

Evidence: reports/model_evaluation.json

Four constrained intervention scenarios | implemented

Baseline, targeted verification, proposed hold and eligible supply substitution, with independent resource checks.

Evidence: backend/optimization.py

Dispatcher approval and audit | implemented for local simulation

Revision guards, explicit holds/releases, targeted verification checklists, incident review and exact-version driver instruction acknowledgment. Identities are self-declared.

Evidence: tests/test_dispatch.py

Inspectable ingested evidence | implemented

Bounded read-only rows, schema, literal filters, page null counts and file checksums; CDC layers never merged with FSIS outcomes.

Evidence: tests/test_data_explorer.py

Authentic Kiro spec execution | pending user sign-in and genuine task execution

Kiro is installed. Existing Codex artifacts and installation evidence do not prove Kiro workflow completion.

Evidence: docs/kiro_handoff.md

Report, reproducible package and presentation | draft artifacts implemented; author review and timed rehearsal pending

Local reviewer bundle, measured results, demonstration scripts and this regenerated planning brief. Not submitted.

Evidence: reports/aegis_report.md

# P1 | Operational differentiators

Interactive Missouri digital twin | implemented for deterministic simulation

Map, official evidence layers, simulated cargo and operational events. Real contracts and physical sensors are absent.

Evidence: backend/simulation.py

Single-farm and multi-origin route planning | implemented as planning sandbox

Custom coordinates, inventory, trucks, demand, deadlines and shelf life. Public OSRM lacks commercial-truck validation.

Evidence: tests/test_route_lab.py

Saved route experiments and comparisons | implemented locally

Immutable runs, checksums, versioned projects, history and exports. No dispatch from the route laboratory.

Evidence: tests/test_planning_library.py

Mobile AEGIS Drive | implemented locally with server-enforced parked-use interactions

Dedicated visual trip view, simulated fuel/origin position/cargo, ten-minute parked attestation, quick reports, instructions and acknowledgment. No actual motion detection or physical sensing.

Evidence: tests/test_drive_integration.py

# P2 | Deferred extensions

LLM operations assistant | deferred behind P0 gates

No assistant or generated safety decisions are claimed.

Evidence: docs/priority_matrix.md

Farm and enterprise accounts | deferred

Planning scales exist; production authentication, tenant isolation and billing do not.

Evidence: docs/priority_matrix.md

Live sensor integrations | deferred

All cargo-temperature telemetry is simulated.

Evidence: docs/simulation_assumptions.md

Additional state DOT feeds | deferred pending cross-state use case

Missouri is the operating scope. Each future feed needs tested schema, timestamp/geometry coverage and explicit fallbacks.

Evidence: docs/stretch_feature_gates.md

Molecular epidemiology | blocked by missing isolate-level genomic linkage

Current aggregate serotype tables do not contain linked genome sequences/accessions. No relatedness or common-source inference is claimed.

Evidence: docs/stretch_feature_gates.md

Real cloud deployment | deferred pending production access controls

Local self-declared identities are not production authentication or tenant isolation. No cloud release is claimed.

Evidence: docs/stretch_feature_gates.md

Real-time streaming infrastructure | deferred pending an actual live stream

Dated public feeds and deterministic simulation are not live sensor streams. Polling retains source timestamps.

Evidence: docs/stretch_feature_gates.md

# Verification | What was actually tested

Latest local verification finished: 2026-10-27T07:56:13.545043+00:00. All requested local checks passed: True.

pytest: PASS; exit 0; tests passed 244; 19.51 seconds. Log: reports/checks/20261027T075532749763Z/pytest.txt. Checked: 2026-10-27T07:55:32.750031+00:00.

vitest: PASS; exit 0; tests passed 51; 9.701 seconds. Log: reports/checks/20261027T075532749763Z/vitest.txt. Checked: 2026-10-27T07:55:52.284731+00:00.

frontend_build: PASS; exit 0; tests passed build check; 11.525 seconds. Log: reports/checks/20261027T075532749763Z/frontend_build.txt. Checked: 2026-10-27T07:56:02.005654+00:00.

Map, scenario, simulator and source-control browser QA: 65 / 65 recorded checks passed. Timestamp: 2026-10-27T07:58:39.813Z. Evidence: reports/browser_qa/controls/results.json. This is a separate run from local unit/build checks.

Visual Drive and parked-use actual-Chrome QA: 65 / 65 recorded checks passed. Timestamp: 2026-10-27T07:58:36.241Z. Evidence: reports/browser_qa/drive/results.json. This is a separate run from local unit/build checks.

Latest feature-depth actual-Chrome QA: 36 / 36 recorded checks passed. Timestamp: 2026-10-27T07:11:33.928Z. Evidence: reports/browser_qa/depth/results.json. This is a separate run from local unit/build checks.

Earlier dispatcher/custom-planning browser QA: 50 / 50 recorded checks passed. Timestamp: 2026-10-27T07:11:39.245Z. Evidence: reports/browser_qa/operations/results.json. This is a separate run from local unit/build checks.

Loopback HTTP smoke artifact records 24 checks against http://127.0.0.1:8000. It does not certify current public-source freshness.

Meaningful failure cases include held/recalled stock, nonrefrigerated trucks, capacity/inventory shortages, stale approval and instruction versions, invalid coordinates, altered planning metrics, corrupt source files, bounded queries and preservation of operator state.

Four upstream Python deprecation warnings have appeared in previous runs; consult the current captured pytest log. Browser, CI and live API tests are distinct evidence and are never inferred from one another.

The first GitHub Actions run succeeded after repository creation. New commits need their own CI result; a local pass alone does not prove a remote run passed.

Executed source refresh actions: 5 new provider responses, 5 usable payloads, 0 failed/stale actions; finished 2026-10-27T07:20:38.737126+00:00. This is distinct from registry catalog/discovery probes. Evidence: reports/source_actions.json.

# Evidence | Coverage and scientific limits

Raw inventory: 42 file records. Originals are preserved locally; inventory checksums remain in data/manifests/inventory.json.

Historical NOAA: 2730 observed station-days of 2730 requested; 9 missing metric values. Status: partial. Window: 2025-01-01 through 2026-06-30.

Weather forecasts, historical reanalysis, observed historical station weather and simulated cargo temperature are different types of evidence. They cannot be relabeled interchangeably. NOAA trace precipitation work remains reserved for genuine Kiro execution.

Chronological model holdout: 23472 rows. Historical prevalence Brier: 0.08855575158082965; logistic Brier: 0.08859439527274823; logistic ROC-AUC: 0.498029361009236.

The logistic model did not establish useful advantage over prevalence in the primary holdout. The transparent historical estimator is retained. These are retrospective results, not validated prospective forecasts or consumer illness probabilities.

Actual sample-result publication dates are absent. Assumed reporting lags and frozen-snapshot sensitivity are documented, but do not establish prospective feature availability.

CDC NORS outbreaks and BEAM surveillance remain distinct from FSIS sampling outcomes. BEAM source exports can include human, animal and food categories; inspect their original source fields.

Recall notices are official evidence, but fictional lots have no genuine traceability supporting a verified product/lot match. No live recall match or regulatory disposition is claimed.

Public OSRM routes are for the driving profile, lack commercial-truck restriction validation and do not automatically include current MoDOT closures. Independent geometry proximity prompts review and can produce false positives.

Cargo projections use uncalibrated physical assumptions and parameter sensitivity, not learned failure probabilities, food-safety thresholds or confidence intervals.

# Walkthrough | What to show behind the buttons

Command: compare A/B/C/D metrics. Open decision details to inspect selected shipments, exclusion reasons and resource limits. Review a proposal with an identity and rationale; stale or unsafe plans are rejected.

Route laboratory: choose one farm, regional fleet or editable custom operation. Run a plan with explicit capacity, shift, ambient and delay assumptions. Inspect each route, travel fallback and thermal sensitivity. This does not dispatch.

Saved experiments: save a completed run, change assumptions and save another version/project. Reopen historical versions, compare two projects and export immutable JSON or stop-sequence CSV. Saved source timestamps are not silently refreshed.

Dispatcher desk: complete or escalate the scenario-B verification checklist, review an incident, record a human lot hold/release and issue versioned instructions. A hold removes affected assignments. Release does not recreate dispatch; a new reviewed plan is necessary.

Drive: open /?mode=drive for the dedicated visual surface. Inspect the approved destination, planned travel, simulated fuel/range, dispatch-origin reference and cargo temperature. No actual GPS progress or real remaining ETA is inferred.

Parked-use controls: self-confirm safe parking to enable reports and acknowledgments for ten minutes. Driving focus and expiry lock these interactions at both the UI and legacy server endpoints. This does not detect actual motion, prove safe parking or prevent other device use.

Driver reports: use a canned refrigeration/road/vehicle/cargo concern or type a report while parked. The standard dispatcher inbox retains original assignment context; no automatic hold, rerouting or external emergency call occurs.

Sources: inspect current source age/fallback labels, historical NOAA coverage and actual paginated source rows. Filter one dataset column at a time; inspect schema and missing cells. Do not cross-link unrelated evidence.

Model evaluation: show the measured baseline and model comparison, calibration and limitations. Explain why an honest weak predictive result is preferable to invented accuracy.

Project brief: download this PDF from the app. Use the feature register, test evidence and remaining decisions to coordinate teammates.

# Presentation | Five-minute narrative

0:00-0:40 | Problem and actor. Explain the regional poultry distributor, Missouri geography, real evidence and fictional operations. State that consequential action requires human review.

0:40-1:20 | Provenance. Show source age, one real FSIS row and the separate CDC layer; identify NOAA gaps. Distinguish forecasts from cargo readings.

1:20-2:00 | Science. Show actual chronological baseline/model results. State the target and publication-timing limitation. Do not claim consumer-illness prediction.

2:00-3:00 | Response choices. Compare scenario cost and unmet demand; inspect constraint checks. Explain why a cheaper plan with more unmet demand is not automatically better.

3:00-4:10 | Operations. Introduce a simulated disruption in an isolated demo database, approve a revised plan, then switch to Drive to acknowledge instructions and report an incident.

4:10-4:40 | Scale and route planning. Show one-farm and multi-origin experiments, source labels and a saved comparison. Avoid claiming certified truck routing.

4:40-5:00 | Contribution and limits. Point to reproducible code, source hashes, tests, human decision records and remaining Kiro evidence. End on the decision-support value, not invented prediction accuracy.

Rehearsal is a planned narrative, not a claim that a timed live presentation has passed. Use reports/demo_script.md and scripts/demo_run.py; preserve the operator database.

# Next decisions | Keep the submission complete

1. Sign into the actual Kiro application and execute/review the reserved NOAA trace-precipitation spec. Retain authentic task and terminal evidence. Codex cannot retroactively satisfy that requirement.

2. Review the full organizer rubric, team authorship and report claims. Resolve required source/timing gaps or explicitly report their scientific consequences.

3. Rehearse the five-minute presentation with the team, verify a clean checkout, and inspect the final reviewer ZIP before submission.

P2 gate: leave account tenancy, billing, LLM assistance and physical sensors deferred while P0 signoff is incomplete. Farm/fleet planning does not imply multi-tenant production readiness.

Operational limitation: this is a local loopback demonstrator with self-declared identities. Teammates share code through GitHub; each local app has separate state unless deliberately provisioned otherwise.

Change history: docs/changelog.md. Detailed research draft: reports/aegis_report.md. Engineering status: docs/progress.md. Build evidence: reports/session_verification.json.
