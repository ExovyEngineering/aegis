"""Event previews calculate the simulator's actual effects without publishing them."""
from contextlib import closing
from copy import deepcopy
import hashlib
import json
import sqlite3

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

import backend.event_impact as impact
from backend.optimization import optimize
from backend.simulation import apply_event, seed_network


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    for key in ('AEGIS_REHEARSAL_ID', 'AEGIS_OFFLINE_DEMO', 'AEGIS_DB_PATH'):
        monkeypatch.delenv(key, raising=False)
    path=tmp_path/'data/operator.sqlite';path.parent.mkdir()
    network=seed_network()
    approved=optimize(network, 'A')['shipments'][:2]
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute('CREATE TABLE state(id INTEGER PRIMARY KEY,payload TEXT,revision INTEGER)')
        connection.execute('CREATE TABLE assignments(id TEXT PRIMARY KEY,payload TEXT,acknowledged INTEGER)')
        connection.execute('CREATE TABLE audit(id INTEGER PRIMARY KEY,payload TEXT)')
        connection.execute('INSERT INTO state VALUES(1,?,7)', (json.dumps(network),))
        connection.executemany('INSERT INTO assignments VALUES(?,?,?)',
                               [(row['id'], json.dumps(row), 0) for row in approved])
    return tmp_path, path, network, approved


def client(path, root):
    app=FastAPI();app.include_router(impact.create_event_impact_router(lambda:path, root=lambda:root))
    return TestClient(app)


def request(event='road_closure', shipment='SH11', revision=7):
    return {'event':event, 'shipment_id':shipment, 'expected_network_revision':revision}


def preview(workspace, **kwargs):
    root,path,_,_=workspace
    with client(path,root) as connection:
        return connection.post('/api/events/preview', json=request(**kwargs))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize('event', sorted(impact.EVENTS))
def test_all_event_previews_match_real_simulator_and_optimizer(workspace,event):
    root,path,before,approved=workspace
    after=deepcopy(before);apply_event(after,event,'SH11')
    response=preview(workspace,event=event)
    assert response.status_code==200,response.text
    result=response.json()
    assert result['simulation'] and result['read_only'] and result['requires_explicit_apply']
    assert not result['operational_state_modified']
    assert len(result['preview_id'])==len(result['snapshot_id'])==64
    assert result['network_revision']==7 and result['shipment_id']=='SH11'
    assert result['assignments']['current_count']==result['assignments']['would_be_invalidated']==len(approved)
    assert result['route_effects']['geometry_changed'] is False
    assert result['route_effects']['distance_changed'] is False
    assert result['route_effects']['stop_order_changed'] is False
    original=next(row for row in before['shipments'] if row['id']=='SH11')
    changed=next(row for row in after['shipments'] if row['id']=='SH11')
    assert result['shipment']['before']['estimated_hours']==original['estimated_hours']
    assert result['shipment']['after']['estimated_hours']==changed['estimated_hours']
    assert result['shipment']['after']['temperature_c']==changed['temperature_c']
    assert len(result['scenarios'])==4
    for comparison in result['scenarios']:
        for key,network in [('before',before),('after',after)]:
            actual=optimize(network, comparison['scenario'])
            shown=comparison[key]
            assert shown['selected_ids']==sorted(row['id'] for row in actual['shipments'])
            assert shown['selected_lots']=={row['id']:row['lot_id'] for row in actual['shipments']}
            assert shown['selected_shipments']==len(actual['shipments'])
            assert shown['constraint_review_passed']==actual['review']['passed']
            assert shown['proposed_hold_lots']==actual['proposed_hold_lots']
            for metric in ('total_logistics_cost','unmet_demand_kg','review_priority_count','food_waste_kg'):
                assert shown[metric]==actual[metric]
        for metric in impact.METRICS:
            assert comparison['delta'][metric]==comparison['after'][metric]-comparison['before'][metric]
        previous=set(comparison['before']['selected_ids']);current=set(comparison['after']['selected_ids'])
        assert comparison['added_shipments']==sorted(current-previous)
        assert comparison['removed_shipments']==sorted(previous-current)


def test_preview_keeps_database_schema_bytes_and_all_assignments(workspace, monkeypatch):
    root,path,_,approved=workspace;before=digest(path)
    real_connect=sqlite3.connect; statements=[];connections=[]
    def connect(*args,**kwargs):
        connections.append((args,kwargs));value=real_connect(*args,**kwargs)
        value.set_trace_callback(statements.append);return value
    monkeypatch.setattr(impact._read_database.__globals__['sqlite3'], 'connect', connect)
    assert preview(workspace,event='refrigeration_fault').status_code==200
    assert digest(path)==before
    assert all('mode=ro' in args[0] and kwargs.get('uri') for args,kwargs in connections)
    forbidden=('CREATE','INSERT','UPDATE','DELETE','DROP','ALTER','REPLACE','COMMIT')
    assert all(not statement.lstrip().upper().startswith(forbidden) for statement in statements)


