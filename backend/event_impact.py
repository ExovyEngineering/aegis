"""Preview a simulated disruption using the real one-wave allocation code.

Preview reads use SQLite's read-only connection. The pure builder can also be
called inside the existing explicit event transaction to verify a displayed
preview before applying it. Neither path changes road geometry or dispatches.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from backend.evidence_assistant import _canonical, _read_database, _validate_network
from backend.optimization import SCENARIOS, optimize
from backend.paths import ROOT
from backend.plan_review import hard_exclusions
from backend.simulation import EVENTS, apply_event


EVENT_LABELS = {
    'road_closure': 'Simulated road closure',
    'severe_weather': 'Simulated severe weather',
    'delivery_delay': 'Simulated delivery delay',
    'refrigeration_fault': 'Simulated refrigeration fault',
    'temperature_excursion': 'Simulated cargo temperature excursion',
    'inventory_shortage': 'Simulated inventory shortage',
}
METRICS = ('total_logistics_cost', 'unmet_demand_kg', 'delayed_shipments',
           'affected_shipments', 'review_priority_count', 'food_waste_kg',
           'selected_shipments', 'supplied_kg')
FIELD_LABELS = {
    'estimated_hours': ('Planning travel duration', 'hours'),
    'deadline_margin_hours': ('Deadline margin', 'hours'),
    'temperature_c': ('Simulated cargo temperature', '°C'),
    'lot_inventory_kg': ('Shared lot inventory', 'kg'),
    'truck_eligible': ('Truck eligible for allocation', None),
    'review_priority': ('Operational review priority', None),
}
LIMITATIONS = [
    'All disruption effects, logistics entities, costs and cargo values here are simulated. This is not an official road closure, sensor observation or verified recall.',
    'Road closure, severe weather and delivery delay each add the simulator\'s fixed two-hour planning delay to the selected candidate. They do not derive delay from live event geometry or alter a road route.',
    'The allocation solver uses fixed truck/origin/destination estimates. Scenario D can substitute eligible simulated lots; it does not reroute, reorder stops or switch trucks.',
    'Travel duration and deadline margin are relative planning hours, not a departure time, arrival timestamp or live ETA.',
    'Scenario C holds are proposals until a separate human approval. A predicted or simulated temperature does not automatically create a mandatory hold.',
    'A changed optimum lists observed plan differences, not a causal explanation of solver choices. Unchanged totals can still hide different selected candidates or lots.',
    'Stock is a one-wave capacity assumption, not a rolling inventory ledger. Unsent inventory is not automatically food waste.',
    'Applying any event through the explicit existing simulator clears every approved assignment, including unrelated trips. This preview clears none.',
]


class EventPreviewRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    event: Literal['road_closure', 'severe_weather', 'delivery_delay',
                   'refrigeration_fault', 'temperature_excursion', 'inventory_shortage']
    shipment_id: str = Field(pattern=r'^[A-Za-z0-9_.-]{1,64}$')
    expected_network_revision: int = Field(ge=0, strict=True)


def _assignments(rows):
    """Normalize the reader and main transaction's parsed assignment records."""
    normalized = []
    for row in rows:
        normalized.append({key: row.get(key) for key in
                           ('id', 'lot_id', 'truck_id', 'quantity_kg', 'verification_status')})
        normalized[-1].update(acknowledged=row.get('acknowledged') in (True, 1),
                              verification_required=row.get('verification_required') is True)
    return sorted(normalized, key=lambda row: row['id'])


def event_snapshot_id(network, revision, assignments):
    """Semantic state identity; no SQL JSON formatting or wall-clock fields."""
    return hashlib.sha256(_canonical({'network':network, 'revision':revision,
                                     'assignments':_assignments(assignments)})).hexdigest()


