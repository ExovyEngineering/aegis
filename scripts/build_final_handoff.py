"""Compile the five-task guide from recorded evidence without mutating the app."""
import argparse
from datetime import datetime
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.build_master_guide import parse_markdown, html_document, render_pdf

ROOT = Path(__file__).resolve().parents[1]
TITLE = 'AEGIS Final Challenge Report'


def read(root, name):
    path = root / name
    if not path.is_file():
        return None
    def invalid(value):
        raise ValueError(f'Nonfinite JSON value: {value}')
    def finite_float(value):
        result=float(value)
        if not math.isfinite(result):
            raise ValueError('Nonfinite JSON number')
        return result
    value = json.loads(path.read_text(encoding='utf-8'), parse_constant=invalid, parse_float=finite_float)
    if not isinstance(value, dict):
        raise ValueError(f'Expected an evidence object: {name}')
    return value


def number(value, digits=4):
    return f'{value:,.{digits}f}' if type(value) in (int, float) and math.isfinite(value) else 'not recorded'


def _successful(value):
    return isinstance(value,dict) and not value.get('error') and not any(word in str(value.get('status','')).lower() for word in ('failed','unavailable'))


def _model_recorded(value):
    if not _successful(value) or value.get('operational_activation_allowed') is not False:
        return False
    split=value.get('primary_split');models=value.get('models')
    if not isinstance(split,dict) or type(split.get('validation_rows')) is not int or split['validation_rows']<1 or not isinstance(models,dict):
        return False
    for key in ('baseline','fsis','core_integrated','with_nors'):
        row=models.get(key);metrics=row.get('metrics') if isinstance(row,dict) else None
        if not isinstance(metrics,dict) or metrics.get('n')!=split['validation_rows'] or type(metrics.get('brier')) not in (int,float) or not 0<=metrics['brier']<=1:
            return False
    return True


def _decision_recorded(value):
    if not _successful(value) or value.get('simulation') is not True or value.get('requires_human_approval') is not True:
        return False
    scenarios=value.get('scenarios')
    return isinstance(scenarios,list) and len(scenarios)>=3 and all(
        isinstance(scenario,dict) and isinstance(scenario.get('policies'),list) and len(scenario['policies'])>=3
        and all(isinstance(policy,dict) and isinstance(policy.get('constraint_review'),dict)
                and policy['constraint_review'].get('passed') is True for policy in scenario['policies']) for scenario in scenarios)


