"""Actual solver/route-ranking checks over explicitly synthetic unit scenarios."""
from copy import deepcopy

import pytest

from backend.freshness_planning import compare_fefo, rank_rescue_options


def warehouse_case():
    return {
        'lots': [
            {'id': 'OLD-COLD', 'warehouse_id': 'W1', 'inventory_kg': 500, 'held': False, 'recalled': False, 'eligible': True,
             'received_at': '2026-10-28T08:00:00-05:00', 'remaining_quality_hours': 20, 'use_by_remaining_hours': 24},
            {'id': 'NEW-WARM', 'warehouse_id': 'W1', 'inventory_kg': 500, 'held': False, 'recalled': False, 'eligible': True,
             'received_at': '2026-10-29T08:00:00-05:00', 'remaining_quality_hours': 3, 'use_by_remaining_hours': 24},
        ],
        'orders': [{'id': 'O1', 'origin_id': 'W1', 'destination_id': 'D1', 'truck_id': 'T1', 'quantity_kg': 500,
                    'destination_demand_kg': 500, 'travel_hours': 1, 'service_hours': .25, 'receiving_buffer_hours': .25, 'deadline_hours': 4}],
        'trucks': [{'id': 'T1', 'capacity_kg': 500, 'eligible': True, 'refrigerated': True}],
        'warehouses': [{'id': 'W1', 'capacity_kg': 1000}],
    }


def test_actual_fefo_sends_newer_warm_lot_while_fifo_sends_older_cold_lot():
    case = warehouse_case(); before = deepcopy(case)
    result = compare_fefo(**case)
    assert case == before
    assert result['fefo']['solver_status'] == result['fifo']['solver_status'] == 'OPTIMAL'
    assert result['fefo']['priority_optimal'] and result['fefo']['fulfillment_optimal']
    assert result['fefo']['picks'][0]['lot_id'] == 'NEW-WARM'
    assert result['fifo']['picks'][0]['lot_id'] == 'OLD-COLD'
    assert result['fefo']['total_supplied_kg'] == result['fifo']['total_supplied_kg'] == 500
    assert result['fefo']['projected_expiry_exposure_kg'] == 0
    assert result['fifo']['projected_expiry_exposure_kg'] == 500
    assert result['delta']['projected_expiry_exposure_kg'] == -500
    assert result['delta']['total_supplied_kg'] == result['delta']['unmet_demand_kg'] == 0
    assert result['requires_human_approval'] and result['operational_state_modified'] is False
    assert all(row['constraint_review']['passed'] for row in (result['fefo'], result['fifo']))


def test_maximizes_supply_before_prioritizing_lots_and_preserves_short_life_for_short_route():
    case = warehouse_case()
    for lot in case['lots']: lot['inventory_kg'] = 100
    case['lots'][1]['remaining_quality_hours'] = 2
    case['orders'][0].update(quantity_kg=100, destination_demand_kg=100)
    case['orders'].append(dict(case['orders'][0], id='O2', destination_id='D2', travel_hours=3, deadline_hours=5))
    result = compare_fefo(**case)['fefo']
    assert result['total_supplied_kg'] == 200 and result['unmet_demand_kg'] == 0
    assert {(row['lot_id'], row['order_id']) for row in result['picks']} == {('NEW-WARM', 'O1'), ('OLD-COLD', 'O2')}
    assert [row['pick_sequence'] for row in result['pick_schedule']] == [1, 2]


