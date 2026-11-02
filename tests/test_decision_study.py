"""Scientific policy comparisons use feasible allocations, not fabricated gains."""
from copy import deepcopy
import csv
import hashlib
import itertools
import json
import sqlite3

import pytest

from backend.decision_study import build_decision_study, compare_policy
from backend.plan_review import review_plan
from scripts.run_decision_study import read_risk_context, run


def small_network():
    nodes = [{'id': 'DC', 'kind': 'dc', 'capacity_kg': 1000},
             {'id': 'SUP', 'kind': 'supplier', 'capacity_kg': 1000},
             {'id': 'large', 'kind': 'destination', 'demand_kg': 1000},
             {'id': 'small', 'kind': 'destination', 'demand_kg': 200},
             {'id': 'medium', 'kind': 'destination', 'demand_kg': 400}]
    lots = [{'id': identity, 'supplier_id': 'SUP', 'inventory_kg': 400,
             'held': False, 'recalled': False, 'eligible': True, 'shelf_life_hours': 24,
             'quality_remaining_hours': clock, 'quality_coverage_complete': True}
            for identity, clock in [('long', 12), ('short', 2)]]
    trucks = [{'id': identity, 'capacity_kg': 400, 'eligible': True, 'refrigerated': True} for identity in ('T1', 'T2')]
    shipments = []
    for index, (destination, quantity, truck, lot) in enumerate([
            ('large', 400, 'T1', 'long'), ('small', 200, 'T1', 'short'),
            ('medium', 400, 'T2', 'short'), ('medium', 400, 'T2', 'long')]):
        shipments.append({'id': f'S{index}', 'origin': 'DC', 'destination': destination,
                          'quantity_kg': quantity, 'truck_id': truck, 'lot_id': lot,
                          'estimated_hours': 1, 'deadline_hours': 6,
                          'estimated_distance_km': 10 + index, 'temperature_c': 8 if index == 0 else 2})
    return {'nodes': nodes, 'lots': lots, 'trucks': trucks, 'shipments': shipments, 'seed': 1}


