"""Reproduce the synthetic quality/FEFO/rescue story in a fresh isolated database."""
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import sys
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from fastapi.testclient import TestClient
import backend.main as application
from scripts.demo_run import database_fingerprints
from backend.paths import write_json


def run_demo(report_path=None):
    original=application.DB
    keys=('AEGIS_DB_PATH','AEGIS_REHEARSAL_ID','AEGIS_OFFLINE_DEMO')
    environment={key:os.environ.get(key) for key in keys}
    protected=[original,ROOT/'data/aegis.sqlite'];before=database_fingerprints(protected)
    result={'started_at':datetime.now(timezone.utc).isoformat(),'simulation':True,'physical_hardware_connected':False,
        'mode':'accelerated deterministic replay; not a timed human presentation','passed':False,'checks':[],
        'limitations':['Illustrative temperature-driven quality estimates, not measured spoilage or food safety.','All logistics, warehouse placement, receiving acceptance and sensor packets are simulated.','FEFO expiry exposure is not observed food waste or a guaranteed quantity saved.']}
    def check(name,condition):
        result['checks'].append({'name':name,'passed':bool(condition)})
        if not condition:raise AssertionError(name)
    try:
        session_id=str(uuid.uuid4());folder=(ROOT/'data/rehearsals').resolve();folder.mkdir(parents=True,exist_ok=True)
        database=(folder/(session_id+'.sqlite')).resolve()
        if database.parent!=folder or not database.is_relative_to(ROOT.resolve()):raise ValueError('Unsafe isolated demo path')
        with database.open('xb'):pass
        os.environ.update(AEGIS_REHEARSAL_ID=session_id,AEGIS_DB_PATH=str(database),AEGIS_OFFLINE_DEMO='1');application.DB=database
        result['database_relative_path']=database.relative_to(ROOT).as_posix();result['rehearsal_id']=session_id
        with TestClient(application.app) as client:
            def request(path,body=None):
                response=client.get('/api'+path) if body is None else client.post('/api'+path,json=body)
                if response.status_code!=200:raise AssertionError(f'{path}: HTTP {response.status_code}: {response.text[:500]}')
                return response.json()
            network=request('/network');runtime=request('/runtime-context')
            check('verified fresh isolated offline runtime',runtime['isolated'] and runtime['offline'] and runtime['rehearsal_id']==session_id)
            context=request('/freshness/context');shipment_id=context['demo_shipment_id'];check('actual eligible demonstration candidate exists',bool(shipment_id))
            snapshot=request('/freshness/sessions',{'expected_network_revision':network['revision'],'shipment_id':shipment_id,'scenario':'poultry_demo'})
            first=snapshot['freshness'];check('baseline quality has supported coverage',first['status']=='estimated' and first['coverage']['complete'])
            check('no assignment published by experiment creation',request('/driver')==[] and request('/network')==network)
            snapshot=request('/freshness/sessions/'+snapshot['id']+'/replay',{'expected_version':snapshot['version'],'event':'heat_excursion'})
            quality=snapshot['freshness'];rescue=snapshot['rescue']
            check('heat consumes the remaining quality budget',quality['remaining_reference_hours']<first['remaining_reference_hours'])
            check('conservative case is separate from point estimate',0<quality['remaining_quality_hours']<quality['remaining_hours_at_forecast_temperature'])
            check('rescue automatically computes a concrete feasible plan',rescue['triggered'] and rescue['proposal_hash'] and rescue['plan_summary']['constraint_violations']==0)
            check('FEFO and FIFO use actual independently reviewed allocations',all(snapshot['fefo'][policy]['constraint_review']['passed'] for policy in ('fefo','fifo')))
            check('sensor replay does not change operational state',request('/driver')==[] and request('/network')==network)
            db_before=database_fingerprints([database]);captured=request('/freshness/sessions/'+snapshot['id']);db_after=database_fingerprints([database])
            check('reading a stored experiment preserves SQLite and sidecars',db_before==db_after and captured['version']==snapshot['version'])
            result['quality']={'baseline_reference_hours':first['remaining_reference_hours'],'point_forward_hours':quality['remaining_hours_at_forecast_temperature'],
                'conservative_case_hours':quality['remaining_quality_hours'],'sensitivity':quality['sensitivity'],'profile':quality['profile']}
            result['warehouse']={policy:{key:snapshot['fefo'][policy][key] for key in ('supplied_kg','unmet_demand_kg','projected_expiry_exposure_kg','priority_lot_ids','lot_totals')} for policy in ('fefo','fifo')}
            result['rescue_before_approval']={'shipment_id':shipment_id,'original_destination':snapshot['shipment']['destination_name'],'required_hours':rescue['original_required_hours'],
                'selected_destination_id':rescue['proposed_destination_id'],'plan_summary':rescue['plan_summary']}
            approved=request('/freshness/sessions/'+snapshot['id']+'/approve',{'expected_version':snapshot['version'],'expected_network_revision':snapshot['network_revision'],
                'proposal_hash':rescue['proposal_hash'],'destination_id':rescue['proposed_destination_id'],'actor':'Synthetic demo dispatcher',
                'reason':'Isolated reproducible quality-rescue exercise; eligibility, receiving and route assumptions reviewed',
                'quality_review_confirmed':True,'recipient_confirmed':True,'routing_review_confirmed':True})
            snapshot=approved['snapshot'];result['approval']=approved['receipt']
            assignments=request('/driver');assignment=next(row for row in assignments if row['id']==shipment_id)
            check('human approval updates the actual simulated driver destination',assignment['destination']==rescue['proposed_destination_id'] and assignment['destination']!=next(row['destination'] for row in network['shipments'] if row['id']==shipment_id))
            updated=request('/network');lots={row['id']:row for row in updated['lots']}
            check('held and recalled stock stays out of every approved assignment',all(not lots[row['lot_id']]['held'] and not lots[row['lot_id']]['recalled'] for row in assignments))
            check('approval preserves inventory quantities',all(row['inventory_kg']==next(old['inventory_kg'] for old in network['lots'] if old['id']==row['id']) for row in updated['lots']))
            snapshot=request('/freshness/sessions/'+snapshot['id']+'/replay',{'expected_version':snapshot['version'],'event':'normal'})
            drive=request('/drive/'+assignment['truck_id']);readiness=request('/readiness')
            check('new telemetry flags driver review without redispatch',snapshot['status']=='review_required' and bool(drive.get('freshness_reviews')) and request('/driver')==assignments)
            record=next(row for row in readiness['assignments'] if row['shipment_id']==shipment_id)
            check('readiness distinguishes the pending freshness review',record['status']!='ready_for_review')
            result['driver']={'truck_id':assignment['truck_id'],'shipment_id':shipment_id,'destination_id':assignment['destination'],'freshness_reviews':drive['freshness_reviews'],'readiness_status_after_new_frame':record['status']}
            result['passed']=True
    except Exception as error:result.update(passed=False,error=f'{type(error).__name__}: {error}')
    finally:
        application.DB=original
        for key,value in environment.items():
            if value is None:os.environ.pop(key,None)
            else:os.environ[key]=value
        after=database_fingerprints(protected);result.update(finished_at=datetime.now(timezone.utc).isoformat(),operator_database_before=before,operator_database_after=after,operator_database_modified=before!=after)
        if before!=after:result.update(passed=False,preservation_error='Protected operational database fingerprints changed; original state was not restored or overwritten')
        write_json(report_path or ROOT/'reports/freshness_demo.json',result)
    return result

if __name__=='__main__':
    result=run_demo();print(json.dumps({'passed':result['passed'],'checks':len(result['checks']),'error':result.get('error'),'operator_database_modified':result['operator_database_modified']}))
    raise SystemExit(0 if result['passed'] else 1)