@pytest.mark.parametrize('kind', ['held', 'recalled', 'ineligible', 'unscored', 'expired', 'use_by', 'future_arrival'])
def test_safety_or_coverage_exclusions_are_identical_under_fifo_and_fefo(kind):
    case = warehouse_case(); lot = case['lots'][1]
    if kind in ('held', 'recalled'): lot[kind] = True
    if kind == 'ineligible': lot['eligible'] = False
    if kind == 'unscored': lot['remaining_quality_hours'] = None
    if kind == 'expired': lot['remaining_quality_hours'] = 0
    if kind == 'use_by': lot['use_by_remaining_hours'] = 1
    if kind == 'future_arrival': lot['received_at'] = '2026-11-01T00:00:00Z'
    result = compare_fefo(**case, evaluation_at='2026-10-30T12:00:00Z')
    for policy in ('fefo', 'fifo'):
        assert {row['lot_id'] for row in result[policy]['picks']} == {'OLD-COLD'}
        assert result[policy]['constraint_review']['passed']
        assert any(row['lot_id'] == 'NEW-WARM' and row['reasons'] for row in result[policy]['excluded_pairs'])


@pytest.mark.parametrize('change', ['truck_capacity', 'warehouse_capacity', 'destination_cap', 'order_cap', 'truck_ineligible', 'no_refrigeration', 'deadline'])
def test_actual_allocation_enforces_shared_resource_and_order_limits(change):
    case = warehouse_case()
    case['orders'].append(dict(case['orders'][0], id='O2'))
    if change == 'truck_capacity': case['trucks'][0]['capacity_kg'] = 300
    if change == 'warehouse_capacity': case['warehouses'][0]['capacity_kg'] = 200
    if change == 'destination_cap':
        for order in case['orders']: order['destination_demand_kg'] = 150
    if change == 'order_cap':
        for order in case['orders']: order['quantity_kg'] = 125
    if change == 'truck_ineligible': case['trucks'][0]['eligible'] = False
    if change == 'no_refrigeration': case['trucks'][0]['refrigerated'] = False
    if change == 'deadline':
        for order in case['orders']: order['deadline_hours'] = .5
    expected = {'truck_capacity': 300, 'warehouse_capacity': 200, 'destination_cap': 150, 'order_cap': 250,
                'truck_ineligible': 0, 'no_refrigeration': 0, 'deadline': 0}[change]
    result = compare_fefo(**case)
    for policy in ('fefo', 'fifo'):
        assert result[policy]['total_supplied_kg'] == expected
        assert result[policy]['constraint_review']['passed']
        assert all(row['used_kg'] <= row['capacity_kg'] for row in result[policy]['resources'])


def test_lot_placement_does_not_allow_stock_to_teleport_between_warehouses():
    case = warehouse_case()
    case['warehouses'].append({'id': 'W2', 'capacity_kg': 500})
    case['lots'][1]['warehouse_id'] = 'W2'
    result = compare_fefo(**case)['fefo']
    assert result['picks'][0]['lot_id'] == 'OLD-COLD'
    assert any('another warehouse' in reason for row in result['excluded_pairs'] for reason in row['reasons'])


def test_one_truck_cannot_be_allocated_to_two_warehouse_origins_in_the_same_wave():
    case = warehouse_case()
    case['warehouses'].append({'id': 'W2', 'capacity_kg': 1000})
    case['lots'][1]['warehouse_id'] = 'W2'
    case['orders'].append(dict(case['orders'][0], id='O2', origin_id='W2', destination_id='D2'))
    case['trucks'][0]['capacity_kg'] = 1000
    result = compare_fefo(**case)
    for policy in ('fefo', 'fifo'):
        assert result[policy]['total_supplied_kg'] == 500
        assert len({row['warehouse_id'] for row in result[policy]['picks']}) == 1
        assert result[policy]['constraint_review']['passed']


def test_expiry_exactly_at_service_plus_buffer_is_not_positive_margin():
    case = warehouse_case()
    for lot in case['lots']: lot['remaining_quality_hours'] = 1.5
    result = compare_fefo(**case)
    for policy in ('fefo', 'fifo'):
        assert result[policy]['picks'] == []
        assert result[policy]['feasible'] and result[policy]['fulfillment_status'] == 'none'
        assert result[policy]['unmet_demand_kg'] == 500


