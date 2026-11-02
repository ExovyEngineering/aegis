import json
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pypdf import PdfReader
import yaml
from backend.project_status import create_project_router
from scripts.build_project_brief import build, sections


def setup(root):
    (root/'config').mkdir();(root/'reports').mkdir()
    (root/'config/feature_register.yaml').write_text(yaml.safe_dump({'features':[{'id':'kiro','priority':'P0','name':'Authentic Kiro','status':'pending','detail':'Actual task required','evidence':'docs/kiro_handoff.md'}]}))


def test_pdf_and_markdown_include_measured_checks_and_pending_gates(tmp_path):
    setup(tmp_path)
    (tmp_path/'reports/session_verification.json').write_text(json.dumps({'finished_at':'2026-10-26T10:00:00Z','all_passed':False,'checks':[{'name':'pytest','passed':False,'exit_code':1,'tests_passed':7,'duration_seconds':2.1,'log':'reports/checks/pytest.txt','checked_at':'2026-10-26T10:00:00Z'}]}))
    result=build(tmp_path)
    reader=PdfReader(tmp_path/result['pdf']);text='\n'.join(page.extract_text() for page in reader.pages)
    assert result['pages']==len(reader.pages) and result['pages']>=8
    assert 'pytest: FAIL' in text and 'tests passed 7' in text
    assert 'pending' in text and 'consumer illness' in text
    assert 'No live API requests' in text
    assert all(str(i+1) in page.extract_text() for i,page in enumerate(reader.pages))
    assert (tmp_path/result['markdown']).exists()
    app=FastAPI();app.include_router(create_project_router(tmp_path))
    with TestClient(app) as c:
        assert c.get('/api/project-brief.pdf').content.startswith(b'%PDF')
        assert c.get('/api/project-status').json()['verification']['all_passed'] is False


def test_missing_verification_is_never_inferred_as_success(tmp_path):
    setup(tmp_path);body=str(sections(tmp_path))
    assert 'not recorded' in body
    app=FastAPI();app.include_router(create_project_router(tmp_path))
    with TestClient(app) as c:
        assert c.get('/api/project-brief.pdf').status_code==404
        assert c.get('/api/project-status').json()['verification'] is None
