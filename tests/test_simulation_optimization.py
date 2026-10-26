from collections import Counter
from copy import deepcopy

import pytest

from backend.simulation import seed_network, apply_event
from backend.optimization import optimize


def test_seed_reproduces_entities_and_telemetry():
    network = seed_network()
    assert network == seed_network()
    assert network != seed_network(42)
    assert len(network['trucks']) == 8
    assert len(network['shipments']) == 24
    assert len([n for n in network['nodes'] if n['kind'] == 'destination']) == 15
    assert 'SIMULATION' in network['provenance']
    assert all(t['provenance'] == 'simulated cargo temperature' for t in network['telemetry'])


@pytest.mark.parametrize('scenario', ['A', 'B', 'C', 'D'])
def test_all_plans_obey_hard_constraints_without_mutating_network(scenario):
    network = seed_network()
    # Introduce independent violations so every constraint matters.
    network['lots'][1]['recalled'] = True
    network['lots'][2]['eligible'] = False
    network['lots'][3]['inventory_kg'] = 0
    network['lots'][4]['shelf_life_hours'] = 0
    network['trucks'][0]['capacity_kg'] = 500
    network['trucks'][1]['eligible'] = False
    network['nodes'][0]['capacity_kg'] = 1000
    network['shipments'][5]['deadline_hours'] = 0
    before = deepcopy(network)
    result = optimize(network, scenario)
    assert network == before
    assert result['feasible']
    assert result['solver_status'] in {'OPTIMAL', 'FEASIBLE'}
    lots = {l['id']: l for l in network['lots']}
    trucks = {t['id']: t for t in network['trucks']}
    nodes = {n['id']: n for n in network['nodes']}
    totals = {name: Counter() for name in ('lots', 'trucks', 'destinations', 'origins')}
    selected = result['shipments']
    assert len({s['id'] for s in selected}) == len(selected)
    for shipment in selected:
        lot = lots[shipment['lot_id']]
        truck = trucks[shipment['truck_id']]
        assert lot['eligible'] and not lot['held'] and not lot['recalled']
        assert truck['eligible']
        assert shipment['estimated_hours'] <= min(lot['shelf_life_hours'], shipment['deadline_hours'])
        if scenario == 'C':
            assert lot['id'] not in result['proposed_hold_lots']
        for key, field in [('lots', 'lot_id'), ('trucks', 'truck_id'), ('destinations', 'destination'), ('origins', 'origin')]:
            totals[key][shipment[field]] += shipment['quantity_kg']
    assert all(q <= lots[k]['inventory_kg'] for k, q in totals['lots'].items())
    assert all(q <= trucks[k]['capacity_kg'] for k, q in totals['trucks'].items())
    assert all(q <= nodes[k]['demand_kg'] for k, q in totals['destinations'].items())
    assert all(q <= nodes[k]['capacity_kg'] for k, q in totals['origins'].items())
    expected_demand = sum(n.get('demand_kg', 0) for n in network['nodes'])
    assert result['unmet_demand_kg'] == expected_demand - sum(s['quantity_kg'] for s in selected)
    assert result['requires_human_approval'] is True


@pytest.mark.parametrize('scenario', ['A', 'B', 'C', 'D'])
def test_no_dispatch_possible_when_all_lots_held_or_recalled(scenario):
    network = seed_network()
    for i, lot in enumerate(network['lots']):
        lot['held'] = i % 2 == 0
        lot['recalled'] = i % 2 == 1
    result = optimize(network, scenario)
    assert result['feasible']
    assert result['shipments'] == []
    assert result['unmet_demand_kg'] == 7500


def test_scenarios_differ_and_hold_is_only_a_proposal():
    network = seed_network()
    scenarios = {key: optimize(network, key) for key in 'ABCD'}
    assert scenarios['C']['proposed_hold_lots']
    assert scenarios['A']['proposed_hold_lots'] == []
    assert scenarios['B']['total_logistics_cost'] != scenarios['A']['total_logistics_cost']
    assert scenarios['C']['shipments'] != scenarios['A']['shipments']
    assert all(not lot['held'] for lot in network['lots'] if lot['id'] in scenarios['C']['proposed_hold_lots'])


@pytest.mark.parametrize('scenario', ['A', 'B', 'C', 'D'])
def test_chilled_poultry_cannot_be_assigned_to_nonrefrigerated_truck(scenario):
    network = seed_network()
    for truck in network['trucks']:
        truck['refrigerated'] = False
        truck['eligible'] = True
    result = optimize(network, scenario)
    assert result['shipments'] == []
    assert result['unmet_demand_kg'] == 7500


@pytest.mark.parametrize('event', ['road_closure', 'severe_weather', 'delivery_delay', 'refrigeration_fault', 'temperature_excursion', 'inventory_shortage'])
def test_events_are_explicit_simulation(event):
    network = seed_network()
    changed = apply_event(network, event, 'SH03')
    assert changed['events'][-1]['type'] == event
    assert changed['events'][-1]['provenance'] == 'simulated operational event'


def test_unverified_recall_event_rejected_without_mutation():
    network = seed_network()
    before = deepcopy(network)
    with pytest.raises(ValueError, match='traceability'):
        apply_event(network, 'verified_recall', 'SH03')
    assert network == before


def test_unknown_shipment_rejected_without_mutation():
    network = seed_network()
    before = deepcopy(network)
    with pytest.raises(ValueError, match='Unknown shipment'):
        apply_event(network, 'road_closure', 'DOES-NOT-EXIST')
    assert network == before
