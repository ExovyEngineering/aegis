"""The assistant explains captured facts without creating operational state."""
from contextlib import closing
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

import backend.evidence_assistant as assistant
from backend.simulation import seed_network, apply_event
from backend.optimization import optimize


def write_report(root, name, value):
    path=root/'reports'/name;path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value),encoding='utf-8')


def prepare(root):
    """Tiny synthetic report metrics are test inputs, not project performance."""
    path=root/'data/operator.sqlite';path.parent.mkdir(parents=True)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute('CREATE TABLE state(id INTEGER PRIMARY KEY,payload TEXT,revision INTEGER)')
        connection.execute('CREATE TABLE assignments(id TEXT PRIMARY KEY,payload TEXT,acknowledged INTEGER)')
        connection.execute('CREATE TABLE audit(id INTEGER PRIMARY KEY,payload TEXT)')
        connection.execute('INSERT INTO state VALUES(1,?,0)',(json.dumps(seed_network()),))
    write_report(root,'model_evaluation.json',{
        'target':'Salmonella positivity in selected national FSIS raw-poultry primary samples',
        'training_rows':12,'validation_rows':4,
        'baseline':{'n':4,'brier':.12},'logistic_regression':{'n':4,'brier':.13,'roc_auc':.49}})
    write_report(root,'model_timing.json',{'prospective_validation_feasible':False})
    write_report(root,'noaa_coverage.json',{'station_count':2,'observed_station_days':4,
        'expected_station_days':5,'missing_metric_values':1,'generated_at':'2026-10-26T12:00:00Z'})
    write_report(root,'api_status.json',[
        {'id':'openmeteo','success':True,'http_status':200,'tested_at':'2026-10-26T12:00:00Z'},
        {'id':'fsis_recalls','success':False,'http_status':None,'tested_at':'2026-10-26T12:00:01Z','failure':'ConnectError: test-only DNS outage'},
    ])
    # The local scope sources are real checked-in implementation/documentation
    # bytes, copied into the isolated fixture root rather than synthesized claims.
    repository=Path(assistant.__file__).resolve().parents[1]
    for relative in assistant.OUTLOOK_GUIDANCE:
        destination=root/relative;destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_bytes((repository/relative).read_bytes())
    return path


def app_client(path, root):
    app=FastAPI();app.include_router(assistant.create_assistant_router(lambda:path,root=lambda:root))
    return TestClient(app)


@pytest.fixture
def workspace(tmp_path,monkeypatch):
    for key in ('AEGIS_REHEARSAL_ID','AEGIS_OFFLINE_DEMO','AEGIS_DB_PATH'):
        monkeypatch.delenv(key,raising=False)
    return tmp_path,prepare(tmp_path)


def get_context(client):
    response=client.get('/api/assistant/context');assert response.status_code==200,response.text
    return response.json()


def ask(client, context, question_id='scenario_compare', **extra):
    return client.post('/api/assistant/ask',json={'question_id':question_id,
        'expected_snapshot_id':context['snapshot_id'],**extra})


def facts(context):
    return {item['id']:item for item in context['facts']}


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_full_catalog_and_all_answers_are_exact_captured_cited_facts(workspace):
    root,path=workspace
    with app_client(path,root) as client:
        context=get_context(client);lookup=facts(context)
        assert len(context['questions'])==6 and len(context['shipments'])==24
        assert len(context['snapshot_id'])==64 and context['network_revision']==0
        assert context['engine']['mode']=='deterministic' and context['engine']['llm_used'] is False
        for question in context['questions']:
            extra={'shipment_id':'SH03'} if question['id']=='shipment_review' else {}
            response=ask(client,context,question['id'],**extra)
            assert response.status_code==200,response.text
            answer=response.json()
            assert answer['question_id']==question['id'] and answer['shipment_id']==extra.get('shipment_id')
            assert answer['snapshot_id']==context['snapshot_id'] and not answer['operational_state_modified']
            assert answer['answer']['items']
            for item in answer['answer']['items']:
                assert item==lookup[item['id']]
                assert item['citations'] and isinstance(item['uncertainty'],list)
        assert 'not a consumer illness probability' in ' '.join(context['limitations'])


