# AEGIS Final Submission Guide

## What to launch and what this build establishes

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

Owner disclosure: Kiro was not used. The Kiro-use criterion is therefore not met. Codex-written steering/specification files and an installed IDE are preparation, not authentic Kiro task history. This document does not claim otherwise. No extra AWS service or cloud deployment is needed to operate this local research build.

## Task 5: Team science and value of new data

Status: Statement and comparison prepared; final team review pending.

Isaac handled the disease side; Micky provided coding help. The project owner reports that disease-side input shaped CDC/BEAM integration and historical analysis. NORS and USDA add domains beyond the three core sources.

### Implemented evidence

- One-page team science draft documents known stakeholder feedback and resulting workflow changes.
- Added-data evaluation reports measured benefit or harm rather than assuming integration improves accuracy.
- Next priorities are timestamped data releases, calibrated poultry telemetry and verified logistics/health partners.

### Limits and remaining evidence

- The owner will add contributor last names; review final names, role wording and authorship with the team.
- No professional credential, external interview or genuine Kiro participation is inferred from these contributions.

### Team science statement

#### Team science statement — prepared for author completion

AEGIS combines public-health surveillance, food-safety sampling, environmental observations, constrained logistics and user-centered operations design. The project owner reports collaborating with **Isaac**, who handled the disease side, and **Micky**, who provided code help. Their last names, affiliations, professional credentials and detailed contribution review remain pending. Implementation and analysis also used Codex assistance; automated checks do not substitute for multidisciplinary human review.

| Required perspective / responsibility | Named contributor and verified contribution |
|---|---|
| Food safety / regulatory interpretation | **Pending author confirmation**; review sampling target, verification, holds/recalls and disposition limits. |
| Disease / public-health perspective | **Isaac — last name pending.** Project owner reports the disease-side role and input toward CDC/BEAM integration and historical analysis; credentials are not supplied. |
| Data science / environment | **Pending author confirmation**; review time-aware validation, assumed availability, NOAA coverage and uncertainty. |
| Software / code support | **Micky — last name pending.** Project owner reports code help; exact implementation contributions and review remain pending. |
| Supply chain / food security | **Pending author confirmation**; review stock, receiving, perishability, service trade-offs and actual recipient need. |
| Project lead / integration / user design | **Project owner — name pending.** Integration and workflow priorities are evidenced by the owner's actual product requests below; no specialist credential is inferred. |

The project owner reports that disease-side input helped choose broader CDC integration, especially the BEAM dashboard, and the idea of examining past data. This is the reported interdisciplinary decision associated with Isaac's disease-side role; it does not attribute specific lag assumptions, model results or credentials to him. Separately, the owner's requests for friendlier “chicken” queries, clearer map/road direction and reduced texting temptation informed guided choices, task presets and parked Drive gates. These actual inputs appear in the working conversation and implementation notes ([progress](progress.md), [Drive design](drive_design.md)); they are not external interviews or usability-trial findings.

The three core domains are FSIS, PulseNet-derived BEAM and NOAA. Two additions are **CDC NORS historical outbreak reports** and **USDA ERS Food Environment Atlas county context**. On the same 171 held-out selected samples, the core integrated model's Brier score was 0.11246; adding NORS worsened it to 0.12449 (paired change +0.01203; week-bootstrap 95% interval +0.00549 to +0.01896). BEAM and NOAA marginal intervals included zero: added predictive value was not established. See [the measured study](../reports/integrated_model_study.md). USDA adds access/store definitions, denominators and suppressed-value transparency for 115 Missouri county identities. It stays contextual because fictional recipients have no verified county or needs assessment. FSIS directory and road/routing layers add context without becoming food-safety outcomes.

The strongest next partner is a real refrigerated distributor/receiving network working with a public-health or food-safety expert. An approved, deidentified lot/establishment/time cross-walk, actual result-publication timestamps, calibrated cargo histories and recipient demand/receiving data would permit defensible exposure and access analysis. Genuine isolate-cluster interpretation requires an authorized public-health partner. Before submission, authors must complete names, review the reported contributions and decision, confirm credit, and disclose Kiro non-use rather than claim execution evidence. A timed team presentation and prospective validation remain separate unfinished human/scientific requirements.

Owner disclosure on November 1: **Kiro was not used**. The team will disclose this unmet challenge criterion. Prepared specs and code are not Kiro execution evidence.


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

## Verification, reproducibility and submission boundary

Latest saved full local checks: 2026-11-02T17:08:47.996965+00:00. These are dated evidence; later edits require their own checks.

- pytest: passed, tests 1256, log reports/checks/20261102T170421298785Z/pytest.txt.
- vitest: passed, tests 406, log reports/checks/20261102T170421298785Z/vitest.txt.
- frontend_build: passed, tests build, log reports/checks/20261102T170421298785Z/frontend_build.txt.

Reproduce the additions: scripts/train_integrated_study.py; scripts/run_decision_study.py; scripts/build_data_dictionary.py; scripts/render_one_health_system.py; scripts/build_final_handoff.py. Use the pinned Python and Node versions in README. Scripts preserve raw files and use separate derived outputs; never silently merge unrecognized sources.

The reviewer ZIP includes code, prebuilt UI, derived evidence and dated fixtures. It excludes original bulk downloads, active operator/rehearsal databases, credentials and local runtimes. Offline checks reuse the installed dependency environment unless a fresh-install report explicitly records otherwise.

This deliverable is a final working software/research handoff, not a claim of completed organizer acceptance. Preserve open scientific limitations, source failures, actual role attestations and Kiro evidence. Nothing is automatically deployed, merged or submitted by creating the package.
