"""Independent checks of a proposed one-wave allocation, separate from the solver."""
from collections import Counter


def hard_exclusions(shipment, lot, truck, proposed_holds=()):
    reasons = []
    if lot['held']: reasons.append('lot held')
    if lot['recalled']: reasons.append('lot recalled')
    if not lot['eligible']: reasons.append('lot ineligible')
    if lot['id'] in proposed_holds: reasons.append('proposed precautionary hold')
    if not truck['eligible']: reasons.append('truck ineligible')
    if not truck['refrigerated']: reasons.append('truck not refrigerated')
    if shipment['estimated_hours'] > shipment['deadline_hours']: reasons.append('delivery deadline exceeded')
    if shipment['estimated_hours'] > lot['shelf_life_hours']: reasons.append('lot shelf life exceeded')
    if 'quality_remaining_hours' in lot:
        import math
        quality=lot['quality_remaining_hours'];buffer=shipment.get('quality_receiving_buffer_hours',0)
        if lot.get('quality_coverage_complete') is not True or type(quality) not in (int,float) or not math.isfinite(quality) or quality<0:
            reasons.append('modeled quality coverage unavailable')
        elif type(buffer) not in (int,float) or not math.isfinite(buffer) or buffer<0 or shipment['estimated_hours']+buffer>=quality:
            reasons.append('modeled quality window exceeded after receiving buffer')
    if lot['inventory_kg'] < shipment['quantity_kg']: reasons.append('insufficient lot inventory for shipment')
    if truck['capacity_kg'] < shipment['quantity_kg']: reasons.append('shipment exceeds truck capacity')
    return reasons


def review_plan(network, selected, proposed_holds=(), scenario='A'):
    """Check canonical candidates, quantities, eligibility and aggregate resource use."""
    lots = {x['id']: x for x in network['lots']}
    trucks = {x['id']: x for x in network['trucks']}
    nodes = {x['id']: x for x in network['nodes']}
    candidates = {x['id']: x for x in network['shipments']}
    usage = {key: Counter() for key in ('lot', 'truck', 'destination', 'origin', 'supplier')}
    violations, seen = [], set()
    for shipment in selected:
        sid = shipment.get('id')
        if sid in seen: violations.append(f'{sid}: duplicate assignment')
        seen.add(sid)
        canonical = candidates.get(sid)
        if canonical is None:
            violations.append(f'{sid}: unknown candidate'); continue
        immutable = ('origin', 'destination', 'truck_id', 'quantity_kg', 'estimated_hours', 'deadline_hours')
        if any(shipment.get(key) != canonical[key] for key in immutable):
            violations.append(f'{sid}: candidate fields changed'); continue
        if scenario != 'D' and shipment.get('lot_id') != canonical['lot_id']:
            violations.append(f'{sid}: lot substitution outside scenario D')
        lot = lots.get(shipment.get('lot_id')); truck = trucks.get(shipment.get('truck_id'))
        if not lot or not truck:
            violations.append(f'{sid}: unknown lot or truck'); continue
        violations.extend(f'{sid}: {reason}' for reason in hard_exclusions(shipment, lot, truck, proposed_holds))
        for group, identity in [('lot', lot['id']), ('truck', truck['id']), ('destination', shipment['destination']), ('origin', shipment['origin']), ('supplier', lot['supplier_id'])]:
            usage[group][identity] += shipment['quantity_kg']
    resources = []
    groups = [('lot', lots, 'inventory_kg'), ('truck', trucks, 'capacity_kg'), ('destination', {k:v for k,v in nodes.items() if v['kind']=='destination'}, 'demand_kg'), ('origin', {k:v for k,v in nodes.items() if v['kind']=='dc'}, 'capacity_kg'), ('supplier', {k:v for k,v in nodes.items() if v['kind']=='supplier'}, 'capacity_kg')]
    for group, records, capacity_key in groups:
        for identity, resource in records.items():
            used, limit = usage[group][identity], resource[capacity_key]
            if used > limit: violations.append(f'{group} {identity}: {used} kg exceeds {limit} kg')
            resources.append({'kind':group, 'id':identity, 'used_kg':used, 'limit_kg':limit, 'remaining_kg':limit-used})
    excluded = []
    for sid, shipment in candidates.items():
        if sid in seen: continue
        eligible_lots = list(lots.values()) if scenario == 'D' else [lots[shipment['lot_id']]]
        by_lot = [hard_exclusions(shipment, lot, trucks[shipment['truck_id']], proposed_holds) for lot in eligible_lots]
        reasons = ['not selected under joint demand, stock, capacity and cost constraints'] if any(not item for item in by_lot) else sorted({reason for item in by_lot for reason in item})
        excluded.append({'shipment_id':sid, 'quantity_kg':shipment['quantity_kg'], 'destination':shipment['destination'], 'reasons':reasons})
    return {'passed':not violations, 'violations':violations, 'resources':resources, 'excluded_shipments':excluded,
            'method':'Independent arithmetic and eligibility checks against the current canonical network; not a solver optimality proof.',
            'exclusion_note':'Reasons describe direct eligibility blocks or joint allocation nonselection, not a counterfactual explanation of the solver.'}
