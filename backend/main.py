import json, sqlite3, uuid, os
from typing import Literal
from contextlib import contextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, model_validator
from backend.custom_operations import CustomOperation
from backend.dispatch import ensure_dispatch_schema,create_driver_incident,create_dispatch_router
from backend.paths import ROOT
from backend.simulation import seed_network, apply_event
from backend.optimization import optimize,SCENARIOS
from backend.adapters import now, OSRMRoutingAdapter, OpenMeteoForecastAdapter,NWSAlertsAdapter,NCEIHistoricalAdapter,FSISRecallAdapter,MoDOTAdapter

app=FastAPI(title='AEGIS',description='Local research demo; all logistics entities simulated')
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:5173','http://127.0.0.1:5173'],allow_methods=['*'],allow_headers=['*'])
DB=Path(os.getenv('AEGIS_DB_PATH') or ROOT/'data/aegis.sqlite')
@contextmanager
def db():
    DB.parent.mkdir(exist_ok=True,parents=True)
    conn=sqlite3.connect(DB,timeout=20)
    try:
        conn.execute('CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY, payload TEXT NOT NULL, revision INTEGER NOT NULL)')
        conn.execute('CREATE TABLE IF NOT EXISTS proposals (id TEXT PRIMARY KEY,payload TEXT NOT NULL, revision INTEGER NOT NULL, status TEXT NOT NULL)')
        conn.execute('CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY, timestamp TEXT, actor TEXT, action TEXT, payload TEXT)')
        conn.execute('CREATE TABLE IF NOT EXISTS assignments (id TEXT PRIMARY KEY, payload TEXT, acknowledged INTEGER DEFAULT 0)')
        ensure_dispatch_schema(conn)
        conn.execute('INSERT OR IGNORE INTO state VALUES (1,?,0)',(json.dumps(seed_network()),)); conn.commit()
        yield conn; conn.commit()
    except Exception: conn.rollback(); raise
    finally: conn.close()
def load(c):
    row=c.execute('SELECT payload,revision FROM state WHERE id=1').fetchone(); return json.loads(row[0]),row[1]
def record(c,actor,action,payload): c.execute('INSERT INTO audit(timestamp,actor,action,payload) VALUES (?,?,?,?)',(now(),actor,action,json.dumps(payload)))
def read_report(name,default):
    p=ROOT/'reports'/name; return json.loads(p.read_text(encoding='utf-8')) if p.exists() else default

@app.get('/api/health')
def health(): return {'status':'ok','mode':'local simulated research demo'}
@app.get('/api/network')
def network():
    with db() as c:
        n,rev=load(c); return dict(n,revision=rev)
@app.get('/api/coverage')
def coverage(): return read_report('api_status.json',[])
@app.get('/api/model')
def model(): return read_report('model_evaluation.json',{'status':'not trained; run ingestion and training scripts'})
@app.get('/api/inventory')
def inventory(): return read_report('../data/manifests/inventory.json',{'status':'audit not run'})
@app.get('/api/evidence/{source}')
def evidence(source:str):
    if source not in {'fsis_recalls','nws_alerts','openmeteo','modot','ncei_historical','openmeteo_archive','osrm_route'}: raise HTTPException(404,'Unknown source')
    p=ROOT/f'data/cache/probe_{source}.json'
    if not p.exists():p=ROOT/f'data/fixtures/{source}.json'
    if not p.exists(): return {'status':'unavailable','source':source,'coverage_warning':'No successful dated response captured'}
    result=json.loads(p.read_text())
    from datetime import datetime,timezone
    try:age=max(0,(datetime.now(timezone.utc)-datetime.fromisoformat(result['retrieved_at'])).total_seconds())
    except (KeyError,ValueError,TypeError):age=None
    ttl={'nws_alerts':300,'modot':300,'openmeteo':3600,'fsis_recalls':3600}.get(source,86400)
    result['stale']=bool(result.get('stale')) or age is None or age>ttl
    result['age_seconds']=age
    if source=='osrm_route' and result.get('road_review'):
        try:road_age=(datetime.now(timezone.utc)-datetime.fromisoformat(result['road_review']['modot_retrieved_at'])).total_seconds()
        except (KeyError,ValueError,TypeError):road_age=float('inf')
        if road_age>600:
            result['road_review']['stale']=True
            for item in result['road_review'].get('alternatives',[]):item['review_required']=True
    return dict(result,status='dated cached public response; check retrieval time',live=False,fixture=p.parent.name=='fixtures')
