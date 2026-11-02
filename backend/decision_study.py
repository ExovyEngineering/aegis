"""Read-only, one-wave food-volume and destination-service policy comparison.

Quality clocks are declared illustrative model outputs, never pathogen-risk
scores. National FSIS selected-sample prevalence is context shared by every
candidate: there is no scientific basis here to rank fictional lots by it.
"""
from collections import Counter
from copy import deepcopy
import math

from ortools.sat.python import cp_model

from backend.freshness_kinetics import evaluate_freshness
from backend.plan_review import hard_exclusions, review_plan
from backend.simulation import seed_network


VERSION = 'decision-study-v1'
HORIZON_HOURS = 6
POLICIES = (
    {'id': 'status_quo', 'name': 'First feasible candidate',
     'logic': 'Take candidates in their declared input order when every shared constraint remains satisfied. No claim that this is an observed operator policy.'},
    {'id': 'model_volume', 'name': 'Quality-guided volume preservation',
     'logic': 'Lexicographically maximize distributed kg, then short-quality-clock kg retained through delivery, then minimize estimated distance.'},
    {'id': 'model_balanced', 'name': 'Quality-guided balanced service',
     'logic': 'First maximize the sum of destination service fractions capped at 50% per destination; then maximize distributed kg, short-quality-clock kg delivered, and minimize estimated distance.'},
)
LIMITATIONS = [
    'Every supply-chain entity, demand, capacity, temperature, quality profile and stress scenario is simulated. These are computed policy results, not observed operational outcomes.',
    'The FSIS model estimates selected surveillance-sample positivity; it cannot identify contaminated shipments or consumer illness. Its national historical prevalence is identical context for all fictional candidates and does not alter allocation.',
    'Quality guidance uses the existing illustrative Q10 model on declared simulated temperatures. Its forward clocks are neither calibrated poultry shelf life nor pathogen-growth predictions, and cannot extend use-by dates.',
    'Hard safety measures count held/recalled/ineligible exclusions and review workload. They are not estimated infections prevented or causal food-safety risk reduction.',
    'Unsent stock remains inventory. Projected quality-budget exposure is unsent stock whose illustrative forward clock ends within six hours; it is not observed waste or a guaranteed quantity saved.',
    'Food security is represented by preserving eligible food volume and reporting destination demand fulfillment. No vulnerable-population, household-food-security or nutritional outcome is inferred.',
    'Historical USDA county need is not used as a destination weight: fictional jittered destinations lack a verified county crosswalk. Balanced service treats destinations equally, not people, and is not proof of equitable access.',
    'The first-feasible comparator is an explicit rule, not an estimate of actual status-quo operator performance. All policies receive the same candidate assignments and hard constraints.',
    'One-wave fixed truck/candidate allocation omits truck sequencing, live roads, loading labor and temperature uncertainty. Distances are haversine-based simulation estimates, not truck-safe routes.',
    'All actions are review proposals. No dispatch, hold, recall, reservation, inventory write, operational database access or human approval is performed by this study.',
]


def _number(value, label, *, integer=False, positive=False):
    if type(value) not in (int, float) or not math.isfinite(value) or value < (1 if positive else 0) or value > 1_000_000:
        raise ValueError(f'{label} must be a finite nonnegative number within study bounds')
    if integer and int(value) != value:
        raise ValueError(f'{label} must use whole kg in this one-wave study')
    return int(value) if integer else float(value)


def _indexed(rows, label, bound=128):
    if not isinstance(rows, list) or len(rows) > bound:
        raise ValueError(f'{label} must be a list with at most {bound} rows')
    result = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('id'), str) or not 1 <= len(row['id']) <= 80 or row['id'] in result:
            raise ValueError(f'{label} requires unique bounded string identifiers')
        result[row['id']] = row
    return result