def test_same_inputs_have_stable_hash_despite_generated_time(workspace):
    root,path=workspace
    first=assistant.capture_context(path,root);second=assistant.capture_context(path,root)
    assert first['generated_at']!=second['generated_at']
    assert first['snapshot_id']==second['snapshot_id']


def test_actual_scenario_metrics_are_calculated_from_the_captured_network(workspace):
    root,path=workspace;context=assistant.capture_context(path,root)
    for summary in context['scenarios']:
        actual=optimize(seed_network(),summary['scenario'])
        assert summary['total_logistics_cost']==actual['total_logistics_cost']
        assert summary['unmet_demand_kg']==actual['unmet_demand_kg']
        assert summary['selected_shipments']==len(actual['shipments'])
        assert str(actual['solver_status']) in facts(context)['scenario.'+summary['scenario']]['text']
    assert 'does not automatically reroute' in facts(context)['scenario.D']['text']
    assert 'driver acknowledgment is separate' in facts(context)['scenario.B']['text']


def test_all_routes_preserve_bytes_schema_audit_and_records(workspace,monkeypatch):
    root,path=workspace;before=fingerprint(path)
    real_connect=sqlite3.connect;statements=[];connections=[]
    def connect(*args,**kwargs):
        connections.append((args,kwargs))
        connection=real_connect(*args,**kwargs);connection.set_trace_callback(statements.append)
        return connection
    monkeypatch.setattr(assistant.sqlite3,'connect',connect)
    with app_client(path,root) as client:
        context=get_context(client)
        for question in context['questions']:
            assert ask(client,context,question['id'],**({'shipment_id':'SH03'} if question['id']=='shipment_review' else {})).status_code==200
    assert fingerprint(path)==before
    assert all('mode=ro' in args[0] and kwargs.get('uri') for args,kwargs in connections)
    assert all(not statement.lstrip().upper().startswith(('CREATE','INSERT','UPDATE','DELETE','DROP','ALTER','REPLACE','COMMIT')) for statement in statements)
    assert any(statement=='BEGIN' for statement in statements)


def test_no_network_provider_or_telemetry_generation_calls(workspace,monkeypatch):
    import httpx
    import backend.adapters as adapters
    root,path=workspace
    def forbidden(*args,**kwargs):raise AssertionError('Read-only summaries must not contact providers')
    monkeypatch.setattr(httpx,'get',forbidden)
    monkeypatch.setattr(httpx,'post',forbidden)
    monkeypatch.setattr(adapters.CachedHTTP,'get',forbidden)
    with app_client(path,root) as client:
        context=get_context(client)
        assert ask(client,context).status_code==200


def test_missing_database_does_not_create_directory_file_or_seed(tmp_path,monkeypatch):
    monkeypatch.delenv('AEGIS_OFFLINE_DEMO',raising=False);monkeypatch.delenv('AEGIS_REHEARSAL_ID',raising=False)
    path=tmp_path/'uncreated/operator.sqlite'
    with app_client(path,tmp_path) as client:
        assert client.get('/api/assistant/context').status_code==503
        assert client.post('/api/assistant/ask',json={'question_id':'next_actions'}).status_code==503
    assert not path.parent.exists()


def test_missing_tables_are_explicit_and_not_created(tmp_path):
    path=tmp_path/'empty.sqlite'
    with closing(sqlite3.connect(path)) as connection, connection:connection.execute('CREATE TABLE marker(id INTEGER)')
    before=fingerprint(path)
    with app_client(path,tmp_path) as client:
        response=client.get('/api/assistant/context')
        assert response.status_code==503 and 'OperationalError' in response.json()['detail']
    assert fingerprint(path)==before
    with closing(sqlite3.connect(path)) as connection, connection:
        assert connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()==[('marker',)]


