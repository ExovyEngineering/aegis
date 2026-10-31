"""Stored sensor experiments, conditional quality clocks and human-reviewed rescue.

Logistics are simulated. Gateway readings are gateway-reported, not authenticated
product traceability or verified sensor calibration. No quality estimate clears
food safety or automatically publishes a route, hold or warehouse transaction.
"""
from contextlib import closing
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import sqlite3
import uuid

from fastapi import APIRouter, Header, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field

from backend.adapters import distance, OSRMRoutingAdapter
from backend.evidence_assistant import _read_database, _validate_network
from backend.freshness_kinetics import MAX_READINGS, evaluate_freshness, normalize_profile
from backend.freshness_planning import compare_fefo, rank_rescue_options
from backend.optimization import optimize
from backend.paths import ROOT
from backend.plan_review import review_plan
from backend.runtime import require_valid_runtime

VERSION='aegis-freshness-workflow-v1'
MAX_FRAMES=12000
MAX_SESSION_BYTES=2*1024*1024
MAX_FRAME_BYTES=32768
HISTORY_LIMIT_HELP='Existing readings and quality budgets were preserved. Continue reviewing existing experiments, or launch a fresh isolated rehearsal for another demonstration.'
LIMITATIONS=[
    'All logistics, receiving agreements, warehouse placement and replay sensors in this application are simulated.',
    'Q10 coefficients and starting quality ages are illustrative assumptions, not a trained AI model, calibrated poultry shelf life or molecular freshness measurement.',
    'A temperature-driven quality estimate cannot establish pathogen safety, extend a supplied use-by limit, or replace a food-safety disposition review.',
    'Humidity, vibration and ethylene are contextual readings; no unsupported poultry decay coefficients are applied to them.',
    'Routes begin at the assumed simulated origin. No physical truck position, verified buyer contract, commercial-vehicle clearance or automatic closure avoidance is established.',
    'Replay and gateway ingestion update this experiment only. Human approval separately replaces the checked simulated distribution plan; picks do not consume an inventory ledger.',
]

def stamp():return datetime.now(timezone.utc).isoformat()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(value):return hashlib.sha256(canonical(value).encode()).hexdigest()
def instant(value):
    try:
        parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
        if parsed.tzinfo is None or parsed.utcoffset() is None:raise ValueError('timezone required')
        return parsed.astimezone(timezone.utc)
    except (ValueError,TypeError,AttributeError) as error:raise HTTPException(422,'Use a valid ISO8601 timestamp with its timezone') from error

class SafeRoute(APIRoute):
    def get_route_handler(self):
        handler=super().get_route_handler()
        async def checked(request):
            try:return await handler(request)
            except RequestValidationError as error:raise HTTPException(422,'Check the documented fields, finite sensor units, integer versions and required review confirmations') from error
        return checked

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False,str_strip_whitespace=True)
class Device(Strict):
    device_id:str=Field(pattern=r'^[A-Za-z0-9_.-]{1,64}$')
    lot_id:str=Field(pattern=r'^[A-Za-z0-9_.-]{1,64}$')
    profile:dict
class CreateSession(Strict):
    expected_network_revision:int=Field(ge=0,strict=True)
    shipment_id:str=Field(pattern=r'^[A-Za-z0-9_.-]{1,64}$')
    scenario:str=Field(default='poultry_demo',pattern=r'^(poultry_demo|gateway)$')
    devices:list[Device]=Field(default_factory=list,max_length=24)
class Versioned(Strict):expected_version:int=Field(ge=1,strict=True)
class Replay(Versioned):event:str=Field(pattern=r'^(normal|heat_excursion|road_delay|recovery)$')
class DestinationChoice(Versioned):destination_id:str=Field(pattern=r'^[A-Za-z0-9_.-]{1,64}$')
class RouteChoice(DestinationChoice):routing:str=Field(default='osrm',pattern=r'^(osrm|estimated)$')
class Rebase(Versioned):expected_network_revision:int=Field(ge=0,strict=True)
class RescueApproval(DestinationChoice):
    expected_network_revision:int=Field(ge=0,strict=True)
    proposal_hash:str=Field(pattern=r'^[a-f0-9]{64}$')
    actor:str=Field(min_length=2,max_length=100)
    reason:str=Field(min_length=5,max_length=1000)
    quality_review_confirmed:bool=Field(strict=True)
    recipient_confirmed:bool=Field(strict=True)
    routing_review_confirmed:bool=Field(strict=True)
class SensorFrame(Strict):
    device_id:str=Field(pattern=r'^[A-Za-z0-9_.-]{1,64}$')
    event_id:str=Field(pattern=r'^[A-Za-z0-9_.-]{1,100}$')
    observed_at:str=Field(min_length=10,max_length=64)
    temperature_c:float|None=Field(default=None,ge=-30,le=60,strict=True)
    ambient_temperature_c:float|None=Field(default=None,ge=-50,le=70,strict=True)
    humidity_percent:float|None=Field(default=None,ge=0,le=100,strict=True)
    vibration_g:float|None=Field(default=None,ge=0,le=100,strict=True)
    ethylene_ppm:float|None=Field(default=None,ge=0,le=10000,strict=True)
class Ingest(Strict):
    session_id:str=Field(pattern=r'^[a-f0-9-]{36}$')
    frames:list[SensorFrame]=Field(min_length=1,max_length=128)

def ensure_schema(c):
    c.execute('CREATE TABLE IF NOT EXISTS freshness_sessions (id TEXT PRIMARY KEY,payload TEXT NOT NULL,version INTEGER NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL)')
    c.execute('CREATE TABLE IF NOT EXISTS freshness_frames (session_id TEXT NOT NULL,event_id TEXT NOT NULL,device_id TEXT NOT NULL,observed_at TEXT NOT NULL,payload TEXT NOT NULL,sha256 TEXT NOT NULL,PRIMARY KEY(session_id,event_id),UNIQUE(session_id,device_id,observed_at))')

