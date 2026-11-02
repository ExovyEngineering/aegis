# AEGIS Final Challenge Report

## Study purpose and principal findings

AEGIS asks how a regional poultry distributor can combine public food-safety, human-surveillance and environmental evidence with logistics constraints to preserve eligible food while responding to disruption. The contribution is a reproducible research pipeline connected to a working, reviewable decision-support application.

The integrated research study retained 490 of 1,534 selected Missouri samples after source-coverage gates. On the chronological held-out cohort, core-model Brier was 0.112456 versus 0.114307 for the prevalence baseline. Individual added-source gains were not established; NORS worsened the recorded holdout score. This evidence supports continued research, not prospective model activation.

Operational experiments independently compare three allocation policies across three simulated conditions. They demonstrate food-volume, destination-service and travel tradeoffs under binding safety exclusions. They do not establish reduced illness, real savings or population equity. Kiro was not used, and that challenge criterion is explicitly unmet.

### Decision statement and application access

Primary actor: regional Missouri poultry distributor/logistics operator. Commodity: refrigerated poultry. Geography: simulated Columbia, Kansas City, Jefferson City, Springfield and St. Louis network. The dispatch horizon is six hours; the separate retrospective sampling study uses seven-day forecast origins.

Decisions: inspect/request information, allocate eligible inventory, review a precautionary hold, compare a route, or approve alternative receiving instructions. Inventory, demand, capacity, deadlines, use-by, recall/hold and eligibility constraints stay binding. Consequential actions require an identified human review.

Launch the existing operator application with Start-AEGIS.cmd, or .venv/Scripts/python scripts/start_local.py. Keep its terminal open. For the prebuilt reviewer ZIP, use Start-AEGIS.cmd --no-build after installing pinned Python dependencies. No Node installation is needed merely to view prebuilt assets.

Open http://127.0.0.1:8000. Use a fresh isolated rehearsal for demonstrations: .venv/Scripts/python scripts/start_rehearsal.py --port 8001. A URL parameter alone does not isolate the operator database. Do not reset saved operator work.

Working research build; scientific and human evidence gates remain open. The challenge requirements below are mapped literally. An implemented research pipeline is distinct from a scientifically validated prospective deployment and from genuine team/Kiro evidence.

## Task 1: Define the One Health system and integrated data layer

Status: Evidence compiled.

A Missouri poultry distributor decides which eligible shipments to review, allocate and reroute over the next six hours; a separate seven-day research target concerns selected FSIS samples.

### Implemented evidence

- One Health system diagram distinguishes human, food/animal, environment, logistics and food-security pathways.
- Common Missouri/state and daily/monthly units, forecast origins, lags and coverage gates are documented.
- Field dictionary, missingness, source provenance and harmonized retrospective analytic CSV are exported.

### Limits and remaining evidence

- No patient-to-lot, genomic, supplier-contract or outbreak-causation linkage is inferred.

### Alignment and provenance

The integrated study aligns Missouri human surveillance aggregates and a five-station ambient index with a selected Missouri FSIS sample at a forecast origin seven days before collection. These are aggregate context features, not person-to-food, genome-to-genome or establishment exposure matches. A complete-source gate drops unsupported rows; missing observations are not invented.

Full definitions: docs/analytic_alignment.md; reports/data_dictionary.csv; reports/source_provenance.json; data/processed/integrated_mo_analytic.csv. Original inventory and raw bytes remain preserved. The diagram uses separate pathways and labeled simulation boundaries.

The required provenance fields are documented in reports/source_provenance.csv and JSON, docs/data_catalog.md and config/api_registry.yaml: source and endpoint, recorded access/retrieval or unknown date, license/terms and geographic/time scope, update cadence, transformations and limitations. Missing publication/access timestamps remain unknown. This distinction is material to prospective validity.

