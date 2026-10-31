# AEGIS | Team and presentation brief

Adaptive Early-warning & Guidance for Integrated Supply Chains

Generated October 31, 2026 at 02:16 AM CT. Target submission: November 2, 2026; feature freeze target October 30.

Audience: project teammates, presenters and reviewers. This is an ongoing planning brief, not a certified final submission or regulatory decision.

AEGIS supports a regional Missouri poultry logistics operator. Command combines public evidence with a deterministic simulated network; Drive carries dispatcher-approved simulated assignments and parked-use reporting.

All suppliers/contracts, lots, trucks, shipments, operational costs, demand and cargo telemetry are fictional. Official establishment locations do not establish supply relationships.

Team repository: https://github.com/ExovyEngineering/aegis (private). Start with CONTRIBUTING.md. Use feature branches and reviewed pull requests.

Update this brief: run scripts/verify_project.py after code changes, then scripts/build_project_brief.py. Update config/feature_register.yaml and docs/changelog.md when capabilities or limitations change. No live API requests are performed by the brief compiler.

# P0 | Required submission core

Source inventory and provenance | implemented; bounded coverage

42 original downloads audited; official evidence and simulated logistics remain distinct. Recursive content-based imports preserve semantic identities, record exact failures, skip duplicate bytes and block conflicting snapshots.

Evidence: reports/data_audit.md

USDA historical county context | implemented as a separate historical evidence layer

115 Missouri counties/county-equivalents and ten 2019/2020/2023 measures, with denominators, source hashes and missing codes. No safety score, current demand estimate or allocation weight is inferred.

Evidence: reports/usda_food_environment.json

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

Isolated guided rehearsal and saved evidence | implemented; genuine team presentation remains pending

Fresh verified database, six planned stages, server-clock timer, version guards and immutable evidence exports. Command and stored freshness-rescue workflows retain distinct operational provenance; reassignment requires a new contextual driver acknowledgment. A linked recording runbook covers the timed narrative and full hands-on review. Offline mode uses dated fixtures and labeled route estimates. Automated checks do not establish a human rehearsal, Kiro execution or author approval.

Evidence: docs/rehearsal_guide.md

Complete printable product handbook | implemented; dated edition requires review when capabilities change

Every workspace, visible controls, farm/fleet and dispatcher/driver use cases, source meanings, measured-model interpretation, rehearsal, storage, recovery and troubleshooting. PDF contents/bookmarks, print-friendly HTML and editable Markdown are available through Project brief.

Evidence: docs/aegis_master_guide.md

Reliable local foreground startup | implemented with configuration, asset and listener checks

Windows Start-AEGIS.cmd keeps a visible user-owned terminal. Source-build, explicit prebuilt and check-only modes remain distinct. Existing listeners are never killed/rebuilt; inherited rehearsal settings are rejected. No installation, original-data reset or background-service persistence is implied.

Evidence: scripts/start_local.py

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

Inspectable dispatch readiness | implemented as read-only diagnostics

Sixteen checks distinguish hard eligibility/resource constraints from outstanding assignment acknowledgment, instruction acknowledgment and targeted verification. Passing the listed checks does not dispatch or certify safety.

Evidence: tests/test_readiness.py

Inspectable internal activity history | implemented read-only with captured pagination and export

Header panel explains actual saved audit rows across existing workspaces, with explicit action/shipment filters, payload errors and bounded snapshots. It never replays decisions or invents missing historical effects. Self-declared actors and incomplete audit coverage are explicit; no production identity claim.

Evidence: docs/activity_history.md

Guided delivery planning outlook | implemented as a read-only deterministic planning projection

Current-input and what-if allocations show unmet demand, candidate deadline pressure and illustrative six-hour cargo checks. Four actual solver responses retain independent constraint review. Inputs and exports remain captured; exact candidate road handoffs and current-plan review shortcuts preserve captured inputs. No prospective delay skill, automatic hold, road reroute or approval is claimed.

Evidence: docs/delivery_outlook.md

Kinetic quality windows, rescue planning and FEFO | implemented with explicit review and uncalibrated model assumptions

Declared product-temperature exposure consumes an irreversible equivalent-age budget. Conservative chosen-case clocks rank closer recipients and constrained OR-Tools FEFO versus FIFO. Only identified, versioned human approval replaces the checked simulated plan and updates Drive; new readings flag renewed review.

Evidence: docs/freshness_science.md

# P2 | Stretch work and deferred extensions

Cited evidence assistant and optional model topic selection | deterministic assistant implemented; actual LLM evaluation remains pending