def _validate(network):
    if not isinstance(network, dict):
        raise ValueError('network must be an object')
    nodes = _indexed(network.get('nodes'), 'nodes')
    lots = _indexed(network.get('lots'), 'lots', 64)
    trucks = _indexed(network.get('trucks'), 'trucks', 64)
    shipments = _indexed(network.get('shipments'), 'shipments')
    destinations = {key: row for key, row in nodes.items() if row.get('kind') == 'destination'}
    for row in nodes.values():
        if row.get('kind') not in ('destination', 'dc', 'supplier'):
            raise ValueError('Unsupported node kind')
        _number(row.get('demand_kg') if row['kind'] == 'destination' else row.get('capacity_kg'), 'node quantity', integer=True)
    for row in lots.values():
        if row.get('supplier_id') not in nodes or nodes[row['supplier_id']]['kind'] != 'supplier':
            raise ValueError('Unknown lot supplier')
        for field in ('held', 'recalled', 'eligible'):
            if type(row.get(field)) is not bool:
                raise ValueError(f'lot.{field} must be boolean')
        _number(row.get('inventory_kg'), 'inventory_kg', integer=True)
        _number(row.get('shelf_life_hours'), 'shelf_life_hours')
        # Missing/invalid modeled quality remains a hard exclusion via the shared
        # review routine, rather than silently assuming a usable quality clock.
    for row in trucks.values():
        _number(row.get('capacity_kg'), 'capacity_kg', integer=True)
        if any(type(row.get(field)) is not bool for field in ('eligible', 'refrigerated')):
            raise ValueError('Truck eligibility and refrigeration must be boolean')
    for row in shipments.values():
        if (row.get('lot_id') not in lots or row.get('truck_id') not in trucks or
                row.get('destination') not in destinations or row.get('origin') not in nodes or nodes[row['origin']]['kind'] != 'dc'):
            raise ValueError('Unknown or incompatible candidate resource')
        _number(row.get('quantity_kg'), 'quantity_kg', integer=True, positive=True)
        for field in ('estimated_hours', 'deadline_hours', 'estimated_distance_km'):
            _number(row.get(field), field)
        if type(row.get('temperature_c')) not in (int, float) or not math.isfinite(row['temperature_c']):
            raise ValueError('temperature_c must be finite')
    return nodes, lots, trucks, list(shipments.values()), destinations


def _short_clock(lot):
    value = lot.get('quality_remaining_hours')
    return (lot.get('quality_coverage_complete') is True and type(value) in (int, float)
            and math.isfinite(value) and 0 <= value <= HORIZON_HOURS)


def _solve(network, policy_id):
    nodes, lots, trucks, shipments, destinations = _validate(network)
    if policy_id == 'status_quo':
        selected = []
        for row in shipments:
            if review_plan(network, selected + [row])['passed']:
                selected.append(deepcopy(row))
        return selected, 'RULE_FEASIBLE', []

    model = cp_model.CpModel()
    variables = [model.new_bool_var(f'candidate_{i}') for i in range(len(shipments))]
    for index, row in enumerate(shipments):
        if hard_exclusions(row, lots[row['lot_id']], trucks[row['truck_id']]):
            model.add(variables[index] == 0)
    groups = [('lot_id', lots, 'inventory_kg'), ('truck_id', trucks, 'capacity_kg'),
              ('destination', destinations, 'demand_kg'),
              ('origin', {key: row for key, row in nodes.items() if row['kind'] == 'dc'}, 'capacity_kg')]
    for field, resources, capacity in groups:
        for identity, resource in resources.items():
            model.add(sum(row['quantity_kg'] * variables[index] for index, row in enumerate(shipments) if row[field] == identity) <= int(resource[capacity]))
    for supplier in (row for row in nodes.values() if row['kind'] == 'supplier'):
        model.add(sum(row['quantity_kg'] * variables[index] for index, row in enumerate(shipments)
                      if lots[row['lot_id']]['supplier_id'] == supplier['id']) <= int(supplier['capacity_kg']))
    volume = sum(row['quantity_kg'] * variables[index] for index, row in enumerate(shipments))
    short_volume = sum(row['quantity_kg'] * variables[index] for index, row in enumerate(shipments) if _short_clock(lots[row['lot_id']]))
    distance = sum(round(row['estimated_distance_km'] * 1000) * variables[index] for index, row in enumerate(shipments))
    objectives = []
    if policy_id == 'model_balanced':
        credits = []
        for destination in destinations.values():
            if destination['demand_kg'] <= 0:
                continue
            # Credit is a fraction of EACH destination's demand (per mille),
            # capped at 50%; large demand receives no extra fairness weight.
            credit = model.new_int_var(0, 500, f'service_{destination["id"]}')
            supplied = sum(row['quantity_kg'] * variables[index] for index, row in enumerate(shipments) if row['destination'] == destination['id'])
            model.add(credit * int(destination['demand_kg']) <= supplied * 1000)
            credits.append(credit)
        objectives.append(('destination_service_credit', sum(credits)))
    objectives.extend([('distributed_kg', volume), ('short_quality_clock_delivered_kg', short_volume), ('negative_distance_m', -distance)])
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 20261026
    solver.parameters.max_time_in_seconds = 10
    stages, selected, status_name = [], [], 'UNKNOWN'
    for name, expression in objectives:
        model.maximize(expression)
        status = solver.solve(model)
        status_name = solver.status_name(status)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            raise RuntimeError(f'No feasible decision-study solution: {status_name}')
        selected = [deepcopy(row) for index, row in enumerate(shipments) if solver.value(variables[index])]
        value = solver.value(expression)
        stages.append({'objective': name, 'value': value, 'solver_status': status_name})
        if status != cp_model.OPTIMAL:
            break
        model.add(expression == value)
    return selected, status_name, stages