@app.get('/api/facilities')
def facilities():
    import pandas as pd
    paths=list((ROOT/'data/processed').glob('establishments_*.parquet'))
    if not paths:return []
    df=pd.read_parquet(paths[0]); return json.loads(df[['establishment_id','establishment_name','latitude','longitude','activities']].to_json(orient='records'))

class Event(BaseModel):
    event:str
    shipment_id:str
@app.post('/api/events')
def event(request:Event):
    with db() as c:
        c.execute('BEGIN IMMEDIATE'); n,rev=load(c)
        try: apply_event(n,request.event,request.shipment_id)
        except ValueError as e: raise HTTPException(400,str(e))
        c.execute('UPDATE state SET payload=?,revision=? WHERE id=1',(json.dumps(n),rev+1)); c.execute('DELETE FROM assignments'); record(c,'simulator','event',request.model_dump()); return {'revision':rev+1,'assignments_invalidated':True}
@app.post('/api/demo/reset')
def reset():
    with db() as c:
        c.execute('BEGIN IMMEDIATE'); _,rev=load(c); c.execute('UPDATE state SET payload=?,revision=? WHERE id=1',(json.dumps(seed_network()),rev+1)); c.execute('DELETE FROM assignments'); record(c,'operator','reset',{}); return {'revision':rev+1}
@app.get('/api/scenarios')
def scenarios():
    with db() as c: n,rev=load(c)
    return [dict(optimize(n,k),network_revision=rev) for k in SCENARIOS]
@app.post('/api/proposals/{scenario}')
def propose(scenario:str):
    if scenario not in SCENARIOS: raise HTTPException(400,'Unknown scenario')
    with db() as c:
        n,rev=load(c); result=optimize(n,scenario); pid=str(uuid.uuid4()); c.execute('INSERT INTO proposals VALUES (?,?,?,?)',(pid,json.dumps(result),rev,'pending')); return dict(result,id=pid,network_revision=rev)
class Approval(BaseModel):
    model_config=ConfigDict(str_strip_whitespace=True)
    actor:str=Field(min_length=2,max_length=100)
    reason:str=Field(min_length=5,max_length=1000)
@app.post('/api/proposals/{pid}/approve')
def approve(pid:str,request:Approval):
    with db() as c:
        c.execute('BEGIN IMMEDIATE'); n,rev=load(c); row=c.execute('SELECT payload,revision,status FROM proposals WHERE id=?',(pid,)).fetchone()
        if not row: raise HTTPException(404,'Unknown proposal')
        if row[2]!='pending': raise HTTPException(409,'Proposal already processed')
        if row[1]!=rev: raise HTTPException(409,'Network changed; generate a fresh proposal')
        result=json.loads(row[0]); fresh=optimize(n,result['scenario'])
        if not fresh['feasible'] or fresh['shipments']!=result['shipments']: raise HTTPException(409,'Plan failed safety revalidation')
        for lot in n['lots']:
            if lot['id'] in result['proposed_hold_lots']: lot['held']=True
        c.execute('DELETE FROM assignments')
        for s in result['shipments']:
            s['instruction']='Dispatcher approved simulated assignment; park before interacting'
            c.execute('INSERT INTO assignments VALUES (?,?,0)',(s['id'],json.dumps(s)))
        c.execute('UPDATE state SET payload=?,revision=? WHERE id=1',(json.dumps(n),rev+1)); c.execute("UPDATE proposals SET status='approved' WHERE id=?",(pid,)); record(c,request.actor,'approve',dict(request.model_dump(),proposal_id=pid,scenario=result['scenario'])); return {'status':'approved','assignments':len(result['shipments'])}
@app.get('/api/driver')
def driver():
    with db() as c:return [dict(json.loads(r[1]),acknowledged=bool(r[2])) for r in c.execute('SELECT * FROM assignments ORDER BY id')]
@app.post('/api/driver/{sid}/acknowledge')
def acknowledge(sid:str):
    with db() as c:
        if not c.execute('SELECT id FROM assignments WHERE id=?',(sid,)).fetchone():raise HTTPException(404,'No approved assignment')
        c.execute('UPDATE assignments SET acknowledged=1 WHERE id=?',(sid,)); record(c,'simulated driver','acknowledge',{'shipment_id':sid}); return {'status':'acknowledged'}
class Incident(BaseModel):
    model_config=ConfigDict(str_strip_whitespace=True)
    shipment_id:str
    description:str=Field(min_length=5,max_length=2000)
@app.post('/api/driver/incident')
def incident(request:Incident):
    with db() as c:return create_driver_incident(c,request.shipment_id,request.description,record)