Six bounded explanations use a read-only network/report snapshot, source citations and measured values. Optional explicitly configured Ollama can select a topic only; it cannot author claims or execute actions. Default requires no model. Configuration and mocked tests are not model evaluation.

Evidence: docs/evidence_assistant.md

Farm and enterprise accounts | deferred

Planning scales exist; production authentication, tenant isolation and billing do not.

Evidence: docs/priority_matrix.md

Live sensor integrations | deferred

All cargo-temperature telemetry is simulated.

Evidence: docs/simulation_assumptions.md

Additional state DOT feeds | Iowa DOT adapter and read-only road workspace implemented; bounded coverage

Official Iowa 511 point records remain separate from MoDOT. A verified dated fixture contains 599 records; Columbia to Des Moines is a planning example. Route alternatives, buffer screening and exports do not dispatch, avoid closures automatically or validate truck restrictions.

Evidence: docs/state_dot.md

Verified local operational-state recovery | implemented; cloud deployment remains deferred

Read-only SQLite online backup includes committed WAL records; checksums, integrity, schema and row counts are verified before restoration to a fresh private file. Operator bytes and ten tables were preserved in an actual CLI exercise. No automatic server rebind or deployment.

Evidence: reports/backup_recovery.json

Molecular epidemiology | blocked by missing isolate-level genomic linkage

Current aggregate serotype tables do not contain linked genome sequences/accessions. No relatedness or common-source inference is claimed.

Evidence: docs/stretch_feature_gates.md

Real cloud deployment | deferred pending production access controls

Local self-declared identities are not production authentication or tenant isolation. No cloud release is claimed.

Evidence: docs/stretch_feature_gates.md

Inspectable disruption impact and Command workflow | implemented with read-only previews and explicit guarded application

Six simulated events compute exact direct/resource changes and four before/after allocations. Preview changes nothing; applying requires matching revision/hash in Command and clears all approved assignments. Map overlays, road-alternative selection, exports and page guides explain what changes. No automatic road reroute, official incident or prospective risk is invented.

Evidence: docs/command_workflow.md

Physical sensor streaming infrastructure | bounded authenticated HTTP ingestion and replay implemented; physical hardware unverified

Append-only gateway packets retain source/observation/retrieval metadata. A five-second browser poll reads stored experiments. No physical device, production broker, calibrated sensor or cloud telemetry deployment is claimed.

Evidence: docs/freshness_gateway.md

# Verification | What was actually tested

Latest local verification finished: 2026-10-31T07:14:59.940348+00:00. All requested local checks passed: True.

pytest: PASS; exit 0; tests passed 1198; 98.127 seconds. Log: reports/checks/20261031T071250192098Z/pytest.txt. Checked: 2026-10-31T07:12:50.192664+00:00.

vitest: PASS; exit 0; tests passed 385; 19.351 seconds. Log: reports/checks/20261031T071250192098Z/vitest.txt. Checked: 2026-10-31T07:14:28.334383+00:00.

frontend_build: PASS; exit 0; tests passed build check; 12.218 seconds. Log: reports/checks/20261031T071250192098Z/frontend_build.txt. Checked: 2026-10-31T07:14:47.708501+00:00.

USDA county context, source provenance and readiness browser QA: 61 / 61 recorded checks passed. Timestamp: 2026-10-28T06:27:38.973Z. Evidence: reports/browser_qa/readiness/results.json. This is a separate run from local unit/build checks.

Map, scenario, simulator and source-control browser QA: 65 / 65 recorded checks passed. Timestamp: 2026-10-28T06:19:25.790Z. Evidence: reports/browser_qa/controls/results.json. This is a separate run from local unit/build checks.

Visual Drive and parked-use actual-Chrome QA: 65 / 65 recorded checks passed. Timestamp: 2026-10-28T06:28:06.730Z. Evidence: reports/browser_qa/drive/results.json. This is a separate run from local unit/build checks.

Earlier feature-depth actual-Chrome QA: 36 / 36 recorded checks passed. Timestamp: 2026-10-28T06:19:01.253Z. Evidence: reports/browser_qa/depth/results.json. This is a separate run from local unit/build checks.

Earlier dispatcher/custom-planning browser QA: 50 / 50 recorded checks passed. Timestamp: 2026-10-28T06:27:54.619Z. Evidence: reports/browser_qa/operations/results.json. This is a separate run from local unit/build checks.

Guided rehearsal actual-Chrome QA: 76 / 76 checks passed, checked 2026-10-28T06:07:06.190Z. Record kind: automated_check; measured duration 5.37 seconds. This automated workflow does not establish a genuine five-minute team presentation. Evidence: reports/browser_qa/rehearsal/results.json.