def stored_object(body,label,maximum):
    """Inspect bounded stored JSON without repairing or replacing its bytes."""
    def invalid_constant(_):raise ValueError('Nonfinite JSON value')
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('Duplicate JSON object key')
            result[key]=value
        return result
    try:
        if not isinstance(body,str):raise ValueError('Expected stored JSON text')
        if len(body.encode('utf-8'))>maximum:raise ValueError('Stored JSON exceeds the inspection bound')
        value=json.loads(body,parse_constant=invalid_constant,object_pairs_hook=unique)
        if not isinstance(value,dict):raise ValueError('Expected a JSON object')
        return value
    except (ValueError,TypeError,RecursionError,UnicodeError) as error:
        raise HTTPException(503,f'{label} could not be inspected: {type(error).__name__}: {str(error)[:250]}. Original stored bytes were preserved.') from error

def session_row(c,sid):
    try:row=c.execute('SELECT substr(payload,1,?),version,created_at,updated_at FROM freshness_sessions WHERE id=?',(MAX_SESSION_BYTES+1,sid)).fetchone()
    except sqlite3.OperationalError:row=None
    if not row:raise HTTPException(404,'Unknown freshness experiment; create one first')
    value=stored_object(row[0],'Stored freshness experiment',MAX_SESSION_BYTES)
    try:
        if type(row[1]) is not int or row[1]<1:raise ValueError('Unsupported stored experiment version')
        required={'network':dict,'network_revision':int,'shipment_id':str,'started_at':str,'evaluation_at':str,
                  'source':str,'devices':list,'routes':dict,'road_delay_minutes':int,'approval_history':list}
        if any(type(value.get(key)) is not kind for key,kind in required.items()):raise ValueError('Required experiment fields are missing or have unsupported types')
        if value['source'] not in {'simulated_replay','gateway_reported'} or value['network_revision']<0 or value['road_delay_minutes']<0:raise ValueError('Unsupported experiment source, revision or delay')
        if 'approval' not in value or value['approval'] is not None and not isinstance(value['approval'],dict):raise ValueError('Unsupported stored approval context')
        if not 1<=len(value['devices'])<=24 or len(value['approval_history'])>20:raise ValueError('Unsupported stored binding or approval-history count')
        _validate_network(value['network'])
        lots={lot['id'] for lot in value['network']['lots']}
        selected=next((trip for trip in value['network']['shipments'] if trip['id']==value['shipment_id']),None)
        if selected is None:raise ValueError('Stored experiment shipment is absent from its captured network')
        devices=[]
        for binding in value['devices']:
            validated=Device.model_validate(binding)
            normalize_profile(validated.profile)
            if validated.lot_id not in lots:raise ValueError('Stored device references an unknown captured lot')
            devices.append(validated)
        if len({device.device_id for device in devices})!=len(devices) or len({device.lot_id for device in devices})!=len(devices):raise ValueError('Stored device/lot bindings are not one to one')
        if selected['lot_id'] not in {device.lot_id for device in devices}:raise ValueError('The selected lot has no stored device binding')
        if instant(value['evaluation_at'])<instant(value['started_at']):raise ValueError('Stored evaluation precedes its quality baseline')
        instant(row[2]);instant(row[3])
    except (ValueError,TypeError,KeyError,HTTPException,RecursionError) as error:
        detail=error.detail if isinstance(error,HTTPException) else str(error)
        raise HTTPException(503,f'Stored freshness experiment has unsupported context: {type(error).__name__}: {str(detail)[:250]}. Original stored bytes were preserved.') from error
    value.update(id=sid,version=row[1],created_at=row[2],updated_at=row[3])
    return value

def frame_rows(c,sid):
    rows=c.execute('SELECT substr(payload,1,?) FROM freshness_frames WHERE session_id=? ORDER BY rowid LIMIT ?',(MAX_FRAME_BYTES+1,sid,MAX_FRAMES+1)).fetchall()
    if len(rows)>MAX_FRAMES:raise HTTPException(503,'Sensor history exceeds its supported bound')
    result=[]
    for row in rows:
        value=stored_object(row[0],'Stored sensor observation',MAX_FRAME_BYTES)
        try:
            frame=SensorFrame.model_validate({key:value.get(key) for key in SensorFrame.model_fields})
            instant(frame.observed_at)
        except (ValueError,TypeError,HTTPException) as error:
            raise HTTPException(503,'Stored sensor observation has unsupported fields or timestamp. Original stored bytes were preserved.') from error
        result.append(value)
    return result

def store(c,meta,version=None):
    version=meta['version']+1 if version is None else version
    body={k:v for k,v in meta.items() if k not in {'id','version','created_at','updated_at'}}
    c.execute('UPDATE freshness_sessions SET payload=?,version=?,updated_at=? WHERE id=?',(canonical(body),version,stamp(),meta['id']))
    return version