def compare_policy(network, policy_id):
    """Compute a feasible proposal; never mutate network or application state."""
    definitions = {row['id']: row for row in POLICIES}
    if policy_id not in definitions:
        raise ValueError('Unknown decision-study policy')
    selected, solver_status, stages = _solve(network, policy_id)
    nodes, lots, trucks, shipments, destinations = _validate(network)
    review = review_plan(network, selected)
    if not review['passed']:
        raise RuntimeError('Independent decision-study constraint review failed')
    destination_totals, lot_totals = Counter(), Counter()
    for row in selected:
        destination_totals[row['destination']] += row['quantity_kg']
        lot_totals[row['lot_id']] += row['quantity_kg']
    service = [{'destination_id': row['id'], 'demand_kg': row['demand_kg'],
                'distributed_kg': destination_totals[row['id']],
                'service_fraction': destination_totals[row['id']] / row['demand_kg'] if row['demand_kg'] else None}
               for row in destinations.values()]
    fractions = [row['service_fraction'] for row in service if row['service_fraction'] is not None]
    distributed = sum(row['quantity_kg'] for row in selected)
    demand = sum(row['demand_kg'] for row in destinations.values())
    eligible_inventory = sum(row['inventory_kg'] for row in lots.values() if row['eligible'] and not row['held'] and not row['recalled'])
    protected_inventory = sum(row['inventory_kg'] for row in lots.values() if row['held'] or row['recalled'])
    expiry_exposure = sum(max(0, row['inventory_kg'] - lot_totals[row['id']]) for row in lots.values()
                          if row['eligible'] and not row['held'] and not row['recalled'] and _short_clock(row))
    high_attention = [row['id'] for row in selected if row['temperature_c'] > 4]
    safety_exclusions = [{'shipment_id': row['id'], 'quantity_kg': row['quantity_kg'],
                          'reasons': hard_exclusions(row, lots[row['lot_id']], trucks[row['truck_id']])}
                         for row in shipments if hard_exclusions(row, lots[row['lot_id']], trucks[row['truck_id']])]
    metrics = {
        'distributed_kg': distributed, 'unmet_demand_kg': demand - distributed,
        'demand_service_fraction': distributed / demand if demand else None,
        'retained_inventory_kg': sum(row['inventory_kg'] for row in lots.values()) - distributed,
        'eligible_retained_inventory_kg': eligible_inventory - distributed,
        'held_or_recalled_inventory_excluded_kg': protected_inventory,
        'held_or_recalled_dispatched_kg': sum(row['quantity_kg'] for row in selected if lots[row['lot_id']]['held'] or lots[row['lot_id']]['recalled']),
        'projected_quality_budget_exposure_kg': expiry_exposure,
        'short_quality_clock_delivered_kg': sum(row['quantity_kg'] for row in selected if _short_clock(lots[row['lot_id']])),
        'destinations_served': sum(row['distributed_kg'] > 0 for row in service),
        'destinations_meeting_50_percent_demand': sum(value >= .5 for value in fractions),
        'min_demand_service_fraction': min(fractions) if fractions else None,
        'mean_capped_service_fraction': sum(min(.5, value) for value in fractions) / len(fractions) if fractions else None,
        'total_estimated_distance_km': round(sum(row['estimated_distance_km'] for row in selected), 3),
        'total_estimated_shipment_hours': round(sum(row['estimated_hours'] for row in selected), 3),
        'mean_estimated_shipment_hours': sum(row['estimated_hours'] for row in selected) / len(selected) if selected else None,
        'temperature_review_shipments': len(high_attention),
        'temperature_review_cargo_kg': sum(row['quantity_kg'] for row in selected if row['temperature_c'] > 4),
        'constraint_violations': len(review['violations']),
    }
    return {
        'policy_id': policy_id, 'policy_name': definitions[policy_id]['name'], 'solver_status': solver_status,
        'metrics': metrics, 'demand_service': service, 'constraint_review': review,
        'selected_shipment_ids': [row['id'] for row in selected], 'objective_stages': stages,
        'hard_exclusions': safety_exclusions,
        'priority_diagnostics': {
            'temperature_review_shipment_ids': high_attention,
            'fsis_individual_risk_ranking_available': False,
            'need_weighting_available': False,
            'balanced_service_target_fraction': .5,
            'interpretation': 'Temperature flags request qualified review. Quality-clock priority is a volume-preservation heuristic, not a contamination ranking. Equal destination service is not population equity.',
        },
        'proposed_actions': [
            {'action': 'review_candidate_allocation', 'shipment_ids': [row['id'] for row in selected], 'requires_human_approval': True},
            {'action': 'request_temperature_and_disposition_review', 'shipment_ids': high_attention, 'requires_human_approval': True},
        ],
        'requires_human_approval': True, 'operator_state_modified': False,
    }


