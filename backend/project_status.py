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
        return {'register':features,'verification':read('session_verification.json'),'brief':read('project_brief_manifest.json'),'manual':read('master_guide_manifest.json'),'simulation':True,'notice':'Recorded evidence is dated. Local tests, browser checks, public API freshness, GitHub CI and author signoff are separate.'}

    @router.get('/api/master-guide.pdf')
    def master_pdf():
        path=root/'reports/aegis_master_guide.pdf'
        if not path.exists():raise HTTPException(404,'Master user guide has not been generated')
        return FileResponse(path,media_type='application/pdf',filename='AEGIS-Master-User-Guide.pdf')

    @router.get('/api/master-guide.html')
    def master_html():
        path=root/'reports/aegis_master_guide.html'
        if not path.exists():raise HTTPException(404,'Master user guide has not been generated')
        return FileResponse(path,media_type='text/html',filename='AEGIS-Master-User-Guide.html',content_disposition_type='inline')

    @router.get('/api/master-guide.md')
    def master_markdown():
        path=root/'docs/aegis_master_guide.md'
        if not path.exists():raise HTTPException(404,'Master user guide has not been generated')
        return FileResponse(path,media_type='text/markdown',filename='AEGIS-Master-User-Guide.md')

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