Road intelligence actual-Chrome QA: 58 / 58 checks passed, checked 2026-10-28T19:15:52.092Z. Offline comparisons, exports and explicit browser-injected failure cases remain separate from actual public-provider requests. Evidence: reports/browser_qa/roads/results.json.

Guided delivery outlook, chicken question, map, road and dispatcher actual-Chrome QA: 76/76 checks at 2026-10-30T19:40:42.320Z. Read-only computations preserved operator/rehearsal state. External tiles used browser-only placeholders; no provider/LLM call or prospective prediction accuracy is inferred. Evidence: reports/friendliness_workflow_evaluation.json.

Recording preparation: real Chrome rescue/driver and automated tracker housekeeping: 116/116 recorded checks passed. Evidence: reports/browser_qa/recording/results.json. These isolated runs use simulated sensor packets and do not establish physical calibration, microbial safety, public-provider availability or a timed human presentation.

Save the Load actual-Chrome workflow: 94/94 recorded checks passed. Evidence: reports/browser_qa/freshness/results.json. These isolated runs use simulated sensor packets and do not establish physical calibration, microbial safety, public-provider availability or a timed human presentation.

Accelerated deterministic freshness replay: 15/15 recorded checks passed. Evidence: reports/freshness_demo.json. These isolated runs use simulated sensor packets and do not establish physical calibration, microbial safety, public-provider availability or a timed human presentation.

A duplicate push CI run failed a rehearsal frontend test while its PR run passed. The test acted before initial React effects settled; synchronization was corrected without relaxing the original assertions or changing product behavior. The failed log and focused follow-up outcomes are retained in reports/ci_followup.json and reports/checks/. Later full checks and remote runs have their own timestamps; a historical pass never substitutes for them.

Earlier separate Python dependency installation: passed=True; pinned packages verified=51; real HTTP checks=31; operator DB modified=False. This predates the road/recovery increment; consult its tested source checksum and timestamp. Fresh Node installation tested=False. Evidence: reports/clean_install.json.

Loopback HTTP smoke artifact records 29 checks against http://127.0.0.1:8000. It does not certify current public-source freshness.

Meaningful failure cases include held/recalled stock, nonrefrigerated trucks, capacity/inventory shortages, stale approval and instruction versions, invalid coordinates, altered planning metrics, corrupt source files, bounded queries and preservation of operator state.

Four upstream Python deprecation warnings have appeared in previous runs; consult the current captured pytest log. Browser, CI and live API tests are distinct evidence and are never inferred from one another.

The first GitHub Actions run succeeded after repository creation. New commits need their own CI result; a local pass alone does not prove a remote run passed.

Executed source refresh actions: 3 new provider responses, 4 usable payloads, 1 failed/stale actions; finished 2026-10-28T06:10:15.479306+00:00. This is distinct from registry catalog/discovery probes. Evidence: reports/source_actions.json.

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

# Source integrity | County context and readiness

Supported CSV/TSV evidence is discovered recursively and recognized by explicit source schemas. Stable semantic identities replace file-order labels. Schema recognition is evidence of structure, not cryptographic provider authenticity or proof of public release timing.

Exact-byte duplicate exports are recorded without pooling observations. Two different exports matching the same semantic table become a conflict; prior output bytes are retained but cannot be presented as the latest successful import. Per-file errors remain explicit, and malformed unrelated JSON no longer aborts all FSIS ingestion.

Recorded re-import comparison: 8 prior tables checked; all values/dtypes unchanged: True. Model artifact hashes unchanged: True. Evidence: reports/ingestion_verification.json.

The source browser verifies and parses the same bounded immutable byte snapshot. Row requests carry their own checksum and import provenance so concurrent replacement cannot silently change the values beneath a verified hash.

USDA Food Environment Atlas status: available; 115 Missouri counties/county-equivalents, 10 inspected variables. Source release note: The original release date of this file is July 2025.. Evidence: reports/usda_food_environment.json.

ACCESS measures use 2019 store access and source-defined historical population/housing-unit denominators. Grocery measures are dated 2020; SNAP-authorized store measures are dated 2023. These are historical county context, not current household conditions, demand estimates, food-safety risk or allocation weights.

USDA missing observations by field: {'LACCESS_POP19': 0, 'PCT_LACCESS_POP19': 0, 'LACCESS_LOWI19': 0, 'PCT_LACCESS_LOWI19': 0, 'LACCESS_HHNV19': 0, 'PCT_LACCESS_HHNV19': 0, 'GROC20': 39, 'GROCPTH20': 39, 'SNAPS23': 0, 'SNAPSPTH23': 0}. Original sentinel codes and sheet/row identities are retained. Missing/suppressed values are never replaced with zero. Repeated county names remain distinct by FIPS; no simulated-destination or route-location join is inferred.