def test_pure_receipt_preserves_inputs_and_has_stable_hash(workspace):
    _,_,network,approved=workspace
    source=deepcopy(network);assignment_source=deepcopy(approved)
    one=impact.build_event_impact(network,7,approved,'road_closure','SH11')
    two=impact.build_event_impact(network,7,approved,'road_closure','SH11')
    assert one['generated_at']!=two['generated_at']
    assert one['preview_id']==two['preview_id']
    assert one['snapshot_id']==two['snapshot_id']
    assert network==source and approved==assignment_source


def test_transaction_assignment_shapes_match_read_only_reader(workspace):
    root,path,network,approved=workspace
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute('UPDATE assignments SET acknowledged=1')
    parsed=[dict(row,acknowledged=1) for row in approved]
    pure=impact.build_event_impact(network,7,parsed,'delivery_delay','SH11')
    response=preview(workspace,event='delivery_delay').json()
    assert pure['snapshot_id']==response['snapshot_id']
    assert pure['preview_id']==response['preview_id']


@pytest.mark.parametrize('event', ['road_closure','delivery_delay','severe_weather'])
def test_delay_is_fixed_two_hour_planning_change_not_a_new_route(workspace,event):
    result=preview(workspace,event=event).json()
    assert result['route_effects']['duration_change_hours']==2
    assert result['shipment']['after']['estimated_distance_km']==result['shipment']['before']['estimated_distance_km']
    assert {row['field'] for row in result['shipment']['changes']}=={'estimated_hours','deadline_margin_hours'}
    assert not result['resource_effects']
    assert 'not a departure time, arrival timestamp or live ETA' in ' '.join(result['limitations'])


def test_shared_truck_ineligibility_affects_other_candidates_without_changing_their_cargo(workspace):
    result=preview(workspace,event='refrigeration_fault').json()
    resource=result['resource_effects'][0]
    assert resource['kind']=='truck' and resource['id']=='T03'
    assert resource['before'] is True and resource['after'] is False
    assert resource['candidate_shipments']==['SH03','SH11','SH19']
    assert {row['shipment_id'] for row in result['candidate_effects']}=={'SH03','SH11','SH19'}
    assert all('truck ineligible' in row['after_exclusions'] for row in result['candidate_effects'])
    assert result['shipment']['after']['temperature_c']==9
    assert result['shipment']['after']['lot_held'] is False


def test_inventory_shortage_reuses_real_stock_constraints_and_d_allows_other_lots(workspace):
    result=preview(workspace,event='inventory_shortage').json()
    assert result['shipment']['after']['lot_inventory_kg']==0
    assert result['resource_effects'][0]['candidate_shipments']==['SH11','SH23']
    a=next(row for row in result['scenarios'] if row['scenario']=='A')
    d=next(row for row in result['scenarios'] if row['scenario']=='D')
    assert 'SH11' not in a['after']['selected_ids'] and 'SH23' not in a['after']['selected_ids']
    assert 'L11' not in d['after']['selected_lots'].values()
    assert result['route_effects']['duration_change_hours']==0


def test_temperature_excursion_only_proposes_c_holds_and_b_verification(workspace):
    result=preview(workspace,event='temperature_excursion').json()
    c=next(row for row in result['scenarios'] if row['scenario']=='C')
    b=next(row for row in result['scenarios'] if row['scenario']=='B')
    assert c['proposed_hold_lots_added']==['L11']
    assert 'L11' not in c['after']['selected_lots'].values()
    assert result['shipment']['after']['lot_held'] is False
    assert b['after']['constraint_review_passed']
    assert 'Scenario C holds are proposals' in ' '.join(result['limitations'])


def test_repeated_existing_excursion_can_have_no_new_metric_effect(workspace):
    _,path,network,_=workspace
    apply_event(network,'temperature_excursion','SH11')
    with closing(sqlite3.connect(path)) as connection,connection:
        connection.execute('UPDATE state SET payload=?',(json.dumps(network),))
    result=preview(workspace,event='temperature_excursion').json()
    assert result['shipment']['changes']==[]
    assert all(all(value==0 for value in row['delta'].values()) for row in result['scenarios'])


