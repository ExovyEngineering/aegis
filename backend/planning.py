"""Immutable experiment runs and versioned local planning projects, never dispatch."""
import csv
import hashlib
import io
import json
import uuid
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from backend.adapters import now


def ensure_planning_schema(c):
    c.execute('CREATE TABLE IF NOT EXISTS planning_runs (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, request_json TEXT NOT NULL, result_json TEXT NOT NULL, checksum TEXT NOT NULL)')
    c.execute('CREATE TABLE IF NOT EXISTS planning_projects (id TEXT PRIMARY KEY, name TEXT NOT NULL, version INTEGER NOT NULL, run_id TEXT NOT NULL, updated_at TEXT NOT NULL, archived INTEGER NOT NULL DEFAULT 0)')
    c.execute('CREATE TABLE IF NOT EXISTS planning_versions (project_id TEXT NOT NULL, version INTEGER NOT NULL, run_id TEXT NOT NULL, name TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(project_id,version))')


def store_run(c, request, result):
    run_id, stamp = str(uuid.uuid4()), now()
    request_json = json.dumps(request, sort_keys=True, separators=(',', ':'), allow_nan=False)
    result_json = json.dumps(result, sort_keys=True, separators=(',', ':'), allow_nan=False)
    checksum = hashlib.sha256((request_json+'\n'+result_json).encode()).hexdigest()
    c.execute('INSERT INTO planning_runs VALUES (?,?,?,?,?)', (run_id, stamp, request_json, result_json, checksum))
    return dict(result, run_id=run_id, run_created_at=stamp, run_checksum=checksum)


def read_run(c, run_id):
    row = c.execute('SELECT created_at,request_json,result_json,checksum FROM planning_runs WHERE id=?', (run_id,)).fetchone()
    if not row: raise HTTPException(404, 'Unknown planning run')
    return {'run_id':run_id, 'created_at':row[0], 'request':json.loads(row[1]), 'result':dict(json.loads(row[2]), run_id=run_id, run_created_at=row[0], run_checksum=row[3]), 'checksum':row[3], 'dispatchable':False}


class SaveProject(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    name: str = Field(min_length=2, max_length=100)
    run_id: str = Field(min_length=1, max_length=100)


class UpdateProject(SaveProject):
    expected_version: int = Field(ge=1)


class ArchiveProject(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: int = Field(ge=1)


def create_planning_router(db, record):
    router = APIRouter(tags=['Saved planning experiments'])

    def project(c, project_id):
        row = c.execute('SELECT name,version,run_id,updated_at,archived FROM planning_projects WHERE id=?', (project_id,)).fetchone()
        if not row: raise HTTPException(404, 'Unknown planning project')
        return {'id':project_id, 'name':row[0], 'version':row[1], 'run_id':row[2], 'updated_at':row[3], 'archived':bool(row[4])}

    @router.get('/api/planning/projects')
    def projects():
        with db() as c:
            c.execute('BEGIN')
            return [project(c, row[0]) for row in c.execute('SELECT id FROM planning_projects WHERE archived=0 ORDER BY updated_at DESC,id LIMIT 200').fetchall()]

    @router.post('/api/planning/projects')
    def save(request:SaveProject):
        with db() as c:
            c.execute('BEGIN IMMEDIATE'); read_run(c, request.run_id)
            identity, stamp = str(uuid.uuid4()), now()
            c.execute('INSERT INTO planning_projects VALUES (?,?,1,?,?,0)', (identity, request.name, request.run_id, stamp))
            c.execute('INSERT INTO planning_versions VALUES (?,1,?,?,?)', (identity, request.run_id, request.name, stamp))
            record(c, 'planning operator', 'save_planning_project', {'project_id':identity, 'run_id':request.run_id, 'version':1})
            return project(c, identity)

    @router.get('/api/planning/projects/{project_id}')
    def detail(project_id:str, version:int|None=Query(default=None,ge=1)):
        with db() as c:
            c.execute('BEGIN'); output = project(c, project_id)
            history = [{'version':r[0], 'run_id':r[1], 'name':r[2], 'created_at':r[3]} for r in c.execute('SELECT version,run_id,name,created_at FROM planning_versions WHERE project_id=? ORDER BY version DESC', (project_id,))]
            chosen = next((r for r in history if r['version']==(version or output['version'])), None)
            if not chosen: raise HTTPException(404, 'Unknown project version')
            return dict(output, viewed_version=chosen['version'], history=history, run=read_run(c, chosen['run_id']))

    @router.post('/api/planning/projects/{project_id}/update')
    def update(project_id:str, request:UpdateProject):
        with db() as c:
            c.execute('BEGIN IMMEDIATE'); current = project(c, project_id)
            if current['archived'] or current['version']!=request.expected_version: raise HTTPException(409, 'Project changed or was archived; reload before saving')
            read_run(c, request.run_id); version, stamp = current['version']+1, now()
            c.execute('UPDATE planning_projects SET name=?,version=?,run_id=?,updated_at=? WHERE id=?', (request.name, version, request.run_id, stamp, project_id))
            c.execute('INSERT INTO planning_versions VALUES (?,?,?,?,?)', (project_id, version, request.run_id, request.name, stamp))
            record(c, 'planning operator', 'update_planning_project', {'project_id':project_id, 'run_id':request.run_id, 'version':version})
            return project(c, project_id)

    @router.post('/api/planning/projects/{project_id}/archive')
    def archive(project_id:str, request:ArchiveProject):
        with db() as c:
            c.execute('BEGIN IMMEDIATE'); current = project(c, project_id)
            if current['archived'] or current['version']!=request.expected_version: raise HTTPException(409, 'Project changed or already archived')
            c.execute('UPDATE planning_projects SET archived=1 WHERE id=?', (project_id,))
            record(c, 'planning operator', 'archive_planning_project', {'project_id':project_id, 'version':current['version']})
            return {'status':'archived', 'history_preserved':True}

    @router.get('/api/planning/runs/{run_id}')
    def run(run_id:str):
        with db() as c: return read_run(c, run_id)

    @router.get('/api/planning/runs/{run_id}/stops.csv')
    def export(run_id:str):
        with db() as c: output = read_run(c, run_id)
        buffer = io.StringIO(newline=''); writer = csv.writer(buffer)
        writer.writerow(['planning_run', 'truck', 'origin', 'stop_order', 'stop_id', 'route_load_kg', 'route_distance_m', 'route_duration_seconds', 'provenance'])
        def cell(value):
            text = str(value)
            return "'"+text if text.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')) else text
        for route in output['result']['routes']:
            for index, stop in enumerate(route['stop_ids'], 1):
                writer.writerow([cell(x) for x in (run_id, route['truck_id'], route['origin_id'], index, stop, route['load_kg'], route['distance_m'], route['duration_seconds'], 'simulated planning; not approved dispatch')])
        return Response(buffer.getvalue(), media_type='text/csv', headers={'Content-Disposition':'attachment; filename="aegis-planning-stops.csv"'})

    return router
