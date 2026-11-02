"""Read-only, six-hour supply-chain planning projections over simulated inputs.

This combines the existing fixed-trip allocation and uncalibrated thermal
scenario functions. It is not a fitted delay, failure or consumer-illness model.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import math
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field

from backend.cold_chain import project_temperature
from backend.evidence_assistant import _canonical, _read_database, _validate_network
from backend.event_impact import event_snapshot_id
from backend.optimization import optimize, SCENARIOS
from backend.paths import ROOT
from backend.simulation import EVENTS


HORIZON_HOURS = 6
METRICS = ('total_logistics_cost','unmet_demand_kg','selected_shipments',
           'supplied_kg','affected_shipments','review_priority_count','food_waste_kg')
PROVENANCE = {
    'model_kind':'deterministic planning projection',
    'network_input':'simulated network and fixed candidate trips; not real supply contracts',
    'weather_input':'user planning assumption; not an observed weather value or fetched forecast',
    'cargo_input':'simulated current cargo temperature; not physical sensor telemetry',
    'travel_input':'fixed origin-destination planning duration, including already recorded simulated delays; no new road routing',
    'model_performance':'No prospective delay or cargo-failure skill is established here. Saved FSIS sampling model evaluation remains a separate scientific task.',
}
LIMITATIONS = [
    'This is a relative one-wave simulation with a six-hour thermal check horizon, not today\'s dispatch schedule, a live ETA or a learned forecast.',
    'Added delay is applied uniformly to every candidate as an explicit planning assumption; it is not estimated from road closures or weather.',
    'Thermal coefficients are uncalibrated. A projected value above the 4°C demonstration review level is not a regulatory finding, pathogen-growth estimate or consumer-illness probability.',
    'Projected temperatures flag candidates for review only. They do not replace current cargo readings, create holds, or enter scenario C as newly observed excursions.',
    'Scenario C holds remain proposed until separate human approval. Held, recalled and ineligible stock stays excluded under every allocation.',
    'Scenario D can substitute eligible simulated lots on fixed trips; no route geometry, stop order or truck assignment is redesigned here.',
    'Candidate counts include trips that may never be selected. Shared stock, capacity, demand, deadlines and eligibility are checked jointly by the actual allocation solver.',
    'Baseline means a newly computed scenario-A allocation of the current inputs, not the current approved driver-assignment list.',
    'Unmet demand and stock are one-wave quantities, not a rolling inventory ledger. Unsent stock is not automatically food waste.',
    'Changed allocations are observed solver comparisons, not a causal proof of why one particular trip was selected.',
    'No event, proposal, assignment, source refresh, model training or approval is performed by this calculation.',
]


class DeliveryOutlookRequest(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False,str_strip_whitespace=True)
    expected_network_revision:int=Field(ge=0,strict=True)
    added_delay_minutes:int=Field(default=0,ge=0,le=240,strict=True)
    ambient_temperature_c:float=Field(default=30,ge=-20,le=45,strict=True)
    fault_truck_id:str|None=Field(default=None,pattern=r'^[A-Za-z0-9_.-]{1,64}$')


class _OutlookRoute(APIRoute):
    def get_route_handler(self):
        handler=super().get_route_handler()
        async def validated(request):
            try: return await handler(request)
            except RequestValidationError as error:
                # JSON decoders can accept 1e999/NaN; do not echo an invalid
                # floating value into a JSON error response and cause a 500.
                raise HTTPException(422,'Check the current integer revision, 0–240 whole delay minutes, a finite -20–45°C ambient assumption and an optional simulated truck ID.') from error
        return validated


def _summary(result):
    return {
        'scenario':result['scenario'],'name':result['name'],
        'total_logistics_cost':result['total_logistics_cost'],
        'unmet_demand_kg':result['unmet_demand_kg'],
        'selected_shipments':len(result['shipments']),
        'supplied_kg':sum(row['quantity_kg'] for row in result['shipments']),
        'affected_shipments':result['affected_shipments'],
        'review_priority_count':result['review_priority_count'],
        'food_waste_kg':result['food_waste_kg'],
        'solver_status':result['solver_status'],'feasible':result['feasible'],
        'constraint_violations':result['constraint_violations'],
        'constraint_review_passed':result['review']['passed'],
        'proposed_hold_lots':list(result['proposed_hold_lots']),
        'selected_ids':sorted(row['id'] for row in result['shipments']),
        'selected_lots':{row['id']:row['lot_id'] for row in sorted(result['shipments'],key=lambda row:row['id'])},
        'requires_human_approval':True,
    }


def _validate(network,revision,delay,ambient,fault):
    try: _validate_network(network)
    except (ValueError,TypeError,KeyError,OverflowError) as error:
        raise HTTPException(503,'The simulated network is incomplete or unsupported; no outlook was produced') from error
    if type(revision) is not int or revision<0:
        raise HTTPException(503,'The captured network revision is unsupported')
    if len(network['shipments'])>50 or len(network['lots'])>24 or len(network['trucks'])>20:
        raise HTTPException(503,'Delivery outlook is bounded to 50 candidates, 24 lots and 20 trucks')
    if type(delay) is not int or not 0<=delay<=240 or type(ambient) not in (int,float) or not math.isfinite(ambient) or not -20<=ambient<=45:
        raise HTTPException(422,'Use an added delay from 0–240 minutes and ambient assumption from -20–45°C')
    truck=next((row for row in network['trucks'] if row['id']==fault),None) if fault is not None else None
    if fault is not None and truck is None: raise HTTPException(404,'Choose a known simulated truck for the fault assumption')
    if truck is not None and not truck['refrigerated']:
        raise HTTPException(422,'The selected truck has no refrigeration equipment to fail; choose a refrigerated simulated truck')
    events=network.get('events')
    if not isinstance(events,list) or len(events)>5000:
        raise HTTPException(503,'Recorded simulated event history is missing or exceeds the inspection bound')
    identities={row['id'] for row in network['shipments']}
    if any(not isinstance(event,dict) or event.get('type') not in EVENTS or event.get('shipment_id') not in identities for event in events):
        raise HTTPException(503,'Recorded simulated event history is unsupported; no missing fault state was assumed')


def build_delivery_outlook(network,revision,assignments,added_delay_minutes=0,ambient_temperature_c=30,fault_truck_id=None):
    """Pure fixed-input comparison. None of the supplied records are modified."""
    _validate(network,revision,added_delay_minutes,ambient_temperature_c,fault_truck_id)
    before=deepcopy(network);after=deepcopy(network)
    for row in after['shipments']: row['estimated_hours']+=added_delay_minutes/60
    if fault_truck_id is not None:
        next(truck for truck in after['trucks'] if truck['id']==fault_truck_id)['eligible']=False
    try:
        original=optimize(before,'A')
        results={scenario:optimize(after,scenario) for scenario in SCENARIOS}
    except (ValueError,TypeError,OverflowError,KeyError) as error:
        raise HTTPException(503,'The allocation inputs could not be evaluated; no outlook or decision was produced') from error
    if not original['feasible'] or any(not result['feasible'] for result in results.values()):
        raise HTTPException(503,'A feasible allocation was not returned within the bounded calculation; no delivery outlook was produced')
    for result in [original,*results.values()]:
        review=result.get('review')
        if (type(result.get('constraint_violations')) is not int or result['constraint_violations']!=0
                or not isinstance(review,dict) or review.get('passed') is not True
                or review.get('violations')!=[]):
            raise HTTPException(503,'Independent allocation checks did not pass; no delivery outlook was produced')
    baseline=_summary(original);current=_summary(results['A'])
    parameters={'added_delay_minutes':added_delay_minutes,'ambient_temperature_c':float(ambient_temperature_c),'fault_truck_id':fault_truck_id}
    source_id=event_snapshot_id(network,revision,assignments)
    snapshot_id=hashlib.sha256(_canonical({'network_snapshot_id':source_id,'parameters':parameters})).hexdigest()
    previous={row['id']:row for row in before['shipments']}
    trucks={row['id']:row for row in after['trucks']}
    destinations={row['id']:row for row in after['nodes'] if row['kind']=='destination'}
    faults={previous[event['shipment_id']]['truck_id'] for event in network['events'] if event['type']=='refrigeration_fault'}
    exclusions={row['shipment_id']:row['reasons'] for row in results['A']['review']['excluded_shipments']}
    rows=[]
    for shipment in after['shipments']:
        truck=trucks[shipment['truck_id']]
        user_fault=truck['id']==fault_truck_id
        existing_fault=truck['id'] in faults
        no_refrigeration=not truck['refrigerated']
        uncontrolled=user_fault or existing_fault or no_refrigeration
        duration=shipment['estimated_hours'];check_hours=min(duration,HORIZON_HOURS)
        thermal=project_temperature(check_hours*60,initial_c=shipment['temperature_c'],ambient_c=ambient_temperature_c,refrigeration_fault=uncontrolled)
        check=thermal['projection'][-1]
        fault_source=('user planning assumption' if user_fault else 'recorded simulated refrigeration-fault event' if existing_fault else 'no refrigeration; passive-warming assumption' if no_refrigeration else 'normal refrigeration assumption')
        destination=destinations[shipment['destination']]
        name=destination.get('name')
        if not isinstance(name,str) or not 0<len(name)<=256: name=destination['id']
        rows.append({
            'id':shipment['id'],'truck_id':shipment['truck_id'],'lot_id':shipment['lot_id'],
            'destination_id':shipment['destination'],'destination_name':name,'quantity_kg':shipment['quantity_kg'],
            'duration_before_hours':previous[shipment['id']]['estimated_hours'],'duration_after_hours':duration,
            'deadline_hours':shipment['deadline_hours'],'deadline_margin_hours':shipment['deadline_hours']-duration,
            'misses_deadline':duration>shipment['deadline_hours'],
            'selected_in_baseline':shipment['id'] in baseline['selected_ids'],
            'selected_after_A':shipment['id'] in current['selected_ids'],
            'exclusion_reasons':exclusions.get(shipment['id'],[]),
            'temperature':{
                'checked_hours':check_hours,
                'checkpoint':'at_modeled_arrival' if duration<=HORIZON_HOURS else 'at_6h_horizon',
                'projected_temperature_c':check['temperature_c'],'max_temperature_c':thermal['max_temperature_c'],
                'time_above_threshold_minutes':thermal['time_above_threshold_minutes'],
                'review_required':thermal['status']=='review','refrigeration_fault':user_fault or existing_fault,
                'thermal_control_unavailable':uncontrolled,
                'fault_source':fault_source,'initial_temperature_c':shipment['temperature_c'],
                'provenance':thermal['provenance'],'assumptions':thermal['assumptions'],
            },
        })
    summary={
        'total_demand_kg':sum(row['demand_kg'] for row in destinations.values()),
        'before_unmet_demand_kg':baseline['unmet_demand_kg'],'after_unmet_demand_kg':current['unmet_demand_kg'],
        'unmet_demand_change_kg':current['unmet_demand_kg']-baseline['unmet_demand_kg'],
        'selected_shipments_before':baseline['selected_shipments'],'selected_shipments_after':current['selected_shipments'],
        'candidate_deadline_misses':sum(row['misses_deadline'] for row in rows),
        'candidate_temperature_reviews':sum(row['temperature']['review_required'] for row in rows),
        'candidate_shipments':len(rows),
    }
    coverage=[]
    for identity,destination in destinations.items():
        supplied_before=sum(row['quantity_kg'] for row in original['shipments'] if row['destination']==identity)
        supplied_after=sum(row['quantity_kg'] for row in results['A']['shipments'] if row['destination']==identity)
        name=destination.get('name')
        if not isinstance(name,str) or not 0<len(name)<=256:name=identity
        coverage.append({'id':identity,'name':name,'demand_kg':destination['demand_kg'],
                         'supplied_before_kg':supplied_before,'supplied_after_kg':supplied_after,
                         'unmet_before_kg':destination['demand_kg']-supplied_before,
                         'unmet_after_kg':destination['demand_kg']-supplied_after})
    comparisons=[]
    for scenario,result in results.items():
        result_summary=_summary(result)
        comparisons.append({'scenario':scenario,'name':SCENARIOS[scenario],'summary':result_summary,
                            'delta_vs_baseline':{key:result_summary[key]-baseline[key] for key in METRICS}})
    delta=summary['unmet_demand_change_kg']
    takeaways=[
        f"Under these assumptions, scenario A selects {current['selected_shipments']} of {len(rows)} candidate trips and allocates {current['supplied_kg']:,} kg; {current['unmet_demand_kg']:,} kg of simulated demand remains unmet.",
        f"Compared with the current inputs, these chosen delay/fault assumptions change scenario-A unmet demand by {delta:+,} kg. This is an observed planning comparison, not a learned forecast.",
        f"{summary['candidate_deadline_misses']} candidate trips exceed their relative delivery deadlines. Candidate checks include trips that may never be selected.",
        f"{summary['candidate_temperature_reviews']} candidates have a modeled temperature above the 4°C demonstration review level during their checked window, capped at six hours. Review flags do not create holds.",
    ]
    return {'kind':'delivery_outlook','snapshot_id':snapshot_id,'network_snapshot_id':source_id,
            'network_revision':revision,'generated_at':datetime.now(timezone.utc).isoformat(),
            'read_only':True,'simulation':True,'operational_state_modified':False,
            'planning_horizon_hours':HORIZON_HOURS,'parameters':parameters,'provenance':dict(PROVENANCE),
            'baseline':baseline,'scenarios':comparisons,'summary':summary,'shipments':rows,'destinations':coverage,
            'takeaways':takeaways,'limitations':list(LIMITATIONS),
            'review_links':[{'view':'command','label':'Compare current response plans'},{'view':'roads','label':'Inspect separate road evidence'},{'view':'dispatch','label':'Open human dispatcher review'}]}


def create_delivery_outlook_router(db_path,root=ROOT):
    router=APIRouter(tags=['Read-only delivery planning outlook'],route_class=_OutlookRoute)
    def capture():
        selected=db_path() if callable(db_path) else db_path
        workspace=Path(root() if callable(root) else root)
        network,revision,assignments,_=_read_database(selected,workspace)
        return network,revision,assignments

    @router.post('/api/delivery-outlook')
    def outlook(request:DeliveryOutlookRequest):
        network,revision,assignments=capture()
        if revision!=request.expected_network_revision:
            raise HTTPException(409,'The network changed. Reload the current inputs before calculating an outlook.')
        result=build_delivery_outlook(network,revision,assignments,request.added_delay_minutes,request.ambient_temperature_c,request.fault_truck_id)
        current,current_revision,current_assignments=capture()
        if event_snapshot_id(current,current_revision,current_assignments)!=result['network_snapshot_id']:
            raise HTTPException(409,'Network or assignments changed during calculation. Reload and calculate again.')
        return result
    return router