def _shipment_state(network, shipment_id):
    shipment = next(row for row in network['shipments'] if row['id'] == shipment_id)
    lot = next(row for row in network['lots'] if row['id'] == shipment['lot_id'])
    truck = next(row for row in network['trucks'] if row['id'] == shipment['truck_id'])
    return {
        **{key:shipment.get(key) for key in ('origin', 'destination', 'truck_id', 'lot_id',
            'quantity_kg', 'estimated_hours', 'estimated_distance_km', 'deadline_hours',
            'temperature_c', 'review_priority', 'routing_provenance')},
        'deadline_margin_hours':round(shipment['deadline_hours']-shipment['estimated_hours'], 6),
        'lot_inventory_kg':lot['inventory_kg'], 'lot_held':lot['held'],
        'lot_recalled':lot['recalled'], 'lot_eligible':lot['eligible'],
        'truck_eligible':truck['eligible'], 'truck_refrigerated':truck['refrigerated'],
        'direct_exclusions':hard_exclusions(shipment, lot, truck),
    }


def _summary(result):
    return {
        **{key:result[key] for key in METRICS if key in result},
        'selected_shipments':len(result['shipments']),
        'supplied_kg':sum(row['quantity_kg'] for row in result['shipments']),
        'solver_status':result['solver_status'], 'feasible':result['feasible'],
        'constraint_violations':result['constraint_violations'],
        'constraint_review_passed':result['review']['passed'],
        'proposed_hold_lots':result['proposed_hold_lots'],
        'selected_ids':sorted(row['id'] for row in result['shipments']),
        'selected_lots':{row['id']:row['lot_id'] for row in sorted(result['shipments'], key=lambda row:row['id'])},
        'verification_required_ids':sorted(row['id'] for row in result['shipments'] if row.get('verification_required')),
    }


def _scenario_comparison(before, after, scenario):
    original = _summary(optimize(before, scenario))
    changed = _summary(optimize(after, scenario))
    previous = set(original['selected_ids']); current = set(changed['selected_ids'])
    return {
        'scenario':scenario, 'name':SCENARIOS[scenario], 'before':original, 'after':changed,
        'delta':{key:changed[key]-original[key] for key in METRICS},
        'added_shipments':sorted(current-previous),
        'removed_shipments':sorted(previous-current),
        'lot_changes':[{'shipment_id':sid, 'before':original['selected_lots'][sid],
                        'after':changed['selected_lots'][sid]}
                       for sid in sorted(previous & current)
                       if original['selected_lots'][sid] != changed['selected_lots'][sid]],
        'proposed_hold_lots_added':sorted(set(changed['proposed_hold_lots'])-set(original['proposed_hold_lots'])),
        'proposed_hold_lots_removed':sorted(set(original['proposed_hold_lots'])-set(changed['proposed_hold_lots'])),
        'verification_added':sorted(set(changed['verification_required_ids'])-set(original['verification_required_ids'])),
        'verification_removed':sorted(set(original['verification_required_ids'])-set(changed['verification_required_ids'])),
    }