def readiness(root):
    model = read(root, 'reports/integrated_model_evaluation.json')
    decision = read(root, 'reports/decision_study.json')
    dictionary = read(root, 'reports/source_provenance.json')
    model_ready=_model_recorded(model);decision_ready=_decision_recorded(decision)
    required_data=('reports/figures/one_health_system.png','reports/data_dictionary.csv',
                   'data/processed/integrated_mo_analytic.csv','docs/one_health_system.md','docs/analytic_alignment.md')
    data_ready=bool(dictionary and isinstance(dictionary.get('datasets'),list) and dictionary['datasets'] and model_ready
                    and all((root/name).is_file() for name in required_data))
    rows = [
        {'id':'Task 1','title':'Define the One Health system and integrated data layer',
         'status':'Evidence compiled' if data_ready else 'Evidence incomplete', 'menu':'evidence',
         'summary':'A Missouri poultry distributor decides which eligible shipments to review, allocate and reroute over the next six hours; a separate seven-day research target concerns selected FSIS samples.',
         'implemented':['One Health system diagram distinguishes human, food/animal, environment, logistics and food-security pathways.',
                        'Common Missouri/state and daily/monthly units, forecast origins, lags and coverage gates are documented.',
                        'Field dictionary, missingness, source provenance and harmonized retrospective analytic CSV are exported.'],
         'remaining':['No patient-to-lot, genomic, supplier-contract or outbreak-causation linkage is inferred.'],
         'artifacts':[{'label':'System diagram','name':'system-map.png'},{'label':'Analytic CSV','name':'analytic-data.csv'},{'label':'Data dictionary','name':'dictionary.csv'},{'label':'Source provenance','name':'provenance.json'}]},
        {'id':'Task 2','title':'Develop and validate the proactive risk model',
         'status':'Research implemented; prospective activation closed' if model_ready else 'Model study missing, failed or incomplete', 'menu':'science',
         'summary':'Chronological Missouri study combines lagged FSIS history, PulseNet-derived BEAM aggregates and NOAA observations, with NORS ablation. Small samples and assumed historical availability prevent prospective deployment claims.',
         'implemented':['Prevalence and FSIS-only baselines, core integration, added-domain ablation and rolling validation.',
                        'Brier, PR-AUC, ROC-AUC, calibration, uncertainty and review-threshold false-positive/negative consequences.',
                        'Held-out monthly time series preserves missing source-coverage periods as gaps.'],
         'remaining':['Actual historical publication times are unknown; lags are explicit assumptions.',
                      'Selected FSIS sampling positivity is not consumer illness or individual-lot risk.',
                      'Added data may worsen results; no automatic model activation or guaranteed gain.'],
         'artifacts':[{'label':'Integrated model results','name':'integrated-model.json'},{'label':'Aligned data','name':'analytic-data.csv'}]},
        {'id':'Task 3','title':'Food safety and food security decision support',
         'status':'Policy study implemented; pathogen-risk action link limited' if decision_ready else 'Policy study missing, failed or incomplete', 'menu':'command',
         'summary':'Compare a feasible input-order rule, volume/quality-guided optimization and balanced destination service across three simulated scenarios. Preserving eligible food volume is the explicit food-security objective.',
         'implemented':['All policies share stock, perishability, capacity, eligibility, hold/recall and delivery constraints.',
                        'Quantified distributed/unmet kilograms, quality-budget exposure, service, distance and time.',
                        'Existing Command and freshness workflows require separate human approval before assigning Drive work.'],
         'remaining':['National/regional surveillance cannot supply valid individualized risk for fictional lots.',
                      'Quality forecasts are illustrative; no causal risk reduction or observed food waste is claimed.',
                      'No verified destination-to-county/population linkage exists, so USDA need weights are not invented.'],
         'artifacts':[{'label':'Policy study JSON','name':'decision-study.json'},{'label':'Policy comparison CSV','name':'decision-study.csv'}]},
        {'id':'Task 4','title':'Operationalize with AWS Kiro',
         'status':'App operational; Kiro not used; requirement not met', 'menu':'command',
         'summary':'The project owner confirmed that Kiro was not used and will disclose this. React/FastAPI workflows operate, but prepared specifications do not satisfy genuine Kiro use.',
         'implemented':['Documented local launch and reproducible frontend/backend build.',
                        'Explicit uncertainty/source labels, immutable captured exports and hard operational constraints.',
                        'Specifications/steering and a concrete genuine-Kiro handoff task.'],
         'remaining':['Kiro was not used. The owner will disclose this unmet challenge criterion; no Kiro history or authorship is claimed.',
                      'Local reviewer identities are self-declared, without production authentication or tenancy.'],
         'artifacts':[{'label':'Final guide','name':'guide.pdf'}]},
        {'id':'Task 5','title':'Team science and value of new data',
         'status':'Statement and comparison prepared; final team review pending' if model_ready and data_ready else 'Data comparison incomplete; final team review pending', 'menu':'evidence',
         'summary':'Isaac Jenkins led disease-side evidence and databases; Micky fact-checked code and helped establish GitHub collaboration; the project lead handled supply-chain logistics, gathered remaining data and designed application requirements and extensions. Disease-side input shaped CDC/BEAM integration and historical analysis. NORS and USDA add domains beyond the three core sources.',
         'implemented':['One-page team science draft documents known stakeholder feedback and resulting workflow changes.',
                        'Added-data evaluation reports measured benefit or harm rather than assuming integration improves accuracy.',
                        'Next priorities are timestamped data releases, calibrated poultry telemetry and verified logistics/health partners.'],
         'remaining':['Isaac Jenkins is named as provided. Review role wording and authorship with the team; Micky\'s surname and the lead\'s preferred author name remain for completion.',
                      'No professional credential, external interview or genuine Kiro participation is inferred from these contributions.'],
         'artifacts':[{'label':'One-page team statement','name':'team-science.pdf'},{'label':'Editable team statement','name':'team-science.md'},{'label':'Ablation results','name':'integrated-model.json'}]},
    ]
    return {'generated_at':datetime.now(ZoneInfo('America/Chicago')).isoformat(),
            'release_status':'Working research build; scientific and human evidence gates remain open',
            'requirement_reference':'docs/challenge_tasks_source.md','tasks':rows,
            'limitations':['No physical sensors or validated poultry spoilage model are demonstrated.',
                           'No regulatory authority, consumer-illness probability, genomic causation or truck-safe routing is asserted.',
                           'Kiro was not used, as disclosed by the owner. Team review and a timed human presentation are not inferred from software tests.']}


