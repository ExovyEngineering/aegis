"""Regenerate a planning/presentation brief from recorded evidence, without network calls."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import textwrap
from zoneinfo import ZoneInfo
import yaml

ROOT=Path(__file__).resolve().parents[1]


def load(root,name,default=None):
    p=root/name
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else default


def sections(root):
    register=yaml.safe_load((root/'config/feature_register.yaml').read_text(encoding='utf-8'))
    checked=load(root,'reports/session_verification.json',{})
    model=load(root,'reports/model_evaluation.json',{})
    weather=load(root,'reports/noaa_coverage.json',{})
    audit=load(root,'data/manifests/inventory.json',{})
    generated=datetime.now(ZoneInfo('America/Chicago')).strftime('%B %d, %Y at %I:%M %p CT')
    output=[('AEGIS | Team and presentation brief',[
        'Adaptive Early-warning & Guidance for Integrated Supply Chains',
        f'Generated {generated}. Target submission: November 2, 2026; feature freeze target October 30.',
        'Audience: project teammates, presenters and reviewers. This is an ongoing planning brief, not a certified final submission or regulatory decision.',
        'AEGIS supports a regional Missouri poultry logistics operator. Command combines public evidence with a deterministic simulated network; Drive carries dispatcher-approved simulated assignments and parked-use reporting.',
        'All suppliers/contracts, lots, trucks, shipments, operational costs, demand and cargo telemetry are fictional. Official establishment locations do not establish supply relationships.',
        'Team repository: https://github.com/ExovyEngineering/aegis (private). Start with CONTRIBUTING.md. Use feature branches and reviewed pull requests.',
        'Update this brief: run scripts/verify_project.py after code changes, then scripts/build_project_brief.py. Update config/feature_register.yaml and docs/changelog.md when capabilities or limitations change. No live API requests are performed by the brief compiler.'
    ])]
    for priority,title in [('P0','Required submission core'),('P1','Operational differentiators'),('P2','Deferred extensions')]:
        body=[]
        for f in register['features']:
            if f['priority']==priority:body.extend([f"{f['name']} | {f['status']}",f['detail'],f"Evidence: {f['evidence']}"])
        output.append((priority+' | '+title,body))
    testlines=[f"Latest local verification finished: {checked.get('finished_at','not recorded')}. All requested local checks passed: {checked.get('all_passed','not recorded')}."]
    for c in checked.get('checks',[]):
        testlines.append(f"{c['name']}: {'PASS' if c['passed'] else 'FAIL'}; exit {c['exit_code']}; tests passed {c['tests_passed'] if c['tests_passed'] is not None else 'build check'}; {c['duration_seconds']} seconds. Log: {c['log']}. Checked: {c['checked_at']}.")
    for path,label in [('reports/browser_qa/controls/results.json','Map, scenario, simulator and source-control browser QA'),('reports/browser_qa/drive/results.json','Visual Drive and parked-use actual-Chrome QA'),('reports/browser_qa/depth/results.json','Latest feature-depth actual-Chrome QA'),('reports/browser_qa/operations/results.json','Earlier dispatcher/custom-planning browser QA')]:
        value=load(root,path,{})
        if value:
            checks=value.get('checks',[])
            testlines.append(f"{label}: {sum(bool(c.get('passed')) for c in checks)} / {len(checks)} recorded checks passed. Timestamp: {value.get('checked_at','see artifact')}. Evidence: {path}. This is a separate run from local unit/build checks.")
    smoke=load(root,'reports/http_smoke.json',{})
    if smoke:testlines.append(f"Loopback HTTP smoke artifact records {smoke.get('passed','unknown')} checks against {smoke.get('base_url','unknown')}. It does not certify current public-source freshness.")
    testlines+=['Meaningful failure cases include held/recalled stock, nonrefrigerated trucks, capacity/inventory shortages, stale approval and instruction versions, invalid coordinates, altered planning metrics, corrupt source files, bounded queries and preservation of operator state.',
        'Four upstream Python deprecation warnings have appeared in previous runs; consult the current captured pytest log. Browser, CI and live API tests are distinct evidence and are never inferred from one another.',
        'The first GitHub Actions run succeeded after repository creation. New commits need their own CI result; a local pass alone does not prove a remote run passed.']
    actions=load(root,'reports/source_actions.json',{})
    if actions:testlines.append(f"Executed source refresh actions: {actions.get('fresh_success_count','not recorded')} new provider responses, {actions.get('usable_response_count','not recorded')} usable payloads, {actions.get('failed_or_stale_count','not recorded')} failed/stale actions; finished {actions.get('finished_at','not recorded')}. This is distinct from registry catalog/discovery probes. Evidence: reports/source_actions.json.")
    output.append(('Verification | What was actually tested',testlines))
    output.append(('Evidence | Coverage and scientific limits',[
        f"Raw inventory: {len(audit.get('files',[]))} file records. Originals are preserved locally; inventory checksums remain in data/manifests/inventory.json.",
        f"Historical NOAA: {weather.get('observed_station_days','not recorded')} observed station-days of {weather.get('expected_station_days','not recorded')} requested; {weather.get('missing_metric_values','not recorded')} missing metric values. Status: {weather.get('status','not recorded')}. Window: {weather.get('start_date','?')} through {weather.get('end_date','?')}.",
        'Weather forecasts, historical reanalysis, observed historical station weather and simulated cargo temperature are different types of evidence. They cannot be relabeled interchangeably. NOAA trace precipitation work remains reserved for genuine Kiro execution.',
        f"Chronological model holdout: {model.get('validation_rows','not recorded')} rows. Historical prevalence Brier: {model.get('baseline',{}).get('brier','not recorded')}; logistic Brier: {model.get('logistic_regression',{}).get('brier','not recorded')}; logistic ROC-AUC: {model.get('logistic_regression',{}).get('roc_auc','not recorded')}.",
        'The logistic model did not establish useful advantage over prevalence in the primary holdout. The transparent historical estimator is retained. These are retrospective results, not validated prospective forecasts or consumer illness probabilities.',
        'Actual sample-result publication dates are absent. Assumed reporting lags and frozen-snapshot sensitivity are documented, but do not establish prospective feature availability.',
        'CDC NORS outbreaks and BEAM surveillance remain distinct from FSIS sampling outcomes. BEAM source exports can include human, animal and food categories; inspect their original source fields.',
        'Recall notices are official evidence, but fictional lots have no genuine traceability supporting a verified product/lot match. No live recall match or regulatory disposition is claimed.',
        'Public OSRM routes are for the driving profile, lack commercial-truck restriction validation and do not automatically include current MoDOT closures. Independent geometry proximity prompts review and can produce false positives.',
        'Cargo projections use uncalibrated physical assumptions and parameter sensitivity, not learned failure probabilities, food-safety thresholds or confidence intervals.'
    ]))
    output.append(('Walkthrough | What to show behind the buttons',[
        'Command: compare A/B/C/D metrics. Open decision details to inspect selected shipments, exclusion reasons and resource limits. Review a proposal with an identity and rationale; stale or unsafe plans are rejected.',
        'Route laboratory: choose one farm, regional fleet or editable custom operation. Run a plan with explicit capacity, shift, ambient and delay assumptions. Inspect each route, travel fallback and thermal sensitivity. This does not dispatch.',
        'Saved experiments: save a completed run, change assumptions and save another version/project. Reopen historical versions, compare two projects and export immutable JSON or stop-sequence CSV. Saved source timestamps are not silently refreshed.',
        'Dispatcher desk: complete or escalate the scenario-B verification checklist, review an incident, record a human lot hold/release and issue versioned instructions. A hold removes affected assignments. Release does not recreate dispatch; a new reviewed plan is necessary.',
        'Drive: open /?mode=drive for the dedicated visual surface. Inspect the approved destination, planned travel, simulated fuel/range, dispatch-origin reference and cargo temperature. No actual GPS progress or real remaining ETA is inferred.',
        'Parked-use controls: self-confirm safe parking to enable reports and acknowledgments for ten minutes. Driving focus and expiry lock these interactions at both the UI and legacy server endpoints. This does not detect actual motion, prove safe parking or prevent other device use.',
        'Driver reports: use a canned refrigeration/road/vehicle/cargo concern or type a report while parked. The standard dispatcher inbox retains original assignment context; no automatic hold, rerouting or external emergency call occurs.',
        'Sources: inspect current source age/fallback labels, historical NOAA coverage and actual paginated source rows. Filter one dataset column at a time; inspect schema and missing cells. Do not cross-link unrelated evidence.',
        'Model evaluation: show the measured baseline and model comparison, calibration and limitations. Explain why an honest weak predictive result is preferable to invented accuracy.',
        'Project brief: download this PDF from the app. Use the feature register, test evidence and remaining decisions to coordinate teammates.'
    ]))
    output.append(('Presentation | Five-minute narrative',[
        '0:00-0:40 | Problem and actor. Explain the regional poultry distributor, Missouri geography, real evidence and fictional operations. State that consequential action requires human review.',
        '0:40-1:20 | Provenance. Show source age, one real FSIS row and the separate CDC layer; identify NOAA gaps. Distinguish forecasts from cargo readings.',
        '1:20-2:00 | Science. Show actual chronological baseline/model results. State the target and publication-timing limitation. Do not claim consumer-illness prediction.',
        '2:00-3:00 | Response choices. Compare scenario cost and unmet demand; inspect constraint checks. Explain why a cheaper plan with more unmet demand is not automatically better.',
        '3:00-4:10 | Operations. Introduce a simulated disruption in an isolated demo database, approve a revised plan, then switch to Drive to acknowledge instructions and report an incident.',
        '4:10-4:40 | Scale and route planning. Show one-farm and multi-origin experiments, source labels and a saved comparison. Avoid claiming certified truck routing.',
        '4:40-5:00 | Contribution and limits. Point to reproducible code, source hashes, tests, human decision records and remaining Kiro evidence. End on the decision-support value, not invented prediction accuracy.',
        'Rehearsal is a planned narrative, not a claim that a timed live presentation has passed. Use reports/demo_script.md and scripts/demo_run.py; preserve the operator database.'
    ]))
    output.append(('Next decisions | Keep the submission complete',[
        '1. Sign into the actual Kiro application and execute/review the reserved NOAA trace-precipitation spec. Retain authentic task and terminal evidence. Codex cannot retroactively satisfy that requirement.',
        '2. Review the full organizer rubric, team authorship and report claims. Resolve required source/timing gaps or explicitly report their scientific consequences.',
        '3. Rehearse the five-minute presentation with the team, verify a clean checkout, and inspect the final reviewer ZIP before submission.',
        'P2 gate: leave account tenancy, billing, LLM assistance and physical sensors deferred while P0 signoff is incomplete. Farm/fleet planning does not imply multi-tenant production readiness.',
        'Operational limitation: this is a local loopback demonstrator with self-declared identities. Teammates share code through GitHub; each local app has separate state unless deliberately provisioned otherwise.',
        'Change history: docs/changelog.md. Detailed research draft: reports/aegis_report.md. Engineering status: docs/progress.md. Build evidence: reports/session_verification.json.'
    ]))
    return output


def render_pdf(content, output):
    os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'data/cache/matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    page_number=0
    with PdfPages(output,metadata={'Title':'AEGIS team and presentation brief','Author':'AEGIS project team','Subject':'Measured implementation status, tests and presentation planning'}) as pdf:
        for title, paragraphs in content:
            fig=None; y=0
            def new_page():
                nonlocal fig,y,page_number
                if fig is not None:pdf.savefig(fig);plt.close(fig)
                fig=plt.figure(figsize=(8.27,11.69),facecolor='#fafbf8');page_number+=1
                fig.text(.08,.94,'AEGIS',fontsize=23,weight='bold',color='#184b3e')
                fig.text(.08,.905,title,fontsize=12,weight='bold',color='#184b3e')
                fig.text(.08,.055,'SIMULATED OPERATIONS | TRACEABLE EVIDENCE | HUMAN DECISIONS',fontsize=7,color='#65746b')
                fig.text(.9,.055,str(page_number),fontsize=8,color='#65746b',ha='right')
                y=.865
            new_page()
            for paragraph in paragraphs:
                # Break long checksums/URLs too, so content never spills past the margin.
                lines=textwrap.wrap(paragraph,width=91,break_long_words=True,break_on_hyphens=False) or ['']
                while lines:
                    available=int((y-.105)/.017)
                    if available<2:new_page();continue
                    part,lines=lines[:available],lines[available:]
                    fig.text(.08,y,'\n'.join(part),fontsize=9.3,color='#263f36',va='top',linespacing=1.4)
                    y-=len(part)*.017+.022
            if fig is not None:pdf.savefig(fig);plt.close(fig)
    return page_number


def build(root=ROOT):
    content=sections(root);reports=root/'reports';reports.mkdir(exist_ok=True)
    md=reports/'project_brief.md';pdf=reports/'aegis_project_brief.pdf'
    md.write_text('\n\n'.join('# '+title+'\n\n'+'\n\n'.join(body) for title,body in content)+'\n',encoding='utf-8')
    pages=render_pdf(content,pdf)
    artifact={'generated_at':datetime.now(ZoneInfo('America/Chicago')).isoformat(),'pdf':'reports/aegis_project_brief.pdf','markdown':'reports/project_brief.md','pages':pages,'sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'bytes':pdf.stat().st_size,'live_api_requests_performed':False,'feature_register':'config/feature_register.yaml','verification':'reports/session_verification.json'}
    (reports/'project_brief_manifest.json').write_text(json.dumps(artifact,indent=2),encoding='utf-8')
    return artifact

if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(build(),indent=2))
