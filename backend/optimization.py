"""Binary one-wave dispatch optimization, not vehicle routing or truck-safe navigation."""
from ortools.sat.python import cp_model
SCENARIOS={'A':'Baseline distribution','B':'Targeted verification','C':'Precautionary hold pending review','D':'Alternative eligible supply'}
def optimize(network,scenario='A'):
    if scenario not in SCENARIOS: raise ValueError('Unknown scenario')
    m=cp_model.CpModel(); shipments=network['shipments']; lots={l['id']:l for l in network['lots']}; trucks={t['id']:t for t in network['trucks']}; destinations={n['id']:n for n in network['nodes'] if n['kind']=='destination'}
    choices={}; costs={}; candidate_holds={s['lot_id'] for s in shipments if s['temperature_c']>4} if scenario=='C' else set()
    for i,s in enumerate(shipments):
        eligible_lots=list(lots) if scenario=='D' else [s['lot_id']]
        for lid in eligible_lots:
            lot=lots[lid]; x=m.new_bool_var(f'{i}_{lid}'); choices[i,lid]=x
            if lot['held'] or lot['recalled'] or not lot['eligible'] or lid in candidate_holds or not trucks[s['truck_id']]['eligible'] or not trucks[s['truck_id']]['refrigerated'] or s['estimated_hours']>min(s['deadline_hours'],lot['shelf_life_hours']): m.add(x==0)
            # A model score never creates a hold. C is a proposed human-reviewed scenario.
            cost=round(50+s['estimated_distance_km']*1.4+(75 if scenario=='B' and s['temperature_c']>4 else 0)+(45 if lid!=s['lot_id'] else 0))
            costs[i,lid]=cost
        m.add(sum(choices[i,lid] for lid in eligible_lots)<=1)
    for lid,l in lots.items(): m.add(sum(shipments[i]['quantity_kg']*x for (i,k),x in choices.items() if k==lid)<=l['inventory_kg'])
    for tid,t in trucks.items(): m.add(sum(shipments[i]['quantity_kg']*x for (i,k),x in choices.items() if shipments[i]['truck_id']==tid)<=t['capacity_kg'])
    for did,d in destinations.items(): m.add(sum(shipments[i]['quantity_kg']*x for (i,k),x in choices.items() if shipments[i]['destination']==did)<=d['demand_kg'])
    for dc in [n for n in network['nodes'] if n['kind']=='dc']: m.add(sum(shipments[i]['quantity_kg']*x for (i,k),x in choices.items() if shipments[i]['origin']==dc['id'])<=dc['capacity_kg'])
    for supplier in [n for n in network['nodes'] if n['kind']=='supplier']: m.add(sum(shipments[i]['quantity_kg']*x for (i,k),x in choices.items() if lots[k]['supplier_id']==supplier['id'])<=supplier['capacity_kg'])
    m.maximize(sum((shipments[i]['quantity_kg']*100-costs[i,lid])*x for (i,lid),x in choices.items()))
    solver=cp_model.CpSolver(); solver.parameters.num_search_workers=1; solver.parameters.random_seed=network['seed']; solver.parameters.max_time_in_seconds=10
    status=solver.solve(m); feasible=status in (cp_model.OPTIMAL,cp_model.FEASIBLE)
    selected=[dict(shipments[i],lot_id=lid,logistics_cost=costs[i,lid],instruction='Proposed assignment; requires dispatcher approval',verification_required=scenario=='B' and shipments[i]['temperature_c']>4) for (i,lid),x in choices.items() if feasible and solver.value(x)]
    supplied=sum(s['quantity_kg'] for s in selected); demand=sum(d['demand_kg'] for d in destinations.values())
    return {'scenario':scenario,'name':SCENARIOS[scenario],'solver_status':solver.status_name(status),'feasible':feasible,'shipments':selected,'total_logistics_cost':sum(s['logistics_cost'] for s in selected),'unmet_demand_kg':demand-supplied,'delayed_shipments':sum(s['estimated_hours']>s['deadline_hours'] for s in selected),'affected_shipments':len(shipments)-len(selected),'review_priority_count':sum(s['temperature_c']>4 for s in selected),'food_waste_kg':0,'food_waste_note':'No expiry in one-wave six-hour horizon; unsent stock remains inventory, not waste.','constraint_violations':0 if feasible else None,'proposed_hold_lots':sorted(candidate_holds),'requires_human_approval':True,'limitations':'One-wave allocation with fixed truck/OD estimates. D allows interchangeable simulated lots; rerouting alternatives require separate route review. Costs are simulated dollars.'}