def _quality_network():
    """Evaluate declared synthetic histories using the existing quality model."""
    network = seed_network()
    evidence = []
    for index, lot in enumerate(network['lots']):
        profile = {'started_at': '2026-10-26T08:00:00-05:00', 'reference_life_hours': 12,
                   'initial_equivalent_age_hours': 7 if index % 3 == 1 else 0,
                   'forecast_temperature_c': 4, 'max_gap_minutes': 120,
                   'profile_id': 'decision-study-illustrative-quality', 'product_category': 'simulated chilled poultry'}
        readings = [{'observed_at': profile['started_at'], 'temperature_c': 8 if index % 3 == 1 else 2,
                     'source_kind': 'declared deterministic simulation'}]
        result = evaluate_freshness(readings, profile, '2026-10-26T09:00:00-05:00')
        complete = result['coverage']['complete_under_hold_assumption'] and result['status'] == 'estimated'
        lot.update(quality_remaining_hours=result['remaining_quality_hours'], quality_coverage_complete=complete)
        evidence.append({'lot_id': lot['id'], 'profile': result['profile'], 'readings': readings,
                         'evaluation_at': '2026-10-26T09:00:00-05:00',
                         'remaining_quality_hours': result['remaining_quality_hours'],
                         'sensitivity': result['sensitivity'], 'coverage_complete': complete})
    return network, evidence