Historical NOAA observations, Open-Meteo forecasts, NWS official alerts and simulated cargo temperature retain separate labels. Ambient weather is not the temperature inside a load. The required historical stream here covers the inspected five-station window; it is not claimed complete for all historical FSIS samples.

## Task 2: Develop and validate the proactive risk model

Status: Research implemented; prospective activation closed.

Chronological Missouri study combines lagged FSIS history, PulseNet-derived BEAM aggregates and NOAA observations, with NORS ablation. Small samples and assumed historical availability prevent prospective deployment claims.

### Implemented evidence

- Prevalence and FSIS-only baselines, core integration, added-domain ablation and rolling validation.
- Brier, PR-AUC, ROC-AUC, calibration, uncertainty and review-threshold false-positive/negative consequences.
- Held-out monthly time series preserves missing source-coverage periods as gaps.

### Limits and remaining evidence

- Actual historical publication times are unknown; lags are explicit assumptions.
- Selected FSIS sampling positivity is not consumer illness or individual-lot risk.
- Added data may worsen results; no automatic model activation or guaranteed gain.

### Target, features and validation design

The outcome is Salmonella positivity in a selected Missouri FSIS primary raw-poultry sample collected seven days after its declared forecast origin. It is conditional on being sampled; neither representative regional prevalence nor an illness probability is estimated. Logistic regression with training-only scaling is compared with fixed smoothed training prevalence. Small samples and uncertain source availability do not justify a more complex boosted model.

Predictors are lagged Missouri FSIS prevalence, seasonal sine/cosine, log human Salmonella isolate counts from the BEAM export, and trailing 28-day five-station NOAA temperature/precipitation summaries. NORS adds lagged historical outbreak-record counts in a separate ablation. Standardized coefficients describe conditional associations, not causal effects.

Declared availability assumptions: FSIS collection plus 90 days; BEAM month-end plus 90 days; NORS month-end plus 730 days; NOAA reporting label plus seven days. Training labels must become assumed-available before validation starts. The same complete-case cohort is used in all comparisons, with no random split, future labels or missing-weather imputation. Actual historical publication vintages are unavailable; these assumptions cannot prove the snapshots existed at forecast time.

Measured primary split: 255 training samples; 171 held-out samples, including 22 positives. Validation origins 2026-01-05 to 2026-06-23. Outcomes occur seven days later; fitting uses the declared label embargo.

| Model | Brier score | Brier 95% interval | PR-AUC | ROC-AUC |
| --- | --- | --- | --- | --- |
| baseline | 0.114307 | 0.07476 to 0.15555 | 0.12865 | 0.50000 |
| fsis | 0.112557 | 0.07322 to 0.15297 | 0.17222 | 0.60677 |
| fsis_cdc | 0.112651 | 0.07295 to 0.15352 | 0.16635 | 0.59945 |
| core_integrated | 0.112456 | 0.07259 to 0.15244 | 0.15293 | 0.58527 |
| with_nors | 0.124489 | 0.07830 to 0.17244 | 0.16761 | 0.57398 |

Lower Brier is better. Models are compared on the same supported cohort. Weekly bootstrap bands address within-cohort variation, not publication-lag uncertainty or transportability. Calibration Wilson bands assume independent binomial observations and omit clustering. A no-sample month remains a gap, not zero risk.

- PulseNet-derived BEAM aggregate: Brier change 0.000095; paired 95% interval -0.000971 to 0.001587. Paired interval includes zero; added value not established
- NOAA ambient context: Brier change -0.000195; paired 95% interval -0.001311 to 0.000644. Paired interval includes zero; added value not established
- NORS exported outbreak-record context: Brier change 0.012033; paired 95% interval 0.005491 to 0.018963. Higher Brier in this conditional holdout; added source did not improve calibration/error
- All integrated domains: Brier change 0.010183; paired 95% interval 0.003787 to 0.016888. Higher Brier in this conditional holdout; added source did not improve calibration/error