def test_use_by_limit_caps_an_improved_modeled_quality_clock():
    case = warehouse_case()
    case['lots'][0].update(remaining_quality_hours=100, use_by_remaining_hours=.5)
    result = compare_fefo(**case)
    assert all(row['lot_id'] != 'OLD-COLD' for policy in ('fefo', 'fifo') for row in result[policy]['picks'])
    assert next(row for row in result['fefo']['lot_totals'] if row['lot_id'] == 'OLD-COLD')['effective_remaining_hours'] == .5


def test_fifo_uses_chronological_timezone_normalized_arrival_not_string_sorting():
    case = warehouse_case()
    case['lots'][0]['received_at'] = '2026-10-29T10:00:00+02:00'  # 08:00Z
    case['lots'][1]['received_at'] = '2026-10-29T09:00:00Z'
    assert compare_fefo(**case)['fifo']['picks'][0]['lot_id'] == 'OLD-COLD'


def test_ties_are_deterministic_and_independent_of_input_record_order():
    case = warehouse_case()
    for lot in case['lots']:
        lot.update(remaining_quality_hours=10, received_at='2026-10-29T00:00:00Z')
    first = compare_fefo(**case)
    for key in case: case[key].reverse()
    assert compare_fefo(**case) == first


def test_quantities_preserve_whole_grams_without_rounding_up_stock():
    case = warehouse_case()
    for lot in case['lots']: lot['inventory_kg'] = .334
    case['orders'][0].update(quantity_kg=.333, destination_demand_kg=.333)
    result = compare_fefo(**case)['fefo']
    assert result['picks'][0]['quantity_kg'] == .333
    assert next(row for row in result['lot_totals'] if row['lot_id'] == 'NEW-WARM')['remaining_inventory_kg'] == .001


def test_missing_use_by_dates_are_explicit_and_unknown_quality_still_cannot_ship():
    case = warehouse_case()
    for lot in case['lots']:
        lot.pop('use_by_remaining_hours'); lot['remaining_quality_hours'] = None
    result = compare_fefo(**case)
    assert result['missing_use_by_lot_ids'] == ['NEW-WARM', 'OLD-COLD']
    assert result['fefo']['picks'] == result['fifo']['picks'] == []
    assert any('use-by' in line for line in result['limitations'])


def test_empty_problem_is_feasible_and_does_not_invent_demand_or_waste():
    result = compare_fefo([], [], [], [])
    assert result['fefo']['feasible'] and result['fifo']['feasible']
    assert result['fefo']['total_demand_kg'] == result['fefo']['unmet_demand_kg'] == result['fefo']['projected_expiry_exposure_kg'] == 0


@pytest.mark.parametrize('value', [True, -1, float('inf'), float('nan'), 10**400, '2', .0001])
def test_bad_or_overprecise_quantities_are_rejected_without_silent_reinterpretation(value):
    case = warehouse_case(); case['lots'][0]['inventory_kg'] = value
    with pytest.raises(ValueError): compare_fefo(**case)


@pytest.mark.parametrize('change', ['duplicate_lot', 'unknown_warehouse', 'unknown_truck', 'inconsistent_demand', 'naive_received', 'negative_quality'])
def test_incomplete_or_conflicting_inputs_fail_explicitly(change):
    case = warehouse_case()
    if change == 'duplicate_lot': case['lots'].append(deepcopy(case['lots'][0]))
    if change == 'unknown_warehouse': case['lots'][0]['warehouse_id'] = 'MISSING'
    if change == 'unknown_truck': case['orders'][0]['truck_id'] = 'MISSING'
    if change == 'inconsistent_demand': case['orders'].append(dict(case['orders'][0], id='O2', destination_demand_kg=700))
    if change == 'naive_received': case['lots'][0]['received_at'] = '2026-10-29T00:00:00'
    if change == 'negative_quality': case['lots'][0]['remaining_quality_hours'] = -1
    with pytest.raises(ValueError): compare_fefo(**case)


