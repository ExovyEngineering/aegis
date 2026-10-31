"""Pure, human-reviewed freshness allocation and rescue calculations.

The supplied clocks are modeled QUALITY budgets at a declared future cargo
temperature. They are not pathogen estimates, use-by extensions or safety
clearance. No reading, database, routing service or operational record is changed.
"""
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
import re
import time

from ortools.sat.python import cp_model


VERSION = 'freshness-planning-v1'
_GRAMS = 1000
_EPS = 1e-9
_MAX_KG = 1_000_000


def _number(value, label, *, minimum=0, maximum=87600):
    if type(value) not in (int, float) or not minimum <= value <= maximum or not math.isfinite(value):
        raise ValueError(f'{label} must be a finite number from {minimum} to {maximum}')
    return float(value)


def _quantity(value, label):
    _number(value, label, maximum=_MAX_KG)
    grams = Decimal(str(value)) * _GRAMS
    if grams != grams.to_integral_value():
        raise ValueError(f'{label} must use whole grams (at most three decimal places in kg)')
    return int(grams)


def _identifier(value, label):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,80}', value):
        raise ValueError(f'{label} must be a bounded identifier')
    return value


def _boolean(value, label):
    if type(value) is not bool:
        raise ValueError(f'{label} must be a boolean')
    return value


def _timestamp(value, label):
    if not isinstance(value, str) or len(value) > 80:
        raise ValueError(f'{label} must be a timezone-aware ISO timestamp')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError('Missing timezone')
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError) as error:
        raise ValueError(f'{label} must be a timezone-aware ISO timestamp') from error


def _rows(values, label, maximum):
    if not isinstance(values, (list, tuple)) or len(values) > maximum:
        raise ValueError(f'{label} must be a sequence with at most {maximum} records')
    result = {}
    for value in values:
        if not isinstance(value, dict):
            raise ValueError(f'{label} records must be objects')
        identity = _identifier(value.get('id'), f'{label}.id')
        if identity in result:
            raise ValueError(f'Duplicate {label} identifier: {identity}')
        result[identity] = value
    return result


def _kg(grams):
    return round(grams / _GRAMS, 3)


def _clock(value):
    return None if value is None else round(value, 9)


def _effective_clock(row):
    quality = row.get('remaining_quality_hours')
    if quality is not None:
        quality = _number(quality, 'remaining_quality_hours')
    use_by = row.get('use_by_remaining_hours')
    if use_by is not None:
        use_by = _number(use_by, 'use_by_remaining_hours')
    return None if quality is None else min(quality, use_by) if use_by is not None else quality


FEFO_LIMITATIONS = [
    'FEFO and FIFO receive the same stock, demand, capacity, eligibility, quality-window and provided use-by constraints. FIFO is not permitted to ship held, recalled or unscored stock.',
    'Remaining clocks must be projected hours at the declared FUTURE cargo-temperature assumption, not reference-temperature equivalent hours. The caller owns kinetic coverage and parameter provenance.',
    'A modeled quality clock is not measured molecular freshness, a pathogen-growth estimate, food-safety clearance or authority to extend a manufacturer use-by limit.',
    'The recommendation sequences one-wave picks; it does not create a warehouse labor timetable, reserve inventory, impose a hold or dispatch a truck.',
    'Unselected inventory whose supplied quality clock ends within the chosen horizon is projected expiry exposure, not measured waste or an instruction to discard food.',
    'A missing independent use-by clock is reported as missing; no actual manufacturer date is inferred from a simulated quality budget.',
]


