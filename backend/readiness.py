"""Read-only diagnostics for approved simulated assignments.

This report distinguishes existing hard allocation constraints from outstanding
human workflow records. Passing the checklist is a request for final human
review, never a dispatch command, product-safety certification or road clearance.
"""
from collections import Counter
from datetime import datetime, timezone
import json
import math

from fastapi import APIRouter

from backend.adapters import now


LIMITATIONS = [
    'Read-only diagnostics for simulated assignments; this report does not dispatch cargo, consume inventory, create a hold or approve a decision.',
    'Ready for review means the listed checks passed, not that a shipment is safe, legally cleared or authorized to depart.',
    'Capacity and stock are checked across the current one-wave allocation. Multi-stop sequencing, commercial-truck restrictions and live road clearance are not validated here.',
    'Acknowledgments and verification are local human-recorded workflow evidence, not authenticated identity, laboratory results or physical sensor observations.',
    'A predictive score alone never creates a hard block. This refers to FSIS sampling-risk scores; an explicitly approved modeled quality-window constraint is separate. Consequential disposition still requires human approval.',
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


def _utc_now():
    return datetime.now(timezone.utc)


def _aware_timestamp(value):
    if not isinstance(value, str) or len(value) > 80:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo is not None and parsed.utcoffset() is not None else None
    except (ValueError, OverflowError):
        return None


def _table_exists(connection, name):
    return connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def freshness_review_records(connection, network_revision, assignments, instant=None, network=None):
    """Read bounded optional monitoring context; never create tables or clear lots.

    Relevant contexts are the current approval revision, a retained assignment
    rescue-session link, or the lot's approved quality-source link. A normal plan
    reapproval cannot erase the lot link. Unrelated experiments confer no clearance.
    Only outstanding reviews are returned; an empty list is not safety approval.
    """
    instant = instant or _utc_now()
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError('Freshness monitoring requires a timezone-aware clock')
    instant = instant.astimezone(timezone.utc)
    assignments = [row for row in assignments if isinstance(row, dict) and isinstance(row.get('id'), str)]
    lots = {row['id']: row for row in network.get('lots', []) if isinstance(row, dict) and isinstance(row.get('id'), str)} if isinstance(network, dict) else {}
    links = {}
    for assignment in assignments:
        link = assignment.get('freshness_rescue')
        if isinstance(link, dict) and isinstance(link.get('session_id'), str):
            links.setdefault(link['session_id'], []).append(assignment)
        lot = lots.get(assignment.get('lot_id'), {})
        if isinstance(lot.get('quality_session_id'), str):
            linked = links.setdefault(lot['quality_session_id'], [])
            if assignment not in linked: linked.append(assignment)
    records = []

    def add(session_id, assignment, reasons, *, latest=None, approved=None, source=None,
            observed=None, max_gap=None, age=None, context=None, basis=None):
        if not reasons:
            return
        context = context or ('lot_quality_link' if lots.get(assignment.get('lot_id'), {}).get('quality_session_id') == session_id else 'assignment_link')
        if approved is None and context == 'lot_quality_link':
            stored_version = lots.get(assignment.get('lot_id'), {}).get('quality_source_version')
            if type(stored_version) is int and stored_version >= 1: approved = stored_version
        records.append(dict(session_id=session_id, shipment_id=assignment['id'], lot_id=assignment.get('lot_id'),
            reason=' '.join(reasons), reasons=reasons, latest_version=latest, approved_version=approved,
            source=source, observed_at=observed, max_gap_minutes=max_gap, telemetry_age_minutes=age,
            context=context, timestamp_basis=basis, quality_only=True,
            provenance='Read-only freshness-context review; no lot hold, route change, sensor measurement or safety clearance is created.'))

    if not _table_exists(connection, 'freshness_sessions'):
        for session_id, linked in sorted(links.items()):
            for assignment in linked:
                add(session_id, assignment, ['The linked freshness experiment is unavailable. Ask the dispatcher to review its latest quality context.'])
        return records
    columns = {row[1] for row in connection.execute('PRAGMA table_info(freshness_sessions)')}
    if not {'id', 'payload', 'version'} <= columns:
        for session_id, linked in sorted(links.items()):
            for assignment in linked:
                add(session_id, assignment, ['The linked freshness-monitoring schema is unsupported. Dispatcher review is required.'])
        return records
    # The core retains at most forty sessions. SQL bounds each inspected payload
    # before transferring it, rather than loading arbitrary database text first.
    rows = connection.execute(
        'SELECT id,CASE WHEN length(CAST(payload AS BLOB))<=? THEN payload ELSE NULL END,version '
        'FROM freshness_sessions ORDER BY rowid DESC LIMIT 40', (2 * 1024 * 1024,)).fetchall()
    frames_available = _table_exists(connection, 'freshness_frames')
    frame_columns = {row[1] for row in connection.execute('PRAGMA table_info(freshness_frames)')} if frames_available else set()
    frames_available = frames_available and {'session_id', 'device_id', 'observed_at'} <= frame_columns
    seen = set()
    for session_id, encoded, latest_version in rows:
        seen.add(session_id)
        try:
            meta = json.loads(encoded)
            if not isinstance(meta, dict): raise ValueError('context is not an object')
        except (TypeError, ValueError, RecursionError):
            for assignment in links.get(session_id, []):
                add(session_id, assignment, ['The linked freshness context cannot be inspected within its supported bounds. Dispatcher review is required.'])
            continue
        approval = meta.get('approval')
        approval = approval if isinstance(approval, dict) else {}
        same_approval = type(approval.get('network_revision')) is int and approval['network_revision'] == network_revision
        devices = meta.get('devices')
        devices_valid = isinstance(devices, list) and len(devices) <= 24 and all(isinstance(row, dict) for row in devices)
        mapped = {}
        if devices_valid:
            for device in devices:
                if isinstance(device.get('lot_id'), str) and isinstance(device.get('device_id'), str):
                    mapped.setdefault(device['lot_id'], []).append(device)
        relevant = [assignment for assignment in assignments
            if assignment in links.get(session_id, []) or same_approval and assignment.get('lot_id') in mapped]
        if not relevant:
            continue
        latest_valid = type(latest_version) is int and latest_version >= 1
        source = meta.get('source') if meta.get('source') in ('simulated_replay', 'gateway_reported') else None
        latest_observations = {}
        if source == 'gateway_reported' and frames_available:
            latest_observations = dict(connection.execute(
                'SELECT device_id,CASE WHEN length(MAX(observed_at))<=80 THEN MAX(observed_at) ELSE NULL END '
                'FROM freshness_frames WHERE session_id=? AND length(device_id)<=100 GROUP BY device_id LIMIT 25',
                (session_id,)).fetchall())
        for assignment in relevant:
            linked = assignment in links.get(session_id, [])
            lot = lots.get(assignment.get('lot_id'), {})
            lot_linked = lot.get('quality_session_id') == session_id
            approved_version = lot.get('quality_source_version') if lot_linked else approval.get('sensor_version')
            approved_valid = type(approved_version) is int and approved_version >= 1
            context = 'lot_quality_link' if lot_linked else 'assignment_link' if linked else 'current_approval'
            reasons = []
            if not approved_valid or not latest_valid:
                reasons.append('The approved and latest freshness versions cannot be verified. Dispatcher review is required.')
            elif latest_version > approved_version:
                reasons.append('Cargo freshness inputs changed after approval. Ask the dispatcher to review the latest sensor and planning context while safely parked.')
            elif latest_version < approved_version:
                reasons.append('The stored freshness version precedes its approval record. Dispatcher review is required.')
            if source is None:
                reasons.append('The freshness source kind is unavailable; no live sensor coverage is inferred.')
            lot_devices = mapped.get(assignment.get('lot_id'), [])
            if not devices_valid or not lot_devices:
                reasons.append('The assignment lot has no inspectable device mapping in its linked freshness context.')
            observed = None; max_gap = None; age = None; basis = None
            if source == 'gateway_reported':
                times = []
                for device in lot_devices:
                    profile = device.get('profile')
                    gap = _number(profile.get('max_gap_minutes')) if isinstance(profile, dict) else None
                    if gap is None or not 0 < gap <= 1440:
                        reasons.append('The mapped gateway sensor gap limit is unavailable; coverage age needs review.')
                        continue
                    raw_time = latest_observations.get(device['device_id'])
                    reported = _aware_timestamp(raw_time)
                    used_fallback = False
                    if reported is None:
                        # Evaluation time is retained only as declared metadata;
                        # it never substitutes for an actual per-device reading.
                        reported = _aware_timestamp(meta.get('evaluation_at'))
                        raw_time = meta.get('evaluation_at')
                        used_fallback = True
                        reasons.append('Mapped gateway observations are unavailable. The session evaluation timestamp does not verify per-device coverage.')
                    if reported is None:
                        reasons.append('The gateway observation/evaluation timestamp is unavailable; quality coverage needs review.')
                        continue
                    minutes = (instant - reported).total_seconds() / 60
                    if minutes < -5:
                        reasons.append('The reported gateway observation is more than five minutes in the future; its clock needs review.')
                    elif minutes > gap:
                        reasons.append('Gateway observations are older than the declared sensor gap limit; quality coverage needs dispatcher review.')
                    times.append((max(0, minutes) / gap, raw_time, max(0, minutes), gap, used_fallback))
                if times:
                    # Keep the age and gap from the SAME most-constrained device;
                    # unrelated sensors must not synthesize a new coverage claim.
                    bottleneck = max(times, key=lambda item: item[0])
                    observed = bottleneck[1]; age = round(bottleneck[2], 3); max_gap = bottleneck[3]
                    basis = 'session_evaluation_at_fallback' if bottleneck[4] else 'gateway_reported_observation'
            add(session_id, assignment, list(dict.fromkeys(reasons)), latest=latest_version if latest_valid else None,
                approved=approved_version if approved_valid else None, source=source, observed=observed,
                max_gap=max_gap, age=age, context=context, basis=basis)
    for session_id in sorted(set(links) - seen):
        for assignment in links[session_id]:
            add(session_id, assignment, ['The linked freshness experiment is unavailable in the bounded monitoring snapshot. Dispatcher review is required.'])
    return sorted(records, key=lambda row: (row['shipment_id'], str(row['session_id'])))


def build_readiness(network, revision, rows, freshness_reviews=None):
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
        if 'quality_receiving_buffer_hours' in assignment or canonical and 'quality_receiving_buffer_hours' in canonical:
            immutable_fields += ('quality_receiving_buffer_hours',)
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
        if lot is not None and 'quality_remaining_hours' in lot:
            quality = _number(lot.get('quality_remaining_hours'))
            buffer = _number(assignment.get('quality_receiving_buffer_hours', 0))
            valid = (lot.get('quality_coverage_complete') is True and quality is not None and quality >= 0
                     and hours is not None and hours >= 0 and buffer is not None and buffer >= 0)
            passed = valid and hours + buffer < quality
            hard('quality_window', 'Modeled quality delivery window', passed,
                 f'{hours:g} travel hours plus {buffer:g} receiving-buffer hours against {quality:g} modeled quality hours. This is a planning constraint, not a hold or food-safety clearance.'
                 if valid else 'Modeled quality coverage, remaining hours or receiving buffer are unavailable or invalid. Review the quality plan; no automatic hold or safety finding is created.')
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
        pending_freshness = [row for row in freshness_reviews or [] if row.get('shipment_id') == shipment_id]
        if pending_freshness:
            workflow('freshness_telemetry_review', 'Freshness inputs since approval', False,
                     ' '.join(dict.fromkeys(row['reason'] for row in pending_freshness)))
        blockers = [item['id'] for item in checks if item['status'] == 'blocked']
        reviews = [item['id'] for item in checks if item['status'] == 'review_required']
        assignments.append(dict(
            shipment_id=shipment_id, truck_id=truck_id if isinstance(truck_id, str) else None,
            lot_id=lot_id if isinstance(lot_id, str) else None,
            status='blocked' if blockers else 'review_required' if reviews else 'ready_for_review',
            checks=checks, blockers=blockers, reviews_required=reviews,
            **({'freshness_reviews': pending_freshness} if pending_freshness else {}),
        ))
    summary = dict(total_assignments=len(assignments),
                   **{status: sum(item['status'] == status for item in assignments)
                      for status in ('blocked', 'review_required', 'ready_for_review')})
    return dict(network_revision=revision, checked_at=now(), assignments=assignments,
                summary=summary, resources=resources, limitations=LIMITATIONS,
                **({'freshness_reviews': freshness_reviews} if freshness_reviews else {}),
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
            decoded = []
            for _, encoded, _ in rows:
                try:
                    assignment = json.loads(encoded)
                    if isinstance(assignment, dict): decoded.append(assignment)
                except (ValueError, TypeError):
                    pass  # Existing readiness diagnostics report the corrupt row.
            reviews = freshness_review_records(connection, revision, decoded, network=network)
            return build_readiness(network, revision, rows, reviews)

    return router