def test_independent_resource_review_detects_a_faulty_solver_value(monkeypatch):
    from backend import freshness_planning as module
    original = module.cp_model.CpSolver
    class CorruptValueSolver(original):
        def value(self, variable): return super().value(variable) + 600000
    monkeypatch.setattr(module.cp_model, 'CpSolver', CorruptValueSolver)
    result = compare_fefo(**warehouse_case())['fefo']
    assert result['feasible']
    assert result['constraint_review']['passed'] is False
    assert result['constraint_review']['violations']


def test_feasible_solver_result_does_not_claim_lexicographic_optimality(monkeypatch):
    from backend import freshness_planning as module
    original = module.cp_model.CpSolver
    class MerelyFeasibleSolver(original):
        def solve(self, model):
            super().solve(model)
            return module.cp_model.FEASIBLE
    monkeypatch.setattr(module.cp_model, 'CpSolver', MerelyFeasibleSolver)
    result = compare_fefo(**warehouse_case())['fefo']
    assert result['solver_status'] == 'FEASIBLE'
    assert result['fulfillment_optimal'] is result['priority_optimal'] is False
    assert result['constraint_review']['passed']


def rescue_case():
    network = {'provenance': 'Explicit synthetic unit network',
        'nodes': [{'id': 'W1', 'kind': 'dc', 'name': 'Simulated origin', 'capacity_kg': 12000},
                  {'id': 'FAR', 'kind': 'destination', 'name': 'Simulated original buyer', 'demand_kg': 500},
                  {'id': 'NEAR', 'kind': 'destination', 'name': 'Simulated nearby buyer', 'demand_kg': 500},
                  {'id': 'LATER', 'kind': 'destination', 'name': 'Simulated distant alternative', 'demand_kg': 500},
                  {'id': 'HUB', 'kind': 'dc', 'name': 'Simulated contingency hub', 'capacity_kg': 99999}],
        'lots': [{'id': 'L1', 'inventory_kg': 1500, 'held': False, 'recalled': False, 'eligible': True}],
        'trucks': [{'id': 'T1', 'capacity_kg': 1000, 'eligible': True, 'refrigerated': True}],
        'shipments': [{'id': 'S1', 'lot_id': 'L1', 'truck_id': 'T1', 'origin': 'W1', 'destination': 'FAR', 'quantity_kg': 400, 'estimated_hours': 5}]}
    options = [route('NEAR', .5), route('LATER', 3), route('HUB', .1)]
    return network, options


def route(destination, hours):
    return {'destination_id': destination, 'duration_seconds': hours * 3600, 'distance_m': hours * 60000,
        'fallback': True, 'provenance': 'Explicit unit-test estimated connection, not road geometry',
        'recipient_confirmed': True, 'acceptance_capacity_kg': 500,
        'geometry': {'type': 'LineString', 'coordinates': [[-92.3341, 38.9517], [-92.2, 39.0]]}}


def test_rescue_trigger_ranks_closer_options_but_recommends_only_dispatchable_destination():
    network, options = rescue_case(); before = deepcopy((network, options))
    result = rank_rescue_options(network, 'S1', 2.5, options)
    assert (network, options) == before
    assert result['triggered'] and result['status'] == 'rescue_recommended'
    assert result['original']['margin_after_receiving_hours'] == -3.75
    assert result['candidates'][0]['destination_id'] == 'HUB'
    recommended = next(row for row in result['candidates'] if row['id'] == result['recommended_candidate_id'])
    assert recommended['destination_id'] == 'NEAR' and recommended['dispatchable']
    assert recommended['remaining_at_arrival_hours'] == 2
    assert recommended['margin_after_receiving_hours'] == .75
    assert recommended['route']['fallback'] is True and recommended['route']['provenance'] == options[0]['provenance']
    assert result['requires_human_approval'] and result['operational_state_modified'] is False