def test_stale_network_revision_is_rejected_without_action(workspace):
    root,path=workspace
    with app_client(path,root) as client:
        context=get_context(client)
        with closing(sqlite3.connect(path)) as connection, connection:connection.execute('UPDATE state SET revision=revision+1')
        before=fingerprint(path)
        response=ask(client,context)
        assert response.status_code==409 and fingerprint(path)==before
        assert get_context(client)['snapshot_id']!=context['snapshot_id']


def test_assignment_change_invalidates_context_even_without_network_revision(workspace):
    root,path=workspace
    assigned=optimize(seed_network(),'A')['shipments'][0]
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute('INSERT INTO assignments VALUES(?,?,0)',(assigned['id'],json.dumps(assigned)))
    with app_client(path,root) as client:
        context=get_context(client)
        with closing(sqlite3.connect(path)) as connection, connection:connection.execute('UPDATE assignments SET acknowledged=1')
        assert ask(client,context,'driver_workflow').status_code==409
        current=get_context(client)
        assert current['network_revision']==context['network_revision']
        assert '1 acknowledged' in facts(current)['driver.assignments']['text']


def test_changed_report_bytes_invalidate_the_context(workspace):
    root,path=workspace
    with app_client(path,root) as client:
        context=get_context(client)
        source=root/'reports/model_evaluation.json'
        source.write_text(source.read_text()+'\n',encoding='utf-8')
        assert ask(client,context,'model_limits').status_code==409
        assert get_context(client)['network_revision']==context['network_revision']


def test_model_metrics_are_measured_not_replaced_with_an_accuracy(workspace):
    root,path=workspace;context=assistant.capture_context(path,root)
    item=facts(context)['model.metrics']
    assert '0.12000000' in item['text'] and '0.13000000' in item['text']
    assert '0.490000' in item['text'] and '4 holdout rows' in item['text']
    assert 'consumer illness' in ' '.join(item['uncertainty'])
    assert 'lower or equal Brier' in facts(context)['model.comparison']['text']
    assert item['citations'][0]['sha256']==fingerprint(root/'reports/model_evaluation.json')
    assert item['citations'][0]['retrieved_at'] is None


@pytest.mark.parametrize('change',[{'target':'Campylobacter in another task'}, {'validation_rows':5},
    {'baseline':{'n':4,'brier':-1}}, {'logistic_regression':{'n':4,'brier':.13,'roc_auc':'invented'}}])
def test_unsupported_metrics_do_not_create_a_performance_claim(workspace,change):
    root,path=workspace;source=root/'reports/model_evaluation.json';model=json.loads(source.read_text());model.update(change);write_report(root,source.name,model)
    context=assistant.capture_context(path,root);lookup=facts(context)
    assert 'model.metrics' not in lookup
    assert 'report.model_evaluation.json.unavailable' in lookup


@pytest.mark.parametrize('content',['{partial','{"baseline":NaN}','{"baseline":{},"baseline":{}}','[]'])
def test_corrupt_or_ambiguous_report_continues_other_evidence(workspace,content):
    root,path=workspace;(root/'reports/model_evaluation.json').write_text(content,encoding='utf-8')
    context=assistant.capture_context(path,root);lookup=facts(context)
    assert 'report.model_evaluation.json.unavailable' in lookup and 'sources.noaa' in lookup
    metadata=next(item for item in context['snapshot_sources'] if item['path']=='reports/model_evaluation.json')
    assert metadata['status']=='unavailable' and metadata['error']


def test_missing_reports_show_unknown_hash_and_no_fabricated_results(workspace):
    root,path=workspace
    for name in assistant.REPORTS:(root/'reports'/name).unlink()
    context=assistant.capture_context(path,root);lookup=facts(context)
    assert 'model.metrics' not in lookup and 'sources.probes' not in lookup and 'sources.noaa' not in lookup
    missing=[item for item in context['facts'] if item['id'].startswith('report.')]
    assert len(missing)==3
    assert all('sha256' not in item['citations'][0] for item in missing)
    assert any('Saved timing audit is unavailable' in message for message in lookup['model.availability']['uncertainty'])