def _prepare_fefo(lots, orders, trucks, warehouses, evaluation_at):
    lots = _rows(lots, 'lots', 24)
    orders = _rows(orders, 'orders', 50)
    trucks = _rows(trucks, 'trucks', 20)
    warehouses = _rows(warehouses, 'warehouses', 20)
    at = None if evaluation_at is None else _timestamp(evaluation_at, 'evaluation_at')
    prepared_lots = {}
    for identity, row in lots.items():
        warehouse = _identifier(row.get('warehouse_id'), 'lot.warehouse_id')
        if warehouse not in warehouses:
            raise ValueError(f'Unknown lot warehouse: {warehouse}')
        prepared_lots[identity] = {
            'id': identity, 'warehouse_id': warehouse,
            'inventory': _quantity(row.get('inventory_kg'), 'lot.inventory_kg'),
            'held': _boolean(row.get('held'), 'lot.held'),
            'recalled': _boolean(row.get('recalled'), 'lot.recalled'),
            'eligible': _boolean(row.get('eligible'), 'lot.eligible'),
            'received': _timestamp(row.get('received_at'), 'lot.received_at'),
            'received_at': row['received_at'], 'remaining': _effective_clock(row),
            'quality': row.get('remaining_quality_hours'),
            'use_by': row.get('use_by_remaining_hours'),
        }
    prepared_trucks = {}
    for identity, row in trucks.items():
        prepared_trucks[identity] = {'capacity': _quantity(row.get('capacity_kg'), 'truck.capacity_kg'),
            'eligible': _boolean(row.get('eligible'), 'truck.eligible'),
            'refrigerated': _boolean(row.get('refrigerated'), 'truck.refrigerated')}
    prepared_warehouses = {identity: _quantity(row.get('capacity_kg'), 'warehouse.capacity_kg') for identity, row in warehouses.items()}
    prepared_orders = {}
    destination_caps = {}
    for identity, row in orders.items():
        origin = _identifier(row.get('origin_id'), 'order.origin_id')
        destination = _identifier(row.get('destination_id'), 'order.destination_id')
        truck = _identifier(row.get('truck_id'), 'order.truck_id')
        if origin not in warehouses or truck not in trucks:
            raise ValueError(f'Unknown order warehouse or truck: {identity}')
        demand = _quantity(row.get('destination_demand_kg'), 'order.destination_demand_kg')
        if destination in destination_caps and destination_caps[destination] != demand:
            raise ValueError(f'Inconsistent aggregate demand for destination: {destination}')
        destination_caps[destination] = demand
        travel = _number(row.get('travel_hours'), 'order.travel_hours')
        service = _number(row.get('service_hours', 0), 'order.service_hours')
        buffer = _number(row.get('receiving_buffer_hours', 0), 'order.receiving_buffer_hours')
        deadline = row.get('deadline_hours')
        if deadline is not None:
            deadline = _number(deadline, 'order.deadline_hours')
        prepared_orders[identity] = {'id': identity, 'origin_id': origin, 'destination_id': destination,
            'truck_id': truck, 'quantity': _quantity(row.get('quantity_kg'), 'order.quantity_kg'),
            'travel_hours': travel, 'service_hours': service, 'receiving_buffer_hours': buffer,
            'required_hours': travel + service + buffer, 'deadline_hours': deadline}
    excluded = []
    allowed = []
    for lid in sorted(prepared_lots):
        lot = prepared_lots[lid]
        for oid in sorted(prepared_orders):
            order = prepared_orders[oid]
            truck = prepared_trucks[order['truck_id']]
            reasons = []
            if lot['warehouse_id'] != order['origin_id']: reasons.append('Lot is at another warehouse')
            if lot['held']: reasons.append('Lot is held')
            if lot['recalled']: reasons.append('Lot is recalled')
            if not lot['eligible']: reasons.append('Lot is ineligible')
            if lot['inventory'] == 0: reasons.append('No lot inventory')
            if at is not None and lot['received'] > at: reasons.append('Lot has not arrived at the evaluation time')
            if lot['remaining'] is None: reasons.append('Modeled quality coverage is unscored')
            elif lot['remaining'] - order['required_hours'] <= _EPS: reasons.append('No positive quality/use-by margin after travel, service and receiving buffer')
            if not truck['eligible']: reasons.append('Truck is ineligible')
            if not truck['refrigerated']: reasons.append('Truck has no refrigeration')
            if order['deadline_hours'] is not None and order['travel_hours'] + order['service_hours'] > order['deadline_hours'] + _EPS:
                reasons.append('Service would exceed the order deadline')
            if reasons: excluded.append({'lot_id': lid, 'order_id': oid, 'reasons': reasons})
            else: allowed.append((lid, oid))
    return prepared_lots, prepared_orders, prepared_trucks, prepared_warehouses, destination_caps, allowed, excluded