Dispatch readiness checks current approved assignments in one consistent read-only database snapshot. Thirteen constraint diagnostics and three workflow checks expose resource limits, assignment acknowledgment, exact-version instruction acknowledgment and scenario-B verification. A passing checklist does not dispatch, consume stock, create a hold, certify food safety or clear a commercial-truck route.

Use Sources to compare counties, inspect definitions and download the checked county CSV. Use Dispatcher desk to select a trip, filter readiness status and inspect the evidence for each check. Genuine Kiro work and final author review remain separate gates.

# Rehearsal | Practice without altering operator state

Start scripts/start_rehearsal.py --port 8001 in a separate terminal. It reserves a new UUID database and launches a separate loopback server. The operator app remains on port 8000. Partial/mismatched runtime settings are rejected before database initialization.

The rehearsal URL opens the Project brief panel with six stages totaling 300 planned seconds. Every view displays the verified isolated-runtime banner. A URL parameter alone never creates isolation.

Start with a self-declared presenter, purpose and record type. Elapsed time comes from the backend clock. Navigation and reload do not stop the timer; the UI does not infer attendance or presentation quality.

Record stage coverage or an explicit skip reason. Operational stages require recorded events, human approval and a coherent parked acknowledgment/report sequence during that run. Stale versions and unrelated or invalidated trip evidence are rejected.

Completion or abort retains an immutable snapshot of timing, milestones, network/audit state and evidence-file hashes. Download the JSON or reopen history; subsequent resets and regenerated reports cannot rewrite that export.

Offline rehearsal uses dated source fixtures, disables provider refresh and returns labeled OSRM estimates without mutable HTTP cache access. Map tiles and deliberately opened external source links can still need internet.

The accelerated demo script now measures original/configured operator SQLite and sidecar hashes before and after. A modified or unreadable protected file cannot become an invented preservation success. This utility is separate from the guided browser timer.

Automated checks and self-reported practice do not complete genuine Kiro execution, author/rubric review or a live timed team presentation. The reserved Kiro task remains untouched.

# Stretch | Official road evidence and local recovery

Road intelligence now compares captured Missouri and Iowa evidence independently. The Iowa DOT public ArcGIS feed was verified through its official source and queried in bounded pages; its dated fixture retains 599 point records and repeated event IDs without merging them.

Choose a Columbia-to-Des Moines planning corridor or custom coordinates. Inspect provider fields, unverified event clocks, attribution and geometry gaps. Source previews are bounded at 200 records; route screening uses all bounded supported geometries and lists up to 100 nearby records per source/alternative.

Compare estimated connections or available public OSRM ordinary-driving alternatives, inspect separate proximity matches, change assumptions and export the captured JSON. Changed inputs/evidence flag a prior result. No record match establishes a clear road, automatic closure avoidance or commercial-truck suitability.

Actual live road-workspace requests checked at 2026-10-28T19:08:49.250823+00:00. Endpoints recorded: 2. Detailed provider/cache/failure and route-fallback fields: reports/road_intelligence_live.json. Offline browser checks are a different artifact.

Local SQLite recovery now creates a read-only online backup including committed WAL records, verifies checksum/integrity/schema/row counts, and restores only to a fresh private data/recovered file. Existing operator state is never overwritten or automatically rebound. Backups/receipts are excluded from Git and reviewer packages.

Actual CLI recovery exercise status: passed; checked 2026-10-28T19:05:29.819398+00:00. Measured preservation fields: {'operator_database_bytes_unchanged': True, 'operator_database_sha256_unchanged': True, 'operator_all_tables_unchanged': True, 'recovered_all_tables_equal_original': True, 'recovered_hold_recall_flags_equal_original': True, 'restored_bytes_equal_backup': True, 'restore_receipt_present': True, 'server_started': False, 'cloud_deployed': False}. Evidence: reports/backup_recovery.json. A restored copy still requires human review of assignments and state.

These are bounded stretches. Cloud deployment, production authentication, tenant isolation, physical sensors, genomic attribution and LLM assistance remain unimplemented. Genuine Kiro, final author review and a timed team rehearsal remain open submission gates.

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

P2 gate: leave account tenancy, billing, model-authored advice and physical sensors deferred while P0 signoff is incomplete. Farm/fleet planning does not imply multi-tenant production readiness.

Operational limitation: this is a local loopback demonstrator with self-declared identities. Teammates share code through GitHub; each local app has separate state unless deliberately provisioned otherwise.

Change history: docs/changelog.md. Detailed research draft: reports/aegis_report.md. Engineering status: docs/progress.md. Build evidence: reports/session_verification.json.