def test_oversized_report_is_bounded_and_explicit(workspace,monkeypatch):
    root,path=workspace;monkeypatch.setattr(assistant,'MAX_REPORT_BYTES',32)
    context=assistant.capture_context(path,root)
    unavailable=[item for item in context['snapshot_sources'] if item.get('error')]
    assert any('exceeds the inspection bound' in item.get('error','') for item in unavailable)
    assert all(item['sha256'] is None and item['bytes'] is None and item['read_prefix_sha256'] for item in unavailable)


def test_saved_probe_failure_and_naive_future_dates_do_not_become_live_success(workspace):
    root,path=workspace
    write_report(root,'api_status.json',[
        {'id':'first','success':True,'http_status':200,'tested_at':'2026-10-28T12:00:00'},
        {'id':'second','success':False,'http_status':None,'tested_at':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()},
    ])
    lookup=facts(assistant.capture_context(path,root))
    assert '1 successful HTTP checks out of 2' in lookup['sources.probes']['text']
    assert 'Recorded failures: second' in lookup['sources.probes']['text']
    assert all(lookup['source.'+name]['citations'][0]['retrieved_at'] is None for name in ('first','second'))
    assert all('not treated as verified' in lookup['source.'+name]['text'] for name in ('first','second'))


def test_inconsistent_probe_success_is_reported_unavailable(workspace):
    root,path=workspace
    write_report(root,'api_status.json',[{'id':'bad','success':True,'http_status':500}])
    lookup=facts(assistant.capture_context(path,root))
    assert 'sources.probes' not in lookup and 'report.api_status.json.unavailable' in lookup


def test_held_recalled_ineligible_candidate_flags_and_excursion_are_review_only(workspace):
    root,path=workspace;network=seed_network();shipment=network['shipments'][2];lot=next(row for row in network['lots'] if row['id']==shipment['lot_id']);lot.update(held=True,recalled=True,eligible=False)
    with closing(sqlite3.connect(path)) as connection, connection:connection.execute('UPDATE state SET payload=?',(json.dumps(network),))
    before=fingerprint(path)
    with app_client(path,root) as client:
        context=get_context(client);response=ask(client,context,'shipment_review',shipment_id=shipment['id'])
        assert response.status_code==200
        text=' '.join(item['text'] for item in response.json()['answer']['items'])
        assert 'lot is held' in text and 'lot is recalled' in text and 'lot is ineligible' in text
        assert 'exceeds the application’s 4°C' in text and 'does not' not in response.json()['answer']['title']
    assert fingerprint(path)==before


def test_alternative_supply_assignment_is_not_confused_with_original_candidate(workspace):
    root,path=workspace;network=seed_network();shipment=network['shipments'][0]
    assigned=dict(shipment,lot_id='L02',verification_required=True)
    with closing(sqlite3.connect(path)) as connection, connection:connection.execute('INSERT INTO assignments VALUES(?,?,0)',(shipment['id'],json.dumps(assigned)))
    context=assistant.capture_context(path,root)
    assert 'candidate lot L01' in facts(context)['shipment.SH01.context']['text']
    assert 'actual captured assignment uses lot L02' in facts(context)['shipment.SH01.assignment']['text']
    assert 'not held' in facts(context)['shipment.SH01.assignment']['text']
    assert '1 assignments still requiring' in facts(context)['driver.assignments']['text']


@pytest.mark.parametrize('body',[
    {'question_id':'invented'}, {'question_id':'shipment_review'},
    {'question_id':'source_coverage','shipment_id':'SH01'},
    {'question_id':'next_actions','expected_snapshot_id':'incorrect'},
    {'question_id':'next_actions','approve':True},
    {'question_id':'shipment_review','shipment_id':'../data/aegis.sqlite'},
])
def test_unsupported_actions_inputs_and_paths_rejected(workspace,body):
    root,path=workspace;before=fingerprint(path)
    with app_client(path,root) as client:assert client.post('/api/assistant/ask',json=body).status_code==422
    assert fingerprint(path)==before


