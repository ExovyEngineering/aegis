"""Read-only, cited operations summaries assembled from a captured local snapshot.

This engine is deterministic. It has no provider/model client, write tools,
free-form prompt interpreter or authority to approve a safety disposition.
"""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.optimization import optimize, SCENARIOS
from backend.paths import ROOT
from backend.runtime import require_valid_runtime


ENGINE = {'mode':'deterministic', 'label':'Deterministic evidence summary',
          'llm_used':False, 'version':'aegis-evidence-summary-v1'}
QUESTION_IDS = Literal['scenario_compare','shipment_review','model_limits',
                       'source_coverage','driver_workflow','next_actions']
QUESTIONS = [
    {'id':'scenario_compare','label':'What if deliveries are disrupted?',
     'prompt':'How can I try a delivery what-if and compare the four current response scenarios?'},
    {'id':'shipment_review','label':'What needs attention on this shipment?',
     'prompt':'What should a dispatcher inspect for the selected simulated shipment?'},
    {'id':'model_limits','label':'What can AEGIS actually predict?',
     'prompt':'How does delivery outlook differ from the measured historical baseline and model, and what remains unvalidated?'},
    {'id':'source_coverage','label':'Which sources can I use for this plan?',
     'prompt':'Which saved source checks succeeded or failed, and what coverage is missing?'},
    {'id':'driver_workflow','label':'How does a plan reach the driver?',
     'prompt':'How do approval, parked acknowledgment, verification and driver reporting connect?'},
    {'id':'next_actions','label':'Where should I go next?',
     'prompt':'Where should I start with delivery outlook and continue reviewing without changing state here?'},
]
LIMITATIONS = [
    'Read-only explanation for simulated operations. No approval, dispatch, hold, release, source refresh, model training or driver write is performed.',
    'These are server-authored deterministic summaries, not LLM-generated advice or an evaluated AI model.',
    'Historical FSIS sampling positivity is not a consumer illness probability. CDC surveillance and outbreaks remain separate evidence layers.',
    'Routes, road-event proximity and illustrative cargo projections do not certify truck eligibility, road clearance or product safety.',
    'A saved source response or HTTP probe does not establish current provider availability or complete observations. Read its recorded time and scope.',
    'Network/assignment fields share one read-only SQLite transaction. Report and local guidance files are captured independently; provider, retrieval and filesystem reads are not globally atomic.',
    'Names and operational entities are local simulation records; the application does not supply production authentication or tenant isolation.',
]
REPORTS = ('model_evaluation.json','model_timing.json','noaa_coverage.json','api_status.json')
OUTLOOK_GUIDANCE = ('docs/delivery_outlook.md','backend/delivery_outlook.py')
MAX_GUIDANCE_BYTES = 128 * 1024
MAX_REPORT_BYTES = 1024 * 1024
MAX_STATE_BYTES = 8 * 1024 * 1024
MAX_ASSIGNMENTS = 200
MAX_CONTEXT_BYTES = 2 * 1024 * 1024


class AssistantAsk(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    question_id: QUESTION_IDS
    shipment_id: str | None = Field(default=None, pattern=r'^[A-Za-z0-9_-]{1,64}$')
    expected_snapshot_id: str | None = Field(default=None, pattern=r'^[a-f0-9]{64}$')

    @model_validator(mode='after')
    def shipment_scope(self):
        if self.question_id == 'shipment_review' and self.shipment_id is None:
            raise ValueError('Choose a shipment for the shipment review')
        if self.question_id != 'shipment_review' and self.shipment_id is not None:
            raise ValueError('Shipment selection applies only to the shipment review question')
        return self


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def _strict_json(body):
    def invalid(value):
        raise ValueError(f'Nonfinite JSON value: {value}')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON object key')
            result[key] = value
        return result
    return json.loads(body, parse_constant=invalid, object_pairs_hook=unique)


def _integer(value, minimum=0):
    return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


def _number(value, minimum=0, maximum=math.inf):
    try:
        return (isinstance(value, (int, float)) and not isinstance(value, bool)
                and math.isfinite(value) and minimum <= value <= maximum)
    except (OverflowError,TypeError):
        return False


def _identifier(value):
    return isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_.-]{1,64}',value) is not None


