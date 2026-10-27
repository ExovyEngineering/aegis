"""Read recorded project evidence; never promote unexecuted checks to passes."""
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import yaml
from backend.paths import read_json


def create_project_router(root):
    router=APIRouter(tags=['Team status and presentation brief'])

    @router.get('/api/project-status')
    def status():
        register=root/'config/feature_register.yaml'
        features=yaml.safe_load(register.read_text(encoding='utf-8')) if register.exists() else {'features':[]}
        def read(name):
            path=root/'reports'/name
            return read_json(path) if path.exists() else None
        return {'register':features,'verification':read('session_verification.json'),'brief':read('project_brief_manifest.json'),'simulation':True,'notice':'Recorded evidence is dated. Local tests, browser checks, public API freshness, GitHub CI and author signoff are separate.'}

    @router.get('/api/project-brief.pdf')
    def pdf():
        path=root/'reports/aegis_project_brief.pdf'
        if not path.exists():raise HTTPException(404,'Project brief has not been generated; run scripts/build_project_brief.py')
        return FileResponse(path,media_type='application/pdf',filename='AEGIS-project-and-presentation-brief.pdf')

    @router.get('/api/project-brief.md')
    def markdown():
        path=root/'reports/project_brief.md'
        if not path.exists():raise HTTPException(404,'Project brief has not been generated')
        return FileResponse(path,media_type='text/markdown',filename='AEGIS-project-brief.md')
    return router