def test_unknown_shipment_not_silently_replaced(workspace):
    root,path=workspace
    with app_client(path,root) as client:
        context=get_context(client)
        assert ask(client,context,'shipment_review',shipment_id='unknown').status_code==404


@pytest.mark.parametrize('mutate',[
    lambda n:n['lots'][0].update(held='false'),
    lambda n:n['shipments'][0].update(lot_id='unknown'),
    lambda n:n['trucks'][0].update(capacity_kg=float('nan')),
    lambda n:n['shipments'].append(n['shipments'][0]),
])
def test_malformed_network_is_not_silently_reinterpreted(workspace,mutate):
    root,path=workspace;network=seed_network();mutate(network)
    with closing(sqlite3.connect(path)) as connection, connection:connection.execute('UPDATE state SET payload=?',(json.dumps(network),))
    before=fingerprint(path)
    with app_client(path,root) as client:
        assert client.get('/api/assistant/context').status_code==503
    assert fingerprint(path)==before


def test_oversized_state_is_rejected_before_parsing_or_optimization(workspace,monkeypatch):
    root,path=workspace;monkeypatch.setattr(assistant,'MAX_STATE_BYTES',16)
    monkeypatch.setattr(assistant,'optimize',lambda *args:pytest.fail('Oversized state was optimized'))
    with app_client(path,root) as client:assert client.get('/api/assistant/context').status_code==503


def test_misconfigured_rehearsal_is_rejected_without_opening_sqlite(workspace,monkeypatch):
    root,path=workspace;monkeypatch.setenv('AEGIS_OFFLINE_DEMO','1')
    monkeypatch.setattr(assistant.sqlite3,'connect',lambda *args,**kwargs:pytest.fail('Invalid runtime opened SQLite'))
    with app_client(path,root) as client:assert client.get('/api/assistant/context').status_code==503


def test_verified_offline_rehearsal_reads_existing_state_without_provider_access(tmp_path,monkeypatch):
    identifier=str(uuid4());original=prepare(tmp_path);destination=tmp_path/f'data/rehearsals/{identifier}.sqlite';destination.parent.mkdir();original.rename(destination)
    monkeypatch.setenv('AEGIS_REHEARSAL_ID',identifier);monkeypatch.setenv('AEGIS_DB_PATH',str(destination));monkeypatch.setenv('AEGIS_OFFLINE_DEMO','1')
    with app_client(destination,tmp_path) as client:
        context=get_context(client)
        assert ask(client,context,'source_coverage').status_code==200


def test_solver_failure_is_explicit_and_does_not_store_a_proposal(workspace,monkeypatch):
    root,path=workspace;before=fingerprint(path)
    def fail(*args):raise ValueError('test-only solver failure')
    monkeypatch.setattr(assistant,'optimize',fail)
    with app_client(path,root) as client:
        response=client.get('/api/assistant/context')
        assert response.status_code==503 and 'test-only solver failure' in response.json()['detail']
    assert fingerprint(path)==before


def test_nonfinite_conversion_of_huge_numeric_metric_is_an_unavailable_report(workspace):
    root,path=workspace;source=root/'reports/model_evaluation.json';model=json.loads(source.read_text())
    model['baseline']['brier']=10**400;write_report(root,source.name,model)
    lookup=facts(assistant.capture_context(path,root))
    assert 'model.metrics' not in lookup and 'report.model_evaluation.json.unavailable' in lookup


def test_derived_context_response_is_bounded_without_mutation(workspace,monkeypatch):
    root,path=workspace;before=fingerprint(path);monkeypatch.setattr(assistant,'MAX_CONTEXT_BYTES',64)
    with app_client(path,root) as client:
        response=client.get('/api/assistant/context')
        assert response.status_code==503 and '2 MiB' in response.json()['detail']
    assert fingerprint(path)==before