### Core-model calibration and error consequences

At a predeclared 0.10 research-review threshold, the held-out core model has: {"tp": 13, "fp": 62, "tn": 87, "fn": 9}. These are selected-sample classification counts, not illnesses or actual operational holds.

| Bin n | Mean estimate | Observed fraction | Wilson 95% band |
| --- | --- | --- | --- |
| 11 | 0.0481 | 0.0909 | 0.0162 to 0.3774 |
| 85 | 0.0677 | 0.0941 | 0.0485 to 0.1749 |
| 75 | 0.1192 | 0.1733 | 0.1042 to 0.2743 |

Review false positives as consumed inspection capacity and false negatives as missed positive selected samples, never illnesses caused or a safe/unsafe classification. The NORS holdout feature can be constant; a harmful result here is not a general verdict against outbreak surveillance. The original national FSIS evaluation is a separate target/cohort and is retained in reports/model_evaluation.json.

Core precision at the diagnostic 0.10 threshold is 0.1733 and recall is 0.5909; fraction prioritized is 0.4386. The threshold is a research diagnostic, not an instruction to hold cargo. Rolling-origin evaluations and unavailable folds are retained in the full JSON; uncertainty is based on 400 weekly block resamples, not individual shipment intervals.

CDC confirms the BEAM dashboard uses PulseNet and NORS data: https://www.cdc.gov/beam/about/index.html. The supplied BEAM report data are aggregate SEDRIC surveillance, not genomes or linked patients. The three core sources and additions retain their own observation and retrieval dates.

## Task 3: Food safety and food security decision support

Status: Policy study implemented; pathogen-risk action link limited.

Compare a feasible input-order rule, volume/quality-guided optimization and balanced destination service across three simulated scenarios. Preserving eligible food volume is the explicit food-security objective.

### Implemented evidence

- All policies share stock, perishability, capacity, eligibility, hold/recall and delivery constraints.
- Quantified distributed/unmet kilograms, quality-budget exposure, service, distance and time.
- Existing Command and freshness workflows require separate human approval before assigning Drive work.

### Limits and remaining evidence

- National/regional surveillance cannot supply valid individualized risk for fictional lots.
- Quality forecasts are illustrative; no causal risk reduction or observed food waste is claimed.
- No verified destination-to-county/population linkage exists, so USDA need weights are not invented.

### Decision formulation

Candidate-shipment binary decisions share stock, origin/supplier throughput, refrigerated-truck capacity, destination demand, eligibility, hold/recall, use-by, receiving buffer and delivery-deadline constraints. The rule policy takes the first feasible candidates in declared input order. The volume policy lexicographically maximizes eligible delivered kilograms, then short-clock kilograms preserved through delivery, then minimizes estimated distance. The balanced policy first maximizes destination service fractions capped at 50%, then applies those volume/quality/distance priorities. This is equal destination service, not a verified population-vulnerability weight.

Quality budgets integrate simulated product-temperature history with an illustrative Q10 rate relative to 4 C; remaining reference life is divided by the forecast rate for a forward window. Chosen Q10 sensitivity cases are not confidence intervals. Unknown coverage, held/recalled stock and exceeded modeled clocks remain exclusions. This freshness calculation is not a calibrated poultry spoilage, pathogen-growth or molecular measurement model.

A proposed rescue compares the quality window with journey and receiving time, screens eligible closer recipients and presents alternatives for dispatcher review. A separate approval updates the exact simulated driver assignment. No predictive score alone can impose a mandatory hold, and no route is certified for commercial-truck restrictions.

### Quantified policy comparisons