def independent_objective(network, selected, policy):
    """Small exhaustive reference expresses policy tradeoffs without CP-SAT."""
    supplied = {row['id']: sum(s['quantity_kg'] for s in selected if s['destination'] == row['id'])
                for row in network['nodes'] if row['kind'] == 'destination'}
    fair_credit = sum(min(500, supplied[row['id']] * 1000 // row['demand_kg'])
                      for row in network['nodes'] if row['kind'] == 'destination' and row['demand_kg'])
    short_ids = {row['id'] for row in network['lots'] if row['quality_remaining_hours'] <= 6}
    score = (sum(row['quantity_kg'] for row in selected),
             sum(row['quantity_kg'] for row in selected if row['lot_id'] in short_ids),
             -sum(round(row['estimated_distance_km'] * 1000) for row in selected))
    return (fair_credit,) + score if policy == 'model_balanced' else score


@pytest.mark.parametrize('policy', ['model_volume', 'model_balanced'])
def test_optimized_policy_matches_exhaustive_feasible_reference(policy):
    network = small_network()
    candidates = network['shipments']
    alternatives = [[row for flag, row in zip(flags, candidates) if flag]
                    for flags in itertools.product((False, True), repeat=len(candidates))]
    feasible = [rows for rows in alternatives if review_plan(network, rows)['passed']]
    expected = max(independent_objective(network, rows, policy) for rows in feasible)
    actual = compare_policy(network, policy)
    selected = [row for row in candidates if row['id'] in actual['selected_shipment_ids']]
    assert independent_objective(network, selected, policy) == expected
    assert all(stage['solver_status'] == 'OPTIMAL' for stage in actual['objective_stages'])


def test_balancing_destination_service_exposes_a_real_volume_tradeoff():
    network = small_network()
    volume = compare_policy(network, 'model_volume')
    balanced = compare_policy(network, 'model_balanced')
    assert volume['metrics']['distributed_kg'] == 800
    assert balanced['metrics']['distributed_kg'] == 600
    assert balanced['metrics']['mean_capped_service_fraction'] > volume['metrics']['mean_capped_service_fraction']
    assert balanced['metrics']['short_quality_clock_delivered_kg'] < volume['metrics']['short_quality_clock_delivered_kg']
    assert {row['destination_id']: row['distributed_kg'] for row in balanced['demand_service']} == {'large': 0, 'small': 200, 'medium': 400}


def test_quality_guidance_prioritizes_short_clock_without_claiming_food_safety():
    network = small_network()
    network['shipments'] = [deepcopy(network['shipments'][0]), deepcopy(network['shipments'][1])]
    network['shipments'][1].update(quantity_kg=400, destination='large')
    baseline = compare_policy(network, 'status_quo')
    guided = compare_policy(network, 'model_volume')
    assert baseline['selected_shipment_ids'] == ['S0']
    assert guided['selected_shipment_ids'] == ['S1']
    assert guided['metrics']['distributed_kg'] == baseline['metrics']['distributed_kg'] == 400
    assert guided['metrics']['projected_quality_budget_exposure_kg'] == 0
    assert baseline['metrics']['projected_quality_budget_exposure_kg'] == 400
    assert guided['priority_diagnostics']['fsis_individual_risk_ranking_available'] is False
    assert 'not a contamination ranking' in guided['priority_diagnostics']['interpretation']


@pytest.mark.parametrize('policy', ['status_quo', 'model_volume', 'model_balanced'])
def test_every_policy_is_read_only_and_held_or_recalled_stock_never_dispatches(policy):
    network = small_network()
    network['lots'][0]['held'] = True
    network['lots'][1]['recalled'] = True
    before = deepcopy(network)
    result = compare_policy(network, policy)
    assert network == before
    assert result['selected_shipment_ids'] == []
    assert result['metrics']['unmet_demand_kg'] == 1600
    assert result['metrics']['retained_inventory_kg'] == 800
    assert result['metrics']['held_or_recalled_inventory_excluded_kg'] == 800
    assert result['metrics']['held_or_recalled_dispatched_kg'] == 0
    assert result['constraint_review']['passed']
    assert result['requires_human_approval'] and not result['operator_state_modified']
    assert all(action['requires_human_approval'] for action in result['proposed_actions'])


@pytest.mark.parametrize('change', ['expired', 'deadline', 'not_refrigerated', 'unscored', 'receiving_buffer'])
def test_shared_quality_and_operational_constraints_apply_to_all_policies(change):
    network = small_network()
    if change == 'expired':
        for lot in network['lots']: lot['shelf_life_hours'] = .5
    elif change == 'deadline':
        for row in network['shipments']: row['deadline_hours'] = .5
    elif change == 'not_refrigerated':
        for truck in network['trucks']: truck['refrigerated'] = False
    elif change == 'unscored':
        for lot in network['lots']: lot['quality_coverage_complete'] = False
    else:
        for row in network['shipments']: row['quality_receiving_buffer_hours'] = 20
    for policy in ('status_quo', 'model_volume', 'model_balanced'):
        result = compare_policy(network, policy)
        assert result['selected_shipment_ids'] == []
        assert all(row['reasons'] for row in result['hard_exclusions'])
        assert result['constraint_review']['passed']


def test_three_scenario_results_balance_food_volume_service_and_review_workload():
    study = build_decision_study({'status': 'historical context', 'historical_prevalence': .09})
    assert len(study['scenarios']) == 3 and study['simulation']
    for scenario in study['scenarios']:
        assert len(scenario['policies']) == 3
        for policy in scenario['policies']:
            m = policy['metrics']
            demand = sum(row['demand_kg'] for row in policy['demand_service'])
            assert m['distributed_kg'] + m['unmet_demand_kg'] == demand
            assert sum(row['distributed_kg'] for row in policy['demand_service']) == m['distributed_kg']
            assert m['held_or_recalled_dispatched_kg'] == m['constraint_violations'] == 0
            assert policy['constraint_review']['passed']
            assert not policy['priority_diagnostics']['need_weighting_available']
    scarcity = study['scenarios'][1]['policies']
    rule, volume, balanced = [row['metrics'] for row in scarcity]
    assert volume['distributed_kg'] > rule['distributed_kg']
    assert balanced['destinations_served'] > volume['destinations_served']
    assert balanced['projected_quality_budget_exposure_kg'] > volume['projected_quality_budget_exposure_kg']
    assert balanced['total_estimated_shipment_hours'] > volume['total_estimated_shipment_hours']
    assert study['risk_context']['used_for_allocation'] is False
    assert study['risk_context']['individual_shipment_linkage'] is False
    assert 'unavailable' in study['unresolved_risk_action_link']


def test_risk_context_cannot_fabricate_a_prior_when_source_missing_or_invalid(tmp_path):
    assert read_risk_context(tmp_path)['historical_prevalence'] is None
    (tmp_path / 'reports').mkdir()
    path = tmp_path / 'reports/model_evaluation.json'
    for invalid in (True, -1, 2, None, '0.1'):
        path.write_text(json.dumps({'historical_prevalence': invalid}), encoding='utf-8')
        assert read_risk_context(tmp_path)['status'] == 'unavailable'
    raw = json.dumps({'historical_prevalence': .09, 'target': 'selected sample'}).encode()
    path.write_bytes(raw)
    context = read_risk_context(tmp_path)
    assert context['historical_prevalence'] == .09
    assert context['source_sha256'] == hashlib.sha256(raw).hexdigest()


def test_report_reproduces_with_no_database_access(tmp_path, monkeypatch):
    def reject_database(*args, **kwargs):
        raise AssertionError('Decision study must not access an operational database')
    monkeypatch.setattr(sqlite3, 'connect', reject_database)
    first = run(tmp_path)
    first_bytes = (tmp_path / 'decision_study.json').read_bytes()
    second = run(tmp_path)
    assert first == second
    assert (tmp_path / 'decision_study.json').read_bytes() == first_bytes
    with (tmp_path / 'decision_study.csv').open(newline='', encoding='utf-8') as stream:
        assert len(list(csv.DictReader(stream))) == 9
    with (tmp_path / 'decision_study_demand_service.csv').open(newline='', encoding='utf-8') as stream:
        assert len(list(csv.DictReader(stream))) == 135
    assert 'not pathogen-risk reduction' in (tmp_path / 'decision_study.md').read_text(encoding='utf-8')


@pytest.mark.parametrize('value', [float('nan'), float('inf'), True, -1, .5])
def test_invalid_integer_quantities_are_rejected_without_mutation(value):
    network = small_network()
    network['shipments'][0]['quantity_kg'] = value
    with pytest.raises(ValueError):
        compare_policy(network, 'model_volume')