def _allocate(prepared, policy, seed, horizon):
    lots, orders, trucks, warehouses, demand, allowed, excluded = prepared
    if policy == 'fefo':
        priority = sorted(lots, key=lambda identity: (lots[identity]['remaining'] is None,
            lots[identity]['remaining'] if lots[identity]['remaining'] is not None else math.inf,
            lots[identity]['received'], identity))
    else:
        priority = sorted(lots, key=lambda identity: (lots[identity]['received'], identity))
    model = cp_model.CpModel()
    choices = {pair: model.new_int_var(0, min(lots[pair[0]]['inventory'], orders[pair[1]]['quantity']), f'pick_{index}') for index, pair in enumerate(allowed)}
    for identity, lot in lots.items():
        model.add(sum(value for (lid, _), value in choices.items() if lid == identity) <= lot['inventory'])
    for identity, order in orders.items():
        model.add(sum(value for (_, oid), value in choices.items() if oid == identity) <= order['quantity'])
    for identity, cap in demand.items():
        model.add(sum(value for (_, oid), value in choices.items() if orders[oid]['destination_id'] == identity) <= cap)
    for identity, truck in trucks.items():
        model.add(sum(value for (_, oid), value in choices.items() if orders[oid]['truck_id'] == identity) <= truck['capacity'])
        origins = sorted({order['origin_id'] for order in orders.values() if order['truck_id'] == identity})
        if len(origins) > 1:
            enabled = {origin: model.new_bool_var(f'truck_origin_{identity}_{origin}') for origin in origins}
            model.add(sum(enabled.values()) <= 1)
            for origin, active in enabled.items():
                model.add(sum(value for (_, oid), value in choices.items()
                    if orders[oid]['truck_id'] == identity and orders[oid]['origin_id'] == origin) <= truck['capacity'] * active)
    for identity, cap in warehouses.items():
        model.add(sum(value for (_, oid), value in choices.items() if orders[oid]['origin_id'] == identity) <= cap)
    total = sum(choices.values())
    best = {pair: 0 for pair in choices}
    statuses = []
    started = time.monotonic()

    def solve(expression, name):
        remaining = 5 - (time.monotonic() - started)
        if remaining <= .001: return False
        model.maximize(expression)
        solver = cp_model.CpSolver()
        solver.parameters.num_search_workers = 1
        solver.parameters.random_seed = seed
        solver.parameters.max_time_in_seconds = min(2, remaining)
        status = solver.solve(model)
        statuses.append({'stage': name, 'status': solver.status_name(status)})
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            best.update({pair: solver.value(variable) for pair, variable in choices.items()})
        if status != cp_model.OPTIMAL: return False
        model.add(expression == round(solver.objective_value))
        return True

    fulfillment_optimal = solve(total, 'maximize fulfilled kg')
    complete = fulfillment_optimal
    # True lexicographic priority: fixing each preceding lot avoids the misleading
    # trade-offs possible in a weighted sum of lot ranks.
    if complete:
        for identity in priority:
            expression = sum(value for (lid, _), value in choices.items() if lid == identity)
            if not solve(expression, f'prioritize {identity}'):
                complete = False
                break
    if complete:
        order_rank = {identity: index for index, identity in enumerate(sorted(orders))}
        complete = solve(-sum(order_rank[oid] * value for (_, oid), value in choices.items()), 'deterministic order preference')
    feasible = any(stage['status'] in ('OPTIMAL', 'FEASIBLE') for stage in statuses)
    lot_used = Counter(); order_used = Counter(); truck_used = Counter(); origin_used = Counter(); destination_used = Counter()
    picks = []
    for (lid, oid), amount in best.items():
        if not feasible or amount <= 0: continue
        lot, order = lots[lid], orders[oid]
        lot_used[lid] += amount; order_used[oid] += amount
        truck_used[order['truck_id']] += amount; origin_used[order['origin_id']] += amount
        destination_used[order['destination_id']] += amount
        picks.append({'lot_id': lid, 'order_id': oid, 'warehouse_id': order['origin_id'],
            'destination_id': order['destination_id'], 'truck_id': order['truck_id'], 'quantity_kg': _kg(amount),
            'remaining_quality_hours': _clock(lot['quality']), 'use_by_remaining_hours': _clock(lot['use_by']),
            'effective_remaining_hours': _clock(lot['remaining']), 'travel_hours': order['travel_hours'],
            'service_hours': order['service_hours'], 'receiving_buffer_hours': order['receiving_buffer_hours'],
            'remaining_at_arrival_hours': _clock(lot['remaining'] - order['travel_hours']),
            'remaining_at_service_hours': _clock(lot['remaining'] - order['travel_hours'] - order['service_hours']),
            'margin_after_receiving_hours': _clock(lot['remaining'] - order['required_hours']),
            'requires_human_approval': True})
    rank = {identity: index for index, identity in enumerate(priority)}
    picks.sort(key=lambda row: (rank[row['lot_id']], row['order_id']))
    schedule = [dict(row, pick_sequence=index + 1) for index, row in enumerate(picks)]
    resources = []
    violations = []
    for kind, used, caps in [('lot', lot_used, {identity: lot['inventory'] for identity, lot in lots.items()}),
                            ('order', order_used, {identity: row['quantity'] for identity, row in orders.items()}),
                            ('truck', truck_used, {identity: truck['capacity'] for identity, truck in trucks.items()}),
                            ('warehouse', origin_used, warehouses), ('destination', destination_used, demand)]:
        for identity, cap in sorted(caps.items()):
            amount = used[identity]
            resources.append({'kind': kind, 'id': identity, 'used_kg': _kg(amount), 'capacity_kg': _kg(cap), 'remaining_kg': _kg(cap - amount)})
            if amount > cap: violations.append(f'{kind} {identity} exceeds capacity')
    allowed_set = set(allowed)
    for row in picks:
        if (row['lot_id'], row['order_id']) not in allowed_set: violations.append('A selected pair failed independent eligibility review')
        if row['margin_after_receiving_hours'] <= 0: violations.append('A selected pair has no positive receiving quality margin')
    for identity in trucks:
        selected_origins = {row['warehouse_id'] for row in picks if row['truck_id'] == identity}
        if len(selected_origins) > 1: violations.append(f'Truck {identity} is allocated to multiple origins in one wave')
    if any(type(amount) is not int or amount < 0 for amount in best.values()):
        violations.append('The solver returned an invalid pick quantity')
    supplied = sum(lot_used.values())
    exposure = sum(max(0, lot['inventory'] - lot_used[identity]) for identity, lot in lots.items()
        if lot['eligible'] and not lot['held'] and not lot['recalled'] and lot['remaining'] is not None and lot['remaining'] <= horizon)
    return {'policy': policy, 'name': 'Predictive FEFO quality-clock ordering' if policy == 'fefo' else 'FIFO arrival-order baseline',
        'picks': picks, 'pick_schedule': schedule, 'priority_lot_ids': priority,
        'lot_totals': [{'lot_id': identity, 'picked_kg': _kg(lot_used[identity]), 'remaining_inventory_kg': _kg(lots[identity]['inventory'] - lot_used[identity]),
                        'remaining_quality_hours': _clock(lots[identity]['quality']), 'use_by_remaining_hours': _clock(lots[identity]['use_by']),
                        'effective_remaining_hours': _clock(lots[identity]['remaining']), 'received_at': lots[identity]['received_at']} for identity in priority],
        'resources': resources, 'excluded_pairs': excluded, 'total_supplied_kg': _kg(supplied),
        'total_demand_kg': _kg(sum(demand.values())), 'unmet_demand_kg': _kg(sum(demand.values()) - supplied),
        'projected_expiry_exposure_kg': _kg(exposure), 'projection_horizon_hours': horizon,
        'solver_status': 'OPTIMAL' if complete else 'FEASIBLE' if feasible else statuses[-1]['status'] if statuses else 'UNKNOWN',
        'solver_stages': statuses, 'feasible': feasible, 'fulfillment_optimal': fulfillment_optimal, 'priority_optimal': complete,
        'fulfillment_status': 'complete' if supplied == sum(demand.values()) else 'partial' if supplied else 'none',
        'constraint_review': {'passed': feasible and not violations, 'violations': violations, 'method': 'Independent sums and selected-pair eligibility review'},
        'requires_human_approval': True, 'operational_state_modified': False}


