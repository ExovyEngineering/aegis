"""Server-timed, self-reported practice on an explicitly isolated demo database.

Operational evidence proves that simulated actions were recorded during the run,
not that the presenter showed them on screen. Completion never closes Kiro,
scientific, authorship or final-submission approval gates.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Literal
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.paths import ROOT
from backend.runtime import runtime_context


STAGES = [
    {'id':'overview', 'title':'Actor, map and simulation', 'planned_seconds':40,
     'description':'Explain the distributor, geography and fictional operations. Coverage is self-reported.', 'requires_evidence':[]},
    {'id':'evidence_science', 'title':'Sources, coverage and measured science', 'planned_seconds':80,
     'description':'Show provenance, NOAA gaps and measured baseline/model limits. Coverage is self-reported.', 'requires_evidence':[]},
    {'id':'disruption', 'title':'Simulated disruption and tradeoffs', 'planned_seconds':60,
     'description':'Introduce a simulated event and compare responses. Covered requires an event recorded since this run began.', 'requires_evidence':['event']},
    {'id':'approval', 'title':'Explicit dispatcher decision', 'planned_seconds':60,
     'description':'Review and approve a simulated scenario. Covered requires an approval recorded since this run began.', 'requires_evidence':['approve']},
    {'id':'driver', 'title':'Parked driver workflow', 'planned_seconds':40,
     'description':'Confirm parking, acknowledge an assignment and report an incident. Covered requires those recorded actions during this run.', 'requires_evidence':['driver_focus','acknowledge','incident']},
    {'id':'closing', 'title':'Contribution and honest limitations', 'planned_seconds':20,
     'description':'Summarize the contribution and remaining gates. Coverage is self-reported.', 'requires_evidence':[]},
]
TARGET_SECONDS = sum(stage['planned_seconds'] for stage in STAGES)
MAX_AUDIT_SNAPSHOT = 2000
REPORT_PATHS = (
    'reports/api_status.json', 'reports/model_evaluation.json', 'reports/model_timing.json',
    'reports/noaa_coverage.json', 'reports/usda_food_environment.json',
    'reports/session_verification.json', 'reports/project_brief_manifest.json',
    'reports/ingestion_verification.json',
)
SOURCES = ('openmeteo','nws_alerts','ncei_historical','fsis_recalls','modot','osrm_route')
NOTICE = ('Recorded timer and self-reported milestone coverage for a simulated rehearsal. '
          'Operational evidence establishes recorded app actions, not what was shown on screen. '
          'This does not verify a five-minute team presentation, authentic Kiro work, author approval or final submission readiness.')


def _now():
    return datetime.now(timezone.utc)


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def ensure_rehearsal_schema(connection):
    connection.execute(
        'CREATE TABLE IF NOT EXISTS rehearsal_runs ('
        'id TEXT PRIMARY KEY, version INTEGER NOT NULL, status TEXT NOT NULL, '
        'payload TEXT NOT NULL, snapshot_json TEXT, snapshot_sha256 TEXT)'
    )


class StartRun(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    presenter: str = Field(min_length=2, max_length=100)
    purpose: str = Field(min_length=5, max_length=1000)
    run_kind: Literal['practice','automated_check'] = 'practice'


class Checkpoint(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    expected_version: int = Field(ge=1, strict=True)
    stage_id: Literal['overview','evidence_science','disruption','approval','driver','closing']
    outcome: Literal['covered','skipped']
    notes: str = Field(default='', max_length=2000)

    @model_validator(mode='after')
    def explain_skip(self):
        if self.outcome == 'skipped' and len(self.notes) < 5:
            raise ValueError('Record a reason of at least five characters for a skipped stage')
        return self


class FinishRun(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    expected_version: int = Field(ge=1, strict=True)
    outcome: Literal['completed','aborted']
    notes: str = Field(default='', max_length=2000)

    @model_validator(mode='after')
    def explain_abort(self):
        if self.outcome == 'aborted' and len(self.notes) < 5:
            raise ValueError('Record a reason of at least five characters when aborting a rehearsal')
        return self


def _elapsed(run, instant):
    start = datetime.fromisoformat(run['started_at'])
    if start.tzinfo is None or instant.tzinfo is None or instant < start:
        raise HTTPException(409, 'Rehearsal clock moved backwards or lacks a timezone; resolve the server clock before continuing')
    return round((instant - start).total_seconds(), 3)


def _audit_delta(connection, start_id):
    rows = connection.execute(
        'SELECT id,timestamp,actor,action,payload FROM audit WHERE id>? ORDER BY id LIMIT ?',
        (start_id, MAX_AUDIT_SNAPSHOT + 1),
    ).fetchall()
    output = []
    for row in rows[:MAX_AUDIT_SNAPSHOT]:
        try:
            payload = json.loads(row[4])
        except (ValueError, TypeError):
            payload = {'error':'Audit payload cannot be decoded; no operational action inferred.'}
        output.append(dict(id=row[0],timestamp=row[1],actor=row[2],action=row[3],payload=payload))
    return output, len(rows) > MAX_AUDIT_SNAPSHOT


def _driver_evidence(connection, audit):
    """Match parked -> acknowledgment -> report for one immutable trip context."""
    if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='incidents'").fetchone():
        return None
    for incident in reversed(audit):
        payload=incident['payload']
        if incident['action']!='incident' or not isinstance(payload,dict):
            continue
        incident_id=payload.get('incident_id');shipment_id=payload.get('shipment_id')
        if not isinstance(incident_id,str) or not isinstance(shipment_id,str):
            continue
        row=connection.execute('SELECT shipment_id,payload FROM incidents WHERE id=?',(incident_id,)).fetchone()
        if row is None or row[0]!=shipment_id:
            continue
        try:
            report=json.loads(row[1]);assignment=report['reporting_assignment'];truck_id=assignment['truck_id']
        except (ValueError,TypeError,KeyError):
            continue
        if not isinstance(assignment,dict) or assignment.get('id')!=shipment_id or not isinstance(truck_id,str):
            continue
        earlier=[item for item in audit if item['id']<incident['id']]
        invalidations=[item['id'] for item in earlier if item['action'] in {'approve','event','reset'}
                       or item['action']=='lot_hold' and isinstance(item['payload'],dict)
                       and shipment_id in item['payload'].get('invalidated_shipments',[])]
        boundary=max(invalidations,default=0)
        acknowledgments=[item for item in earlier if item['action']=='acknowledge'
                         and item['id']>boundary and isinstance(item['payload'],dict)
                         and item['payload'].get('shipment_id')==shipment_id]
        for acknowledgment in reversed(acknowledgments):
            focus=[item for item in earlier if item['id']<acknowledgment['id']
                   and item['action']=='driver_focus' and isinstance(item['payload'],dict)
                   and item['payload'].get('truck_id')==truck_id]
            latest=focus[-1] if focus else None
            if latest and latest['payload'].get('mode')=='parked' and latest['payload'].get('parked_confirmation') is True:
                return {'matched':[latest,acknowledgment,incident],
                        'assignment_context':assignment,'incident_id':incident_id,
                        'reported_network_revision':report.get('reported_network_revision')}
    return None


def _evidence(connection, run, stage, outcome):
    if outcome == 'skipped':
        return {'kind':'skipped', 'requirements':stage['requires_evidence'], 'audit_ids':[],
                'notice':'Stage was explicitly skipped; it is not recorded as demonstrated.'}
    required = stage['requires_evidence']
    if not required:
        return {'kind':'self_reported_coverage', 'requirements':[], 'audit_ids':[],
                'notice':'Presenter reports coverage; the application does not verify what was shown or said.'}
    audit, truncated = _audit_delta(connection, run['audit_start_id'])
    if truncated:
        raise HTTPException(409, 'Rehearsal audit exceeds its bounded evidence window; abort and begin a fresh run rather than infer missing actions')
    if stage['id']=='driver':
        chain=_driver_evidence(connection,audit)
        if chain is None:
            raise HTTPException(409,'Cannot mark driver covered: record parked confirmation, then acknowledgment and incident for the same approved trip during this rehearsal, or explicitly skip it with a reason')
        matched=chain['matched']
        return {'kind':'recorded_operational_actions','requirements':required,
                'audit_ids':[item['id'] for item in matched],
                'actions':[{'id':item['id'],'action':item['action'],'timestamp':item['timestamp']} for item in matched],
                'assignment_context':chain['assignment_context'],'incident_id':chain['incident_id'],
                'reported_network_revision':chain['reported_network_revision'],
                'notice':'One trip has a recorded parked-confirmation, acknowledgment and report sequence after the run began; this does not prove it was shown on screen.'}
    matched = []
    for action in required:
        choices = [item for item in audit if item['action'] == action]
        if action == 'driver_focus':
            choices = [item for item in choices if isinstance(item['payload'],dict)
                       and item['payload'].get('mode') == 'parked'
                       and item['payload'].get('parked_confirmation') is True]
        if not choices:
            raise HTTPException(409, f'Cannot mark {stage["id"]} covered: record {action} during this rehearsal, or explicitly skip it with a reason')
        matched.append(choices[-1])
    return {'kind':'recorded_operational_actions', 'requirements':required,
            'audit_ids':[item['id'] for item in matched],
            'actions':[{'id':item['id'],'action':item['action'],'timestamp':item['timestamp']} for item in matched],
            'notice':'These simulated actions were recorded after the run started; this does not prove they were shown on screen.'}


def _file_evidence(root, offline=False):
    names = list(REPORT_PATHS)
    for source in SOURCES:
        cache = f'data/cache/probe_{source}.json'
        fixture = f'data/fixtures/{source}.json'
        names.append(fixture if offline else cache if (root/cache).is_file() else fixture)
    evidence = []
    for name in names:
        path = root/name
        entry = {'path':name, 'kind':'dated_source_file' if name.startswith('data/') else 'recorded_report'}
        try:
            if not path.is_file():
                entry['status']='unavailable'
            elif not path.resolve().is_relative_to(root.resolve()):
                entry.update(status='unavailable',error='Evidence path escapes the project workspace')
            else:
                digest=hashlib.sha256()
                size=0
                with path.open('rb') as stream:
                    for chunk in iter(lambda:stream.read(1024*1024),b''):
                        size += len(chunk);digest.update(chunk)
                entry.update(status='recorded',bytes=size,sha256=digest.hexdigest())
        except OSError as error:
            entry.update(status='unavailable',error=f'{type(error).__name__}: {error}')
        evidence.append(entry)
    return evidence


def create_rehearsal_router(db, load, record, db_path, root=ROOT):
    router=APIRouter(tags=['Isolated guided rehearsal'])
    workspace=lambda:Path(root() if callable(root) else root).resolve()
    context=lambda:runtime_context(db_path(),root=workspace())

    def isolated():
        value=context()
        if value['mode']=='misconfigured':
            raise HTTPException(503,value['warning'])
        if not value['isolated']:
            raise HTTPException(403,'Guided rehearsal changes require a separate isolated rehearsal server. The operator database was not opened or reset.')
        return value

    def begin(connection):
        if not connection.in_transaction:
            connection.execute('BEGIN IMMEDIATE')
        ensure_rehearsal_schema(connection)

    def read_run(connection, identity):
        row=connection.execute('SELECT version,status,payload,snapshot_json,snapshot_sha256 FROM rehearsal_runs WHERE id=?',(identity,)).fetchone()
        if not row:
            raise HTTPException(404,'Unknown rehearsal run')
        run=json.loads(row[2])
        run.update(version=row[0],status=row[1])
        return run,row[3],row[4]

    def rendered(run, instant=None):
        instant=instant or _now()
        result=dict(run)
        end=datetime.fromisoformat(run['finished_at']) if run.get('finished_at') else instant
        elapsed=_elapsed(run,end)
        if run['status']=='active' and run['milestones'] and elapsed<run['milestones'][-1]['elapsed_seconds']:
            raise HTTPException(409,'Rehearsal clock moved backwards since the preceding checkpoint; resolve the server clock before displaying or recording another duration')
        result.update(elapsed_seconds=elapsed,server_time=instant.isoformat(),
                      next_stage_id=STAGES[len(run['milestones'])]['id'] if run['status']=='active' and len(run['milestones'])<len(STAGES) else None,
                      target_seconds=TARGET_SECONDS,notice=NOTICE,
                      timing_assessment='under_target' if elapsed<TARGET_SECONDS else 'at_or_over_target')
        return result

    def save(connection, run):
        connection.execute('UPDATE rehearsal_runs SET version=?,status=?,payload=? WHERE id=?',
                           (run['version'],run['status'],_json(run),run['id']))

    def mutable(connection, identity, expected):
        run,_,_=read_run(connection,identity)
        if run['status']!='active':
            raise HTTPException(409,'This rehearsal is finished and immutable; begin a new run')
        if run['version']!=expected:
            raise HTTPException(409,'Rehearsal changed; reload before recording another step')
        return run

    @router.get('/api/runtime-context')
    def runtime():
        return context()

    @router.get('/api/rehearsal')
    def status():
        value=context()
        if not value['isolated']:
            return {'runtime':value,'stages':STAGES,'active':None,'runs':[]}
        with db() as connection:
            begin(connection)
            rows=connection.execute('SELECT id FROM rehearsal_runs ORDER BY rowid DESC LIMIT 100').fetchall()
            runs=[rendered(read_run(connection,row[0])[0]) for row in rows]
            active=next((run for run in runs if run['status']=='active'),None)
            summaries=[{key:run.get(key) for key in ('id','version','status','presenter','purpose','run_kind','started_at','finished_at','elapsed_seconds','target_seconds')} for run in runs]
            return {'runtime':value,'stages':STAGES,'active':active,'runs':summaries}

    @router.post('/api/rehearsal/start')
    def start(request:StartRun):
        value=isolated()
        with db() as connection:
            begin(connection)
            if connection.execute("SELECT 1 FROM rehearsal_runs WHERE status='active' LIMIT 1").fetchone():
                raise HTTPException(409,'A rehearsal is already active; finish or abort it before starting another')
            instant=_now()
            network,revision=load(connection)
            audit_start=connection.execute('SELECT COALESCE(MAX(id),0) FROM audit').fetchone()[0]
            run=dict(request.model_dump(),id=str(uuid.uuid4()),version=1,status='active',
                     rehearsal_id=value['rehearsal_id'],started_at=instant.isoformat(),finished_at=None,
                     milestones=[],notes='',audit_start_id=audit_start,start_network_revision=revision,
                     seed=network['seed'],start_evidence=_file_evidence(workspace(),value['offline']))
            connection.execute('INSERT INTO rehearsal_runs VALUES (?,?,?,?,NULL,NULL)',(run['id'],1,'active',_json(run)))
            record(connection,request.presenter,'rehearsal_start',{'run_id':run['id'],'run_kind':request.run_kind})
            return rendered(run,instant)

    @router.get('/api/rehearsal/{identity}')
    def detail(identity:str):
        isolated()
        with db() as connection:
            begin(connection)
            return rendered(read_run(connection,identity)[0])

    @router.post('/api/rehearsal/{identity}/checkpoint')
    def checkpoint(identity:str,request:Checkpoint):
        isolated()
        with db() as connection:
            begin(connection)
            run=mutable(connection,identity,request.expected_version)
            if len(run['milestones'])>=len(STAGES) or STAGES[len(run['milestones'])]['id']!=request.stage_id:
                raise HTTPException(409,'Record stages in the displayed order; duplicate or skipped-ahead checkpoints are rejected')
            instant=_now();elapsed=_elapsed(run,instant)
            if run['milestones'] and elapsed<run['milestones'][-1]['elapsed_seconds']:
                raise HTTPException(409,'Rehearsal clock moved backwards since the preceding checkpoint')
            stage=STAGES[len(run['milestones'])]
            evidence=_evidence(connection,run,stage,request.outcome)
            run['milestones'].append({'stage_id':request.stage_id,'outcome':request.outcome,'notes':request.notes,
                                      'recorded_at':instant.isoformat(),'elapsed_seconds':elapsed,'evidence':evidence})
            run['version']+=1
            save(connection,run)
            record(connection,run['presenter'],'rehearsal_checkpoint',{'run_id':identity,'stage_id':request.stage_id,'outcome':request.outcome})
            return rendered(run,instant)

    @router.post('/api/rehearsal/{identity}/finish')
    def finish(identity:str,request:FinishRun):
        value=isolated()
        with db() as connection:
            begin(connection)
            run=mutable(connection,identity,request.expected_version)
            if request.outcome=='completed' and len(run['milestones'])!=len(STAGES):
                raise HTTPException(409,'Record all six stages, including explicit skips, before completing the timer')
            instant=_now();elapsed=_elapsed(run,instant)
            if run['milestones'] and elapsed<run['milestones'][-1]['elapsed_seconds']:
                raise HTTPException(409,'Rehearsal clock moved backwards since the preceding checkpoint')
            run.update(status=request.outcome,finished_at=instant.isoformat(),notes=request.notes,version=run['version']+1)
            record(connection,run['presenter'],'rehearsal_finish',{'run_id':identity,'outcome':request.outcome,'elapsed_seconds':elapsed})
            network,revision=load(connection)
            audit,truncated=_audit_delta(connection,run['audit_start_id'])
            output={'schema_version':1,'run':rendered(run,instant),'runtime':value,'stages':STAGES,
                    'network':dict(network,revision=revision),'audit_delta':audit,'audit_truncated':truncated,
                    'source_report_evidence':_file_evidence(workspace(),value['offline']),'notice':NOTICE,
                    'author_signoff_verified':False,'genuine_kiro_execution_verified':False,
                    'five_minute_presentation_verified':False}
            serialized=_json(output)
            digest=hashlib.sha256(serialized.encode()).hexdigest()
            save(connection,run)
            connection.execute('UPDATE rehearsal_runs SET snapshot_json=?,snapshot_sha256=? WHERE id=?',(serialized,digest,identity))
            return rendered(run,instant)

    @router.get('/api/rehearsal/{identity}/export')
    def export(identity:str):
        isolated()
        with db() as connection:
            begin(connection)
            run,serialized,digest=read_run(connection,identity)
            if run['status']=='active' or serialized is None:
                raise HTTPException(409,'Finish or abort the rehearsal before exporting its immutable snapshot')
            if hashlib.sha256(serialized.encode()).hexdigest()!=digest:
                raise HTTPException(503,'Stored rehearsal snapshot checksum does not match; no export was inferred')
            return Response(serialized,media_type='application/json',headers={
                'Content-Disposition':f'attachment; filename="aegis-rehearsal-{run["id"]}.json"',
                'X-AEGIS-Snapshot-SHA256':digest,
            })

    return router