def test_changed_revision_rejects_before_optimizer(workspace,monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('Stale preview must not solve')
    monkeypatch.setattr(impact,'optimize',forbidden)
    response=preview(workspace,revision=6)
    assert response.status_code==409 and 'reload' in response.text


def test_unknown_shipment_returns404(workspace):
    assert preview(workspace,shipment='SH999').status_code==404


@pytest.mark.parametrize('payload', [
    request(event='verified_recall'), request(revision=True), request(revision=-1),
    {**request(),'unexpected':'ignored?'}, {key:value for key,value in request().items() if key!='expected_network_revision'},
])
def test_invalid_preview_requests_do_not_silently_reinterpret_inputs(workspace,payload):
    root,path,_,_=workspace
    with client(path,root) as connection:
        assert connection.post('/api/events/preview',json=payload).status_code==422


def test_no_source_or_model_requests(workspace, monkeypatch):
    import backend.adapters as adapters
    import httpx
    def forbidden(*args,**kwargs):raise AssertionError('Event preview must not query providers or a model')
    monkeypatch.setattr(adapters.CachedHTTP,'get',forbidden)
    monkeypatch.setattr(httpx,'get',forbidden);monkeypatch.setattr(httpx,'post',forbidden)
    assert preview(workspace).status_code==200


def test_missing_database_stays_missing(tmp_path,monkeypatch):
    for key in ('AEGIS_REHEARSAL_ID','AEGIS_OFFLINE_DEMO','AEGIS_DB_PATH'):
        monkeypatch.delenv(key,raising=False)
    path=tmp_path/'missing/operation.sqlite'
    with client(path,tmp_path) as connection:
        response=connection.post('/api/events/preview',json=request())
    assert response.status_code==503 and not path.parent.exists()


@pytest.mark.parametrize('mutation', ['network','assignment'])
def test_state_change_during_calculation_rejects_obsolete_receipt(workspace,monkeypatch,mutation):
    root,path,_,_=workspace;actual=impact.build_event_impact
    def build(*args,**kwargs):
        result=actual(*args,**kwargs)
        with closing(sqlite3.connect(path)) as connection,connection:
            if mutation=='network':connection.execute('UPDATE state SET revision=revision+1')
            else:connection.execute('UPDATE assignments SET acknowledged=1')
        return result
    monkeypatch.setattr(impact,'build_event_impact',build)
    response=preview(workspace)
    assert response.status_code==409 and 'during event comparison' in response.text


def test_oversized_comparison_fails_before_solver(workspace,monkeypatch):
    _,path,network,_=workspace
    for index in range(24,51):
        network['shipments'].append(dict(network['shipments'][0],id=f'EXTRA{index}'))
    with closing(sqlite3.connect(path)) as connection,connection:
        connection.execute('UPDATE state SET payload=?',(json.dumps(network),))
    def forbidden(*args,**kwargs):raise AssertionError('Oversized network must not solve')
    monkeypatch.setattr(impact,'optimize',forbidden)
    response=preview(workspace)
    assert response.status_code==503 and '50 candidates' in response.text


def test_malformed_history_is_explicit_unavailable(workspace):
    _,path,network,_=workspace;network['events']=None
    with closing(sqlite3.connect(path)) as connection,connection:
        connection.execute('UPDATE state SET payload=?',(json.dumps(network),))
    assert preview(workspace).status_code==503


def test_event_identity_is_bound_even_when_two_events_have_same_numeric_effect(workspace):
    _,_,network,approved=workspace
    closure=impact.build_event_impact(network,7,approved,'road_closure','SH11')
    delay=impact.build_event_impact(network,7,approved,'delivery_delay','SH11')
    assert closure['shipment']==delay['shipment']
    assert closure['snapshot_id']==delay['snapshot_id']
    assert closure['preview_id']!=delay['preview_id']


def test_new_deadline_violation_excludes_candidate_from_every_allocation(workspace):
    _,path,network,_=workspace
    next(row for row in network['shipments'] if row['id']=='SH11')['estimated_hours']=4.5
    with closing(sqlite3.connect(path)) as connection,connection:
        connection.execute('UPDATE state SET payload=?',(json.dumps(network),))
    result=preview(workspace,event='road_closure').json()
    assert result['shipment']['before']['deadline_margin_hours']==1.5
    assert result['shipment']['after']['deadline_margin_hours']==-.5
    assert 'delivery deadline exceeded' in result['shipment']['after']['direct_exclusions']
    for scenario in result['scenarios']:
        assert 'SH11' not in scenario['after']['selected_ids']
        assert scenario['after']['constraint_review_passed']


def test_held_recalled_stock_stays_excluded_under_every_preview_response(workspace):
    _,path,network,_=workspace
    network['lots'][1]['recalled']=True
    with closing(sqlite3.connect(path)) as connection,connection:
        connection.execute('UPDATE state SET payload=?',(json.dumps(network),))
    before=digest(path)
    result=preview(workspace,event='temperature_excursion').json()
    for scenario in result['scenarios']:
        assert not {'L01','L02'} & set(scenario['after']['selected_lots'].values())
        assert scenario['after']['constraint_review_passed']
    assert digest(path)==before
