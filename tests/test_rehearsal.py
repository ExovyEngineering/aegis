"""Timed practice is isolated evidence, never automatic submission signoff."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest

import backend.rehearsal as rehearsal
from backend.runtime import runtime_context, require_valid_runtime
from backend.simulation import seed_network


RUN_ID='5b7fe631-6ab6-4af1-b2f2-07514909a66c'
IDENTITY={'presenter':'Team presenter','purpose':'Timed practice of the competition narrative','run_kind':'practice'}


def env_for(root,identity=RUN_ID):
    return {'AEGIS_REHEARSAL_ID':identity,'AEGIS_DB_PATH':str(root/f'data/rehearsals/{identity}.sqlite'),'AEGIS_OFFLINE_DEMO':'1'}


def test_operator_runtime_does_not_create_or_open_a_database(tmp_path):
    selected=tmp_path/'data/aegis.sqlite'
    context=runtime_context(selected,root=tmp_path,env={})
    assert context['mode']=='operator' and not context['isolated']
    assert context['database_relative_path']=='data/aegis.sqlite'
    assert require_valid_runtime(selected,root=tmp_path,env={})==context
    assert not selected.parent.exists()


def test_exact_canonical_rehearsal_identity_and_path_are_verified(tmp_path):
    environment=env_for(tmp_path)
    context=runtime_context(root=tmp_path,env=environment)
    assert context['mode']=='isolated_rehearsal' and context['isolated'] and context['offline']
    assert context['rehearsal_id']==RUN_ID
    assert context['database_relative_path']==f'data/rehearsals/{RUN_ID}.sqlite'
    assert not Path(environment['AEGIS_DB_PATH']).exists()


@pytest.mark.parametrize('update',[
    {'AEGIS_REHEARSAL_ID':''},
    {'AEGIS_REHEARSAL_ID':RUN_ID.upper()},
    {'AEGIS_REHEARSAL_ID':'../operator'},
    {'AEGIS_REHEARSAL_ID':'{'+RUN_ID+'}'},
    {'AEGIS_DB_PATH':'data/aegis.sqlite'},
    {'AEGIS_OFFLINE_DEMO':'yes'},
])
def test_partial_or_noncanonical_configuration_is_misconfigured(tmp_path,update):
    environment=env_for(tmp_path);environment.update(update)
    context=runtime_context(root=tmp_path,env=environment)
    assert context['mode']=='misconfigured' and not context['isolated']
    with pytest.raises(HTTPException) as rejected:
        require_valid_runtime(Path(environment['AEGIS_DB_PATH']),root=tmp_path,env=environment)
    assert rejected.value.status_code==503


@pytest.mark.parametrize('environment',[{'AEGIS_OFFLINE_DEMO':'1'},{'AEGIS_REHEARSAL_ID':''},{'AEGIS_OFFLINE_DEMO':'0'}])
def test_partial_configuration_cannot_silently_become_operator_mode(tmp_path,environment):
    assert runtime_context(root=tmp_path,env=environment)['mode']=='misconfigured'


def test_a_rehearsal_path_without_its_identity_is_misconfigured(tmp_path):
    path=tmp_path/f'data/rehearsals/{RUN_ID}.sqlite'
    assert runtime_context(path,root=tmp_path,env={})['mode']=='misconfigured'


def test_existing_hardlink_to_operator_database_is_rejected(tmp_path):
    operator=tmp_path/'data/aegis.sqlite';operator.parent.mkdir()
    operator.write_bytes(b'operator bytes')
    path=tmp_path/f'data/rehearsals/{RUN_ID}.sqlite';path.parent.mkdir()
    os.link(operator,path)
    context=runtime_context(path,root=tmp_path,env=env_for(tmp_path))
    assert context['mode']=='misconfigured' and 'aliases' in context['warning']
    assert operator.read_bytes()==b'operator bytes'


@pytest.fixture
def practice(tmp_path,monkeypatch):
    root=tmp_path/'workspace';root.mkdir()
    environment=env_for(root)
    for key,value in environment.items():monkeypatch.setenv(key,value)
    selected=Path(environment['AEGIS_DB_PATH'])
    clock=[datetime(2026,10,27,20,0,tzinfo=timezone.utc)]
    monkeypatch.setattr(rehearsal,'_now',lambda:clock[0])
    @contextmanager
    def db():
        require_valid_runtime(selected,root=root)
        selected.parent.mkdir(parents=True,exist_ok=True)
        connection=sqlite3.connect(selected,timeout=10)
        try:
            connection.execute('CREATE TABLE IF NOT EXISTS state(id INTEGER PRIMARY KEY,payload TEXT,revision INTEGER)')
            connection.execute('CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,timestamp TEXT,actor TEXT,action TEXT,payload TEXT)')
            connection.execute('CREATE TABLE IF NOT EXISTS incidents(id TEXT PRIMARY KEY,shipment_id TEXT,payload TEXT,status TEXT,version INTEGER)')
            connection.execute('INSERT OR IGNORE INTO state VALUES(1,?,0)',(json.dumps(seed_network()),))
            connection.commit()
            yield connection
            connection.commit()
        except Exception:
            connection.rollback();raise
        finally:connection.close()
    def load(connection):
        payload,revision=connection.execute('SELECT payload,revision FROM state WHERE id=1').fetchone()
        return json.loads(payload),revision
    def record(connection,actor,action,payload):
        connection.execute('INSERT INTO audit(timestamp,actor,action,payload) VALUES(?,?,?,?)',(clock[0].isoformat(),actor,action,json.dumps(payload)))
    app=FastAPI();app.include_router(rehearsal.create_rehearsal_router(db,load,record,lambda:selected,root=root))
    with TestClient(app) as client:
        yield {'client':client,'db':db,'load':load,'record':record,'clock':clock,'root':root,'path':selected}


def start(practice,**updates):
    response=practice['client'].post('/api/rehearsal/start',json=dict(IDENTITY,**updates))
    assert response.status_code==200,response.text
    return response.json()


def checkpoint(practice,run,stage=None,outcome='covered',notes='',**updates):
    request={'expected_version':run['version'],'stage_id':stage or run['next_stage_id'],'outcome':outcome,'notes':notes}
    request.update(updates)
    return practice['client'].post(f'/api/rehearsal/{run["id"]}/checkpoint',json=request)


def actions(practice,*names):
    with practice['db']() as connection:
        for name in names:
            payload={'mode':'parked','parked_confirmation':True,'truck_id':'T03'} if name=='driver_focus' else {'shipment_id':'SH03'}
            if name=='incident':
                incident_id=str(uuid.uuid4())
                assignment={'id':'SH03','truck_id':'T03','lot_id':'L03','origin':'DC1','destination':'D03'}
                connection.execute('INSERT INTO incidents VALUES(?,?,?,?,0)',
                                   (incident_id,'SH03',json.dumps({'reporting_assignment':assignment,'reported_network_revision':0}),'open'))
                payload['incident_id']=incident_id
            practice['record'](connection,'Simulated actor',name,payload)


def all_stages(practice,run,skip=False):
    for stage in rehearsal.STAGES:
        if stage['requires_evidence'] and not skip:actions(practice,*stage['requires_evidence'])
        response=checkpoint(practice,run,outcome='skipped' if skip else 'covered',notes='Explicitly skipped during automated test' if skip else '')
        assert response.status_code==200,response.text
        run=response.json()
    return run


def test_operator_status_and_mutations_never_invoke_db(tmp_path,monkeypatch):
    for name in ('AEGIS_REHEARSAL_ID','AEGIS_OFFLINE_DEMO','AEGIS_DB_PATH'):monkeypatch.delenv(name,raising=False)
    calls=[]
    def forbidden_db():calls.append(True);raise AssertionError('operator database must not be opened')
    app=FastAPI();app.include_router(rehearsal.create_rehearsal_router(forbidden_db,None,None,lambda:tmp_path/'data/aegis.sqlite',root=tmp_path))
    with TestClient(app) as client:
        assert client.get('/api/runtime-context').json()['mode']=='operator'
        body=client.get('/api/rehearsal').json()
        assert body['active'] is None and body['runs']==[]
        assert client.post('/api/rehearsal/start',json=IDENTITY).status_code==403
        assert client.get('/api/rehearsal/unknown').status_code==403
        assert client.get('/api/rehearsal/unknown/export').status_code==403
    assert calls==[] and not (tmp_path/'data').exists()


def test_misconfigured_runtime_does_not_invoke_db(tmp_path,monkeypatch):
    monkeypatch.setenv('AEGIS_REHEARSAL_ID',RUN_ID)
    app=FastAPI()
    def forbidden_db():raise AssertionError('misconfigured database must not be opened')
    app.include_router(rehearsal.create_rehearsal_router(forbidden_db,None,None,lambda:tmp_path/'data/aegis.sqlite',root=tmp_path))
    with TestClient(app) as client:
        assert client.get('/api/runtime-context').json()['mode']=='misconfigured'
        assert client.get('/api/rehearsal').json()['runtime']['mode']=='misconfigured'
        assert client.post('/api/rehearsal/start',json=IDENTITY).status_code==503


def test_start_is_persistent_and_only_one_active_run_allowed(practice):
    run=start(practice)
    assert run['next_stage_id']=='overview' and run['target_seconds']==300
    assert run['run_kind']=='practice' and run['elapsed_seconds']==0
    assert practice['client'].post('/api/rehearsal/start',json=IDENTITY).status_code==409
    practice['clock'][0]+=timedelta(seconds=12)
    status=practice['client'].get('/api/rehearsal').json()
    assert status['active']['id']==run['id'] and status['active']['elapsed_seconds']==12
    assert status['runs'][0]['presenter']==IDENTITY['presenter']


@pytest.mark.parametrize('updates',[{'presenter':' '},{'purpose':'  '},{'run_kind':'verified'},{'elapsed_seconds':300}])
def test_run_identity_and_server_clock_are_not_client_forged(practice,updates):
    response=practice['client'].post('/api/rehearsal/start',json=dict(IDENTITY,**updates))
    assert response.status_code==422
    assert practice['client'].get('/api/rehearsal').json()['active'] is None


def test_order_stale_versions_and_duplicate_checkpoints_are_rejected_atomically(practice):
    run=start(practice)
    assert checkpoint(practice,run,stage='approval').status_code==409
    first=checkpoint(practice,run).json()
    assert checkpoint(practice,run,stage='overview').status_code==409
    assert checkpoint(practice,first,stage='overview').status_code==409
    actual=practice['client'].get('/api/rehearsal/'+run['id']).json()
    assert actual['version']==2 and len(actual['milestones'])==1


def test_skips_require_an_explicit_reason_and_are_not_claimed_as_coverage(practice):
    run=start(practice)
    assert checkpoint(practice,run,outcome='skipped',notes='no').status_code==422
    response=checkpoint(practice,run,outcome='skipped',notes='The presenter deferred this section')
    assert response.status_code==200
    milestone=response.json()['milestones'][0]
    assert milestone['outcome']=='skipped' and milestone['evidence']['kind']=='skipped'


def test_operational_coverage_requires_actions_since_this_run_started(practice):
    actions(practice,'event','approve','driver_focus','acknowledge','incident')
    run=start(practice)
    run=checkpoint(practice,run).json();run=checkpoint(practice,run).json()
    assert checkpoint(practice,run).status_code==409
    actions(practice,'event')
    run=checkpoint(practice,run).json()
    assert run['milestones'][-1]['evidence']['actions'][0]['action']=='event'
    assert checkpoint(practice,run).status_code==409
    actions(practice,'approve');run=checkpoint(practice,run).json()
    assert checkpoint(practice,run).status_code==409
    actions(practice,'driver_focus','acknowledge','incident');run=checkpoint(practice,run).json()
    assert run['next_stage_id']=='closing'


def test_driving_focus_is_not_parked_evidence(practice):
    run=start(practice)
    for _ in range(4):run=checkpoint(practice,run,outcome='skipped',notes='Skipped to inspect the driver evidence requirement').json()
    actions(practice,'acknowledge','incident')
    with practice['db']() as connection:
        practice['record'](connection,'Driver','driver_focus',{'mode':'driving','parked_confirmation':False})
    assert checkpoint(practice,run).status_code==409


def test_completion_records_actual_timer_not_a_five_minute_verification(practice):
    run=start(practice,run_kind='automated_check')
    run=all_stages(practice,run)
    practice['clock'][0]+=timedelta(seconds=37)
    response=practice['client'].post(f'/api/rehearsal/{run["id"]}/finish',json={'expected_version':run['version'],'outcome':'completed','notes':'Accelerated automated workflow'})
    assert response.status_code==200
    result=response.json()
    assert result['elapsed_seconds']==37 and result['timing_assessment']=='under_target'
    exported=practice['client'].get(f'/api/rehearsal/{run["id"]}/export')
    assert exported.status_code==200
    snapshot=exported.json()
    assert not snapshot['five_minute_presentation_verified'] and not snapshot['genuine_kiro_execution_verified'] and not snapshot['author_signoff_verified']
    assert snapshot['run']['run_kind']=='automated_check'
    assert snapshot['network']['seed']==20261026
    assert hashlib.sha256(exported.content).hexdigest()==exported.headers['x-aegis-snapshot-sha256']


def test_short_and_over_target_elapsed_are_comparisons_not_pass_flags(practice):
    run=all_stages(practice,start(practice),skip=True)
    practice['clock'][0]+=timedelta(seconds=380)
    finished=practice['client'].post(f'/api/rehearsal/{run["id"]}/finish',json={'expected_version':run['version'],'outcome':'completed'}).json()
    assert finished['elapsed_seconds']==380 and finished['timing_assessment']=='at_or_over_target'
    assert 'not verify' in finished['notice']
    assert all(stage['outcome']=='skipped' for stage in finished['milestones'])


def test_finished_export_is_immutable_after_later_network_audit_and_report_changes(practice):
    reports=practice['root']/'reports';reports.mkdir()
    path=reports/'model_evaluation.json';path.write_text('{"brier":0.1}')
    run=all_stages(practice,start(practice))
    finish=f'/api/rehearsal/{run["id"]}/finish'
    assert practice['client'].post(finish,json={'expected_version':run['version'],'outcome':'completed'}).status_code==200
    url=f'/api/rehearsal/{run["id"]}/export'
    first=practice['client'].get(url)
    path.write_text('{"brier":0.9}')
    with practice['db']() as connection:
        network,revision=practice['load'](connection);network['lots'][0]['inventory_kg']=0
        connection.execute('UPDATE state SET payload=?,revision=? WHERE id=1',(json.dumps(network),revision+1))
        practice['record'](connection,'Later actor','event',{'event':'later action'})
    practice['clock'][0]+=timedelta(hours=1)
    assert practice['client'].get(url).content==first.content
    assert checkpoint(practice,run,stage='overview').status_code==409
    assert practice['client'].post(finish,json={'expected_version':run['version']+1,'outcome':'completed'}).status_code==409


def test_finish_requires_stages_and_abort_requires_reason(practice):
    run=start(practice)
    url=f'/api/rehearsal/{run["id"]}/finish'
    assert practice['client'].post(url,json={'expected_version':1,'outcome':'completed'}).status_code==409
    assert practice['client'].post(url,json={'expected_version':1,'outcome':'aborted'}).status_code==422
    response=practice['client'].post(url,json={'expected_version':1,'outcome':'aborted','notes':'Stopping this practice attempt'})
    assert response.status_code==200 and response.json()['status']=='aborted'
    assert practice['client'].get('/api/rehearsal').json()['active'] is None
    assert start(practice)['id']!=run['id']


def test_active_run_cannot_export_an_immutable_finish_snapshot(practice):
    run=start(practice)
    assert practice['client'].get(f'/api/rehearsal/{run["id"]}/export').status_code==409


def test_clock_rollback_rejects_checkpoint_without_audit_or_run_writes(practice):
    run=start(practice)
    practice['clock'][0]-=timedelta(seconds=1)
    response=checkpoint(practice,run)
    assert response.status_code==409 and 'backwards' in response.json()['detail']
    with practice['db']() as connection:
        assert connection.execute('SELECT version FROM rehearsal_runs').fetchone()[0]==1
        assert connection.execute('SELECT COUNT(*) FROM audit').fetchone()[0]==1


def test_clock_rollback_between_milestones_is_not_hidden(practice):
    run=start(practice);practice['clock'][0]+=timedelta(seconds=20)
    run=checkpoint(practice,run).json()
    practice['clock'][0]-=timedelta(seconds=10)
    assert checkpoint(practice,run).status_code==409


def test_active_status_does_not_display_time_before_its_last_checkpoint(practice):
    run=start(practice)
    practice['clock'][0]+=timedelta(seconds=20)
    run=checkpoint(practice,run).json()
    practice['clock'][0]-=timedelta(seconds=10)
    for endpoint in ('/api/rehearsal',f'/api/rehearsal/{run["id"]}'):
        response=practice['client'].get(endpoint)
        assert response.status_code==409 and 'backwards' in response.json()['detail']
    practice['clock'][0]+=timedelta(seconds=11)
    recovered=practice['client'].get('/api/rehearsal').json()['active']
    assert recovered['elapsed_seconds']==21 and recovered['version']==run['version']


def test_snapshot_tampering_fails_instead_of_exporting_unverified_evidence(practice):
    run=start(practice)
    practice['client'].post(f'/api/rehearsal/{run["id"]}/finish',json={'expected_version':1,'outcome':'aborted','notes':'End this test attempt'})
    with practice['db']() as connection:
        connection.execute('UPDATE rehearsal_runs SET snapshot_json=?',('{"changed":true}',))
    assert practice['client'].get(f'/api/rehearsal/{run["id"]}/export').status_code==503


def test_source_paths_outside_workspace_are_not_read(practice):
    root=practice['root'];outside=root.parent/'external_report.json';outside.write_text('not eligible evidence')
    (root/'reports').mkdir()
    try:
        (root/'reports/model_evaluation.json').symlink_to(outside)
    except OSError:
        pytest.skip('Symbolic links are unavailable in this Windows test context')
    run=start(practice)
    source=next(item for item in run['start_evidence'] if item['path']=='reports/model_evaluation.json')
    assert source['status']=='unavailable' and 'escapes' in source['error']


def test_reading_status_does_not_create_approvals_holds_or_driver_actions(practice):
    before=practice['client'].get('/api/rehearsal').json()
    assert before['active'] is None
    with practice['db']() as connection:
        network,_=practice['load'](connection)
        assert sum(item['held'] for item in network['lots'])==1
        assert connection.execute('SELECT COUNT(*) FROM audit').fetchone()[0]==0


def test_bounded_audit_requires_fresh_run_instead_of_silent_missing_evidence(practice,monkeypatch):
    monkeypatch.setattr(rehearsal,'MAX_AUDIT_SNAPSHOT',3)
    run=start(practice);run=checkpoint(practice,run).json();run=checkpoint(practice,run).json()
    actions(practice,'event')
    response=checkpoint(practice,run)
    assert response.status_code==409 and 'bounded evidence window' in response.json()['detail']


def test_offline_evidence_hashes_only_fixtures_never_shared_caches(practice):
    root=practice['root']
    (root/'data/cache').mkdir(parents=True)
    (root/'data/fixtures').mkdir(parents=True)
    (root/'data/cache/probe_openmeteo.json').write_text('new shared cache')
    fixture=root/'data/fixtures/openmeteo.json';fixture.write_text('explicitly dated fixture')
    (root/'data/cache/probe_modot.json').write_text('cache must not fill missing fixture')
    run=start(practice)
    forecast=next(item for item in run['start_evidence'] if item['path']=='data/fixtures/openmeteo.json')
    assert forecast['sha256']==hashlib.sha256(fixture.read_bytes()).hexdigest()
    modot=next(item for item in run['start_evidence'] if item['path']=='data/fixtures/modot.json')
    assert modot['status']=='unavailable'
    assert not any('/cache/' in item['path'] for item in run['start_evidence'])


def driver_stage(practice):
    run=start(practice)
    for _ in range(4):
        run=checkpoint(practice,run,outcome='skipped',notes='Only the coherent driver chain is under test').json()
    return run


@pytest.mark.parametrize('mismatch',['acknowledgment_trip','parked_truck','incident_context'])
def test_driver_coverage_cannot_combine_unrelated_trip_actions(practice,mismatch):
    run=driver_stage(practice)
    actions(practice,'driver_focus','acknowledge','incident')
    with practice['db']() as connection:
        if mismatch=='acknowledgment_trip':
            connection.execute("UPDATE audit SET payload=? WHERE action='acknowledge'",(json.dumps({'shipment_id':'SH04'}),))
        if mismatch=='parked_truck':
            connection.execute("UPDATE audit SET payload=? WHERE action='driver_focus'",(json.dumps({'truck_id':'T04','mode':'parked','parked_confirmation':True}),))
        if mismatch=='incident_context':
            connection.execute('UPDATE incidents SET shipment_id=?',('SH04',))
    response=checkpoint(practice,run)
    assert response.status_code==409 and 'same approved trip' in response.json()['detail']


def test_old_acknowledgment_cannot_cover_a_reapproved_same_id_trip(practice):
    run=driver_stage(practice)
    actions(practice,'driver_focus','acknowledge','approve','incident')
    assert checkpoint(practice,run).status_code==409
    actions(practice,'acknowledge','incident')
    response=checkpoint(practice,run)
    assert response.status_code==200
    proof=response.json()['milestones'][-1]['evidence']
    assert proof['assignment_context']['id']=='SH03' and proof['assignment_context']['truck_id']=='T03'
    assert proof['incident_id'] and proof['reported_network_revision']==0


def test_driver_coverage_requires_acknowledgment_before_report(practice):
    run=driver_stage(practice)
    actions(practice,'driver_focus','incident','acknowledge')
    assert checkpoint(practice,run).status_code==409


@pytest.mark.parametrize('action',['event','reset','lot_hold','freshness_rescue_approve'])
def test_driver_acknowledgment_must_follow_trip_invalidation(practice,action):
    run=driver_stage(practice)
    actions(practice,'driver_focus','acknowledge')
    with practice['db']() as connection:
        payload={'invalidated_shipments':['SH03']} if action=='lot_hold' else {}
        practice['record'](connection,'Dispatcher or simulator',action,payload)
    actions(practice,'incident')
    assert checkpoint(practice,run).status_code==409
    actions(practice,'acknowledge','incident')
    response=checkpoint(practice,run)
    assert response.status_code==200
    proof=response.json()['milestones'][-1]['evidence']
    assert [item['action'] for item in proof['actions']]==['driver_focus','acknowledge','incident']
    assert proof['assignment_context']['id']=='SH03'


def test_unrelated_lot_hold_does_not_invalidate_another_trip_evidence(practice):
    run=driver_stage(practice)
    actions(practice,'driver_focus','acknowledge')
    with practice['db']() as connection:
        practice['record'](connection,'Dispatcher','lot_hold',{'invalidated_shipments':['SH04']})
    actions(practice,'incident')
    assert checkpoint(practice,run).status_code==200
