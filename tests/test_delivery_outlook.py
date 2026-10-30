"""Actual solver/thermal comparisons over temporary simulated state only."""
from copy import deepcopy
import json
import sqlite3

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest

from backend.cold_chain import project_temperature
import backend.delivery_outlook as outlook
from backend.optimization import optimize
from backend.simulation import apply_event, seed_network


@pytest.fixture
def api(tmp_path,monkeypatch):
    monkeypatch.delenv('AEGIS_REHEARSAL_ID',raising=False)
    monkeypatch.delenv('AEGIS_OFFLINE_DEMO',raising=False)
    database=tmp_path/'network.sqlite'
    with sqlite3.connect(database) as connection:
        connection.execute('CREATE TABLE state(id INTEGER PRIMARY KEY,payload TEXT,revision INTEGER)')
        connection.execute('CREATE TABLE assignments(id TEXT PRIMARY KEY,payload TEXT,acknowledged INTEGER DEFAULT 0)')
        connection.execute('INSERT INTO state VALUES (1,?,3)',(json.dumps(seed_network()),))
    application=FastAPI();application.include_router(outlook.create_delivery_outlook_router(database,root=tmp_path))
    with TestClient(application) as client:yield client,database


def request(client,**changes):
    return client.post('/api/delivery-outlook',json={'expected_network_revision':3,**changes})


def test_default_outlook_matches_real_baseline_and_preserves_inputs():
    network=seed_network();before=deepcopy(network)
    result=outlook.build_delivery_outlook(network,3,[])
    baseline=optimize(network,'A')
    assert network==before
    assert result['baseline']['selected_ids']==sorted(row['id'] for row in baseline['shipments'])
    assert result['summary']['before_unmet_demand_kg']==baseline['unmet_demand_kg']==result['summary']['after_unmet_demand_kg']
    assert result['summary']['unmet_demand_change_kg']==0
    assert result['read_only'] and not result['operational_state_modified']
    assert all(row['delta_vs_baseline']['unmet_demand_kg']==row['summary']['unmet_demand_kg']-baseline['unmet_demand_kg'] for row in result['scenarios'])


def test_delay_and_fault_results_match_each_real_solver_and_independent_review():
    network=seed_network();changed=deepcopy(network)
    for row in changed['shipments']:row['estimated_hours']+=2
    next(row for row in changed['trucks'] if row['id']=='T03')['eligible']=False
    result=outlook.build_delivery_outlook(network,3,[],added_delay_minutes=120,fault_truck_id='T03')
    for comparison in result['scenarios']:
        expected=optimize(changed,comparison['scenario'])
        assert comparison['summary']['selected_ids']==sorted(row['id'] for row in expected['shipments'])
        assert comparison['summary']['selected_lots']=={row['id']:row['lot_id'] for row in expected['shipments']}
        assert comparison['summary']['unmet_demand_kg']==expected['unmet_demand_kg']
        assert comparison['summary']['total_logistics_cost']==expected['total_logistics_cost']
        assert comparison['summary']['constraint_review_passed'] and comparison['summary']['constraint_violations']==0
        assert all(row['truck_id']!='T03' for row in expected['shipments'])
    assert all(row['duration_after_hours']==row['duration_before_hours']+2 for row in result['shipments'])


def test_held_recalled_and_capacity_constraints_still_apply_to_every_scenario():
    network=seed_network()
    network['lots'][1]['recalled']=True
    network['trucks'][3]['capacity_kg']=200
    result=outlook.build_delivery_outlook(network,3,[],added_delay_minutes=60)
    for comparison in result['scenarios']:
        assert not {'L01','L02'} & set(comparison['summary']['selected_lots'].values())
        assert comparison['summary']['constraint_violations']==0
        assert comparison['summary']['constraint_review_passed']


def test_destination_coverage_is_the_actual_one_wave_allocation_not_individual_delivery_chances():
    result=outlook.build_delivery_outlook(seed_network(),3,[],added_delay_minutes=240)
    assert sum(row['unmet_after_kg'] for row in result['destinations'])==result['summary']['after_unmet_demand_kg']
    assert sum(row['supplied_after_kg'] for row in result['destinations'])==result['scenarios'][0]['summary']['supplied_kg']
    assert sum(row['demand_kg'] for row in result['destinations'])==result['summary']['total_demand_kg']
    assert all(row['unmet_after_kg']>=0 for row in result['destinations'])
    assert 'rolling inventory' in ' '.join(result['limitations'])


