"""Read-only diagnostics for approved simulated assignments.

This report distinguishes existing hard allocation constraints from outstanding
human workflow records. Passing the checklist is a request for final human
review, never a dispatch command, product-safety certification or road clearance.
"""
from collections import Counter
import json
import math

from fastapi import APIRouter

from backend.adapters import now


LIMITATIONS = [
    'Read-only diagnostics for simulated assignments; this report does not dispatch cargo, consume inventory, create a hold or approve a decision.',
    'Ready for review means the listed checks passed, not that a shipment is safe, legally cleared or authorized to depart.',
    'Capacity and stock are checked across the current one-wave allocation. Multi-stop sequencing, commercial-truck restrictions and live road clearance are not validated here.',
    'Acknowledgments and verification are local human-recorded workflow evidence, not authenticated identity, laboratory results or physical sensor observations.',
    'A predictive score alone never creates a hard block. Any consequential disposition still requires the explicit human approval workflow.',
]


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        return value if math.isfinite(value) else None
    except OverflowError:
        return None


def _check(identity, label, category, status, detail):
    return dict(id=identity, label=label, category=category, status=status, detail=detail)


def build_readiness(network, revision, rows):
    """Evaluate a supplied database snapshot without changing any of its records."""
    lots = {item['id']: item for item in network['lots']}
    trucks = {item['id']: item for item in network['trucks']}
    nodes = {item['id']: item for item in network['nodes']}
    candidates = {item['id']: item for item in network['shipments']}
    decoded = []
    usage = {key: Counter() for key in ('lot', 'truck', 'origin', 'supplier', 'destination')}
    for shipment_id, encoded, acknowledged in rows:
        try:
            payload = json.loads(encoded)
            if not isinstance(payload, dict):
                raise ValueError('assignment payload is not an object')
            error = None
        except (ValueError, TypeError) as exc:
            payload, error = {}, f'Assignment record cannot be evaluated: {exc}'
        decoded.append((shipment_id, payload, acknowledged == 1, error))
        quantity = _number(payload.get('quantity_kg'))
        if quantity is None or quantity <= 0:
            continue
        for kind, identity in (
            ('lot', payload.get('lot_id')), ('truck', payload.get('truck_id')),
            ('origin', payload.get('origin')), ('destination', payload.get('destination')),
        ):
            if isinstance(identity, str):
                usage[kind][identity] += quantity
        lot = lots.get(payload.get('lot_id')) if isinstance(payload.get('lot_id'), str) else None
        if lot:
            usage['supplier'][lot['supplier_id']] += quantity

    resources, resource_lookup = [], {}
    groups = (
        ('lot', lots, 'inventory_kg'), ('truck', trucks, 'capacity_kg'),
        ('origin', {key: value for key, value in nodes.items() if value['kind'] == 'dc'}, 'capacity_kg'),
        ('supplier', {key: value for key, value in nodes.items() if value['kind'] == 'supplier'}, 'capacity_kg'),
        ('destination', {key: value for key, value in nodes.items() if value['kind'] == 'destination'}, 'demand_kg'),
    )
    for kind, records, field in groups:
        for identity, resource in records.items():
            used = _number(usage[kind][identity])
            limit = _number(resource.get(field))
            valid = used is not None and limit is not None and limit >= 0
            passed = valid and used <= limit
            detail = (
                f'{identity}: {used:g} kg allocated against {limit:g} kg.'
                if valid else f'{identity}: aggregate quantity or {field} is missing or invalid.'
            )
            item = dict(kind=kind, id=identity, used_kg=used, limit_kg=limit,
                        remaining_kg=limit-used if valid else None,
                        status='pass' if passed else 'blocked', detail=detail)
            resources.append(item)
            resource_lookup[kind, identity] = item

    assignments = []
    for shipment_id, assignment, acknowledged, decode_error in decoded:
        checks = []

        def hard(identity, label, passed, detail):
            checks.append(_check(identity, label, 'hard_constraint', 'pass' if passed else 'blocked', detail))

        def workflow(identity, label, passed, detail):
            checks.append(_check(identity, label, 'workflow', 'pass' if passed else 'review_required', detail))

        canonical = candidates.get(shipment_id)
        hard('canonical_assignment', 'Current canonical shipment',
             decode_error is None and canonical is not None and assignment.get('id') == shipment_id,
             decode_error or ('Approved record matches a known shipment identifier.'
                              if canonical and assignment.get('id') == shipment_id
                              else 'Approved record has an unknown or inconsistent shipment identifier.'))
        immutable_fields = ('origin', 'destination', 'truck_id', 'quantity_kg', 'estimated_hours', 'deadline_hours')
        mismatches = [key for key in immutable_fields if canonical is None or assignment.get(key) != canonical.get(key)]
        hard('canonical_fields', 'Current shipment assumptions', not mismatches,
             'Approved fields match the current shipment assumptions; eligible lot substitution remains permitted.'
             if not mismatches else 'Current canonical fields differ or are unavailable: ' + ', '.join(mismatches) + '.')
        lot_id, truck_id = assignment.get('lot_id'), assignment.get('truck_id')
        lot = lots.get(lot_id) if isinstance(lot_id, str) else None
        truck = trucks.get(truck_id) if isinstance(truck_id, str) else None
        lot_reasons = []
        if lot is None:
            lot_reasons.append('lot unavailable')
        else:
            if lot.get('held') is not False:
                lot_reasons.append('lot held or hold status unverified')
            if lot.get('recalled') is not False:
                lot_reasons.append('lot recalled or recall status unverified')
            if lot.get('eligible') is not True:
                lot_reasons.append('lot ineligible or eligibility unverified')
        hard('lot_eligibility', 'Lot eligibility and disposition', not lot_reasons,
             '; '.join(lot_reasons) + '.' if lot_reasons else 'Lot is eligible and is neither held nor recalled in the current simulation.')
        hard('truck_eligibility', 'Truck eligibility', bool(truck and truck.get('eligible') is True),
             'Truck is eligible in the current simulation.' if truck and truck.get('eligible') is True
             else 'Truck is missing, ineligible or eligibility is unverified.')
        hard('refrigeration', 'Refrigerated truck', bool(truck and truck.get('refrigerated') is True),
             'Truck is configured as refrigerated; this is not physical equipment verification.'
             if truck and truck.get('refrigerated') is True else 'Truck refrigeration is unavailable or not configured.')
        quantity = _number(assignment.get('quantity_kg'))
        hard('shipment_quantity', 'Positive cargo quantity', quantity is not None and quantity > 0,
             f'Approved quantity: {quantity:g} kg.' if quantity is not None and quantity > 0
             else 'Cargo quantity must be a finite positive number.')
        hours = _number(assignment.get('estimated_hours'))
        deadline = _number(assignment.get('deadline_hours'))
        shelf_life = _number(lot.get('shelf_life_hours')) if lot else None
        for identity, label, limit in (
            ('delivery_deadline', 'Planned delivery deadline', deadline),
            ('shelf_life', 'Planned lot shelf life', shelf_life),
        ):
            valid = hours is not None and limit is not None and hours >= 0 and limit >= 0
            hard(identity, label, valid and hours <= limit,
                 f'{hours:g} planned travel hours against {limit:g} available hours; no live ETA is inferred.'
                 if valid else 'Planned travel time or the applicable limit is missing or invalid.')
        references = (
            ('lot', lot_id, 'aggregate_lot_inventory', 'Allocated lot inventory'),
            ('truck', truck_id, 'aggregate_truck_capacity', 'Allocated truck capacity'),
            ('origin', assignment.get('origin'), 'aggregate_origin_capacity', 'Allocated origin capacity'),
            ('supplier', lot.get('supplier_id') if lot else None, 'aggregate_supplier_capacity', 'Allocated supplier capacity'),
            ('destination', assignment.get('destination'), 'aggregate_destination_demand', 'Destination demand limit'),
        )
        for kind, identity, check_id, label in references:
            resource = resource_lookup.get((kind, identity)) if isinstance(identity, str) else None
            hard(check_id, label, resource is not None and resource['status'] == 'pass',
                 resource['detail'] if resource else f'Current {kind} resource is unknown; allocation cannot be checked.')
        workflow('assignment_acknowledged', 'Driver assignment acknowledgment', acknowledged,
                 'Driver acknowledgment is recorded for this approved assignment.' if acknowledged
                 else 'Driver assignment acknowledgment is outstanding. Review while safely parked.')
        instruction_version = assignment.get('instruction_revision', 0)
        valid_version = isinstance(instruction_version, int) and not isinstance(instruction_version, bool) and instruction_version >= 0
        instruction_complete = valid_version and (instruction_version == 0 or assignment.get('instruction_acknowledged') is True)
        workflow('instruction_acknowledged', 'Current instruction acknowledgment', instruction_complete,
                 'No separately versioned dispatcher instruction is outstanding.' if valid_version and instruction_version == 0
                 else f'Current dispatcher instruction v{instruction_version} is acknowledged.' if instruction_complete
                 else f'Current dispatcher instruction v{instruction_version} requires its own acknowledgment or version review.')
        required = assignment.get('verification_required') is True
        review = assignment.get('verification_review')
        review = review if isinstance(review, dict) else {}
        review_checks = review.get('checks')
        review_context = review.get('context')
        valid_review = (
            assignment.get('verification_status') == 'complete'
            and isinstance(assignment.get('verification_version'), int)
            and not isinstance(assignment.get('verification_version'), bool)
            and assignment['verification_version'] >= 1
            and review.get('status') == 'complete'
            and review.get('version') == assignment['verification_version']
            and isinstance(review_checks, dict)
            and all(review_checks.get(key) is True for key in
                    ('temperature_history_reviewed', 'packaging_condition_reviewed', 'simulated_lot_identity_reviewed'))
            and isinstance(review_context, dict)
            and all(review_context.get(key) == assignment.get(key) for key in ('id', 'lot_id', 'truck_id', 'origin', 'destination'))
        )
        workflow('targeted_verification', 'Requested targeted verification', not required or valid_review,
                 'Targeted verification is not requested by this approved assignment.' if not required
                 else 'A complete dispatcher checklist is recorded for this assignment context; this does not certify product safety.' if valid_review
                 else 'Scenario-B targeted verification is pending, requests further review or lacks a complete matching review record.')
        blockers = [item['id'] for item in checks if item['status'] == 'blocked']
        reviews = [item['id'] for item in checks if item['status'] == 'review_required']
        assignments.append(dict(
            shipment_id=shipment_id, truck_id=truck_id if isinstance(truck_id, str) else None,
            lot_id=lot_id if isinstance(lot_id, str) else None,
            status='blocked' if blockers else 'review_required' if reviews else 'ready_for_review',
            checks=checks, blockers=blockers, reviews_required=reviews,
        ))
    summary = dict(total_assignments=len(assignments),
                   **{status: sum(item['status'] == status for item in assignments)
                      for status in ('blocked', 'review_required', 'ready_for_review')})
    return dict(network_revision=revision, checked_at=now(), assignments=assignments,
                summary=summary, resources=resources, limitations=LIMITATIONS,
                provenance='Read-only checks of current approved simulated assignments and local workflow records.')


def create_readiness_router(db, load):
    router = APIRouter(tags=['Read-only dispatch readiness diagnostics'])

    @router.get('/api/readiness')
    def readiness():
        with db() as connection:
            if not connection.in_transaction:
                connection.execute('BEGIN')
            network, revision = load(connection)
            rows = connection.execute('SELECT id,payload,acknowledged FROM assignments ORDER BY id').fetchall()
            return build_readiness(network, revision, rows)

    return router