| Scenario / policy | Distributed kg | Unmet kg | Destinations | Quality exposure kg |
| --- | --- | --- | --- | --- |
| Baseline quality-constrained wave / First feasible candidate | 4,400 | 3,100 | 11 | 4,800 |
| Baseline quality-constrained wave / Quality-guided volume preservation | 4,400 | 3,100 | 11 | 4,800 |
| Baseline quality-constrained wave / Quality-guided balanced service | 4,400 | 3,100 | 11 | 4,800 |
| Fleet scarcity and heterogeneous demand / First feasible candidate | 2,800 | 6,200 | 6 | 5,600 |
| Fleet scarcity and heterogeneous demand / Quality-guided volume preservation | 3,200 | 5,800 | 7 | 4,400 |
| Fleet scarcity and heterogeneous demand / Quality-guided balanced service | 3,200 | 5,800 | 8 | 4,800 |
| Delay and supply restriction / First feasible candidate | 3,200 | 4,300 | 8 | 4,800 |
| Delay and supply restriction / Quality-guided volume preservation | 3,200 | 4,300 | 8 | 4,800 |
| Delay and supply restriction / Quality-guided balanced service | 3,200 | 4,300 | 8 | 4,800 |

Food security is operationalized as preserved eligible food volume and destination service. Modeled quality-budget exposure is neither observed waste nor predicted pathogen risk. Balancing service can trade travel or short-clock preservation for more destinations served. Inspect independent constraints and the full per-destination service export.

| Scenario / policy | Estimated distance km | Solver status | Constraint violations |
| --- | --- | --- | --- |
| Baseline quality-constrained wave / First feasible candidate | 1,878.67 | RULE_FEASIBLE | 0 |
| Baseline quality-constrained wave / Quality-guided volume preservation | 1,209.27 | OPTIMAL | 0 |
| Baseline quality-constrained wave / Quality-guided balanced service | 1,209.27 | OPTIMAL | 0 |
| Fleet scarcity and heterogeneous demand / First feasible candidate | 1,294.85 | RULE_FEASIBLE | 0 |
| Fleet scarcity and heterogeneous demand / Quality-guided volume preservation | 1,093.99 | OPTIMAL | 0 |
| Fleet scarcity and heterogeneous demand / Quality-guided balanced service | 1,266.32 | OPTIMAL | 0 |
| Delay and supply restriction / First feasible candidate | 574.27 | RULE_FEASIBLE | 0 |
| Delay and supply restriction / Quality-guided volume preservation | 574.27 | OPTIMAL | 0 |
| Delay and supply restriction / Quality-guided balanced service | 574.27 | OPTIMAL | 0 |

All comparisons retain per-policy independent arithmetic and eligibility checks. An OPTIMAL solver status applies to the declared mathematical instance, not to real-world logistics or true food safety. Under scarcity, extra destination service can require more travel or retain less short-clock inventory; unchanged outcomes under the delay scenario are also reported rather than presented as improvement.

These comparisons are fixed-seed studies; they do not change current assignments. Operational actions remain in Command, Dispatcher and Save the Load. Unknown quality, held/recalled stock, ineligible supply and capacity violations cannot become an eligible dispatch through an objective weight.

## Task 4: Operationalize with AWS Kiro

Status: App operational; Kiro not used; requirement not met.

The project owner confirmed that Kiro was not used and will disclose this. React/FastAPI workflows operate, but prepared specifications do not satisfy genuine Kiro use.

### Implemented evidence

- Documented local launch and reproducible frontend/backend build.
- Explicit uncertainty/source labels, immutable captured exports and hard operational constraints.
- Specifications/steering and a concrete genuine-Kiro handoff task.

### Limits and remaining evidence

- Kiro was not used. The owner will disclose this unmet challenge criterion; no Kiro history or authorship is claimed.
- Local reviewer identities are self-declared, without production authentication or tenancy.

Current-risk/evidence view: Command and Model evaluation. Prioritized attention: Command review queue and Dispatcher. Scenario builder: Command disruption preview, A/B/C/D and Route laboratory. Recommended action: reviewed plans/rescue options. Explanation: evidence assistant and source/model details. No model can declare a shipment safe or unsafe.