def test_existing_delays_remain_in_before_and_the_added_assumption_is_not_a_live_eta():
    network=seed_network();apply_event(network,'delivery_delay','SH03')
    original=next(row for row in network['shipments'] if row['id']=='SH03')
    result=outlook.build_delivery_outlook(network,3,[],added_delay_minutes=90)
    row=next(row for row in result['shipments'] if row['id']=='SH03')
    assert row['duration_before_hours']==original['estimated_hours']
    assert row['duration_after_hours']==original['estimated_hours']+1.5
    assert row['misses_deadline']==(row['duration_after_hours']>row['deadline_hours'])
    if row['misses_deadline']:assert 'delivery deadline exceeded' in row['exclusion_reasons']
    assert 'live ETA' in ' '.join(result['limitations'])


def test_temperature_starts_at_current_cargo_and_fault_does_not_invent_immediate_nine_degrees():
    network=seed_network();result=outlook.build_delivery_outlook(network,3,[],fault_truck_id='T01',ambient_temperature_c=35)
    for row in result['shipments']:
        original=next(item for item in network['shipments'] if item['id']==row['id'])
        thermal=row['temperature']
        assert thermal['initial_temperature_c']==original['temperature_c']
        expected=project_temperature(min(row['duration_after_hours'],6)*60,initial_c=original['temperature_c'],ambient_c=35,refrigeration_fault=row['truck_id']=='T01')
        assert thermal['projected_temperature_c']==expected['projection'][-1]['temperature_c']
        assert thermal['max_temperature_c']==expected['max_temperature_c']
        assert thermal['time_above_threshold_minutes']==expected['time_above_threshold_minutes']
    assert next(row for row in result['shipments'] if row['id']=='SH01')['temperature']['initial_temperature_c']!=9


def test_thermal_horizon_is_six_hours_not_a_claim_about_a_later_arrival():
    network=seed_network();network['shipments'][0]['estimated_hours']=9
    result=outlook.build_delivery_outlook(network,3,[],added_delay_minutes=240)
    row=result['shipments'][0]
    assert row['duration_after_hours']==13 and row['temperature']['checked_hours']==6
    assert row['temperature']['checkpoint']=='at_6h_horizon'
    shorter=next(item for item in result['shipments'] if item['duration_after_hours']<6)
    assert shorter['temperature']['checkpoint']=='at_modeled_arrival'
    assert shorter['temperature']['checked_hours']==shorter['duration_after_hours']


def test_projection_review_flag_does_not_create_cargo_observation_or_new_scenario_c_hold():
    network=seed_network();before=deepcopy(network)
    result=outlook.build_delivery_outlook(network,3,[],fault_truck_id='T02',ambient_temperature_c=45)
    assert network==before
    proposed=next(row['summary']['proposed_hold_lots'] for row in result['scenarios'] if row['scenario']=='C')
    assert set(proposed)=={row['lot_id'] for row in network['shipments'] if row['temperature_c']>4}
    assert any(row['temperature']['review_required'] and row['lot_id'] not in proposed for row in result['shipments'] if row['truck_id']=='T02')
    assert 'do not replace current cargo readings' in ' '.join(result['limitations'])


def test_existing_recorded_fault_applies_to_the_shared_truck_but_ineligibility_alone_is_not_a_fault():
    network=seed_network();apply_event(network,'refrigeration_fault','SH03')
    network['trucks'][0]['eligible']=False
    result=outlook.build_delivery_outlook(network,3,[])
    assert all(row['temperature']['refrigeration_fault'] for row in result['shipments'] if row['truck_id']=='T03')
    assert all(not row['temperature']['refrigeration_fault'] for row in result['shipments'] if row['truck_id']=='T01')
    assert all('recorded simulated' in row['temperature']['fault_source'] for row in result['shipments'] if row['truck_id']=='T03')


def test_unrefrigerated_candidate_uses_explicit_passive_assumption_not_an_invented_equipment_fault():
    network=seed_network();network['trucks'][0]['refrigerated']=False
    result=outlook.build_delivery_outlook(network,3,[])
    row=result['shipments'][0]
    assert row['temperature']['thermal_control_unavailable']
    assert not row['temperature']['refrigeration_fault'] and 'no refrigeration' in row['temperature']['fault_source']
    assert 'truck not refrigerated' in row['exclusion_reasons']