def compare_fefo(lots, orders, trucks, warehouses, *, seed=20261026, projection_horizon_hours=6, evaluation_at=None):
    """Compare lexicographic FEFO/FIFO under identical hard one-wave constraints.

    Quantities use kg with whole-gram precision. Orders need destination_demand_kg
    (one consistent aggregate cap per destination). Lots need an aware received_at,
    explicit warehouse placement and remaining_quality_hours or None for unscored.
    An optional independent use_by_remaining_hours always caps the quality clock.
    """
    if type(seed) is not int or not 0 <= seed <= 2**31 - 1: raise ValueError('seed must be a bounded integer')
    horizon = _number(projection_horizon_hours, 'projection_horizon_hours', maximum=168)
    prepared = _prepare_fefo(lots, orders, trucks, warehouses, evaluation_at)
    fefo = _allocate(prepared, 'fefo', seed, horizon)
    fifo = _allocate(prepared, 'fifo', seed, horizon)
    return {'method_version': VERSION, 'fefo': fefo, 'fifo': fifo,
        'delta': {key: round(fefo[key] - fifo[key], 3) for key in ('total_supplied_kg', 'unmet_demand_kg', 'projected_expiry_exposure_kg')},
        'missing_use_by_lot_ids': sorted(row['id'] for row in lots if row.get('use_by_remaining_hours') is None),
        'requires_human_approval': True, 'operational_state_modified': False,
        'provenance': 'One-wave mathematical picking recommendation over caller-supplied stock, relative modeled quality clocks and explicit arrival/placement assumptions; not observed molecular freshness.',
        'limitations': list(FEFO_LIMITATIONS)}