Owner disclosure: Kiro was not used. The Kiro-use criterion is therefore not met. Implementation was developed outside Kiro with Codex assistance and human direction. No Kiro-generated code or authentic Kiro task history exists to claim; prepared steering/specification files do not establish use. No extra AWS service or cloud deployment is needed to operate this local research build.

## Task 5: Team science and value of new data

Status: Statement and comparison prepared; final team review pending.

Isaac Jenkins led disease-side evidence and databases; Micky fact-checked code and helped establish GitHub collaboration; the project lead handled supply-chain logistics, gathered remaining data and designed application requirements and extensions. Disease-side input shaped CDC/BEAM integration and historical analysis. NORS and USDA add domains beyond the three core sources.

### Implemented evidence

- One-page team science draft documents known stakeholder feedback and resulting workflow changes.
- Added-data evaluation reports measured benefit or harm rather than assuming integration improves accuracy.
- Next priorities are timestamped data releases, calibrated poultry telemetry and verified logistics/health partners.

### Limits and remaining evidence

- Isaac Jenkins is named as provided. Review role wording and authorship with the team; Micky's surname and the lead's preferred author name remain for completion.
- No professional credential, external interview or genuine Kiro participation is inferred from these contributions.

### Team science statement

AEGIS began with a practical question: how can a poultry distributor use public food-safety and environmental evidence to make better delivery decisions while keeping food available? As the idea developed, we connected retrospective risk research to a simulated Missouri distribution network, then added temperature-history replay, freshness-aware allocation, routing alternatives and a driver view. Our central contribution is an auditable path from evidence to an operational choice that a person can review.

| Contributor | Project contribution reported by the team lead |
|---|---|
| **Isaac Jenkins** | Led the disease and public-health perspective, including disease-related databases and the use of CDC evidence. |
| **Micky** | Fact-checked code and helped establish the GitHub repository and collaboration setup. |
| **Project lead** | Led supply-chain logistics, gathered the remaining data, defined the application's purpose and designed its operational features and extensions. |

These roles describe project contributions, not professional credentials. Codex assisted implementation, documentation and automated testing. Micky's surname and the lead's preferred author name may be added during final author review.

**A decision changed by another perspective.** Isaac's disease-side input helped broaden the original logistics concept to include CDC data, especially BEAM, and examination of historical patterns. This changed the evidence available to the research pipeline. It also made a scientific boundary essential: human surveillance can provide regional context, but cannot identify a fictional shipment as contaminated. The lead's feedback about confusing controls and driver distraction subsequently shaped guided questions, clearer map workflows and parked-use reporting. These are reported project decisions, not a formal external usability study.

**What integration taught us.** FSIS selected poultry samples supply the outcome, PulseNet-derived BEAM aggregates supply human-surveillance context, and NOAA supplies an ambient-weather index. NORS historical outbreaks and USDA Food Environment Atlas county context add two domains beyond those core sources. On 171 held-out Missouri samples, the core model's Brier score was 0.11246 versus 0.11431 for the prevalence baseline. BEAM and NOAA marginal intervals included zero. Adding NORS worsened Brier to 0.12449; its old, constant holdout feature limits interpretation. More data did not automatically produce a better prediction. USDA remains contextual because simulated recipients have no verified population-need crosswalk.

**How the question evolved.** Rather than turn uncertain surveillance into automatic shipment holds, we kept scientific estimates separate from binding recall/hold exclusions and human approval. Freshness replay and constrained scenario comparisons show how timing, eligible inventory and destination service interact. Their quality parameters and all logistics outcomes are simulated; they do not establish measured spoilage, prevented illness or real-world savings.

**Next collaboration.** A refrigerated distributor working with a public-health or food-safety partner could supply deidentified lot/establishment/time traceability, actual release timestamps, calibrated cargo histories and receiving/demand data. That would enable prospective validation and stronger food-access analysis. Authors will review credit and claims before submission. **Kiro was not used**; prepared specs and steering files do not satisfy genuine Kiro use.