def content(root, state):
    model = read(root, 'reports/integrated_model_evaluation.json') or {}
    decision = read(root, 'reports/decision_study.json') or {}
    checks = read(root, 'reports/session_verification.json') or {}
    core=model.get('models',{}).get('core_integrated',{}).get('metrics',{})
    baseline=model.get('models',{}).get('baseline',{}).get('metrics',{})
    coverage=model.get('coverage',{})
    lines = ['## Study purpose and principal findings','',
             'AEGIS asks how a regional poultry distributor can combine public food-safety, human-surveillance and environmental evidence with logistics constraints to preserve eligible food while responding to disruption. The contribution is a reproducible research pipeline connected to a working, reviewable decision-support application.', '',
             f"The integrated research study retained {number(coverage.get('eligible_samples'),0)} of {number(coverage.get('mo_samples'),0)} selected Missouri samples after source-coverage gates. On the chronological held-out cohort, core-model Brier was {number(core.get('brier'),6)} versus {number(baseline.get('brier'),6)} for the prevalence baseline. Individual added-source gains were not established; NORS worsened the recorded holdout score. This evidence supports continued research, not prospective model activation.", '',
             'Operational experiments independently compare three allocation policies across three simulated conditions. They demonstrate food-volume, destination-service and travel tradeoffs under binding safety exclusions. They do not establish reduced illness, real savings or population equity. Kiro was not used, and that challenge criterion is explicitly unmet.', '',
             '### Decision statement and application access', '',
             'Primary actor: regional Missouri poultry distributor/logistics operator. Commodity: refrigerated poultry. Geography: simulated Columbia, Kansas City, Jefferson City, Springfield and St. Louis network. The dispatch horizon is six hours; the separate retrospective sampling study uses seven-day forecast origins.', '',
             'Decisions: inspect/request information, allocate eligible inventory, review a precautionary hold, compare a route, or approve alternative receiving instructions. Inventory, demand, capacity, deadlines, use-by, recall/hold and eligibility constraints stay binding. Consequential actions require an identified human review.', '',
             'Launch the existing operator application with Start-AEGIS.cmd, or .venv/Scripts/python scripts/start_local.py. Keep its terminal open. For the prebuilt reviewer ZIP, use Start-AEGIS.cmd --no-build after installing pinned Python dependencies. No Node installation is needed merely to view prebuilt assets.', '',
             'Open http://127.0.0.1:8000. Use a fresh isolated rehearsal for demonstrations: .venv/Scripts/python scripts/start_rehearsal.py --port 8001. A URL parameter alone does not isolate the operator database. Do not reset saved operator work.', '',
             state['release_status']+'. The challenge requirements below are mapped literally. An implemented research pipeline is distinct from a scientifically validated prospective deployment and from genuine team/Kiro evidence.']
    for task in state['tasks']:
        lines += ['', f"## {task['id']}: {task['title']}", '', f"Status: {task['status']}.", '', task['summary'], '', '### Implemented evidence', '']
        lines += ['- '+item for item in task['implemented']]
        lines += ['', '### Limits and remaining evidence', '']+['- '+item for item in task['remaining']]
        if task['id']=='Task 1':
            lines += ['', '### Alignment and provenance', '',
                      'The integrated study aligns Missouri human surveillance aggregates and a five-station ambient index with a selected Missouri FSIS sample at a forecast origin seven days before collection. These are aggregate context features, not person-to-food, genome-to-genome or establishment exposure matches. A complete-source gate drops unsupported rows; missing observations are not invented.', '',
                      'Full definitions: docs/analytic_alignment.md; reports/data_dictionary.csv; reports/source_provenance.json; data/processed/integrated_mo_analytic.csv. Original inventory and raw bytes remain preserved. The diagram uses separate pathways and labeled simulation boundaries.', '',
                      'The required provenance fields are documented in reports/source_provenance.csv and JSON, docs/data_catalog.md and config/api_registry.yaml: source and endpoint, recorded access/retrieval or unknown date, license/terms and geographic/time scope, update cadence, transformations and limitations. Missing publication/access timestamps remain unknown. This distinction is material to prospective validity.', '',
                      'Historical NOAA observations, Open-Meteo forecasts, NWS official alerts and simulated cargo temperature retain separate labels. Ambient weather is not the temperature inside a load. The required historical stream here covers the inspected five-station window; it is not claimed complete for all historical FSIS samples.']
        if task['id']=='Task 2':
            split=model.get('primary_split',{})
            lines += ['', '### Target, features and validation design', '',
                      'The outcome is Salmonella positivity in a selected Missouri FSIS primary raw-poultry sample collected seven days after its declared forecast origin. It is conditional on being sampled; neither representative regional prevalence nor an illness probability is estimated. Logistic regression with training-only scaling is compared with fixed smoothed training prevalence. Small samples and uncertain source availability do not justify a more complex boosted model.', '',
                      'Predictors are lagged Missouri FSIS prevalence, seasonal sine/cosine, log human Salmonella isolate counts from the BEAM export, and trailing 28-day five-station NOAA temperature/precipitation summaries. NORS adds lagged historical outbreak-record counts in a separate ablation. Standardized coefficients describe conditional associations, not causal effects.', '',
                      'Declared availability assumptions: FSIS collection plus 90 days; BEAM month-end plus 90 days; NORS month-end plus 730 days; NOAA reporting label plus seven days. Training labels must become assumed-available before validation starts. The same complete-case cohort is used in all comparisons, with no random split, future labels or missing-weather imputation. Actual historical publication vintages are unavailable; these assumptions cannot prove the snapshots existed at forecast time.', '',
                      f"Measured primary split: {number(split.get('training_rows'),0)} training samples; {number(split.get('validation_rows'),0)} held-out samples, including {number(split.get('validation_positives'),0)} positives. Validation origins {split.get('validation_start','not recorded')} to {split.get('validation_end','not recorded')}. Outcomes occur seven days later; fitting uses the declared label embargo.", '',
                      '| Model | Brier score | Brier 95% interval | PR-AUC | ROC-AUC |','| --- | --- | --- | --- | --- |']
            for key, row in model.get('models',{}).items():
                metric=row.get('metrics',{})
                band=metric.get('brier_week_block_bootstrap_95_ci')
                band_text=' to '.join(number(value,5) for value in band) if isinstance(band,list) and len(band)==2 else 'not recorded'
                lines.append(f"| {key} | {number(metric.get('brier'),6)} | {band_text} | {number(metric.get('pr_auc_average_precision'),5)} | {number(metric.get('roc_auc'),5)} |")
            lines += ['', 'Lower Brier is better. Models are compared on the same supported cohort. Weekly bootstrap bands address within-cohort variation, not publication-lag uncertainty or transportability. Calibration Wilson bands assume independent binomial observations and omit clustering. A no-sample month remains a gap, not zero risk.', '']
            for row in model.get('ablations',[]):
                band=row.get('paired_week_block_bootstrap_95_ci')
                band_text=' to '.join(number(value,6) for value in band) if isinstance(band,list) and len(band)==2 else 'not recorded'
                lines.append(f"- {row.get('added_domain','Added domain')}: Brier change {number(row.get('brier_change'),6)}; paired 95% interval {band_text}. {row.get('interpretation','Read the saved uncertainty interval.')}")
            core=model.get('models',{}).get('core_integrated',{}).get('metrics',{})
            lines += ['', '### Core-model calibration and error consequences', '',
                      f"At a predeclared 0.10 research-review threshold, the held-out core model has: {json.dumps(core.get('confusion_at_0_1','not recorded'))}. These are selected-sample classification counts, not illnesses or actual operational holds."]
            if core.get('calibration'):
                lines += ['', '| Bin n | Mean estimate | Observed fraction | Wilson 95% band |','| --- | --- | --- | --- |']
                for row in core['calibration']:
                    band=row.get('wilson_95_ci')
                    band_text=' to '.join(number(value,4) for value in band) if isinstance(band,list) and len(band)==2 else 'not recorded'
                    lines.append(f"| {number(row.get('n'),0)} | {number(row.get('mean_predicted'),4)} | {number(row.get('observed'),4)} | {band_text} |")
            lines += ['', 'Review false positives as consumed inspection capacity and false negatives as missed positive selected samples, never illnesses caused or a safe/unsafe classification. The NORS holdout feature can be constant; a harmful result here is not a general verdict against outbreak surveillance. The original national FSIS evaluation is a separate target/cohort and is retained in reports/model_evaluation.json.', '',
                      f"Core precision at the diagnostic 0.10 threshold is {number(core.get('precision_at_0_1'),4)} and recall is {number(core.get('recall_at_0_1'),4)}; fraction prioritized is {number(core.get('review_fraction_at_0_1'),4)}. The threshold is a research diagnostic, not an instruction to hold cargo. Rolling-origin evaluations and unavailable folds are retained in the full JSON; uncertainty is based on 400 weekly block resamples, not individual shipment intervals.", '',
                      'CDC confirms the BEAM dashboard uses PulseNet and NORS data: https://www.cdc.gov/beam/about/index.html. The supplied BEAM report data are aggregate SEDRIC surveillance, not genomes or linked patients. The three core sources and additions retain their own observation and retrieval dates.']
        if task['id']=='Task 3':
            lines += ['', '### Decision formulation', '',
                      'Candidate-shipment binary decisions share stock, origin/supplier throughput, refrigerated-truck capacity, destination demand, eligibility, hold/recall, use-by, receiving buffer and delivery-deadline constraints. The rule policy takes the first feasible candidates in declared input order. The volume policy lexicographically maximizes eligible delivered kilograms, then short-clock kilograms preserved through delivery, then minimizes estimated distance. The balanced policy first maximizes destination service fractions capped at 50%, then applies those volume/quality/distance priorities. This is equal destination service, not a verified population-vulnerability weight.', '',
                      'Quality budgets integrate simulated product-temperature history with an illustrative Q10 rate relative to 4 C; remaining reference life is divided by the forecast rate for a forward window. Chosen Q10 sensitivity cases are not confidence intervals. Unknown coverage, held/recalled stock and exceeded modeled clocks remain exclusions. This freshness calculation is not a calibrated poultry spoilage, pathogen-growth or molecular measurement model.', '',
                      'A proposed rescue compares the quality window with journey and receiving time, screens eligible closer recipients and presents alternatives for dispatcher review. A separate approval updates the exact simulated driver assignment. No predictive score alone can impose a mandatory hold, and no route is certified for commercial-truck restrictions.', '',
                      '### Quantified policy comparisons', '', '| Scenario / policy | Distributed kg | Unmet kg | Destinations | Quality exposure kg |','| --- | --- | --- | --- | --- |']
            for scenario in decision.get('scenarios',[]):
                for policy in scenario.get('policies',[]):
                    metric=policy.get('metrics',{})
                    lines.append(f"| {scenario['name']} / {policy['policy_name']} | {number(metric.get('distributed_kg'),0)} | {number(metric.get('unmet_demand_kg'),0)} | {number(metric.get('destinations_served'),0)} | {number(metric.get('projected_quality_budget_exposure_kg'),0)} |")
            lines += ['', 'Food security is operationalized as preserved eligible food volume and destination service. Modeled quality-budget exposure is neither observed waste nor predicted pathogen risk. Balancing service can trade travel or short-clock preservation for more destinations served. Inspect independent constraints and the full per-destination service export.', '',
                      '| Scenario / policy | Estimated distance km | Solver status | Constraint violations |','| --- | --- | --- | --- |']
            for scenario in decision.get('scenarios',[]):
                for policy in scenario.get('policies',[]):
                    metric=policy.get('metrics',{})
                    lines.append(f"| {scenario['name']} / {policy['policy_name']} | {number(metric.get('total_estimated_distance_km'),2)} | {policy.get('solver_status','not recorded')} | {number(metric.get('constraint_violations'),0)} |")
            lines += ['', 'All comparisons retain per-policy independent arithmetic and eligibility checks. An OPTIMAL solver status applies to the declared mathematical instance, not to real-world logistics or true food safety. Under scarcity, extra destination service can require more travel or retain less short-clock inventory; unchanged outcomes under the delay scenario are also reported rather than presented as improvement.', '',
                      'These comparisons are fixed-seed studies; they do not change current assignments. Operational actions remain in Command, Dispatcher and Save the Load. Unknown quality, held/recalled stock, ineligible supply and capacity violations cannot become an eligible dispatch through an objective weight.']
        if task['id']=='Task 4':
            lines += ['', 'Current-risk/evidence view: Command and Model evaluation. Prioritized attention: Command review queue and Dispatcher. Scenario builder: Command disruption preview, A/B/C/D and Route laboratory. Recommended action: reviewed plans/rescue options. Explanation: evidence assistant and source/model details. No model can declare a shipment safe or unsafe.', '',
                      'Owner disclosure: Kiro was not used. The Kiro-use criterion is therefore not met. Implementation was developed outside Kiro with Codex assistance and human direction. No Kiro-generated code or authentic Kiro task history exists to claim; prepared steering/specification files do not establish use. No extra AWS service or cloud deployment is needed to operate this local research build.']
        if task['id']=='Task 5':
            lines += ['', '### Included one-page team science statement', '',
                      'Appendix A is the final page of this PDF and includes the complete standalone one-page team science statement, preserved from reports/team_science_statement.pdf. It records the team roles, how disease-side input changed the original logistics idea, measured added-data findings and the next partner/data need. The editable author-review source remains docs/team_science_statement.md.']
    lines += ['', '## Every dashboard menu and its use case', '', '| Menu | What to find and do | What changes state |','| --- | --- | --- |']
    menus=[
        ('Command center','Missouri map/layers, attention queue, delivery outlook, route comparison, event preview, four response plans.','Only explicit event application or identified plan approval.'),
        ('Save the Load','Stored temperature replay, point/conservative clocks, eligible rescue recipients, FEFO/FIFO picks, reviewed exact-driver handoff.','Replay changes experiment history; separate approval replaces the checked plan.'),
        ('Route laboratory','One-farm/multiple-origin fleet experiments, custom locations, truck loads, deadlines, saved versions and exports.','Saved laboratory experiments, not Command dispatch.'),
        ('Road intelligence','Missouri/Iowa incident evidence, named/custom journeys, route proximity, alternatives, capture/export.','Planning inspection only; no truck certification or automatic closure avoidance.'),
        ('Dispatcher desk','Incident inbox, hold/release decisions, instructions and read-only readiness checks.','Explicit human decisions can remove or revise assignments; release does not redispatch.'),
        ('AEGIS Drive','Approved truck/trip/destination, simulated fuel/position/cargo, disruptions, parked acknowledgment/reporting.','Parked confirmations, versioned acknowledgments and incident reports.'),
        ('Evidence assistant','Type chicken or select a question; inspect captured factual answers, citations and suggested workspace.','Read-only guidance; no autonomous decision or evaluated model-written advice.'),
        ('Model evaluation','New Missouri integrated study, same-cohort ablations, uncertainty/time series; separate original national baseline and error analysis.','None; viewing does not train or activate a model.'),
        ('Project brief','Five task cards, final PDF, policy comparisons, full handbook, team brief, execution evidence and isolated rehearsal timer.','Rehearsal records only in a verified isolated runtime.'),
        ('Sources & evidence','Source coverage/failures, raw inventory, underlying tables, NOAA gaps, USDA county context and provenance.','Explicit source refresh updates caches; never dispatch.'),
    ]
    for row in menus:lines.append('| '+' | '.join(row)+' |')
    lines += ['', 'Header controls: Reload application data rereads current network/supporting reports; it is not a universal provider refresh. The bell focuses the review queue. Recent activity inspects saved actions without replaying them. An avatar is not production login.', '',
              '## Presentation idea: from evidence to a reviewed decision', '',
              'Story: a Missouri poultry dispatcher must preserve food access while responding to uncertain evidence and a temperature-exposed load. Show the action chain and one quantified tradeoff, then disclose the negative model result. Do not spend the whole video touring menus.', '',
              '| Time | Scene | Point to make |','| --- | --- | --- |',
              '| 0:00–0:35 | Command map and One Health diagram | Name the actor, six-hour decision, fictional network and distinct source pathways. |',
              '| 0:35–1:20 | Sources, Model evaluation | Show three core sources, seven-day integrated study, uncertainty and an ablation that does not improve prediction. |',
              '| 1:20–2:05 | Project brief policy comparison | Compare rule, volume and balanced service under scarcity; show kilograms, service and hard safety exclusions. |',
              '| 2:05–3:25 | Save the Load in a fresh isolated session | Replay heat, distinguish point from conservative quality, inspect FEFO/FIFO and whole-plan tradeoffs. |',
              '| 3:25–4:20 | Human rescue review to Drive | Three confirmations, exact truck/trip update, parked acknowledgment and short incident report. |',
              '| 4:20–5:00 | Five task checklist and conclusion | State real team roles and genuine Kiro evidence only if completed; name limits and the next dataset/partner. |', '',
              'Practice with a timer; this outline is not a claim of a completed human video. The longer button-by-button runbook is in docs/recording_guide.md and the full master guide. Disclose that Kiro was not used. Final team/author review and a watched/listened-to take remain required.', '',
              '## Reproducibility and submission deliverables', '',
              '| Deliverable | Included files and how to use them |','| --- | --- |',
              '| Analysis notebooks and scripts | notebooks/00 through 03; scripts/audit_data.py, source-specific ingest scripts, train_model.py, train_integrated_study.py, run_decision_study.py and execute_notebooks.py. |',
              '| Development artifacts | .kiro/specs/, .kiro/steering/ and AGENTS.md contain structured requirements and guidance. Kiro was not used; there is no authentic Kiro-generated code or task history. |',
              '| Runnable application | React/TypeScript frontend, FastAPI backend, prebuilt assets and Setup-Judges-Windows.cmd / Start-Judges-Windows.cmd; local deployment instructions in docs/local_startup.md, docs/judge_quick_start.md and README. GitHub Pages alone cannot host the Python backend; no public cloud deployment is claimed. |',
              '| Dictionary and provenance | reports/data_dictionary.csv; reports/source_provenance.json; docs/data_catalog.md; config/api_registry.yaml and original inventory manifests. |',
              '| Report and team science | This report includes the complete one-page team science statement as Appendix A on its final page. The identical standalone page is reports/team_science_statement.pdf; editable sources are reports/final_submission_guide.md and docs/team_science_statement.md. |',
              '| Setup and dependencies | README.md, JUDGES_START_HERE.md, requirements-lock.txt, optional requirements-notebooks.txt and frontend/package-lock.json. |', '',
              '### Executed notebooks', '',
              'Install optional notebook dependencies using .venv/Scripts/python -m pip install -r requirements-notebooks.txt, then run .venv/Scripts/python scripts/execute_notebooks.py. The four notebooks cover coverage/provenance, preprocessing/integration, modeling/evaluation and scenario analysis. Static previews are in reports/notebooks/index.html; they do not require Jupyter to read.', '',
              'The default profile reruns maintained analysis functions and scripts from included processed snapshots and selected original NOAA responses. Numeric assertions compare recomputed cohorts, metrics and policy outcomes with the recorded study. Each run has a private copied workspace and blocks provider requests; operator records and original source bytes are preserved. Timestamps, UUIDs and timings are not fixed scientific results.', '',
              'The raw-data profile additionally requires the separately supplied original downloads: .venv/Scripts/python scripts/execute_notebooks.py --notebook 01_Preprocessing_and_Integration.ipynb --raw-data-dir PATH. It verifies provenance-listed filenames and hashes, audits copies, runs source adapters, regenerates model and decision results and compares them. Bulk originals are excluded from the judge ZIP and GitHub repository; obtain them separately or reproduce the bundled-snapshot profile.']
    notebook=read(root,'reports/notebook_execution.json')
    raw_notebook=read(root,'reports/notebook_raw_execution.json')
    for label,record in [('Bundled notebook run',notebook),('Original-data replay',raw_notebook)]:
        if record:
            executed=sum(row.get('executed_code_cells',0) for row in record.get('notebooks',[]))
            lines += ['', f"{label}: saved status {'passed' if record.get('passed') is True else 'failed or incomplete'}; {executed} executed code cells; operator preserved: {record.get('operator_preserved','not recorded')}; started {record.get('started_at','not recorded')}. These are measured execution records, not assertions that every later source revision will yield identical results."]
    lines += ['', '### Verification and submission boundary', '',
              f"Latest saved full local checks: {checks.get('finished_at','not recorded')}. These are dated evidence; later edits require their own checks.", '']
    for row in checks.get('checks',[]):
        lines.append(f"- {row['name']}: {'passed' if row['passed'] else 'failed'}, tests {row['tests_passed'] if row['tests_passed'] is not None else 'build'}, log {row['log']}.")
    lines += ['', 'Reproduce the additions: scripts/train_integrated_study.py; scripts/run_decision_study.py; scripts/build_data_dictionary.py; scripts/render_one_health_system.py; scripts/build_final_handoff.py. Use the pinned Python and Node versions in README. Scripts preserve raw files and use separate derived outputs; never silently merge unrecognized sources.', '',
              'The reviewer ZIP includes code, prebuilt UI, derived evidence and dated fixtures. It excludes original bulk downloads, active operator/rehearsal databases, credentials and local runtimes. Offline checks reuse the installed dependency environment unless a fresh-install report explicitly records otherwise.', '',
              'This deliverable is a final working software/research handoff, not a claim of completed organizer acceptance. Preserve open scientific limitations, source failures, actual role attestations and Kiro evidence. Nothing is automatically deployed, merged or submitted by creating the package.']
    return '\n'.join(lines)+'\n'