def build_event_impact(network, revision, assignments, event, shipment_id):
    """Pure receipt builder. Inputs and operational storage remain untouched."""
    if event not in EVENTS:
        raise HTTPException(422, 'Unsupported simulated event; a verified recall requires genuine traceability')
    try:
        _validate_network(network)
    except (ValueError, TypeError, KeyError, OverflowError) as error:
        raise HTTPException(503, f'Unsupported event-preview network: {error}') from error
    if len(network['shipments']) > 50 or len(network['lots']) > 24 or len(network['trucks']) > 20:
        raise HTTPException(503, 'Event comparison is bounded to 50 candidates, 24 lots and 20 trucks; no event was applied')
    if not isinstance(network.get('events'), list) or len(network['events']) > 5000:
        raise HTTPException(503, 'Event history is absent or exceeds the preview inspection bound')
    if not any(row['id'] == shipment_id for row in network['shipments']):
        raise HTTPException(404, 'Unknown simulated shipment')
    before = deepcopy(network); after = deepcopy(network)
    apply_event(after, event, shipment_id)
    original = _shipment_state(before, shipment_id); changed = _shipment_state(after, shipment_id)
    changes = []
    for field, (label, unit) in FIELD_LABELS.items():
        if original[field] != changed[field]:
            numeric = type(original[field]) in (int,float) and type(changed[field]) in (int,float)
            changes.append({'field':field, 'label':label, 'unit':unit,
                            'before':original[field], 'after':changed[field],
                            'delta':round(changed[field]-original[field], 6) if numeric else None})
    resources = []
    affected = {shipment_id}
    for kind, rows, field, key in (
            ('truck', before['trucks'], 'eligible', 'truck_id'),
            ('lot', before['lots'], 'inventory_kg', 'lot_id')):
        current = {row['id']:row for row in after['trucks' if kind=='truck' else 'lots']}
        for row in rows:
            if row[field] != current[row['id']][field]:
                candidates = sorted(item['id'] for item in before['shipments'] if item[key] == row['id'])
                affected.update(candidates)
                resources.append({'kind':kind, 'id':row['id'], 'field':field,
                                  'before':row[field], 'after':current[row['id']][field],
                                  'candidate_shipments':candidates})
    candidates = []
    for sid in sorted(affected):
        previous = _shipment_state(before, sid); current = _shipment_state(after, sid)
        candidates.append({'shipment_id':sid, 'before_exclusions':previous['direct_exclusions'],
                           'after_exclusions':current['direct_exclusions'],
                           'note':'Direct original-lot checks only; joint allocation and scenario-D alternative lots are separate.'})
    comparisons = [_scenario_comparison(before, after, scenario) for scenario in SCENARIOS]
    result = {
        'network_revision':revision, 'snapshot_id':event_snapshot_id(network, revision, assignments),
        'event':event, 'event_label':EVENT_LABELS[event], 'shipment_id':shipment_id,
        'simulation':True, 'read_only':True, 'operational_state_modified':False,
        'requires_explicit_apply':True,
        'shipment':{'id':shipment_id, 'before':original, 'after':changed, 'changes':changes},
        'route_effects':{
            'geometry_changed':False, 'distance_changed':False, 'stop_order_changed':False,
            'duration_change_hours':round(changed['estimated_hours']-original['estimated_hours'], 6),
            'explanation':'This event changes simulation planning inputs only. It does not recompute OSRM geometry, avoid a closure, reorder stops or publish a driver route. Use route comparison and separate dispatcher approval.'},
        'resource_effects':resources, 'candidate_effects':candidates,
        'assignments':{'current_count':len(assignments), 'would_be_invalidated':len(assignments),
                       'explanation':'Explicitly applying any simulator event clears all approved assignments. This preview keeps them unchanged; generate and approve a fresh plan after an applied event.'},
        'scenarios':comparisons, 'limitations':LIMITATIONS,
        'next_steps':[
            'Inspect the before/after values and all four allocation comparisons; preview has changed nothing.',
            'Apply the simulated event only if this is the intended exercise. Applying clears every approved assignment.',
            'Compare and propose a fresh allocation, then use the separate human approval workflow. Route geometry requires its own route request/review.',
        ],
    }
    result['preview_id'] = hashlib.sha256(_canonical(result)).hexdigest()
    result['generated_at'] = datetime.now(timezone.utc).isoformat()
    return result


def create_event_impact_router(db_path, root=ROOT):
    router = APIRouter(tags=['Read-only simulated event impact'])

    def capture():
        selected = db_path() if callable(db_path) else db_path
        workspace = Path(root() if callable(root) else root)
        network, revision, assignments, _ = _read_database(selected, workspace)
        return network, revision, assignments

    @router.post('/api/events/preview')
    def preview(request:EventPreviewRequest):
        network, revision, assignments = capture()
        if revision != request.expected_network_revision:
            raise HTTPException(409, 'Network changed; reload Command before previewing this event')
        result = build_event_impact(network, revision, assignments, request.event, request.shipment_id)
        current, current_revision, current_assignments = capture()
        if event_snapshot_id(current, current_revision, current_assignments) != result['snapshot_id']:
            raise HTTPException(409, 'Network or assignments changed during event comparison; reload and preview again')
        return result

    return router