@app.get('/api/audit')
def audit():
    with db() as c: return [dict(id=r[0],timestamp=r[1],actor=r[2],action=r[3],payload=json.loads(r[4])) for r in c.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 100')]
class Route(BaseModel):
    coordinates:list[tuple[float,float]]=Field(min_length=2,max_length=20)
    alternatives:bool=False
@app.post('/api/route')
def route(request:Route):
    try:
        result=OSRMRoutingAdapter().route(request.coordinates,request.alternatives)
        from backend.route_review import review_routes
        p=ROOT/'data/cache/probe_modot.json'
        if not p.exists():p=ROOT/'data/fixtures/modot.json'
        modot=json.loads(p.read_text(encoding='utf-8')) if p.exists() else None
        result['road_review']=review_routes(result,modot); return result
    except ValueError as e:raise HTTPException(400,str(e))
@app.get('/api/evidence-summary')
def evidence_summary():return read_report('evidence_ingestion.json',[])
@app.get('/api/noaa-coverage')
def noaa_coverage():return read_report('noaa_coverage.json',{'status':'not acquired','coverage_warning':'Run scripts/acquire_noaa.py; complete historical coverage is not established'})
@app.get('/api/model-timing')
def model_timing():return read_report('model_timing.json',{'status':'not evaluated','prospective_validation':False})
@app.get('/api/operations/presets')
def operation_presets():
    from backend.route_lab import operation_preset
    return [operation_preset(p) for p in ('farm','regional')]
class RouteLabRequest(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    preset:Literal['farm','regional','custom']='farm'
    custom_operation:CustomOperation|None=None
    routing:Literal['estimated','osrm']='estimated'
    truck_count:int|None=Field(default=None,ge=1,le=10)
    truck_capacity_kg:int|None=Field(default=None,ge=100,le=5000)
    max_route_hours:float=Field(default=8,ge=.25,le=16)
    refrigeration_fault:bool=False
    ambient_temperature_c:float=Field(default=30,ge=-30,le=55)
    delay_minutes:int=Field(default=0,ge=0,le=360)
    @model_validator(mode='after')
    def validate_custom_selection(self):
        if self.preset=='custom':
            if self.custom_operation is None:raise ValueError('Custom planning requires custom_operation')
            if self.truck_count is not None or self.truck_capacity_kg is not None:raise ValueError('Custom fleet rows define truck counts/capacities; omit preset overrides')
        elif self.custom_operation is not None:raise ValueError('Select the custom preset to use custom_operation; planning inputs cannot be silently ignored')
        return self
@app.post('/api/route-lab')
def route_lab(request:RouteLabRequest):
    from backend.route_lab import plan_routes
    try:
        params=request.model_dump(exclude={'custom_operation'})
        if request.custom_operation is not None:params['operation']=request.custom_operation.build_operation()
        return plan_routes(**params)
    except ValueError as e:raise HTTPException(400,str(e))
@app.get('/api/shipments/{sid}/exposure')
def shipment_exposure(sid:str):
    from backend.cold_chain import project_temperature
    with db() as c:n,revision=load(c)
    shipment=next((s for s in n['shipments'] if s['id']==sid),None)
    if not shipment:raise HTTPException(404,'Unknown shipment')
    fault=any(e['shipment_id']==sid and e['type']=='refrigeration_fault' for e in n['events'])
    result=project_temperature(min(1440,shipment['estimated_hours']*60),initial_c=shipment['temperature_c'],ambient_c=30,refrigeration_fault=fault)
    return dict(result,shipment_id=sid,network_revision=revision,ambient_provenance='30°C simulated planning assumption; not a current weather observation',advisories=[e for e in n['events'] if e['shipment_id']==sid])
@app.post('/api/refresh/{source}')
def refresh(source:str):
    adapters={'openmeteo':OpenMeteoForecastAdapter,'nws_alerts':NWSAlertsAdapter,'ncei_historical':NCEIHistoricalAdapter,'fsis_recalls':FSISRecallAdapter,'modot':MoDOTAdapter}
    if source not in adapters:raise HTTPException(404,'Unsupported source')
    try:
        result=adapters[source]().fetch()
        from backend.paths import write_json
        write_json(ROOT/f'data/cache/probe_{source}.json',result); return result
    except Exception as e: return {'status':'failed','error':f'{type(e).__name__}: {e}','source':source}

app.include_router(create_dispatch_router(db,load,record))

dist=ROOT/'frontend/dist'
if dist.exists():app.mount('/',StaticFiles(directory=dist,html=True),name='frontend')