def append_frames(c,meta,frames,source):
    devices={item['device_id']:item for item in meta['devices']}
    count=c.execute('SELECT COUNT(*) FROM freshness_frames WHERE session_id=?',(meta['id'],)).fetchone()[0]
    device_counts=dict(c.execute('SELECT device_id,COUNT(*) FROM freshness_frames WHERE session_id=? GROUP BY device_id',(meta['id'],)).fetchall())
    added=0
    for frame in frames:
        body=frame.model_dump() if isinstance(frame,SensorFrame) else deepcopy(frame)
        binding=devices.get(body['device_id'])
        if not binding:raise HTTPException(422,'The sensor device is not bound to a lot in this experiment')
        when=instant(body['observed_at'])
        if when<instant(binding['profile']['started_at']):raise HTTPException(422,'Sensor frame precedes its declared quality-budget baseline')
        if source=='gateway_reported' and when>datetime.now(timezone.utc)+timedelta(minutes=5):raise HTTPException(422,'Gateway observation is more than five minutes in the future')
        identity=digest(body)
        existing=c.execute('SELECT sha256 FROM freshness_frames WHERE session_id=? AND event_id=?',(meta['id'],body['event_id'])).fetchone()
        if existing:
            if existing[0]!=identity:raise HTTPException(409,'Sensor event ID already exists with different contents; original observation preserved')
            continue
        if count+added>=MAX_FRAMES:raise HTTPException(413,'The experiment sensor-history limit has been reached. '+HISTORY_LIMIT_HELP)
        if device_counts.get(body['device_id'],0)>=MAX_READINGS:raise HTTPException(413,f'This device has reached the {MAX_READINGS:,}-reading model limit. '+HISTORY_LIMIT_HELP)
        last=c.execute('SELECT observed_at FROM freshness_frames WHERE session_id=? AND device_id=? ORDER BY rowid DESC LIMIT 1',(meta['id'],body['device_id'])).fetchone()
        if last and when<=instant(last[0]):raise HTTPException(409,'Sensor observations must append in strictly increasing device time; no silent sorting or replacement')
        body.update(lot_id=binding['lot_id'],source_kind=source,source=source,retrieved_at=stamp(),temperature_basis=binding['profile']['temperature_basis'],calibration_status='not independently verified',normalized_observed_at=when.isoformat())
        c.execute('INSERT INTO freshness_frames VALUES (?,?,?,?,?,?)',(meta['id'],body['event_id'],body['device_id'],when.isoformat(),canonical(body),identity));added+=1
        device_counts[body['device_id']]=device_counts.get(body['device_id'],0)+1
    return added

def expected(meta,version):
    if meta['version']!=version:raise HTTPException(409,'Sensor experiment changed; reload its latest version before continuing')


def changed_pick_lots(fefo,fifo):
    """Identify changed allocations or actual pick priorities, not membership alone."""
    def signature(policy):
        quantities={row['lot_id']:row['picked_kg'] for row in policy['lot_totals']}
        priorities={identity:index for index,identity in enumerate(policy['priority_lot_ids'])}
        picks={}
        for index,row in enumerate(policy['picks']):
            picks.setdefault(row['lot_id'],[]).append((index,row['order_id'],row['quantity_kg'],row['warehouse_id'],row['truck_id'],row['destination_id']))
        return quantities,priorities,picks
    first,second=signature(fefo),signature(fifo)
    identities=set(first[0])|set(second[0])
    return sorted(identity for identity in identities
                  if (first[0].get(identity,0)>0 or second[0].get(identity,0)>0)
                  and (first[0].get(identity,0)!=second[0].get(identity,0)
                       or first[1].get(identity)!=second[1].get(identity)
                       or first[2].get(identity,[])!=second[2].get(identity,[])))

def _demo(network,shipment):
    start='2026-10-30T08:00:00-05:00';devices=[]
    for index,lot in enumerate(network['lots']):
        initial=230 if lot['id']==shipment['lot_id'] else 180+(index%5)*8
        profile=normalize_profile({'started_at':start,'reference_temperature_c':4,'reference_life_hours':240,'initial_equivalent_age_hours':initial,'forecast_temperature_c':4,'q10':2,'q10_low':1.5,'q10_high':3,'max_gap_minutes':120,'temperature_basis':'product'})
        devices.append({'device_id':'demo-'+lot['id'],'lot_id':lot['id'],'profile':profile})
    return devices

def _assumed_routes(network,shipment,meta):
    origin=next(row for row in network['nodes'] if row['id']==shipment['origin']);routes=[]
    for node in network['nodes']:
        if node['kind'] not in {'destination','dc'} or node['id']==shipment['origin']:continue
        meters=distance(origin['coordinates'],node['coordinates'])*1.25
        row={'destination_id':node['id'],'duration_seconds':meters/(65000/3600)+meta.get('road_delay_minutes',0)*60,'distance_m':meters,'fallback':True,
             'geometry':{'type':'LineString','coordinates':[origin['coordinates'],node['coordinates']]},
             'provenance':'Estimated haversine ×1.25 at 65 km/h plus chosen road delay; not road geometry or live traffic',
             'recipient_confirmed':node['kind']=='destination','acceptance_capacity_kg':node.get('demand_kg',0) if node['kind']=='destination' else 0}
        # Explicit destination demand is a simulated receiving assumption. DC
        # throughput is never relabeled as available inbound receiving space.
        captured=meta.get('routes',{}).get(node['id'])
        if captured:row.update(deepcopy(captured));row['duration_seconds']+=meta.get('road_delay_minutes',0)*60
        routes.append(row)
    return routes

def _use_by_remaining(meta,evaluation_at):
    deadlines=meta.get('use_by_deadlines') or {lot['id']:(instant(meta['started_at'])+timedelta(hours=lot['shelf_life_hours'])).isoformat() for lot in meta['network']['lots']}
    return {identity:max(0,(instant(deadline)-instant(evaluation_at)).total_seconds()/3600) for identity,deadline in deadlines.items()}

def _quality_network(network,qualities,use_by):
    result=deepcopy(network)
    for lot in result['lots']:
        quality=qualities.get(lot['id'])
        lot.update(quality_remaining_hours=None if quality is None else quality['remaining_quality_hours'],quality_coverage_complete=quality is not None and quality['status']=='estimated',quality_model_version=None if quality is None else quality['model_version'],quality_evaluated_at=None if quality is None else quality['evaluation_at'],quality_observed_at=None if quality is None else quality.get('last_observed_at'))
        lot['shelf_life_hours']=min(lot['shelf_life_hours'],use_by[lot['id']])
    for shipment in result['shipments']:shipment['quality_receiving_buffer_hours']=.5
    return result