def build(root=ROOT, preview_dir=None):
    from pypdf import PdfReader, PdfWriter
    root=Path(root).resolve();reports=root/'reports';reports.mkdir(parents=True,exist_ok=True)
    statement=reports/'team_science_statement.pdf'
    if not statement.is_file():
        raise FileNotFoundError('Required one-page team science PDF missing: '+str(statement))
    statement_bytes=statement.read_bytes()
    try:
        statement_reader=PdfReader(BytesIO(statement_bytes))
        if statement_reader.is_encrypted or len(statement_reader.pages)!=1:
            raise ValueError('Team science statement must be one unencrypted PDF page')
        statement_page=statement_reader.pages[0]
        if not statement_page.extract_text().strip():
            raise ValueError('Team science statement page has no readable text')
    except Exception as error:
        raise ValueError('Invalid one-page team science PDF: '+str(error)) from error
    state=readiness(root)
    (reports/'challenge_readiness.json').write_text(json.dumps(state,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    body=content(root,state);markdown=reports/'final_submission_guide.md'
    markdown.write_text('# '+TITLE+'\n\n'+body,encoding='utf-8')
    blocks=parse_markdown(body)
    figures=[('reports/figures/one_health_system.png','Task 1:', 'One Health pathways. Aggregate associations and simulated logistics do not establish transmission or causation.'),
             ('reports/figures/integrated_model_validation.png','Task 2:', 'Held-out Missouri time series and paired added-domain comparisons. Gaps and intervals retain the study limitations; surveillance context is not individual-shipment risk.')]
    for name,chapter,caption in figures:
        image=root/name
        if image.is_file():
            position=next((i+1 for i,row in enumerate(blocks) if row.get('kind')=='heading' and row.get('text','').startswith(chapter)),None)
            if position is not None:blocks.insert(position,{'kind':'image','bytes':image.read_bytes(),'caption':caption})
    generated=datetime.now(ZoneInfo('America/Chicago')).strftime('%B %d, %Y at %I:%M %p CT')
    (reports/'final_submission_guide.html').write_text(html_document(blocks,generated,title=TITLE),encoding='utf-8')
    pdf=reports/'final_submission_guide.pdf'
    cover=[('Research question','How can a Missouri poultry distributor use food-safety, public-health and environmental evidence to preserve eligible food through a disruption?'),
           ('What is reported','Five task responses; data integration and provenance; time-aware model evaluation; quantified simulated policies; limitations and team science.'),
           ('What is delivered','A runnable React/FastAPI application, four executed analysis notebooks, maintained scripts, dependency locks and an organized judge handoff.'),
           ('Scientific and development disclosure','Results concern selected samples and simulated logistics. Prospective validity is unestablished. Kiro was not used; the requirement is unmet.')]
    layout=render_pdf(blocks,pdf,generated,Path(preview_dir) if preview_dir else None,title=TITLE,
                      cover_subtitle='Final Challenge Report',preview_all=True,cover_sections=cover,
                      cover_label='Final Submission Guide',subject='Five challenge tasks, reproducible methods, measured results, operational scenarios and team science')
    main_pages=layout['pages']
    writer=PdfWriter(clone_from=BytesIO(pdf.read_bytes()))
    writer.append(statement_reader,import_outline=False)
    appendix_title='Appendix A: One-page team science statement'
    writer.add_outline_item(appendix_title,main_pages)
    combined=BytesIO();writer.write(combined);pdf.write_bytes(combined.getvalue())
    appendix={'id':'appendix-a-team-science-statement','title':appendix_title,'kind':'appendix',
              'page':main_pages+1,'pages':1,'source':'reports/team_science_statement.pdf',
              'source_sha256':hashlib.sha256(statement_bytes).hexdigest(),
              'paper_points':[float(statement_page.mediabox.width),float(statement_page.mediabox.height)],
              'inclusion':'Original page content and dimensions preserved; not reflowed'}
    layout['main_report_pages']=main_pages
    layout['main_report_paper']=layout['paper']
    layout['paper']='US Letter main report; original appendix page dimensions preserved'
    layout['pages']=main_pages+1
    layout['bookmarks']+=1
    layout['chapters'].append(appendix)
    layout['appendices']=[appendix]
    layout['pagination_note']='Main report printed page numbers and contents refer to its own pages. Appendix A is the final PDF page and retains its standalone one-page pagination.'
    layout['preview_scope']='Generated print-render previews show main report pages only; the appended source PDF page is preserved without re-rendering.'
    if preview_dir:
        for old_preview in Path(preview_dir).glob('print-render-page-*.png'):
            suffix=old_preview.stem.removeprefix('print-render-page-')
            if suffix.isdigit() and int(suffix)>main_pages:
                old_preview.unlink()
    inputs=['reports/integrated_model_evaluation.json','reports/decision_study.json','reports/source_provenance.json','reports/session_verification.json','docs/team_science_statement.md','docs/challenge_tasks_source.md','reports/figures/one_health_system.png']
    inputs += ['reports/figures/integrated_model_validation.png','reports/notebook_execution.json','reports/notebook_raw_execution.json','reports/team_science_statement.pdf']
    result={'generated_at':state['generated_at'],'title':TITLE,'pdf':'reports/final_submission_guide.pdf','markdown':'reports/final_submission_guide.md','html':'reports/final_submission_guide.html',
            'sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'bytes':pdf.stat().st_size,**layout,
            'inputs':[{'path':name,'sha256':hashlib.sha256((root/name).read_bytes()).hexdigest()} for name in inputs if (root/name).is_file()],
            'original_data_modified':False,'operational_database_accessed':False,'human_submission_verified':False}
    (reports/'final_handoff_manifest.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--preview-dir',type=Path);args=parser.parse_args()
    print(json.dumps(build(preview_dir=args.preview_dir),indent=2))