RESCUE_LIMITATIONS = [
    'Rescue options are automatic calculations only. Consequential lot, inventory, assignment and dispatch changes require a separate identified human review and current-state recheck.',
    'A projected quality clock is not a food-safety clearance. Held, recalled and ineligible lots and trucks stay blocked regardless of the estimated freshness or travel objective.',
    'Recipient confirmation and receiving capacity are supplied planning inputs. In the AEGIS demo they describe simulated recipients, not real buyers or verified supply contracts.',
    'Receiving capacity means NET available capacity after committed work. Distribution-center outbound capacity is not reinterpreted as spare receiving/storage capacity.',
    'Distribution-center transfers can be shown as review-only contingencies. The current core dispatch optimizer serves existing destination nodes; these transfer rows cannot be dispatched through this recommendation.',
    'Routing duration and geometry retain supplied provenance/fallback labels. Neither ordinary-driving OSRM nor a distance estimate establishes truck-safe eligibility or current closure avoidance.',
    'The caller must provide the remaining quality clock at a declared future cargo temperature and any independent use-by cap. Missing sensor coverage or an unscored clock cannot become an eligible rescue.',
]


def _coordinate(point):
    return isinstance(point, (list, tuple)) and len(point) == 2 and all(type(value) in (int, float) and abs(value) <= limit and math.isfinite(value) for value, limit in zip(point, (180, 90)))


