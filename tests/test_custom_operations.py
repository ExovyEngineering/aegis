import copy

import pytest
from pydantic import ValidationError

from backend.custom_operations import CustomOperation, build_operation
from backend.route_lab import plan_routes


@pytest.fixture
def custom_input():
    return {
        'name': 'Farm route experiment',
        'origins': [{'id': 'FARM1', 'name': 'Planning origin', 'coordinates': [-92.4, 39.0], 'inventory_kg': 1200}],
        'stops': [
            {'id': 'STOP1', 'name': 'Planning stop one', 'coordinates': [-92.38, 39.02], 'demand_kg': 300},
            {'id': 'STOP2', 'name': 'Planning stop two', 'coordinates': [-92.39, 39.01], 'demand_kg': 300},
        ],
        'trucks': [{'id': 'TRUCK1', 'origin_id': 'FARM1', 'capacity_kg': 1000}],
    }


def test_custom_inputs_become_labeled_planning_operation_without_mutating_input(custom_input):
    original = copy.deepcopy(custom_input)
    operation = build_operation(custom_input)
    assert custom_input == original
    assert operation['id'] == 'custom' and operation['simulation'] is True
    assert operation['nodes'] == operation['origins'] + operation['stops']
    assert operation['stops'][0]['lot_id'] == 'PLAN-STOP1'
    assert 'not verified' in operation['provenance']
    assert operation == CustomOperation.model_validate(custom_input).build_operation()
    plan = plan_routes(operation=operation)
    assert plan['feasible'] and plan['routes']
    assert not plan['summary']['unmet_demand_kg']
    assert plan['mutates_assignments'] is False
    assert plan['provenance'] == operation['provenance']
    assert any('user-entered planning inputs' in value for value in plan['limitations'])
    assert all(route['load_kg'] <= 1000 for route in plan['routes'])


@pytest.mark.parametrize('coordinates', [[181, 39], [-92, 91], [-92, float('nan')], [-92, float('inf')], [True, 39], ['-92', 39], [-92], [-92, 39, 10]])
def test_coordinate_errors_are_not_silently_coerced(custom_input, coordinates):
    custom_input['origins'][0]['coordinates'] = coordinates
    with pytest.raises(ValidationError):
        build_operation(custom_input)


@pytest.mark.parametrize('field,value', [('inventory_kg', -1), ('inventory_kg', 1.5), ('inventory_kg', True)])
def test_origin_stock_must_be_nonnegative_whole_kilograms(custom_input, field, value):
    custom_input['origins'][0][field] = value
    with pytest.raises(ValidationError):
        build_operation(custom_input)


@pytest.mark.parametrize('field,value', [('demand_kg', 0), ('deadline_hours', 0), ('deadline_hours', float('inf')), ('shelf_life_hours', 0), ('held', 'false')])
def test_delivery_values_and_flags_are_explicit(custom_input, field, value):
    custom_input['stops'][0][field] = value
    with pytest.raises(ValidationError):
        build_operation(custom_input)


@pytest.mark.parametrize('change', ['duplicate_stop', 'cross_group_id', 'unknown_origin', 'invalid_id', 'extra_field', 'shared_lot'])
def test_ambiguous_custom_entities_are_rejected(custom_input, change):
    if change == 'duplicate_stop':
        custom_input['stops'][1]['id'] = 'STOP1'
    elif change == 'cross_group_id':
        custom_input['trucks'][0]['id'] = 'STOP1'
    elif change == 'unknown_origin':
        custom_input['trucks'][0]['origin_id'] = 'UNKNOWN'
    elif change == 'invalid_id':
        custom_input['origins'][0]['id'] = '../../file'
    elif change == 'extra_field':
        custom_input['origins'][0]['remote_file'] = 'https://example.test/data'
    else:
        for stop in custom_input['stops']:
            stop['lot_id'] = 'SAME_LOT'
        custom_input['stops'][0]['held'] = True
    with pytest.raises(ValidationError):
        build_operation(custom_input)


@pytest.mark.parametrize('group,count', [('origins', 4), ('stops', 21), ('trucks', 11)])
def test_custom_problem_size_is_bounded(custom_input, group, count):
    custom_input[group] = [copy.deepcopy(custom_input[group][0]) for _ in range(count)]
    with pytest.raises(ValidationError):
        build_operation(custom_input)


@pytest.mark.parametrize('flag', ['held', 'recalled', 'ineligible'])
def test_custom_hold_recall_and_eligibility_exclusions_are_hard_constraints(custom_input, flag):
    custom_input['stops'][0][flag if flag != 'ineligible' else 'eligible'] = flag != 'ineligible'
    plan = plan_routes(operation=build_operation(custom_input))
    assert 'STOP1' in plan['summary']['unserved_stops']
    assert all('STOP1' not in route['stop_ids'] for route in plan['routes'])


def test_custom_stock_capacity_and_nonrefrigerated_vehicle_are_enforced(custom_input):
    custom_input['origins'][0]['inventory_kg'] = 300
    plan = plan_routes(operation=build_operation(custom_input))
    assert sum(route['load_kg'] for route in plan['routes']) <= 300
    assert plan['summary']['unmet_demand_kg'] >= 300
    custom_input['trucks'][0]['capacity_kg'] = 200
    assert not plan_routes(operation=build_operation(custom_input))['routes']
    custom_input['trucks'][0]['capacity_kg'] = 1000
    custom_input['trucks'][0]['refrigerated'] = False
    assert not plan_routes(operation=build_operation(custom_input))['routes']


@pytest.mark.parametrize('constraint', ['deadline_hours', 'shelf_life_hours'])
def test_service_must_finish_before_custom_deadline_or_shelf_life(custom_input, constraint):
    # Coincident coordinates isolate service time: zero driving cannot excuse a
    # ten-minute service that exceeds five minutes of life/deadline.
    for stop in custom_input['stops']:
        stop['coordinates'] = custom_input['origins'][0]['coordinates'][:]
        stop[constraint] = 5 / 60
    plan = plan_routes(operation=build_operation(custom_input))
    assert not plan['routes']
    assert plan['summary']['unmet_demand_kg'] == 600


def test_custom_multi_origin_vehicle_origins_and_stock_remain_separate(custom_input):
    custom_input['origins'].append({'id': 'DEPOT2', 'name': 'Second planning depot', 'kind': 'dc', 'coordinates': [-90.20, 38.63], 'inventory_kg': 300})
    custom_input['origins'][0]['inventory_kg'] = 300
    custom_input['stops'][1]['coordinates'] = [-90.21, 38.64]
    custom_input['trucks'].append({'id': 'TRUCK2', 'origin_id': 'DEPOT2', 'capacity_kg': 500})
    plan = plan_routes(operation=build_operation(custom_input))
    assert {route['origin_id'] for route in plan['routes']} == {'FARM1', 'DEPOT2'}
    origins = {origin['id']: origin for origin in plan['preset']['origins']}
    for route in plan['routes']:
        assert route['geometry']['coordinates'][0] == route['geometry']['coordinates'][-1] == origins[route['origin_id']]['coordinates']
        assert route['load_kg'] <= origins[route['origin_id']]['inventory_kg']