def test_dc_outbound_capacity_is_never_reinterpreted_as_available_inbound_capacity():
    network, _ = rescue_case(); option = route('HUB', .1); option['acceptance_capacity_kg'] = 0
    result = rank_rescue_options(network, 'S1', 2.5, [option])
    assert not result['candidates'][0]['eligible']
    assert not result['candidates'][0]['dispatchable']
    assert result['recommended_candidate_id'] is None
    option['acceptance_capacity_kg'] = 500
    result = rank_rescue_options(network, 'S1', 2.5, [option])
    assert result['status'] == 'review_only_options'
    assert result['recommended_candidate_id'] is None


@pytest.mark.parametrize('change', ['held', 'recalled', 'lot_ineligible', 'truck_ineligible', 'no_refrigeration', 'lot_stock', 'truck_capacity', 'origin_capacity'])
def test_no_quality_or_distance_objective_overrides_hard_dispatch_block(change):
    network, options = rescue_case()
    if change in ('held', 'recalled'): network['lots'][0][change] = True
    if change == 'lot_ineligible': network['lots'][0]['eligible'] = False
    if change == 'truck_ineligible': network['trucks'][0]['eligible'] = False
    if change == 'no_refrigeration': network['trucks'][0]['refrigerated'] = False
    if change == 'lot_stock': network['lots'][0]['inventory_kg'] = 399
    if change == 'truck_capacity': network['trucks'][0]['capacity_kg'] = 399
    if change == 'origin_capacity': network['nodes'][0]['capacity_kg'] = 399
    result = rank_rescue_options(network, 'S1', 2.5, options)
    assert result['status'] == 'blocked' and result['dispatch_blockers']
    assert result['recommended_candidate_id'] is None
    assert all(not row['eligible'] for row in result['candidates'])


def test_receiving_buffer_can_trigger_review_even_when_original_arrival_precedes_quality_end():
    network, options = rescue_case(); network['shipments'][0]['estimated_hours'] = 1.5
    result = rank_rescue_options(network, 'S1', 2, options)
    assert result['triggered'] and result['original']['required_hours_with_receiving'] == 2.75


def test_no_rescue_recommendation_when_original_plan_retains_quality_margin():
    network, options = rescue_case()
    result = rank_rescue_options(network, 'S1', 20, options)
    assert result['status'] == 'within_modeled_window' and not result['triggered']
    assert result['recommended_candidate_id'] is None


def test_unscored_quality_and_provided_use_by_caps_remain_distinct():
    network, options = rescue_case()
    unknown = rank_rescue_options(network, 'S1', None, options, use_by_remaining_hours=10)
    assert unknown['status'] == 'unscored' and unknown['recommended_candidate_id'] is None
    assert all(not row['eligible'] for row in unknown['candidates'])
    capped = rank_rescue_options(network, 'S1', 100, options, use_by_remaining_hours=2)
    assert capped['original']['effective_remaining_hours'] == 2 and capped['triggered']
    assert next(row for row in capped['candidates'] if row['destination_id'] == 'NEAR')['margin_after_receiving_hours'] == .25


@pytest.mark.parametrize('change', ['not_confirmed', 'inbound_capacity', 'destination_demand', 'recipient_ineligible', 'exact_quality_boundary', 'longer_route'])
def test_rescue_candidate_eligibility_requires_acceptance_demand_and_positive_quality_margin(change):
    network, _ = rescue_case(); option = route('NEAR', .5)
    if change == 'not_confirmed': option['recipient_confirmed'] = False
    if change == 'inbound_capacity': option['acceptance_capacity_kg'] = 399
    if change == 'destination_demand': network['nodes'][2]['demand_kg'] = 399
    if change == 'recipient_ineligible': network['nodes'][2]['eligible'] = False
    if change == 'exact_quality_boundary': option['duration_seconds'] = 1.25 * 3600
    if change == 'longer_route': option['duration_seconds'] = 6 * 3600
    result = rank_rescue_options(network, 'S1', 2.5, [option])
    assert result['status'] == 'no_eligible_rescue'
    assert result['candidates'][0]['reasons'] and not result['candidates'][0]['eligible']