def build_decision_study(risk_context=None):
    """Return reproducible simulation artifacts without reading operator state."""
    base, quality_evidence = _quality_network()
    scarcity = deepcopy(base)
    for truck in scarcity['trucks']:
        truck['capacity_kg'] = 400
    for index, row in enumerate(scarcity['shipments']):
        if index % 3 == 0:
            row['quantity_kg'] = 200
    # Vary demand explicitly to make equal destination-service and volume
    # objectives distinguishable. These values are scenario inputs, not need data.
    for index, row in enumerate(n for n in scarcity['nodes'] if n['kind'] == 'destination'):
        row['demand_kg'] = 200 if index % 3 == 0 else 800
    delayed = deepcopy(base)
    for row in delayed['shipments']:
        row['estimated_hours'] = round(row['estimated_hours'] + 2, 3)
    delayed['lots'][2]['recalled'] = True
    delayed['lots'][3]['inventory_kg'] = 400
    for truck in delayed['trucks']:
        truck['capacity_kg'] = 800
    definitions = [
        ('baseline', 'Baseline quality-constrained wave', base,
         ['Canonical seeded candidates, inventory and demand.', 'All lot quality clocks come from declared synthetic Q10 histories; held L01 remains excluded.']),
        ('fleet_scarcity', 'Fleet scarcity and heterogeneous demand', scarcity,
         ['Every truck has 400 kg available one-wave capacity.', 'Every third candidate is 200 kg rather than 400 kg.', 'Every third destination demands 200 kg; other destinations demand 800 kg. These are declared stress inputs.']),
        ('delay_supply_stress', 'Delay and supply restriction', delayed,
         ['Every candidate incurs two additional estimated journey hours.', 'L03 is recalled in this simulation; L04 inventory is 400 kg; truck capacity is 800 kg.', 'The recall is an existing scenario input, never inferred from a score or imposed on operator state.']),
    ]
    scenarios = []
    for identity, name, network, assumptions in definitions:
        results = [compare_policy(network, policy['id']) for policy in POLICIES]
        baseline = results[0]['metrics']
        comparisons = []
        for result in results[1:]:
            current = result['metrics']
            comparisons.append({'policy_id': result['policy_id'], 'comparator': 'status_quo',
                                'distributed_kg_delta': current['distributed_kg'] - baseline['distributed_kg'],
                                'quality_budget_exposure_kg_delta': current['projected_quality_budget_exposure_kg'] - baseline['projected_quality_budget_exposure_kg'],
                                'destinations_served_delta': current['destinations_served'] - baseline['destinations_served'],
                                'estimated_shipment_hours_delta': round(current['total_estimated_shipment_hours'] - baseline['total_estimated_shipment_hours'], 3),
                                'interpretation': 'Computed differences under declared simulation inputs; not causal safety or food-security effects.'})
        scenarios.append({'id': identity, 'name': name, 'assumptions': assumptions,
                          'input_network': network, 'policies': results, 'comparison': comparisons})
    context = deepcopy(risk_context) if isinstance(risk_context, dict) else {'status': 'unavailable', 'historical_prevalence': None}
    context.update(individual_shipment_linkage=False, used_for_allocation=False,
                   interpretation='National selected-FSIS-sample historical prevalence is equal context for every simulated candidate; no shipment-level risk or causal risk-reduction claim.')
    return {
        'status': 'computed simulation; not operational validation', 'study_version': VERSION,
        'simulation': True, 'requires_human_approval': True, 'operator_state_modified': False,
        'objective': 'Preserve eligible food volume, reduce modeled short-clock inventory exposure, and examine equal destination demand service under shared safety and logistics constraints.',
        'food_security_objective': 'Preserving food volume, explicitly permitted by Task 3; no unsupported population-need mapping.',
        'decision_actor': 'Human regional chilled-food distribution dispatcher',
        'horizon_hours': HORIZON_HOURS, 'risk_context': context,
        'policy_definitions': deepcopy(list(POLICIES)), 'scenarios': scenarios,
        'quality_model_evidence': quality_evidence, 'limitations': list(LIMITATIONS),
        'unresolved_risk_action_link': 'Prospective individual-shipment FSIS risk is unavailable. Quality-guided allocation and hard safety exclusions demonstrate decision mechanics without claiming validated pathogen-risk personalization.',
    }