def build_snapshot(meta,frames,current_revision):
    network=deepcopy(meta['network']);shipment=next(row for row in network['shipments'] if row['id']==meta['shipment_id'])
    nodes={row['id']:row for row in network['nodes']};qualities={};latest={}
    evaluation=stamp() if meta['source']=='gateway_reported' else meta['evaluation_at']
    use_by=_use_by_remaining(meta,evaluation)
    for device in meta['devices']:
        readings=[row for row in frames if row['device_id']==device['device_id']]
        quality=evaluate_freshness(readings,device['profile'],evaluation)
        quality['last_observed_at']=None if not readings else readings[-1]['observed_at']
        qualities[device['lot_id']]=quality
        if readings:latest[device['lot_id']]=readings[-1]
    selected=qualities[shipment['lot_id']]
    original_hours=shipment['estimated_hours']+meta.get('road_delay_minutes',0)/60
    routes=_assumed_routes(network,shipment,meta)
    ranked=rank_rescue_options(network,shipment['id'],selected['remaining_quality_hours'],routes,receiving_buffer_hours=.5,service_hours=0,original_remaining_hours=original_hours,use_by_remaining_hours=use_by[shipment['lot_id']])
    options=[]
    for row in ranked['candidates']:
        options.append({'destination_id':row['destination_id'],'destination_name':row['destination_name'],'kind':row['destination_kind'],'eligible':row['eligible'],'dispatchable':row['dispatchable'],
            'duration_hours':row['duration_seconds']/3600,'distance_km':row['distance_m']/1000,'quality_margin_hours':row['margin_after_receiving_hours'],
            'fallback':row['route']['fallback'],'provenance':row['route']['provenance'],'geometry':row['route'].get('geometry'),'exclusion_reasons':row['reasons']})
    eligible=[row for row in options if row['eligible'] and row['dispatchable']]
    chosen=next((row for row in eligible if row['destination_id']==meta.get('selected_destination_id')),None) or (eligible[0] if eligible and ranked['triggered'] else None)
    proposal=None;plan=None;plan_error=None
    if chosen and ranked['triggered']:
        proposed=_quality_network(network,qualities,use_by)
        trip=next(row for row in proposed['shipments'] if row['id']==shipment['id'])
        trip.update(destination=chosen['destination_id'],estimated_hours=chosen['duration_hours'],estimated_distance_km=chosen['distance_km'],routing_provenance=chosen['provenance'])
        plan=optimize(proposed,'A',required_shipment_ids=[shipment['id']])
        if not plan['feasible'] or not plan['review']['passed'] or plan['constraint_violations']:
            plan_error='A complete capacity/stock/deadline/quality-feasible rescue plan was not found';plan=None
        else:proposal=digest({'version':VERSION,'session':meta['id'],'sensor_version':meta['version'],'network_revision':meta['network_revision'],'network':meta['network'],'devices':meta['devices'],'frames':digest(frames),
            'destination':{key:chosen[key] for key in ('destination_id','duration_hours','distance_km','geometry','fallback','provenance')},'shipments':plan['shipments']})
    warehouses=[{'id':node['id'],'capacity_kg':node['capacity_kg']} for node in network['nodes'] if node['kind']=='dc']
    lots=[]
    for index,lot in enumerate(network['lots']):
        warehouse=shipment['origin'] if lot['id']==shipment['lot_id'] else warehouses[index%len(warehouses)]['id']
        received=instant(meta['started_at'])-timedelta(hours=12 if lot['id']==shipment['lot_id'] else 48+index)
        lots.append({**lot,'warehouse_id':warehouse,'received_at':received.isoformat(),'remaining_quality_hours':qualities.get(lot['id'],{}).get('remaining_quality_hours'),'use_by_remaining_hours':use_by[lot['id']]})
    orders=[{'id':row['id'],'origin_id':row['origin'],'destination_id':row['destination'],'truck_id':row['truck_id'],'quantity_kg':row['quantity_kg'],
        'travel_hours':row['estimated_hours']+(meta.get('road_delay_minutes',0)/60 if row['truck_id']==shipment['truck_id'] else 0),'service_hours':0,'receiving_buffer_hours':.5,'deadline_hours':row['deadline_hours'],'destination_demand_kg':nodes[row['destination']]['demand_kg']} for row in network['shipments']]
    comparison=compare_fefo(lots,orders,network['trucks'],warehouses,seed=network['seed'],evaluation_at=meta['evaluation_at'])
    if any(value['constraint_review'].get('passed') is not True or value['constraint_review'].get('violations') for value in (comparison['fefo'],comparison['fifo'])):raise ValueError('Independent FEFO/FIFO allocation checks failed')
    def policy(value):
        picks=[{**row,'rank':i+1,'remaining_at_arrival_hours':row.get('remaining_at_arrival_hours',row.get('quality_margin_hours'))} for i,row in enumerate(value['picks'])]
        return {**value,'picks':picks,'supplied_kg':value['total_supplied_kg'],'estimated_expiry_waste_kg':value['projected_expiry_exposure_kg']}
    fefo=policy(comparison['fefo']);fifo=policy(comparison['fifo'])
    sensor=latest.get(shipment['lot_id'])
    quality={**selected,'coverage':{**selected['coverage'],'complete':selected['coverage']['complete_under_hold_assumption'],'warnings':selected['warnings']},'initial_remaining_reference_hours':max(0,selected['profile']['reference_life_hours']-selected['profile']['initial_equivalent_age_hours']),
        'sensitivity':{**selected['sensitivity'],'lower_hours':selected['sensitivity']['remaining_hours_at_forecast_temperature']['lower'],'upper_hours':selected['sensitivity']['remaining_hours_at_forecast_temperature']['upper']},
        'timeline':[{**row,'observed_at':row['end_at'],'equivalent_age_hours':row['cumulative_equivalent_age_hours']} for row in selected['timeline']]}
    approval=meta.get('approval')
    status='active'
    if approval:status='stale' if current_revision!=approval['network_revision'] else 'approved' if approval['sensor_version']==meta['version'] else 'review_required'
    elif current_revision!=meta['network_revision'] or meta.get('_assignments_changed'):status='stale'
    summary=None if not plan else {'assignments_count':len(plan['shipments']),'total_logistics_cost':plan['total_logistics_cost'],'unmet_demand_kg':plan['unmet_demand_kg'],'constraint_violations':plan['constraint_violations'],'solver_status':plan['solver_status']}
    return {'id':meta['id'],'version':meta['version'],'network_revision':meta['network_revision'],'current_network_revision':current_revision,'simulation':True,'status':status,
        'created_at':meta['created_at'],'updated_at':meta['updated_at'],
        'shipment':{**shipment,'origin_name':nodes[shipment['origin']]['name'],'destination_name':nodes[shipment['destination']]['name'],'origin':nodes[shipment['origin']]['coordinates'],'destination':nodes[shipment['destination']]['coordinates'],'original_duration_hours':original_hours,'original_distance_km':shipment['estimated_distance_km']},
        'sensor':sensor,'readings':[row for row in frames if row['lot_id']==shipment['lot_id']][-360:],'freshness':quality,
        'rescue':{'triggered':ranked['triggered'],'reason':ranked['status'],'original_required_hours':ranked['original']['required_hours_with_receiving'],'receiving_buffer_hours':.5,'options':options,
            'proposal_id':None if proposal is None else 'rescue-'+proposal[:16],'proposal_hash':proposal,'proposed_destination_id':None if chosen is None else chosen['destination_id'],'plan_summary':summary,'proposed_assignments':[] if plan is None else plan['shipments'],'plan_error':plan_error,'limitations':ranked['limitations']},
        'fefo':{'status':'computed','feasible':fefo['feasible'] and fifo['feasible'],'solver_status':fefo['solver_status'],'fefo':fefo,'fifo':fifo,'changed_pick_lots':changed_pick_lots(fefo,fifo),'limitations':comparison['limitations']},
        'approval':approval,'approval_history':meta.get('approval_history',[]),
        'provenance':{'model_kind':selected['model_kind'],'telemetry':meta['source'],'logistics':'Simulated network; assumed warehouse placements and receiving acceptance. No actual contracts or physical vehicle location.'},
        'gateway':{'configured':len(os.getenv('AEGIS_SENSOR_INGEST_TOKEN',''))>=32,'endpoint':'/api/freshness/telemetry','notice':'Gateway bearer token stays server-side. Registered device/source declarations do not establish physical calibration or real lot traceability.'},
        'limitations':list(LIMITATIONS)}

