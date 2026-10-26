import copy,json
import pytest
from backend.route_lab import plan_routes,operation_preset
from backend.cold_chain import project_temperature

@pytest.mark.parametrize('preset',['farm','regional'])
def test_routing_visits_once_returns_to_origin_and_enforces_constraints(preset):
    plan=plan_routes(preset=preset)
    assert plan['feasible'] and plan['summary']['constraint_violations']==0
    assert plan['mutates_assignments'] is False
    data=plan['preset'];nodes={n['id']:n for n in data['nodes']};stops={s['id']:s for s in data['stops']}
    visited=[];loads={o['id']:0 for o in data['origins']}
    for route in plan['routes']:
        assert route['fallback'] and 'estimated' in route['routing_provenance'] and 'road geometry' in route['routing_provenance']
        assert route['geometry']['coordinates'][0]==route['geometry']['coordinates'][-1]==nodes[route['origin_id']]['coordinates']
        assert route['load_kg']<=route['capacity_kg']
        assert route['duration_seconds']<=8*3600
        for arrival in route['arrivals']:
            stop=stops[arrival['stop_id']];assert not stop['held'] and not stop['recalled'] and stop['eligible']
            assert arrival['arrival_minutes']+arrival['service_minutes']<=stop['deadline_hours']*60+.01
        loads[route['origin_id']]+=route['load_kg'];visited+=route['stop_ids']
    assert len(visited)==len(set(visited))
    assert set(visited)|set(plan['summary']['unserved_stops'])==set(stops)
    assert all(loads[o['id']]<=o['inventory_kg'] for o in data['origins'])

def test_short_capacity_reports_unmet_demand_instead_of_overloading():
    plan=plan_routes(truck_count=1,truck_capacity_kg=500)
    assert sum(len(r['stop_ids']) for r in plan['routes'])<=1
    assert plan['summary']['unmet_demand_kg']>=2100
    assert plan['summary']['constraint_violations']==0

def test_origin_stock_and_truck_refrigeration_cannot_be_overridden():
    operation=operation_preset('regional')
    for origin in operation['origins']:origin['inventory_kg']=0
    assert not plan_routes(operation=operation)['routes']
    operation=operation_preset('farm')
    for truck in operation['trucks']:truck['refrigerated']=False
    assert not plan_routes(operation=operation)['routes']

def test_recalled_and_ineligible_delivery_are_excluded_even_with_capacity():
    operation=operation_preset('farm')
    operation['stops'][0]['recalled']=True;operation['stops'][1]['eligible']=False
    operation['nodes']=operation['origins']+operation['stops']
    plan=plan_routes(operation=operation)
    assert {'FD01','FD02','FD08'}<=set(plan['summary']['unserved_stops'])

def test_routing_plan_is_deterministic_and_input_is_unchanged():
    operation=operation_preset('farm');original=copy.deepcopy(operation)
    first=plan_routes(operation=operation);second=plan_routes(operation=operation)
    assert first==second
    assert operation==original

def test_road_delay_changes_schedule_and_thermal_exposure():
    normal=plan_routes();delayed=plan_routes(delay_minutes=120,refrigeration_fault=True)
    assert delayed['routes']
    assert all(r['arrivals'][0]['arrival_minutes']>=120 for r in delayed['routes'])
    assert all(r['cold_chain']['status']=='review' for r in delayed['routes'])
    assert all(r['cold_chain']['max_temperature_c']>20 for r in delayed['routes'])

def test_normal_refrigeration_and_fault_have_distinct_unvalidated_projections():
    healthy=project_temperature(120,ambient_c=35)
    fault=project_temperature(120,ambient_c=35,refrigeration_fault=True)
    assert healthy['status']=='within_assumed_target' and healthy['time_above_threshold_minutes']==0
    assert fault['status']=='review' and fault['time_above_threshold_minutes']>100
    assert fault['max_temperature_c']>20
    assert 'not observed sensor data' in fault['provenance']
    assert all(p['lower_c']<=p['temperature_c']<=p['upper_c'] for p in fault['projection'])
    assert any('not statistical confidence' in x for x in fault['assumptions'])

def test_existing_excursion_does_not_disappear_from_projection():
    projection=project_temperature(60,initial_c=9)
    assert projection['status']=='review' and projection['time_above_threshold_minutes']>0
    assert projection['projection'][0]['temperature_c']==9

@pytest.mark.parametrize('duration',[-1,1441,float('nan')])
def test_invalid_thermal_horizons_fail(duration):
    with pytest.raises(ValueError):project_temperature(duration)

def test_route_lab_never_modifies_dispatcher_state(client):
    before=client.get('/api/network').json()
    response=client.post('/api/route-lab',json={'preset':'farm','routing':'estimated'})
    assert response.status_code==200 and response.json()['routes']
    assert client.get('/api/driver').json()==[]
    assert client.get('/api/network').json()==before
    assert client.post('/api/route-lab',json={'preset':'farm','truck_count':0}).status_code==422
    assert client.post('/api/route-lab',json={'preset':'farm','routing':'truck-safe'}).status_code==422
    assert client.get('/api/shipments/SH11/exposure').json()['shipment_id']=='SH11'
    assert client.get('/api/shipments/missing/exposure').status_code==404