def test_stable_snapshot_covers_inputs_and_assumptions_not_generation_time():
    network=seed_network();one=outlook.build_delivery_outlook(network,3,[]);two=outlook.build_delivery_outlook(network,3,[])
    assert one['snapshot_id']==two['snapshot_id']
    delayed=outlook.build_delivery_outlook(network,3,[],added_delay_minutes=30)
    assert one['snapshot_id']!=delayed['snapshot_id'] and one['network_snapshot_id']==delayed['network_snapshot_id']
    network['lots'][1]['held']=True
    assert outlook.build_delivery_outlook(network,3,[])['snapshot_id']!=one['snapshot_id']


def test_api_is_read_only_and_does_not_call_providers_or_models(api,monkeypatch):
    import httpx
    client,database=api;before=database.read_bytes()
    monkeypatch.setattr(httpx,'get',lambda *args,**kwargs:pytest.fail('Outlook requested a provider'))
    # TestClient already exists. A provider/model Client must not be constructed
    # inside the outlook, but the test's existing ASGI transport remains usable.
    monkeypatch.setattr(httpx.Client,'__init__',lambda *args,**kwargs:pytest.fail('Outlook constructed a provider/model client'))
    response=request(client)
    assert response.status_code==200,response.text
    value=response.json()
    assert value['read_only'] and value['simulation'] and not value['operational_state_modified']
    assert value['provenance']['model_kind']=='deterministic planning projection'
    assert 'user planning assumption' in value['provenance']['weather_input']
    assert 'simulated' in value['provenance']['cargo_input']
    assert database.read_bytes()==before
    with sqlite3.connect(database) as connection:
        assert connection.execute('SELECT COUNT(*) FROM assignments').fetchone()[0]==0
        assert connection.execute('SELECT revision FROM state').fetchone()[0]==3


@pytest.mark.parametrize('changes',[
    {'expected_network_revision':True},{'expected_network_revision':'3'},
    {'added_delay_minutes':-1},{'added_delay_minutes':241},{'added_delay_minutes':2.5},{'added_delay_minutes':True},
    {'ambient_temperature_c':46},{'ambient_temperature_c':-21},{'ambient_temperature_c':'30'},{'ambient_temperature_c':True},
    {'ambient_temperature_c':float('inf')},{'approve':True},{'fault_truck_id':'../truck'},
])
def test_request_bounds_reject_before_mutation(api,changes):
    client,database=api;before=database.read_bytes()
    if any(value==float('inf') for value in changes.values()):
        response=client.post('/api/delivery-outlook',content='{"expected_network_revision":3,"ambient_temperature_c":1e999}',headers={'content-type':'application/json'})
    else:response=request(client,**changes)
    assert response.status_code==422 and database.read_bytes()==before


def test_unknown_fault_and_stale_revision_do_not_change_data(api):
    client,database=api;before=database.read_bytes()
    assert request(client,fault_truck_id='T99').status_code==404
    assert request(client,expected_network_revision=2).status_code==409
    assert database.read_bytes()==before


def test_selected_fault_requires_refrigeration_equipment(api):
    client,database=api
    with sqlite3.connect(database) as connection:
        network=json.loads(connection.execute('SELECT payload FROM state').fetchone()[0])
        network['trucks'][0]['refrigerated']=False
        connection.execute('UPDATE state SET payload=?',(json.dumps(network),))
    before=database.read_bytes()
    response=request(client,fault_truck_id='T01')
    assert response.status_code==422 and 'no refrigeration equipment' in response.json()['detail']
    assert database.read_bytes()==before


def test_both_snapshots_use_query_only_read_transactions_without_schema_or_action_sql(api,monkeypatch):
    client,database=api;before=database.read_bytes();real=sqlite3.connect
    opened=[];queries=[]
    def tracked(path,*args,**kwargs):
        opened.append((str(path),kwargs))
        connection=real(path,*args,**kwargs);connection.set_trace_callback(queries.append)
        return connection
    monkeypatch.setattr(sqlite3,'connect',tracked)
    assert request(client).status_code==200
    assert len(opened)==2 and all('mode=ro' in path and kwargs.get('uri') is True for path,kwargs in opened)
    assert sum(query=='PRAGMA query_only=ON' for query in queries)==2
    assert all(not query.lstrip().upper().startswith(('CREATE','INSERT','UPDATE','DELETE','ALTER','REPLACE','COMMIT')) for query in queries)
    assert database.read_bytes()==before