def create_freshness_router(db,load,record,db_path,root=ROOT):
    router=APIRouter(prefix='/api/freshness',tags=['Freshness planning'],route_class=SafeRoute)
    getroot=lambda:Path(root() if callable(root) else root)
    getpath=lambda:Path(db_path() if callable(db_path) else db_path)
    def read(sid):
        network,revision,_,db_metadata=_read_database(getpath(),getroot())
        with closing(sqlite3.connect(getpath().resolve().as_uri()+'?mode=ro',uri=True,timeout=5)) as c:
            c.execute('PRAGMA query_only=ON');c.execute('PRAGMA trusted_schema=OFF');c.execute('BEGIN')
            meta=session_row(c,sid);frames=frame_rows(c,sid)
        meta['_assignments_changed']=bool(meta.get('assignments_snapshot_id') and meta['assignments_snapshot_id']!=db_metadata['assignments_sha256'])
        return meta,frames,network,revision
    @router.get('/context')
    def context():
        network,revision,_,_=_read_database(getpath(),getroot())
        nodes={row['id']:row for row in network['nodes']};lots={row['id']:row for row in network['lots']};trucks={row['id']:row for row in network['trucks']}
        shipments=[{**row,'origin_name':nodes[row['origin']]['name'],'destination_name':nodes[row['destination']]['name'],'freshness_session_id':lots[row['lot_id']].get('quality_session_id')} for row in network['shipments']]
        eligible=[row for row in shipments if not lots[row['lot_id']]['held'] and not lots[row['lot_id']]['recalled'] and lots[row['lot_id']]['eligible'] and trucks[row['truck_id']]['eligible'] and trucks[row['truck_id']]['refrigerated']]
        demo=next((row['id'] for row in eligible if row['id']=='SH05'),None) or (max(eligible,key=lambda row:row['estimated_hours'])['id'] if eligible else None)
        summaries=[];session_errors=[]
        with closing(sqlite3.connect(getpath().resolve().as_uri()+'?mode=ro',uri=True,timeout=5)) as c:
            try:rows=c.execute('SELECT id FROM freshness_sessions ORDER BY created_at DESC LIMIT 40').fetchall()
            except sqlite3.OperationalError:rows=[]
            for row in rows:
                try:
                    meta=session_row(c,row[0])
                    summaries.append({'id':meta['id'],'version':meta['version'],'created_at':meta['created_at'],'shipment_id':meta['shipment_id']})
                except HTTPException as error:
                    session_errors.append({'session_id':row[0],'error':str(error.detail)})
        notes=list(LIMITATIONS)
        if session_errors:notes.append(f'{len(session_errors)} stored experiment(s) could not be inspected and are not listed as usable. Their IDs and errors are reported in session_errors; original bytes were preserved.')
        return {'network_revision':revision,'simulation':True,'shipments':shipments,'demo_shipment_id':demo,'sessions':summaries,'session_errors':session_errors,
            'gateway':{'configured':len(os.getenv('AEGIS_SENSOR_INGEST_TOKEN',''))>=32,'endpoint':'/api/freshness/telemetry','notice':'Keyless replay works now. External gateway ingestion requires a server-configured token, registered devices and a declared quality baseline; no physical feed has been verified.'},'limitations':notes}
    @router.post('/sessions')
    def create(request:CreateSession):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');ensure_schema(c);network,revision=load(c)
            if revision!=request.expected_network_revision:raise HTTPException(409,'Network changed; reload before starting a freshness experiment')
            _validate_network(network)
            shipment=next((row for row in network['shipments'] if row['id']==request.shipment_id),None)
            if not shipment:raise HTTPException(404,'Unknown simulated shipment')
            tracked=next(lot for lot in network['lots'] if lot['id']==shipment['lot_id']).get('quality_session_id')
            if tracked:raise HTTPException(409,'This lot already has a reviewed exposure history. Open its linked experiment and refresh that planning context; a new session cannot reset consumed quality age. Use a fresh isolated rehearsal for an independent demonstration.')
            if c.execute('SELECT COUNT(*) FROM freshness_sessions').fetchone()[0]>=40:raise HTTPException(409,'This local demo supports forty retained freshness experiments. Continue reviewing existing experiments, or launch a fresh isolated rehearsal for another demonstration.')
            if request.scenario=='poultry_demo':
                if request.devices:raise HTTPException(422,'Replay uses its explicitly seeded simulated sensors; gateway devices cannot be silently ignored')
                devices=_demo(network,shipment);source='simulated_replay'
            else:
                if not request.devices:raise HTTPException(422,'Gateway mode requires explicit device/lot/profile bindings')
                known={row['id'] for row in network['lots']};devices=[]
                for device in request.devices:
                    if device.lot_id not in known:raise HTTPException(422,'Device binding references an unknown simulated lot')
                    try:profile=normalize_profile(device.profile)
                    except ValueError as error:raise HTTPException(422,str(error)) from error
                    if instant(profile['started_at'])>datetime.now(timezone.utc):raise HTTPException(422,'Gateway quality baseline cannot be in the future')
                    devices.append({'device_id':device.device_id,'lot_id':device.lot_id,'profile':profile})
                if len({row['device_id'] for row in devices})!=len(devices) or len({row['lot_id'] for row in devices})!=len(devices):raise HTTPException(422,'Each device and lot must have one explicit binding')
                if shipment['lot_id'] not in {row['lot_id'] for row in devices}:raise HTTPException(422,'The selected shipment lot has no bound device')
                source='gateway_reported'
            created=stamp();sid=str(uuid.uuid4());start=next(row['profile']['started_at'] for row in devices if row['lot_id']==shipment['lot_id'])
            cap_baseline=instant(start) if source=='simulated_replay' else instant(created)
            meta={'id':sid,'version':1,'created_at':created,'updated_at':created,'network':network,'network_revision':revision,'shipment_id':shipment['id'],'started_at':start,'evaluation_at':start,'source':source,'devices':devices,'road_delay_minutes':0,'routes':{},'selected_destination_id':None,'approval':None,'approval_history':[],
                'use_by_deadlines':{lot['id']:(cap_baseline+timedelta(hours=lot['shelf_life_hours'])).isoformat() for lot in network['lots']},
                'assignments_snapshot_id':digest(c.execute('SELECT id,payload,acknowledged FROM assignments ORDER BY id').fetchall())}
            c.execute('INSERT INTO freshness_sessions VALUES (?,?,?,?,?)',(sid,canonical({k:v for k,v in meta.items() if k not in {'id','version','created_at','updated_at'}}),1,created,created))
            if source=='simulated_replay':
                frames=[]
                for step in (0,60):
                    for device in devices:frames.append({'device_id':device['device_id'],'event_id':f'initial-{step}-{device["lot_id"]}','observed_at':(instant(start)+timedelta(minutes=step)).isoformat(),'temperature_c':4.,'ambient_temperature_c':30.,'humidity_percent':78.,'vibration_g':.03,'ethylene_ppm':.02})
                append_frames(c,meta,frames,source);meta['evaluation_at']=(instant(start)+timedelta(hours=1)).isoformat();store(c,meta,version=1)
            record(c,'operator','freshness_session',{'session_id':sid,'shipment_id':shipment['id'],'source':source,'simulation':True})
        return get_session(sid)
    @router.get('/sessions/{sid}')
    def get_session(sid:str):
        meta,frames,_,revision=read(sid)
        try:return build_snapshot(meta,frames,revision)
        except (ValueError,TypeError,KeyError,OverflowError) as error:raise HTTPException(503,f'Freshness calculation abstained: {type(error).__name__}: {error}') from error
    @router.post('/sessions/{sid}/replay')
    def replay(sid:str,request:Replay):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');ensure_schema(c);meta=session_row(c,sid);expected(meta,request.expected_version)
            if meta['source']!='simulated_replay':raise HTTPException(409,'Simulated frames cannot be mixed into gateway-reported sensor history')
            begin=instant(meta['evaluation_at']);frames=[]
            points=[(1,16.),(121,4.)] if request.event=='heat_excursion' else [(30,4.)] if request.event=='normal' else [(15,4.)]
            lot=next(row['lot_id'] for row in meta['network']['shipments'] if row['id']==meta['shipment_id'])
            for minutes,temp in points:
                for device in meta['devices']:
                    frames.append({'device_id':device['device_id'],'event_id':f'v{meta["version"]}-{minutes}-{device["lot_id"]}','observed_at':(begin+timedelta(minutes=minutes)).isoformat(),'temperature_c':temp if device['lot_id']==lot else 4.,'ambient_temperature_c':32. if request.event=='heat_excursion' else 30.,'humidity_percent':83. if request.event=='heat_excursion' else 78.,'vibration_g':.22 if request.event=='road_delay' else .03,'ethylene_ppm':.04 if request.event=='heat_excursion' else .02})
            append_frames(c,meta,frames,'simulated_replay');meta['evaluation_at']=(begin+timedelta(minutes=points[-1][0])).isoformat()
            if request.event=='road_delay':meta['road_delay_minutes']+=60
            meta['selected_destination_id']=None;store(c,meta)
            record(c,'operator','freshness_replay',{'session_id':sid,'shipment_id':meta['shipment_id'],'event':request.event,'frames_added':len(frames),'operational_state_modified':False})
        return get_session(sid)
    @router.post('/telemetry')
    def ingest(request:Ingest,authorization:str|None=Header(default=None)):
        token=os.getenv('AEGIS_SENSOR_INGEST_TOKEN','')
        if len(token)<32:raise HTTPException(503,'External sensor gateway is disabled; configure AEGIS_SENSOR_INGEST_TOKEN with at least 32 characters server-side')
        supplied=authorization[7:] if authorization and authorization.startswith('Bearer ') else ''
        if not hmac.compare_digest(token,supplied):raise HTTPException(401,'Sensor gateway authentication failed')
        with db() as c:
            c.execute('BEGIN IMMEDIATE');ensure_schema(c);meta=session_row(c,request.session_id)
            if meta['source']!='gateway_reported':raise HTTPException(409,'Gateway data cannot be mixed into a simulated replay; create an explicitly bound gateway experiment')
            added=append_frames(c,meta,request.frames,'gateway_reported')
            if added:
                meta['evaluation_at']=max([instant(meta['evaluation_at'])]+[instant(row.observed_at) for row in request.frames]).isoformat();meta['selected_destination_id']=None;version=store(c,meta)
            else:version=meta['version']
        return {'accepted':added,'duplicates':len(request.frames)-added,'session_id':request.session_id,'version':version,'source':'gateway_reported','physical_calibration_verified':False,'operational_state_modified':False}
    @router.post('/sessions/{sid}/proposal')
    def choose(sid:str,request:DestinationChoice):
        snapshot=get_session(sid)
        if snapshot['version']!=request.expected_version:raise HTTPException(409,'Sensor experiment changed; reload before preparing a rescue')
        option=next((row for row in snapshot['rescue']['options'] if row['destination_id']==request.destination_id and row['eligible'] and row['dispatchable']),None)
        if not snapshot['rescue']['triggered'] or not option:raise HTTPException(409,'This destination is not an eligible rescue under the captured assumptions')
        with db() as c:
            c.execute('BEGIN IMMEDIATE');meta=session_row(c,sid);expected(meta,request.expected_version);meta['selected_destination_id']=request.destination_id;store(c,meta)
        return get_session(sid)
    @router.post('/sessions/{sid}/rebase')
    def rebase(sid:str,request:Rebase):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');meta=session_row(c,sid);expected(meta,request.expected_version);network,revision=load(c)
            if revision!=request.expected_network_revision:raise HTTPException(409,'Current network changed; reload before refreshing planning context')
            current_trip=next((trip for trip in network['shipments'] if trip['id']==meta['shipment_id']),None)
            if current_trip is None:raise HTTPException(409,'The captured shipment no longer exists in the current network; its exposure history remains available for inspection')
            linked=next((lot.get('quality_session_id') for lot in network['lots'] if lot['id']==current_trip['lot_id']),None)
            if linked and linked!=sid:raise HTTPException(409,'A different reviewed exposure history is bound to this lot. Reopen that linked experiment; older counterfactual readings cannot overwrite its consumed quality budget.')
            if meta.get('approval'):meta['approval_history']=(meta.get('approval_history',[])+[meta['approval']])[-20:]
            meta.update(network=network,network_revision=revision,approval=None,selected_destination_id=None,routes={},assignments_snapshot_id=digest(c.execute('SELECT id,payload,acknowledged FROM assignments ORDER BY id').fetchall()));store(c,meta)
        return get_session(sid)
    @router.post('/sessions/{sid}/routes')
    def road_route(sid:str,request:RouteChoice):
        meta,_,_,_=read(sid);expected(meta,request.expected_version)
        trip=next(row for row in meta['network']['shipments'] if row['id']==meta['shipment_id']);nodes={row['id']:row for row in meta['network']['nodes']}
        destination=nodes.get(request.destination_id)
        if not destination or destination['kind'] not in {'destination','dc'}:raise HTTPException(422,'Choose a supported simulated destination')
        coordinates=[nodes[trip['origin']]['coordinates'],destination['coordinates']]
        runtime=require_valid_runtime(getpath(),root=getroot())
        if request.routing=='osrm' and not (runtime['isolated'] and runtime['offline']):result=OSRMRoutingAdapter().route(coordinates)
        else:
            meters=distance(*coordinates)*1.25;result={'fallback':True,'provenance':'Estimated haversine ×1.25 at 65 km/h; not road geometry','payload':{'routes':[{'duration':meters/(65000/3600),'distance':meters,'geometry':{'type':'LineString','coordinates':coordinates}}]}}
        try:
            row=result['payload']['routes'][0]
            if not all(type(row[key]) in (int,float) and math.isfinite(row[key]) and row[key]>=0 for key in ('duration','distance')):raise ValueError('Invalid route metrics')
            geometry=row['geometry']
            points=geometry.get('coordinates',[])
            if (geometry.get('type')!='LineString' or not isinstance(points,list) or not 2<=len(points)<=20000
                    or any(not isinstance(point,(list,tuple)) or len(point)!=2 or any(type(value) not in (int,float) or not math.isfinite(value) for value in point) or abs(point[0])>180 or abs(point[1])>90 for point in points)
                    or distance(points[0],coordinates[0])>5000 or distance(points[-1],coordinates[-1])>5000):raise ValueError('Invalid or unrelated line geometry')
        except (KeyError,TypeError,ValueError,IndexError) as error:raise HTTPException(503,'Route response could not be validated; previous estimate preserved') from error
        route={'duration_seconds':row['duration'],'distance_m':row['distance'],'geometry':geometry,'fallback':result.get('fallback',False),'provenance':result.get('provenance','OSRM ordinary-driving route; commercial restrictions/closures unvalidated'),'retrieved_at':result.get('retrieved_at',stamp())}
        with db() as c:
            c.execute('BEGIN IMMEDIATE');latest=session_row(c,sid);expected(latest,request.expected_version);latest['routes'][request.destination_id]=route;latest['selected_destination_id']=None;store(c,latest)
        return get_session(sid)
    @router.post('/sessions/{sid}/approve')
    def approve(sid:str,request:RescueApproval):
        if not all((request.quality_review_confirmed,request.recipient_confirmed,request.routing_review_confirmed)):raise HTTPException(422,'Quality/safety disposition, receiving capacity and route/vehicle review all require explicit confirmation')
        with db() as c:
            c.execute('BEGIN IMMEDIATE');meta=session_row(c,sid);expected(meta,request.expected_version);network,revision=load(c)
            if revision!=request.expected_network_revision or revision!=meta['network_revision'] or digest(network)!=digest(meta['network']):raise HTTPException(409,'Network changed; refresh the planning context and review a fresh rescue plan')
            if meta.get('assignments_snapshot_id')!=digest(c.execute('SELECT id,payload,acknowledged FROM assignments ORDER BY id').fetchall()):raise HTTPException(409,'Assignments or instructions changed; refresh planning context before replacing the reviewed plan')
            if meta.get('approval'):raise HTTPException(409,'This rescue was already approved; refresh planning context for any further review')
            frames=frame_rows(c,sid);snapshot=build_snapshot(meta,frames,revision);rescue=snapshot['rescue']
            if not rescue['proposal_hash'] or not hmac.compare_digest(rescue['proposal_hash'],request.proposal_hash) or rescue['proposed_destination_id']!=request.destination_id:raise HTTPException(409,'Rescue proposal changed or is not feasible; review the current captured plan')
            proposed=deepcopy(network)
            use_by=_use_by_remaining(meta,stamp() if meta['source']=='gateway_reported' else meta['evaluation_at'])
            # Copy only quality fields calculated for this exact reviewed sensor
            # history; never change a hold, recall, eligibility or use-by cap.
            for lot in proposed['lots']:
                lot['shelf_life_hours']=min(lot['shelf_life_hours'],use_by[lot['id']])
                lot.update(quality_session_id=sid,quality_source_version=meta['version']+1)
                device=next((row for row in meta['devices'] if row['lot_id']==lot['id']),None)
                if device:
                    readings=[row for row in frames if row['device_id']==device['device_id']]
                    quality=evaluate_freshness(readings,device['profile'],stamp() if meta['source']=='gateway_reported' else meta['evaluation_at'])
                    lot.update(quality_remaining_hours=quality['remaining_quality_hours'],quality_coverage_complete=quality['status']=='estimated',quality_model_version=quality['model_version'],quality_evaluated_at=quality['evaluation_at'],quality_observed_at=None if not readings else readings[-1]['observed_at'])
                else:lot.update(quality_remaining_hours=None,quality_coverage_complete=False,quality_model_version=None,quality_observed_at=None)
            option=next(row for row in rescue['options'] if row['destination_id']==request.destination_id)
            for trip in proposed['shipments']:
                trip['quality_receiving_buffer_hours']=.5
                if trip['id']==meta['shipment_id']:trip.update(destination=request.destination_id,estimated_hours=option['duration_hours'],estimated_distance_km=option['distance_km'],routing_provenance=option['provenance'])
            fresh=optimize(proposed,'A',required_shipment_ids=[meta['shipment_id']]);checked=review_plan(proposed,fresh['shipments'],(), 'A')
            if not fresh['feasible'] or not checked['passed'] or fresh['shipments']!=rescue['proposed_assignments']:raise HTTPException(409,'Rescue plan failed independent revalidation; no assignments were changed')
            c.execute('DELETE FROM assignments')
            for assignment in fresh['shipments']:
                assignment['instruction']='Dispatcher approved simulated freshness-rescue plan; verify quality disposition and vehicle routing separately. Park before interacting.'
                if assignment['id']==meta['shipment_id']:
                    assignment['instruction']+=f' Save the Load: reviewed destination {request.destination_id}; estimated quality margin {option["quality_margin_hours"]:.2f} h under declared assumptions.'
                    assignment['freshness_rescue']={'session_id':sid,'source_version':meta['version'],'quality_margin_hours':option['quality_margin_hours'],'route':option['geometry'],'route_fallback':option['fallback'],'quality_only':True}
                c.execute('INSERT INTO assignments VALUES (?,?,0)',(assignment['id'],canonical(assignment)))
            c.execute('UPDATE state SET payload=?,revision=? WHERE id=1',(canonical(proposed),revision+1))
            approval={'actor':request.actor,'reason':request.reason,'approved_at':stamp(),'network_revision':revision+1,'assignments_count':len(fresh['shipments']),'selected_destination_id':request.destination_id,'sensor_version':meta['version']+1,'simulation':True}
            meta['approval']=approval;store(c,meta)
            record(c,request.actor,'freshness_rescue_approve',{'session_id':sid,'shipment_id':meta['shipment_id'],'destination_id':request.destination_id,'proposal_hash':request.proposal_hash,'network_revision':revision+1,'assignments_count':len(fresh['shipments']),'reason':request.reason,'quality_review_confirmed':True,'recipient_confirmed':True,'routing_review_confirmed':True})
        return {'snapshot':get_session(sid),'receipt':approval}
    return router