def test_helper_answer_and_routing_never_accept_arbitrary_action_names(workspace):
    root,path=workspace;context=assistant.capture_context(path,root)
    with pytest.raises(Exception) as caught:assistant.answer_from_context(context,'approve')
    assert caught.value.status_code==422
    assert all('approve' not in row['view'] and row['view'] in {'command','dispatch','science','evidence','roads','drive','brief'}
               for question in context['questions']
               for row in assistant.answer_from_context(context,question['id'],'SH01' if question['id']=='shipment_review' else None)['suggested_views'])


def test_delivery_outlook_scope_is_one_exact_cited_fact_shared_by_relevant_answers(workspace):
    root,path=workspace
    with app_client(path,root) as client:
        context=get_context(client);lookup=facts(context);scope=lookup['outlook.scope']
        assert scope['category']=='next_actions'
        assert scope['provenance']=='server-authored scope guidance; captured local documentation and implementation bytes'
        assert {citation['path'] for citation in scope['citations']}==set(assistant.OUTLOOK_GUIDANCE)
        for citation in scope['citations']:
            assert citation['sha256']==fingerprint(root/citation['path'])
            assert citation['retrieved_at'] is None
            source=next(item for item in context['snapshot_sources'] if item['path']==citation['path'])
            assert source['status']=='captured' and source['sha256']==citation['sha256']
            assert source['bytes']==(root/citation['path']).stat().st_size and source['error'] is None
        assert 'every simulated candidate trip' in scope['text']
        assert 'newly computed scenario-A allocation' in scope['text']
        assert 'not the approved driver-assignment list' in scope['text']
        assert 'illustrative projections capped at six hours' in scope['text']
        assert 'not a learned disruption forecast or live ETA' in scope['text']
        assert 'changes no route, inventory, hold or driver assignment' in scope['text']
        assert 'human approval' in scope['text']
        assert 'measured' not in scope['text'] and 'kg' not in scope['text'] and '%' not in scope['text']
        for question_id in ('scenario_compare','model_limits','next_actions'):
            answer=ask(client,context,question_id).json()
            assert answer['snapshot_id']==context['snapshot_id']
            assert next(item for item in answer['answer']['items'] if item['id']=='outlook.scope')==scope
            assert all(item==lookup[item['id']] for item in answer['answer']['items'])
            assert 'delivery' in answer['answer']['summary'].lower()
            assert any(row['view']=='command' and 'delivery' in row['label'].lower() for row in answer['suggested_views'])
        for question_id,extra in [('source_coverage',{}),('driver_workflow',{}),('shipment_review',{'shipment_id':'SH02'})]:
            answer=ask(client,context,question_id,**extra).json()
            assert all(item['id']!='outlook.scope' for item in answer['answer']['items'])
        model_answer=ask(client,context,'model_limits').json()
        assert next(item for item in model_answer['answer']['items'] if item['id']=='model.metrics')==lookup['model.metrics']
        assert 'FSIS' in ' '.join(scope['uncertainty']) and 'CDC BEAM' in ' '.join(scope['uncertainty'])
        assert 'NORS' in ' '.join(scope['uncertainty']) and 'consumer illness' in ' '.join(scope['uncertainty'])


@pytest.mark.parametrize('relative',assistant.OUTLOOK_GUIDANCE)
def test_changed_delivery_scope_source_invalidates_the_captured_answer(workspace,relative):
    root,path=workspace;before=fingerprint(path)
    with app_client(path,root) as client:
        context=get_context(client);source=root/relative
        source.write_bytes(source.read_bytes()+b'\n')
        response=ask(client,context,'model_limits')
        assert response.status_code==409
        current=get_context(client)
        assert current['snapshot_id']!=context['snapshot_id']
        assert current['network_revision']==context['network_revision']
        citation=next(item for item in facts(current)['outlook.scope']['citations'] if item['path']==relative)
        assert citation['sha256']==fingerprint(source)
    assert fingerprint(path)==before