def test_six_hour_arrival_checkpoint_and_zero_horizon_are_explicit():
    network=seed_network();network['shipments'][0]['estimated_hours']=6
    network['shipments'][1]['estimated_hours']=0
    result=outlook.build_delivery_outlook(network,3,[])
    first,second=result['shipments'][:2]
    assert first['temperature']['checkpoint']=='at_modeled_arrival' and first['temperature']['checked_hours']==6
    assert second['temperature']['checked_hours']==0
    assert second['temperature']['projected_temperature_c']==second['temperature']['initial_temperature_c']
    assert not first['misses_deadline']


def test_missing_database_is_not_created(tmp_path):
    path=tmp_path/'absent.sqlite';application=FastAPI()
    application.include_router(outlook.create_delivery_outlook_router(path,root=tmp_path))
    with TestClient(application) as client:response=request(client)
    assert response.status_code==503 and not path.exists()


def test_mid_calculation_network_change_rejects_the_old_result(api,monkeypatch):
    client,database=api;real=outlook.build_delivery_outlook
    def delayed(*args,**kwargs):
        value=real(*args,**kwargs)
        with sqlite3.connect(database) as connection:connection.execute('UPDATE state SET revision=revision+1')
        return value
    monkeypatch.setattr(outlook,'build_delivery_outlook',delayed)
    response=request(client)
    assert response.status_code==409 and 'during calculation' in response.json()['detail']


def test_assignment_change_at_same_network_revision_invalidates_result(api,monkeypatch):
    client,database=api;real=outlook.build_delivery_outlook
    assignment=optimize(seed_network(),'A')['shipments'][0]
    with sqlite3.connect(database) as connection:connection.execute('INSERT INTO assignments VALUES (?,?,0)',(assignment['id'],json.dumps(assignment)))
    def delayed(*args,**kwargs):
        value=real(*args,**kwargs)
        with sqlite3.connect(database) as connection:connection.execute('UPDATE assignments SET acknowledged=1')
        return value
    monkeypatch.setattr(outlook,'build_delivery_outlook',delayed)
    assert request(client).status_code==409


def test_unsupported_or_oversized_simulated_state_is_unavailable():
    network=seed_network();network['events']=[{'type':'unknown','shipment_id':'SH01'}]
    with pytest.raises(HTTPException) as error:outlook.build_delivery_outlook(network,3,[])
    assert error.value.status_code==503
    network=seed_network();source=deepcopy(network['shipments'])
    network['shipments']=[dict(source[index%len(source)],id=f'SH{index+1:03}') for index in range(51)]
    with pytest.raises(HTTPException) as error:outlook.build_delivery_outlook(network,3,[])
    assert error.value.status_code==503 and 'bounded' in error.value.detail


def test_failed_solver_does_not_publish_a_zero_trip_forecast(monkeypatch):
    real=outlook.optimize
    def unavailable(network,scenario):
        value=real(network,scenario);value['feasible']=False;value['solver_status']='UNKNOWN'
        return value
    monkeypatch.setattr(outlook,'optimize',unavailable)
    with pytest.raises(HTTPException) as error:outlook.build_delivery_outlook(seed_network(),3,[])
    assert error.value.status_code==503 and 'no delivery outlook' in error.value.detail


@pytest.mark.parametrize('result_index',range(5),ids=['baseline','after_A','after_B','after_C','after_D'])
@pytest.mark.parametrize('failure',['review_failed','violation_count','review_violation'])
def test_any_failed_independent_allocation_check_abstains_without_writing(api,monkeypatch,result_index,failure):
    client,database=api;before=database.read_bytes();real=outlook.optimize;calls=[]
    def inconsistent(network,scenario):
        value=real(network,scenario)
        if len(calls)==result_index:
            if failure=='review_failed':value['review']['passed']=False
            elif failure=='violation_count':value['constraint_violations']=1
            else:value['review']['violations']=['Explicit unit-test review inconsistency']
        calls.append(scenario)
        return value
    monkeypatch.setattr(outlook,'optimize',inconsistent)
    response=request(client)
    assert response.status_code==503
    assert 'Independent allocation checks' in response.json()['detail']
    assert 'summary' not in response.json() and 'shipments' not in response.json()
    assert calls==['A','A','B','C','D']
    assert database.read_bytes()==before