def test_commitments_count_shared_resources_and_remaining_demand_without_double_subtracting_net_acceptance():
    network, _ = rescue_case(); option = route('NEAR', .5)
    own = deepcopy(network['shipments'][0])
    other = dict(own, id='S2', quantity_kg=100, destination='NEAR')
    option['acceptance_capacity_kg'] = 400  # already net of the 100kg commitment
    result = rank_rescue_options(network, 'S1', 2.5, [option], committed_assignments=[own, other])
    assert result['candidates'][0]['eligible']
    assert result['candidates'][0]['remaining_destination_demand_kg'] == 400
    other['quantity_kg'] = 200
    result = rank_rescue_options(network, 'S1', 2.5, [option], committed_assignments=[own, other])
    assert not result['candidates'][0]['eligible']
    assert any('destination demand' in reason for reason in result['candidates'][0]['reasons'])


def test_other_assignments_can_block_shared_truck_without_consuming_the_replaced_assignment_twice():
    network, options = rescue_case(); own = deepcopy(network['shipments'][0])
    assert rank_rescue_options(network, 'S1', 2.5, options, committed_assignments=[own])['dispatch_blockers'] == []
    other = dict(own, id='S2', quantity_kg=700)
    result = rank_rescue_options(network, 'S1', 2.5, options, committed_assignments=[own, other])
    assert 'Shared truck capacity is insufficient' in result['dispatch_blockers']


def test_remaining_travel_override_is_explicit_and_can_resolve_the_original_trigger():
    network, options = rescue_case()
    result = rank_rescue_options(network, 'S1', 2.5, options, original_remaining_hours=.25)
    assert not result['triggered']
    assert result['original']['duration_provenance'] == 'caller-supplied remaining travel assumption'


def test_route_output_geometry_is_an_independent_copy_and_metadata_retains_actual_provenance():
    network, _ = rescue_case(); option = route('NEAR', .5)
    option.update(retrieved_at='2026-10-29T12:00:00Z', source_url='https://example.test/route', stale=True, cache=True, routing_error='Explicit offline test fallback')
    result = rank_rescue_options(network, 'S1', 2.5, [option])
    saved = result['candidates'][0]['route']
    assert saved['retrieved_at'] == option['retrieved_at'] and saved['stale'] is saved['cache'] is True
    saved['geometry']['coordinates'][0][0] = 0
    assert option['geometry']['coordinates'][0][0] == -92.3341


def test_same_destination_faster_route_is_identified_without_inventing_a_new_buyer():
    network, _ = rescue_case()
    result = rank_rescue_options(network, 'S1', 2.5, [route('FAR', .5)])
    assert result['candidates'][0]['original_destination']
    assert result['candidates'][0]['eligible']


def test_rescue_order_and_identity_are_deterministic_under_input_route_reordering():
    network, options = rescue_case()
    assert rank_rescue_options(network, 'S1', 2.5, options) == rank_rescue_options(network, 'S1', 2.5, list(reversed(options)))


@pytest.mark.parametrize('change', ['unknown_ship', 'unknown_destination', 'duplicate_route', 'missing_acceptance', 'bad_geometry', 'nan_duration', 'bad_metadata_time', 'string_eligible'])
def test_rescue_unsupported_inputs_fail_explicitly(change):
    network, _ = rescue_case(); option = route('NEAR', .5); shipment_id = 'S1'; options = [option]
    if change == 'unknown_ship': shipment_id = 'MISSING'
    if change == 'unknown_destination': option['destination_id'] = 'MISSING'
    if change == 'duplicate_route': options.append(deepcopy(option))
    if change == 'missing_acceptance': option.pop('recipient_confirmed')
    if change == 'bad_geometry': option['geometry']['coordinates'][0] = [1, 91]
    if change == 'nan_duration': option['duration_seconds'] = float('nan')
    if change == 'bad_metadata_time': option['retrieved_at'] = '2026-10-30T12:00:00'
    if change == 'string_eligible': network['nodes'][2]['eligible'] = 'false'
    with pytest.raises(ValueError): rank_rescue_options(network, shipment_id, 2.5, options)