@pytest.mark.parametrize('failure',['missing','invalid_utf8','empty','oversized'])
def test_unavailable_scope_source_is_explicit_and_does_not_hide_other_evidence(workspace,monkeypatch,failure):
    root,path=workspace;source=root/assistant.OUTLOOK_GUIDANCE[0]
    if failure=='missing':source.unlink()
    elif failure=='invalid_utf8':source.write_bytes(b'\xff\xfe\x00')
    elif failure=='empty':source.write_bytes(b' \n')
    else:monkeypatch.setattr(assistant,'MAX_GUIDANCE_BYTES',32)
    before=fingerprint(path);context=assistant.capture_context(path,root);lookup=facts(context)
    assert 'outlook.scope' not in lookup and 'outlook.unavailable' in lookup
    assert 'model.metrics' in lookup and 'scenario.A' in lookup and 'sources.noaa' in lookup
    unavailable=lookup['outlook.unavailable']
    assert unavailable['provenance']=='recorded local guidance failure'
    metadata=next(item for item in context['snapshot_sources'] if item['path']==assistant.OUTLOOK_GUIDANCE[0])
    assert metadata['status']=='unavailable' and metadata['error']
    citation=next(item for item in unavailable['citations'] if item['path']==metadata['path'])
    if failure in {'missing','oversized'}:
        assert 'sha256' not in citation and metadata['sha256'] is None
    else:assert citation['sha256']==fingerprint(source)
    if failure=='oversized':
        assert metadata['bytes_read']==33 and metadata['read_prefix_sha256']==hashlib.sha256(source.read_bytes()[:33]).hexdigest()
    for question_id in ('scenario_compare','model_limits','next_actions'):
        answer=assistant.answer_from_context(context,question_id)
        assert next(item for item in answer['answer']['items'] if item['id']=='outlook.unavailable')==unavailable
        assert all(item['id']!='outlook.scope' for item in answer['answer']['items'])
    assert fingerprint(path)==before


def test_outlook_guidance_reads_neither_compute_an_outlook_nor_contact_providers_or_write_state(workspace,monkeypatch):
    import httpx
    import backend.adapters as adapters
    import backend.cold_chain as cold_chain
    import backend.delivery_outlook as delivery_outlook
    root,path=workspace;before=fingerprint(path)
    guidance_before={relative:fingerprint(root/relative) for relative in assistant.OUTLOOK_GUIDANCE}
    def forbidden(*args,**kwargs):raise AssertionError('Scope guidance cannot execute a projection, provider or model call')
    monkeypatch.setattr(httpx,'get',forbidden);monkeypatch.setattr(httpx,'post',forbidden)
    monkeypatch.setattr(adapters.CachedHTTP,'get',forbidden)
    monkeypatch.setattr(cold_chain,'project_temperature',forbidden)
    monkeypatch.setattr(delivery_outlook,'build_delivery_outlook',forbidden)
    with app_client(path,root) as client:
        monkeypatch.setattr(httpx.Client,'__init__',forbidden)
        context=get_context(client)
        for question_id in ('scenario_compare','model_limits','next_actions'):
            response=ask(client,context,question_id)
            assert response.status_code==200
            assert response.json()['operational_state_modified'] is False
            assert response.json()['engine']['mode']=='deterministic' and response.json()['engine']['llm_used'] is False
    assert fingerprint(path)==before
    assert guidance_before=={relative:fingerprint(root/relative) for relative in assistant.OUTLOOK_GUIDANCE}
    with closing(sqlite3.connect(path)) as connection:
        assert connection.execute('SELECT COUNT(*) FROM audit').fetchone()[0]==0
        assert connection.execute('SELECT COUNT(*) FROM assignments').fetchone()[0]==0