## Every dashboard menu and its use case

| Menu | What to find and do | What changes state |
| --- | --- | --- |
| Command center | Missouri map/layers, attention queue, delivery outlook, route comparison, event preview, four response plans. | Only explicit event application or identified plan approval. |
| Save the Load | Stored temperature replay, point/conservative clocks, eligible rescue recipients, FEFO/FIFO picks, reviewed exact-driver handoff. | Replay changes experiment history; separate approval replaces the checked plan. |
| Route laboratory | One-farm/multiple-origin fleet experiments, custom locations, truck loads, deadlines, saved versions and exports. | Saved laboratory experiments, not Command dispatch. |
| Road intelligence | Missouri/Iowa incident evidence, named/custom journeys, route proximity, alternatives, capture/export. | Planning inspection only; no truck certification or automatic closure avoidance. |
| Dispatcher desk | Incident inbox, hold/release decisions, instructions and read-only readiness checks. | Explicit human decisions can remove or revise assignments; release does not redispatch. |
| AEGIS Drive | Approved truck/trip/destination, simulated fuel/position/cargo, disruptions, parked acknowledgment/reporting. | Parked confirmations, versioned acknowledgments and incident reports. |
| Evidence assistant | Type chicken or select a question; inspect captured factual answers, citations and suggested workspace. | Read-only guidance; no autonomous decision or evaluated model-written advice. |
| Model evaluation | New Missouri integrated study, same-cohort ablations, uncertainty/time series; separate original national baseline and error analysis. | None; viewing does not train or activate a model. |
| Project brief | Five task cards, final PDF, policy comparisons, full handbook, team brief, execution evidence and isolated rehearsal timer. | Rehearsal records only in a verified isolated runtime. |
| Sources & evidence | Source coverage/failures, raw inventory, underlying tables, NOAA gaps, USDA county context and provenance. | Explicit source refresh updates caches; never dispatch. |

Header controls: Reload application data rereads current network/supporting reports; it is not a universal provider refresh. The bell focuses the review queue. Recent activity inspects saved actions without replaying them. An avatar is not production login.

## Presentation idea: from evidence to a reviewed decision

Story: a Missouri poultry dispatcher must preserve food access while responding to uncertain evidence and a temperature-exposed load. Show the action chain and one quantified tradeoff, then disclose the negative model result. Do not spend the whole video touring menus.

| Time | Scene | Point to make |
| --- | --- | --- |
| 0:00–0:35 | Command map and One Health diagram | Name the actor, six-hour decision, fictional network and distinct source pathways. |
| 0:35–1:20 | Sources, Model evaluation | Show three core sources, seven-day integrated study, uncertainty and an ablation that does not improve prediction. |
| 1:20–2:05 | Project brief policy comparison | Compare rule, volume and balanced service under scarcity; show kilograms, service and hard safety exclusions. |
| 2:05–3:25 | Save the Load in a fresh isolated session | Replay heat, distinguish point from conservative quality, inspect FEFO/FIFO and whole-plan tradeoffs. |
| 3:25–4:20 | Human rescue review to Drive | Three confirmations, exact truck/trip update, parked acknowledgment and short incident report. |
| 4:20–5:00 | Five task checklist and conclusion | State real team roles and genuine Kiro evidence only if completed; name limits and the next dataset/partner. |

Practice with a timer; this outline is not a claim of a completed human video. The longer button-by-button runbook is in docs/recording_guide.md and the full master guide. Disclose that Kiro was not used. Final team/author review and a watched/listened-to take remain required.

## Reproducibility and submission deliverables