def rank_rescue_options(network, shipment_id, remaining_quality_hours, route_options, *, receiving_buffer_hours=1, service_hours=.25,
                        original_remaining_hours=None, use_by_remaining_hours=None, committed_assignments=()):
    """Rank supplied routes without fetching providers or changing network state.

    route_options require destination_id, duration_seconds, distance_m, fallback,
    provenance, recipient_confirmed and acceptance_capacity_kg (net after other
    commitments). Optional GeoJSON geometry is retained. Existing assignments are
    independently summed, excluding shipment_id because this is a replacement.
    """
    if not isinstance(network, dict): raise ValueError('network must be an object')
    shipments = _rows(network.get('shipments'), 'shipments', 50)
    lots = _rows(network.get('lots'), 'lots', 24)
    trucks = _rows(network.get('trucks'), 'trucks', 20)
    nodes = _rows(network.get('nodes'), 'nodes', 200)
    _identifier(shipment_id, 'shipment_id')
    if shipment_id not in shipments: raise ValueError('Unknown shipment')
    shipment = shipments[shipment_id]
    if any(shipment.get(key) not in collection for key, collection in [('lot_id', lots), ('truck_id', trucks), ('origin', nodes), ('destination', nodes)]):
        raise ValueError('Shipment references unsupported network entities')
    lot, truck, origin = lots[shipment['lot_id']], trucks[shipment['truck_id']], nodes[shipment['origin']]
    quantity = _quantity(shipment.get('quantity_kg'), 'shipment.quantity_kg')
    inventory = _quantity(lot.get('inventory_kg'), 'lot.inventory_kg')
    truck_capacity = _quantity(truck.get('capacity_kg'), 'truck.capacity_kg')
    origin_capacity = _quantity(origin.get('capacity_kg'), 'origin.capacity_kg')
    buffer = _number(receiving_buffer_hours, 'receiving_buffer_hours')
    service = _number(service_hours, 'service_hours')
    quality = None if remaining_quality_hours is None else _number(remaining_quality_hours, 'remaining_quality_hours')
    use_by = None if use_by_remaining_hours is None else _number(use_by_remaining_hours, 'use_by_remaining_hours')
    effective = None if quality is None else min(quality, use_by) if use_by is not None else quality
    original_hours = _number(shipment.get('estimated_hours') if original_remaining_hours is None else original_remaining_hours, 'original_remaining_hours')
    commitments = _rows(committed_assignments, 'committed_assignments', 50)
    lot_used = Counter(); truck_used = Counter(); origin_used = Counter(); destination_used = Counter()
    for identity, row in commitments.items():
        if identity == shipment_id: continue
        if any(row.get(key) not in collection for key, collection in [('lot_id', lots), ('truck_id', trucks), ('origin', nodes), ('destination', nodes)]):
            raise ValueError('Committed assignment references unknown network entities')
        amount = _quantity(row.get('quantity_kg'), 'assignment.quantity_kg')
        lot_used[row['lot_id']] += amount; truck_used[row['truck_id']] += amount
        origin_used[row['origin']] += amount; destination_used[row['destination']] += amount
    blockers = []
    if _boolean(lot.get('held'), 'lot.held'): blockers.append('Lot is held')
    if _boolean(lot.get('recalled'), 'lot.recalled'): blockers.append('Lot is recalled')
    if not _boolean(lot.get('eligible'), 'lot.eligible'): blockers.append('Lot is ineligible')
    if not _boolean(truck.get('eligible'), 'truck.eligible'): blockers.append('Truck is ineligible')
    if not _boolean(truck.get('refrigerated'), 'truck.refrigerated'): blockers.append('Truck has no refrigeration')
    if quantity <= 0: blockers.append('Shipment contains no cargo')
    if lot_used[lot['id']] + quantity > inventory: blockers.append('Shared lot inventory is insufficient')
    if truck_used[truck['id']] + quantity > truck_capacity: blockers.append('Shared truck capacity is insufficient')
    if origin_used[origin['id']] + quantity > origin_capacity: blockers.append('Shared origin capacity is insufficient')
    if not isinstance(route_options, (list, tuple)) or len(route_options) > 200: raise ValueError('route_options must contain at most 200 routes')
    candidates = []; identities = set()
    for option in route_options:
        if not isinstance(option, dict): raise ValueError('Each rescue route must be an object')
        destination_id = _identifier(option.get('destination_id'), 'route.destination_id')
        if destination_id not in nodes: raise ValueError('Unknown rescue destination')
        destination = nodes[destination_id]
        seconds = _number(option.get('duration_seconds'), 'route.duration_seconds', maximum=87600 * 3600)
        meters = _number(option.get('distance_m'), 'route.distance_m', maximum=100_000_000)
        fallback = _boolean(option.get('fallback'), 'route.fallback')
        confirmed = _boolean(option.get('recipient_confirmed'), 'route.recipient_confirmed')
        available = _quantity(option.get('acceptance_capacity_kg'), 'route.acceptance_capacity_kg')
        provenance = option.get('provenance')
        if not isinstance(provenance, str) or not provenance.strip() or len(provenance) > 3000: raise ValueError('Route provenance is required')
        geometry = option.get('geometry')
        if geometry is not None and (not isinstance(geometry, dict) or geometry.get('type') != 'LineString' or not isinstance(geometry.get('coordinates'), list) or not 2 <= len(geometry['coordinates']) <= 20000 or not all(_coordinate(point) for point in geometry['coordinates'])):
            raise ValueError('Rescue route geometry must be a bounded GeoJSON LineString in longitude/latitude order')
        route = {'duration_seconds': seconds, 'distance_m': meters, 'fallback': fallback, 'provenance': provenance,
                 'geometry': None if geometry is None else json.loads(json.dumps(geometry, allow_nan=False))}
        for key in ('retrieved_at', 'source_url', 'routing_error'):
            if key in option:
                value = option[key]
                if value is not None and (not isinstance(value, str) or len(value) > 3000):
                    raise ValueError(f'route.{key} must be a bounded string or null')
                if key == 'retrieved_at' and value is not None: _timestamp(value, 'route.retrieved_at')
                route[key] = value
        for key in ('stale', 'cache'):
            if key in option: route[key] = _boolean(option[key], f'route.{key}')
        identity_input = [shipment_id, destination_id, route]
        candidate_id = hashlib.sha256(json.dumps(identity_input, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()[:24]
        if candidate_id in identities: raise ValueError('Duplicate rescue route option')
        identities.add(candidate_id)
        hours = seconds / 3600
        required = hours + service + buffer
        margin = None if effective is None else effective - required
        reasons = list(blockers)
        if destination.get('kind') not in ('destination', 'dc'): reasons.append('Node is not a supported delivery destination or distribution center')
        if 'eligible' in destination and not _boolean(destination['eligible'], 'destination.eligible'): reasons.append('Recipient is ineligible')
        if not confirmed: reasons.append('Recipient acceptance is not confirmed in the planning inputs')
        if available < quantity: reasons.append('Net receiving capacity is insufficient for the full load')
        remaining_demand = None
        if destination.get('kind') == 'destination':
            cap = _quantity(destination.get('demand_kg'), 'destination.demand_kg')
            remaining_demand = max(0, cap - destination_used[destination_id])
            if remaining_demand < quantity: reasons.append('Remaining destination demand is insufficient for the full load')
        if effective is None: reasons.append('Modeled quality coverage is unscored')
        elif margin <= _EPS: reasons.append('No positive quality/use-by margin after arrival, service and receiving buffer')
        if hours >= original_hours - _EPS: reasons.append('Route does not shorten the original remaining planning duration')
        dispatchable = destination.get('kind') == 'destination'
        candidates.append({'id': candidate_id, 'shipment_id': shipment_id, 'lot_id': lot['id'], 'truck_id': truck['id'],
            'destination_id': destination_id, 'destination_name': str(destination.get('name') or destination_id), 'destination_kind': destination.get('kind'),
            'original_destination': destination_id == shipment['destination'], 'dispatchable': dispatchable,
            'eligible': not reasons, 'reasons': reasons,
            'review_notes': [] if dispatchable else ['Distribution-center contingency only; core dispatch does not serve this transfer node'],
            'quantity_kg': _kg(quantity), 'duration_seconds': seconds, 'distance_m': meters,
            'time_saved_hours': _clock(original_hours - hours), 'acceptance_capacity_kg': _kg(available),
            'remaining_destination_demand_kg': None if remaining_demand is None else _kg(remaining_demand),
            'remaining_at_arrival_hours': None if effective is None else _clock(effective - hours),
            'margin_after_receiving_hours': _clock(margin), 'recipient_confirmed': confirmed, 'route': route,
            'requires_human_approval': True})
    candidates.sort(key=lambda row: (not row['eligible'], row['duration_seconds'], row['distance_m'], row['destination_id'], row['id']))
    triggered = effective is not None and effective - original_hours - service - buffer <= _EPS
    recommended = next((row for row in candidates if row['eligible'] and row['dispatchable']), None) if triggered and not blockers else None
    if blockers: status = 'blocked'
    elif effective is None: status = 'unscored'
    elif not triggered: status = 'within_modeled_window'
    elif recommended is not None: status = 'rescue_recommended'
    elif any(row['eligible'] for row in candidates): status = 'review_only_options'
    else: status = 'no_eligible_rescue'
    return {'method_version': VERSION, 'triggered': triggered, 'status': status,
        'original': {'shipment_id': shipment_id, 'destination_id': shipment['destination'],
            'destination_name': str(nodes[shipment['destination']].get('name') or shipment['destination']),
            'remaining_planning_hours': original_hours, 'required_hours_with_receiving': original_hours + service + buffer,
            'remaining_quality_hours': _clock(quality), 'use_by_remaining_hours': _clock(use_by), 'effective_remaining_hours': _clock(effective),
            'margin_after_receiving_hours': None if effective is None else _clock(effective - original_hours - service - buffer),
            'duration_provenance': 'caller-supplied remaining travel assumption' if original_remaining_hours is not None else 'fixed shipment planning duration; not a live vehicle ETA'},
        'candidates': candidates, 'recommended_candidate_id': None if recommended is None else recommended['id'],
        'dispatch_blockers': blockers, 'receiving_buffer_hours': buffer, 'service_hours': service,
        'requires_human_approval': True, 'operational_state_modified': False,
        'provenance': 'Read-only route ranking against caller-supplied projected quality hours, provided use-by cap and explicit receiving assumptions. No route provider was queried by this calculation.',
        'limitations': list(RESCUE_LIMITATIONS)}