def _stamp(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None or (parsed - datetime.now(timezone.utc)).total_seconds() > 60:
            return None
        return value
    except (ValueError, TypeError, OverflowError):
        return None


def _validate_network(network):
    if not isinstance(network, dict) or not _integer(network.get('seed')):
        raise ValueError('Expected the simulated network and nonnegative integer seed')
    bounds = {'nodes':200, 'lots':100, 'trucks':100, 'shipments':200}
    for key, maximum in bounds.items():
        rows = network.get(key)
        if not isinstance(rows, list) or not 0 < len(rows) <= maximum:
            raise ValueError(f'Unsupported network {key} count')
        if any(not isinstance(row, dict) or not _identifier(row.get('id')) for row in rows):
            raise ValueError(f'Unsupported network {key} identity')
        if len({row['id'] for row in rows}) != len(rows):
            raise ValueError(f'Duplicate network {key} identity')
    nodes = {row['id']:row for row in network['nodes']}
    lots = {row['id']:row for row in network['lots']}
    trucks = {row['id']:row for row in network['trucks']}
    for node in nodes.values():
        if node.get('kind') not in {'supplier','dc','destination'}:
            raise ValueError('Unsupported network node kind')
        metric = 'demand_kg' if node['kind'] == 'destination' else 'capacity_kg'
        if not _integer(node.get(metric)):
            raise ValueError(f'Network node {metric} is not a nonnegative integer')
    for lot in lots.values():
        if any(not isinstance(lot.get(key), bool) for key in ('held','recalled','eligible')):
            raise ValueError('Unsupported lot eligibility/hold/recall state')
        if not _integer(lot.get('inventory_kg')) or not _number(lot.get('shelf_life_hours')):
            raise ValueError('Unsupported lot stock or shelf life')
        if lot.get('supplier_id') not in nodes or nodes[lot['supplier_id']]['kind'] != 'supplier':
            raise ValueError('Lot references an unknown simulated supplier')
    for truck in trucks.values():
        if (not _integer(truck.get('capacity_kg'))
                or any(not isinstance(truck.get(key), bool) for key in ('eligible','refrigerated'))):
            raise ValueError('Unsupported truck capacity or eligibility')
    for shipment in network['shipments']:
        if (shipment.get('origin') not in nodes or nodes[shipment['origin']]['kind'] != 'dc'
                or shipment.get('destination') not in nodes or nodes[shipment['destination']]['kind'] != 'destination'
                or shipment.get('lot_id') not in lots or shipment.get('truck_id') not in trucks):
            raise ValueError('Shipment references an unknown operation entity')
        if not _integer(shipment.get('quantity_kg'), 1):
            raise ValueError('Unsupported shipment quantity')
        for key in ('deadline_hours','estimated_hours','estimated_distance_km'):
            if not _number(shipment.get(key)):
                raise ValueError(f'Unsupported shipment {key}')
        if not _number(shipment.get('temperature_c'), -100, 100):
            raise ValueError('Unsupported simulated cargo temperature')


def _read_database(path, root):
    runtime = require_valid_runtime(path, root=root)
    selected = Path(path).resolve()
    if not selected.is_file():
        raise HTTPException(503, 'Operational database is unavailable; the assistant will not create or seed it')
    try:
        with closing(sqlite3.connect(selected.as_uri()+'?mode=ro', uri=True, timeout=5)) as connection:
            connection.execute('PRAGMA query_only=ON')
            connection.execute('PRAGMA trusted_schema=OFF')
            connection.execute('BEGIN')
            row = connection.execute('SELECT length(CAST(payload AS BLOB)),revision FROM state WHERE id=1').fetchone()
            if not row or not _integer(row[0], 1) or row[0] > MAX_STATE_BYTES or not _integer(row[1]):
                raise ValueError('Operational state is absent, oversized or has an unsupported revision')
            state = connection.execute('SELECT payload FROM state WHERE id=1').fetchone()[0]
            if not isinstance(state,str):raise ValueError('Operational state must be a JSON text record')
            network = _strict_json(state)
            _validate_network(network)
            count = connection.execute('SELECT COUNT(*) FROM assignments').fetchone()[0]
            if count > MAX_ASSIGNMENTS:
                raise ValueError('Approved assignments exceed the assistant inspection bound')
            lengths = connection.execute('SELECT length(CAST(payload AS BLOB)) FROM assignments').fetchall()
            if any(not _integer(value[0], 1) or value[0] > 128*1024 for value in lengths):
                raise ValueError('Approved assignment payload is absent or oversized')
            assignments = []
            raw_assignments = connection.execute('SELECT id,payload,acknowledged FROM assignments ORDER BY id').fetchall()
            for identifier, body, acknowledged in raw_assignments:
                if not isinstance(body,str):raise ValueError('Approved assignment must be a JSON text record')
                assignment = _strict_json(body)
                if (not isinstance(assignment, dict) or assignment.get('id') != identifier
                        or identifier not in {item['id'] for item in network['shipments']}
                        or acknowledged not in (0,1)
                        or assignment.get('lot_id') not in {item['id'] for item in network['lots']}
                        or assignment.get('truck_id') not in {item['id'] for item in network['trucks']}
                        or not _integer(assignment.get('quantity_kg'),1)):
                    raise ValueError('Unsupported approved assignment identity or acknowledgment state')
                assignments.append({'id':identifier, 'acknowledged':bool(acknowledged),
                                    'verification_required':assignment.get('verification_required') is True,
                                    'verification_status':assignment.get('verification_status'),
                                    'lot_id':assignment['lot_id'],'truck_id':assignment['truck_id'],
                                    'quantity_kg':assignment['quantity_kg'],
                                    'payload_sha256':_sha(body.encode('utf-8'))})
            # All reads above share one SQLite snapshot; closing rolls back the
            # read transaction without a schema/data commit or an action audit.
            return network, row[1], assignments, {
                'path':runtime.get('database_relative_path') or 'configured operational database',
                'state_sha256':_sha(state.encode('utf-8')),
                'assignments_sha256':_sha(_canonical(raw_assignments)),
                'read_only':True,
            }
    except (sqlite3.Error, ValueError, TypeError, KeyError, OverflowError) as error:
        raise HTTPException(503, f'Operational snapshot unavailable: {type(error).__name__}: {error}') from error


def _read_reports(root):
    captured = {}
    for name in REPORTS:
        path = root/'reports'/name
        metadata = {'path':'reports/'+name, 'status':'unavailable', 'sha256':None, 'bytes':None, 'error':None}
        payload = None
        try:
            with path.open('rb') as stream:
                body = stream.read(MAX_REPORT_BYTES+1)
            if len(body) > MAX_REPORT_BYTES:
                metadata.update(bytes_read=len(body),read_prefix_sha256=_sha(body))
                raise ValueError(f'Report exceeds the inspection bound ({MAX_REPORT_BYTES:,} bytes)')
            metadata.update(bytes=len(body), sha256=_sha(body))
            payload = _strict_json(body)
            expected = list if name == 'api_status.json' else dict
            if not isinstance(payload, expected):
                raise ValueError(f'Expected a JSON {expected.__name__} report')
            metadata['status'] = 'captured'
        except (OSError, ValueError, TypeError, UnicodeError) as error:
            detail = error.strerror if isinstance(error, OSError) else str(error)
            metadata['error'] = f'{type(error).__name__}: {detail}'
            payload = None
        captured[name] = {'metadata':metadata, 'payload':payload}
    return captured


def _read_outlook_guidance(root):
    """Fingerprint fixed local guidance; never execute or interpret its contents."""
    sources=[]
    for relative in OUTLOOK_GUIDANCE:
        metadata={'path':relative,'status':'unavailable','sha256':None,'bytes':None,'error':None}
        try:
            with (root/relative).open('rb') as stream:
                body=stream.read(MAX_GUIDANCE_BYTES+1)
            if len(body)>MAX_GUIDANCE_BYTES:
                metadata.update(bytes_read=len(body),read_prefix_sha256=_sha(body))
                raise ValueError(f'Guidance exceeds the inspection bound ({MAX_GUIDANCE_BYTES:,} bytes)')
            metadata.update(bytes=len(body),sha256=_sha(body))
            if not body.decode('utf-8').strip():
                raise ValueError('Guidance is empty')
            metadata['status']='captured'
        except (OSError,ValueError,UnicodeError) as error:
            detail=error.strerror if isinstance(error,OSError) else str(error)
            metadata['error']=f'{type(error).__name__}: {detail}'
        sources.append(metadata)
    return sources


def _citation(identifier, label, path, sha256=None, retrieved_at=None):
    result={'id':identifier,'label':label,'path':path,'retrieved_at':retrieved_at}
    if sha256 is not None:result['sha256']=sha256
    return result


def _fact(identifier, title, text, category, provenance, citations, uncertainty=None, **extra):
    return {'id':identifier,'title':title,'text':text,'category':category,'provenance':provenance,
            'citations':citations,'uncertainty':uncertainty or [],**extra}


def _report_fact(name, reports, title, category):
    report = reports[name]; metadata = report['metadata']
    citation = _citation(name, title, metadata['path'], metadata['sha256'])
    return report, citation, _fact('report.'+name+'.unavailable', title+' unavailable',
        'The saved report could not be used. '+(metadata['error'] or 'Required fields are absent or unsupported.'),
        category, 'recorded source/report failure', [citation],
        ['No missing metric or observation is replaced with an invented result.'])


def capture_context(db_path, root=ROOT):
    """Capture local evidence, then derive bounded facts without provider/write calls."""
    root = Path(root() if callable(root) else root)
    path = db_path() if callable(db_path) else db_path
    network, revision, assignments, database = _read_database(path, root)
    reports = _read_reports(root)
    outlook_guidance = _read_outlook_guidance(root)
    generated = datetime.now(timezone.utc).isoformat()
    facts = []
    db_cite = _citation('network.snapshot','Captured simulated network',database['path'],database['state_sha256'])
    approval_cite = _citation('assignments.snapshot','Captured approved assignments',database['path'],database['assignments_sha256'])
    rules = _citation('workflow.rules','Approval and driver workflow','docs/operations_workflow.md')
    simulation = 'deterministic simulated logistics'
    held = sorted(lot['id'] for lot in network['lots'] if lot['held'])
    recalled = sorted(lot['id'] for lot in network['lots'] if lot['recalled'])
    facts.append(_fact('network.overview','Current simulated operation',
        f"Network revision {revision}, seed {network['seed']}: {len(network['shipments'])} candidate shipments, "
        f"{len(network['trucks'])} trucks, {len(network['lots'])} lots and {len(assignments)} approved assignments. "
        f"Held lots: {', '.join(held) or 'none'}. Recalled lots: {', '.join(recalled) or 'none'}.",
        'next_actions', simulation, [db_cite,approval_cite],
        ['Candidate shipments are not necessarily approved assignments. Contracts, stock, demand and telemetry are fictional.']))
    scenarios = []
    for key in SCENARIOS:
        try:
            result = optimize(network, key)
        except Exception as error:
            raise HTTPException(503, f'Scenario explanation unavailable: {type(error).__name__}: {error}') from error
        # Only a bounded result summary is exposed; no proposal or action is stored.
        summary = {field:result[field] for field in ('scenario','name','solver_status','feasible',
            'total_logistics_cost','unmet_demand_kg','delayed_shipments','affected_shipments',
            'review_priority_count','food_waste_kg','constraint_violations','proposed_hold_lots')}
        summary['selected_shipments'] = len(result['shipments'])
        scenarios.append(summary)
        text = (f"Scenario {key}, {SCENARIOS[key]}: solver {result['solver_status']}; "
                f"{len(result['shipments'])} selected simulated shipments, cost ${result['total_logistics_cost']:,}, "
                f"unmet demand {result['unmet_demand_kg']:,} kg, recorded constraint violations "
                f"{result['constraint_violations']}. Modeled one-wave food waste is {result['food_waste_kg']:,} kg.")
        if not result['feasible']:
            text = f"Scenario {key}, {SCENARIOS[key]}: solver {result['solver_status']}; no feasible allocation was established. Do not treat empty selections or their cost as a usable dispatch plan."
        if key == 'B':text += ' Approval can publish assignments that still require targeted human verification; driver acknowledgment is separate.'
        if key == 'C':text += ' Candidate precautionary lot holds are '+(', '.join(result['proposed_hold_lots']) or 'none')+'; this summary places no hold.'
        if key == 'D':text += ' Eligible simulated lots may be substituted on fixed trips; this does not automatically reroute trucks.'
        facts.append(_fact('scenario.'+key,SCENARIOS[key],text,'scenario_compare',
            'computed one-wave optimization over the captured simulation',
            [db_cite,_citation('solver','Scenario objectives and constraints','backend/optimization.py')],
            ['Costs and demand are simulated. Unsent stock is not automatically waste. A solver result is not human approval or safety certification.']))
    facts.append(_fact('scenario.boundaries','How to compare the responses',
        'Compare feasible scenarios using cost, unmet demand, exclusions and constraints together. Held, recalled and ineligible lots cannot dispatch. A predictive score alone does not impose a mandatory hold. Approval must be recorded in Command against the current revision.',
        'scenario_compare','implemented workflow rules',[rules],
        ['The objective selects a single allocation wave with fixed candidate trip estimates; it is not a continuous inventory ledger.']))
    outlook_citations=[_citation('outlook.guide' if source['path'].startswith('docs/') else 'outlook.implementation',
        'Delivery outlook guide' if source['path'].startswith('docs/') else 'Read-only delivery outlook implementation',
        source['path'],source['sha256']) for source in outlook_guidance]
    if all(source['status']=='captured' for source in outlook_guidance):
        facts.append(_fact('outlook.scope','Try a delivery what-if in Command',
            "Open Command center's delivery outlook. Choose an extra road-delay assumption and select Estimate impact, or use Try a 1-hour delay. "
            'The chosen delay is added to every simulated candidate trip. The preview compares a newly computed scenario-A allocation of current inputs with responses A-D under the chosen assumptions. '
            'Cargo checks are illustrative projections capped at six hours. The baseline is not the approved driver-assignment list. '
            'This is a deterministic planning projection, not a learned disruption forecast or live ETA. Use Inspect to review a candidate or Check road alternatives to inspect separate route evidence. '
            'The preview changes no route, inventory, hold or driver assignment; any consequential action needs the separate human approval workflow.',
            'next_actions','server-authored scope guidance; captured local documentation and implementation bytes',outlook_citations,
            ['This assistant has not calculated a delivery outlook, inferred a delay from DOT or weather, or established predictive skill.',
             'Ambient temperature is a user planning assumption. Cargo is simulated; thermal coefficients are uncalibrated and review flags do not create holds.',
             'Measured retrospective FSIS sampling performance remains separate from delivery what-ifs, CDC BEAM surveillance and NORS outbreaks; none is a consumer illness probability.']))
    else:
        failures='; '.join(source['path']+': '+source['error'] for source in outlook_guidance if source['status']!='captured')
        facts.append(_fact('outlook.unavailable','Delivery outlook guidance could not be captured',
            'The local delivery outlook guide and implementation could not both be captured. '+failures,
            'next_actions','recorded local guidance failure',outlook_citations,
            ['No missing documentation, source hash, delivery projection or model performance is invented. Other captured evidence remains available.']))
    lots = {row['id']:row for row in network['lots']}; trucks = {row['id']:row for row in network['trucks']}
    assigned = {row['id']:row for row in assignments}; shipment_roster=[]
    for shipment in network['shipments']:
        sid=shipment['id'];lot=lots[shipment['lot_id']];truck=trucks[shipment['truck_id']]
        shipment_roster.append({field:shipment[field] for field in ('id','origin','destination','lot_id','truck_id')})
        shipment_roster[-1]['label']=f"{sid}: {shipment['origin']} to {shipment['destination']} ({shipment['truck_id']})"
        facts.append(_fact('shipment.'+sid+'.context','Selected simulated shipment '+sid,
            f"{sid} is a candidate trip from {shipment['origin']} to {shipment['destination']}, "
            f"truck {shipment['truck_id']}, candidate lot {shipment['lot_id']}, quantity {shipment['quantity_kg']:,} kg. "
            f"Its current simulated cargo value is {shipment['temperature_c']:g}°C. "
            f"An approved assignment with this trip ID is {'present' if sid in assigned else 'not present'} in the captured state.",
            'shipment_review',simulation,[db_cite,approval_cite],
            ['An approved alternative-supply assignment can carry a different lot from this candidate. Inspect the actual current assignment before deciding.'],shipment_id=sid))
        if sid in assigned:
            assignment=assigned[sid];active_lot=lots[assignment['lot_id']];active_truck=trucks[assignment['truck_id']]
            text=(f"The actual captured assignment uses lot {assignment['lot_id']}, truck {assignment['truck_id']} and "
                  f"{assignment['quantity_kg']:,} kg. Its lot is {'held' if active_lot['held'] else 'not held'}, "
                  f"{'recalled' if active_lot['recalled'] else 'not recalled'} and "
                  f"{'eligible' if active_lot['eligible'] else 'ineligible'}; the truck is "
                  f"{'eligible' if active_truck['eligible'] else 'ineligible'} and "
                  f"{'refrigerated' if active_truck['refrigerated'] else 'not refrigerated'}. "
                  f"Assignment acknowledgment is {'recorded' if assignment['acknowledged'] else 'not recorded'}.")
        else:text='No approved assignment with this trip ID is present. A candidate on the Command map is not a published driver trip.'
        facts.append(_fact('shipment.'+sid+'.assignment','Current approved assignment context',text,
            'shipment_review','captured simulated assignment and eligibility fields',[db_cite,approval_cite],
            ['An assignment record does not override a current hold, recall, eligibility failure or pending human verification.'],shipment_id=sid))
        constraints=[]
        if lot['held']:constraints.append('candidate lot is held')
        if lot['recalled']:constraints.append('candidate lot is recalled')
        if not lot['eligible']:constraints.append('candidate lot is ineligible')
        if not truck['eligible']:constraints.append('truck is ineligible')
        if not truck['refrigerated']:constraints.append('truck is not refrigerated')
        if shipment['quantity_kg']>lot['inventory_kg']:constraints.append('candidate quantity exceeds this lot’s stock')
        if shipment['quantity_kg']>truck['capacity_kg']:constraints.append('candidate quantity exceeds truck capacity')
        if shipment['estimated_hours']>min(shipment['deadline_hours'],lot['shelf_life_hours']):constraints.append('estimated trip exceeds its deadline or candidate lot shelf life')
        facts.append(_fact('shipment.'+sid+'.constraints','Candidate constraints to inspect',
            ('Direct candidate flags: '+ '; '.join(constraints)+'.') if constraints else
            'No direct single-candidate exclusion was found in the listed lot, truck and timing fields. Aggregate stock, demand, supplier/DC and shared-truck limits still need the full scenario review.',
            'shipment_review','captured candidate fields and modeled constraint checks',[db_cite],
            ['Passing these individual checks does not establish plan-level feasibility, product safety or departure authority.'],shipment_id=sid))
        facts.append(_fact('shipment.'+sid+'.exposure','Temperature and route meaning',
            (f"The simulated cargo value exceeds the application’s 4°C review level. " if shipment['temperature_c']>4 else 'The current simulated cargo value does not exceed the application’s 4°C review level. ')+
            f"The fixed trip estimate is {shipment['estimated_hours']:g} hours against a {shipment['deadline_hours']:g}-hour deadline. "
            'Inspect telemetry context and route evidence separately. A reading or illustrative thermal projection cannot determine illness probability or automatically create a hold.',
            'shipment_review','simulated cargo and estimated travel',[db_cite,_citation('thermal','Illustrative physical projection','backend/cold_chain.py')],
            ['The 4°C level is an app review assumption, not a product disposition. OSRM driving and DOT proximity do not certify a commercial route.'],shipment_id=sid))
    report,citation,unavailable=_report_fact('model_evaluation.json',reports,'Measured historical FSIS evaluation','model_limits')
    model=report['payload']
    try:
        if (not isinstance(model,dict) or not _integer(model.get('training_rows'),1)
                or not _integer(model.get('validation_rows'),1)
                or not isinstance(model.get('target'),str)
                or not all(term in model['target'].lower() for term in ('salmonella','fsis','raw-poultry','primary'))):
            raise ValueError('Unsupported sampling target or evaluation rows')
        baseline=model['baseline']['brier'];logistic=model['logistic_regression']['brier']
        auc=model['logistic_regression']['roc_auc']
        if (not all(_number(value,0,1) for value in (baseline,logistic,auc))
                or not _integer(model['baseline'].get('n'),1)
                or not _integer(model['logistic_regression'].get('n'),1)
                or model['baseline'].get('n')!=model['validation_rows']
                or model['logistic_regression'].get('n')!=model['validation_rows']):
            raise ValueError('Brier/ROC-AUC metric absent, nonfinite or outside its range')
        facts.append(_fact('model.metrics','Measured primary holdout result',
            f"The saved national raw-poultry primary-sample evaluation has {model['training_rows']:,} training rows and "
            f"{model['validation_rows']:,} holdout rows. Historical baseline Brier is {baseline:.8f}; logistic Brier is "
            f"{logistic:.8f}; logistic ROC-AUC is {auc:.6f}. Lower Brier means lower squared probability error for this defined sampling task.",
            'model_limits','measured retrospective FSIS sampling evaluation',[citation],
            ['This measures selected-sample positivity, not consumer illness probability, farm safety or an individualized shipment forecast.']))
        facts.append(_fact('model.comparison','Complexity is not evidence of useful skill',
            ('The baseline has lower or equal Brier error than logistic regression in this saved primary holdout. ' if baseline<=logistic else
             'Logistic regression has lower Brier error in this saved primary holdout, but that single comparison does not establish prospective validity. ')+
            'Inspect calibration, uncertainty, target definition and actual feature-availability dates before claiming an operational forecast.',
            'model_limits','comparison of the recorded evaluation metrics',[citation],
            ['No new accuracy figure, training run or prospective validation is created by this summary.']))
    except (ValueError,KeyError,TypeError):
        facts.append(unavailable)
    timing=reports['model_timing.json'];timing_cite=_citation('timing','Recorded availability audit','reports/model_timing.json',timing['metadata']['sha256'])
    facts.append(_fact('model.availability','Feature availability remains a separate question',
        'A collection-date reporting lag or snapshot-creation date is not proof of first public availability. The current application does not establish a validated prospective illness forecast. Keep FSIS outcomes, CDC BEAM surveillance and NORS outbreaks distinct unless a defensible linkage is demonstrated.',
        'model_limits','scientific interpretation and implementation boundaries',[timing_cite,citation],
        ['The assistant does not infer missing publication dates or genomic relationships from shared labels.',
         *(['Saved timing audit is unavailable: '+(timing['metadata']['error'] or 'unsupported report fields')]
           if not isinstance(timing['payload'],dict) else [])]))
    report,citation,unavailable=_report_fact('api_status.json',reports,'Saved public endpoint checks','source_coverage')
    probes=report['payload']
    valid = (isinstance(probes,list) and len(probes)<=100
             and all(isinstance(row,dict) and _identifier(row.get('id')) and isinstance(row.get('success'),bool)
                     and (row.get('http_status') is None or _integer(row.get('http_status'),100) and row['http_status']<=599)
                     and (not row['success'] or row.get('http_status') is not None and 200<=row['http_status']<400)
                     for row in probes)
             and len({row['id'] for row in probes})==len(probes))
    if valid:
        successes=sum(row['success'] for row in probes);failed=[row['id'] for row in probes if not row['success']]
        facts.append(_fact('sources.probes','Saved connectivity is not complete data coverage',
            f"Saved registry probes record {successes} successful HTTP checks out of {len(probes)} endpoints. "
            f"Recorded failures: {', '.join(failed) or 'none'}. These checks have separate timestamps and include catalogs/documentation; no live request was made here.",
            'source_coverage','dated HTTP probe metadata',[citation],
            ['A past HTTP success is not current uptime, complete observations or a working scientific join.']))
        for row in probes:
            timestamp=_stamp(row.get('tested_at'))
            facts.append(_fact('source.'+row['id'],'Saved source check: '+row['id'],
                f"{row['id']}: saved check {'succeeded' if row['success'] else 'failed'}; "
                f"HTTP {row.get('http_status') if row.get('http_status') is not None else 'not recorded'}. "
                f"Check time: {timestamp or 'missing, invalid, naive or implausibly future; not treated as verified'}. "
                'Inspect the Sources workspace for the actual payload, fallback and coverage.',
                'source_coverage','dated registry probe; no refresh',
                [_citation('probe.'+row['id'],'Probe record '+row['id'],'reports/api_status.json',report['metadata']['sha256'],timestamp)],
                ['The assistant does not turn saved connectivity metadata into a current source-success claim.']))
    else:facts.append(unavailable)
    report,citation,unavailable=_report_fact('noaa_coverage.json',reports,'Historical NOAA station coverage','source_coverage')
    noaa=report['payload']
    if (isinstance(noaa,dict) and all(_integer(noaa.get(key)) for key in ('station_count','observed_station_days','expected_station_days','missing_metric_values'))
            and noaa['observed_station_days']<=noaa['expected_station_days']):
        facts.append(_fact('sources.noaa','Bounded observed historical weather',
            f"The saved NOAA extract covers {noaa['station_count']} stations and returns {noaa['observed_station_days']:,} of "
            f"{noaa['expected_station_days']:,} requested station-day rows; {noaa['missing_metric_values']:,} metric values are missing. "
            'Date-row coverage is separate from numeric/quality coverage. Historical observations, forecasts, reanalysis and simulated cargo are not interchangeable.',
            'source_coverage','observed historical weather coverage report',
            [_citation('noaa.coverage','NOAA coverage report','reports/noaa_coverage.json',report['metadata']['sha256'],_stamp(noaa.get('generated_at')))],
            ['Coverage is bounded to the requested stations/window. No validated FSIS-weather join or invented missing observation is supplied.']))
    else:facts.append(unavailable)
    facts.append(_fact('sources.traceability','Separate evidence is not a verified recall or genomic match',
        'Official recall notices are evidence. Fictional lots lack genuine traceability supporting a verified real recall match. CDC BEAM and NORS are separate layers, and shared serotype labels alone do not establish genomic relatedness or a common source.',
        'source_coverage','scientific and traceability boundaries',
        [_citation('model.card','Model scope and limitations','docs/model_card.md'),db_cite]))
    acknowledgment=sum(row['acknowledged'] for row in assignments)
    verification_pending=sum(row['verification_required'] and row['verification_status']!='complete' for row in assignments)
    facts.append(_fact('driver.assignments','Current approved handoff records',
        f"The captured state has {len(assignments)} approved assignments, {acknowledgment} acknowledged, "
        f"and {verification_pending} assignments still requiring scenario-B verification. These are distinct workflow records.",
        'driver_workflow','captured simulated assignment records',[approval_cite],
        ['A driver acknowledgment is not targeted verification, physical departure authorization or a product-safety finding.']))
    facts.append(_fact('driver.parked','Use Drive while safely parked',
        'Drive starts locked. Its server-checked parked attestation is self-declared and expires after ten minutes. Reporting and acknowledgments require the current truck/trip context. No actual motion, GPS or physical fuel/cargo sensor is detected.',
        'driver_workflow','implemented driver interaction rules',[rules,_citation('drive.design','Driver mode design and limits','docs/drive_design.md')]))
    facts.append(_fact('driver.decisions','Keep reports and dispatcher authority separate',
        'A driver report reaches the local dispatcher inbox without automatically rerouting or holding cargo. A human may review, hold/release a lot or issue a versioned instruction. A hold removes affected assignments; release does not recreate them. Events, resets and new approvals can invalidate an earlier assignment context.',
        'driver_workflow','implemented approval, incident and hold workflow',[rules]))
    facts.append(_fact('next.review','A review path through existing workspaces',
        'Inspect current scenario constraints and exclusions in Command, read dated source/model limits, then use the existing explicit approval and dispatcher workflow when a human chooses an action. Route laboratory and Road intelligence are separate planning tools; saved experiments cannot dispatch.',
        'next_actions','read-only navigation guidance',[rules,_citation('manual','Complete master user handbook','docs/aegis_master_guide.md')],
        ['This answer navigates to review; it cannot execute a recommendation or override a hold, recall or eligibility constraint.']))
    context={'network_revision':revision,'generated_at':generated,'engine':dict(ENGINE),'questions':QUESTIONS,
             'shipments':shipment_roster,'facts':facts,'scenarios':scenarios,'limitations':LIMITATIONS,
             'snapshot_sources':[database,*[value['metadata'] for value in reports.values()],*outlook_guidance],
             'operational_state_modified':False}
    captured=_canonical({key:value for key,value in context.items() if key!='generated_at'})
    if len(captured)>MAX_CONTEXT_BYTES:
        raise HTTPException(503,'Derived assistant context exceeds the 2 MiB response inspection bound')
    context['snapshot_id']=_sha(captured)
    return context


def answer_from_context(context, question_id, shipment_id=None):
    """Select only captured server-authored facts; never compose new model claims."""
    if question_id not in {row['id'] for row in QUESTIONS}:
        raise HTTPException(422,'Unknown assistant question')
    if question_id=='shipment_review':
        if not shipment_id:raise HTTPException(422,'Choose a shipment for the shipment review')
        if shipment_id not in {row['id'] for row in context['shipments']}:
            raise HTTPException(404,'Unknown simulated shipment in this captured context')
    elif shipment_id is not None:raise HTTPException(422,'Shipment selection applies only to shipment review')
    details={
        'scenario_compare':('Current response tradeoffs','Try a read-only delivery what-if in Command, then compare feasible allocations and their limitations before a human chooses a response.', [('command','Try delivery outlook and compare current responses'),('dispatch','Open dispatcher review')]),
        'shipment_review':('Selected shipment review','Inspect the candidate, current assignment context and separate evidence. No disposition is made here.', [('command','Inspect the shipment and scenarios'),('dispatch','Inspect current lot and assignment state'),('roads','Inspect independent road evidence')]),
        'model_limits':('Measured model performance and limits','Delivery outlook explores chosen planning assumptions. Read measured retrospective FSIS results separately, together with feature-availability and target limitations.', [('command','Try an illustrative delivery what-if'),('science','Open measured model evaluation'),('evidence','Inspect source provenance')]),
        'source_coverage':('Saved source coverage and failures','These are captured records and coverage reports, not a new live provider check.', [('evidence','Inspect source times and failures'),('roads','Inspect Missouri and Iowa road evidence')]),
        'driver_workflow':('Human-approved driver handoff','Approval, verification, acknowledgment and incident review remain distinct actions.', [('dispatch','Open dispatcher desk'),('drive','Open parked-use Drive')]),
        'next_actions':('Review steps available now','Start with delivery outlook in Command, inspect candidates and separate evidence, then review a current plan before any human-approved action.', [('command','Start with delivery outlook in Command'),('evidence','Inspect source gaps'),('brief','Read the handbook and rehearsal guide')]),
    }
    title,summary,views=details[question_id]
    items=[fact for fact in context['facts'] if (fact['category']==question_id
           or question_id in {'scenario_compare','model_limits'} and fact['id'] in {'outlook.scope','outlook.unavailable'})
           and (question_id!='shipment_review' or fact.get('shipment_id')==shipment_id)]
    return {'snapshot_id':context['snapshot_id'],'network_revision':context['network_revision'],
            'generated_at':context['generated_at'],'engine':dict(context['engine']),
            'question_id':question_id,'shipment_id':shipment_id,
            'answer':{'title':title,'summary':summary,'items':items},
            'suggested_views':[{'view':view,'label':label} for view,label in views],
            'limitations':context['limitations'],'operational_state_modified':False}


def create_assistant_router(db_path, root=ROOT):
    router=APIRouter(tags=['Read-only evidence assistant'])

    @router.get('/api/assistant/context')
    def get_context():
        return capture_context(db_path,root)

    @router.post('/api/assistant/ask')
    def ask(request:AssistantAsk):
        context=capture_context(db_path,root)
        if request.expected_snapshot_id is not None and request.expected_snapshot_id!=context['snapshot_id']:
            raise HTTPException(409,'Evidence context changed; reload the assistant snapshot before asking again')
        return answer_from_context(context,request.question_id,request.shipment_id)

    return router