| Deliverable | Included files and how to use them |
| --- | --- |
| Analysis notebooks and scripts | notebooks/00 through 03; scripts/audit_data.py, source-specific ingest scripts, train_model.py, train_integrated_study.py, run_decision_study.py and execute_notebooks.py. |
| Development artifacts | .kiro/specs/, .kiro/steering/ and AGENTS.md contain structured requirements and guidance. Kiro was not used; there is no authentic Kiro-generated code or task history. |
| Runnable application | React/TypeScript frontend, FastAPI backend, prebuilt assets and Setup-Judges-Windows.cmd / Start-Judges-Windows.cmd; local deployment instructions in docs/local_startup.md, docs/judge_quick_start.md and README. GitHub Pages alone cannot host the Python backend; no public cloud deployment is claimed. |
| Dictionary and provenance | reports/data_dictionary.csv; reports/source_provenance.json; docs/data_catalog.md; config/api_registry.yaml and original inventory manifests. |
| Report and team science | This report, editable reports/final_submission_guide.md, and reports/team_science_statement.pdf with docs/team_science_statement.md. |
| Setup and dependencies | README.md, JUDGES_START_HERE.md, requirements-lock.txt, optional requirements-notebooks.txt and frontend/package-lock.json. |

### Executed notebooks

Install optional notebook dependencies using .venv/Scripts/python -m pip install -r requirements-notebooks.txt, then run .venv/Scripts/python scripts/execute_notebooks.py. The four notebooks cover coverage/provenance, preprocessing/integration, modeling/evaluation and scenario analysis. Static previews are in reports/notebooks/index.html; they do not require Jupyter to read.

The default profile reruns maintained analysis functions and scripts from included processed snapshots and selected original NOAA responses. Numeric assertions compare recomputed cohorts, metrics and policy outcomes with the recorded study. Each run has a private copied workspace and blocks provider requests; operator records and original source bytes are preserved. Timestamps, UUIDs and timings are not fixed scientific results.

The raw-data profile additionally requires the separately supplied original downloads: .venv/Scripts/python scripts/execute_notebooks.py --notebook 01_Preprocessing_and_Integration.ipynb --raw-data-dir PATH. It verifies provenance-listed filenames and hashes, audits copies, runs source adapters, regenerates model and decision results and compares them. Bulk originals are excluded from the judge ZIP and GitHub repository; obtain them separately or reproduce the bundled-snapshot profile.

Bundled notebook run: saved status passed; 34 executed code cells; operator preserved: True; started 2026-11-02T20:12:34.537473+00:00. These are measured execution records, not assertions that every later source revision will yield identical results.

Original-data replay: saved status passed; 11 executed code cells; operator preserved: True; started 2026-11-02T20:13:47.484535+00:00. These are measured execution records, not assertions that every later source revision will yield identical results.

### Verification and submission boundary

Latest saved full local checks: 2026-11-02T20:44:57.978534+00:00. These are dated evidence; later edits require their own checks.

- pytest: passed, tests 1316, log reports/checks/20261102T204139627497Z/pytest.txt.
- vitest: passed, tests 406, log reports/checks/20261102T204139627497Z/vitest.txt.
- frontend_build: passed, tests build, log reports/checks/20261102T204139627497Z/frontend_build.txt.

Reproduce the additions: scripts/train_integrated_study.py; scripts/run_decision_study.py; scripts/build_data_dictionary.py; scripts/render_one_health_system.py; scripts/build_final_handoff.py. Use the pinned Python and Node versions in README. Scripts preserve raw files and use separate derived outputs; never silently merge unrecognized sources.

The reviewer ZIP includes code, prebuilt UI, derived evidence and dated fixtures. It excludes original bulk downloads, active operator/rehearsal databases, credentials and local runtimes. Offline checks reuse the installed dependency environment unless a fresh-install report explicitly records otherwise.

This deliverable is a final working software/research handoff, not a claim of completed organizer acceptance. Preserve open scientific limitations, source failures, actual role attestations and Kiro evidence. Nothing is automatically deployed, merged or submitted by creating the package.
