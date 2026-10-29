import hashlib
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pypdf import PdfReader

from backend.project_status import create_project_router
from scripts.build_master_guide import PARTS, build, html_document, parse_markdown


def test_guide_parser_keeps_control_tables_lists_code_and_escapes_html():
    source='''## Controls and use cases

Read **simulated cargo**, not a live sensor. <script>bad()</script>

| Control | Meaning |
| --- | --- |
| A \\| B | First or second |

1. Inspect the evidence.
2. Record a reason.

```powershell
python scripts/start_rehearsal.py
```
'''
    blocks=parse_markdown(source)
    table=next(row for row in blocks if row['kind']=='table')
    assert len(table['rows'])==2 and len(table['rows'][1])==2
    output=html_document(blocks,'October 28, 2026')
    assert '<script>bad()' not in output and '&lt;script&gt;bad()' in output
    assert '<strong>simulated cargo</strong>' in output and 'A | B' in output
    assert '<thead>' in output and '@page{size:letter' in output
    assert 'Print this guide' in output and 'https://fonts.' not in output
    assert output.count('href="#controls-and-use-cases"')==1


def test_built_guide_is_printable_bookmarked_and_served_without_database_or_network(tmp_path,monkeypatch):
    import httpx
    def forbidden(*args,**kwargs):
        raise AssertionError('Guide compilation must not contact providers')
    monkeypatch.setattr(httpx,'get',forbidden)
    for index,name in enumerate(PARTS):
        path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(f'## Workspace {index+1}\n\nA real control and its **simulated** use case.\n\n### Read this first\n\n| Control | Meaning | Use case |\n| --- | --- | --- |\n| Review | Human decision | Read '+('long-coordinate-or-source-identity-'*12)+' |\n\nThe simulated cost is $3,018 and the alternative is $3,093.\n',encoding='utf-8')
    operator=tmp_path/'data/aegis.sqlite';operator.parent.mkdir();operator.write_bytes(b'untouched operator sentinel')
    result=build(tmp_path)
    assert operator.read_bytes()==b'untouched operator sentinel'
    assert result['overflow_count']==0 and result['paper']=='US Letter'
    assert not result['live_api_requests_performed'] and not result['operational_database_accessed']
    reader=PdfReader(tmp_path/result['pdf'])
    assert len(reader.pages)==result['pages'] and reader.pages[0].mediabox.width==612
    assert reader.pages[0].mediabox.height==792
    assert len(reader.outline)==result['bookmarks']==len(PARTS)+1
    text='\n'.join(page.extract_text() for page in reader.pages)
    assert '$3,018' in text and '$3,093' in text and 'Not recorded' in text
    assert 'Local suite | PASS' not in text
    for chapter,destination in zip(result['chapters'],reader.outline):
        assert reader.get_destination_page_number(destination)==chapter['page']-1
        assert chapter['title'] in reader.pages[chapter['page']-1].extract_text()
    toc=reader.pages[1]
    assert len(toc['/Annots'])==result['contents_links']
    assert hashlib.sha256((tmp_path/result['pdf']).read_bytes()).hexdigest()==result['sha256']
    app=FastAPI();app.include_router(create_project_router(tmp_path))
    with TestClient(app) as client:
        response=client.get('/api/master-guide.pdf')
        assert response.content.startswith(b'%PDF') and 'attachment' in response.headers['content-disposition']
        response=client.get('/api/master-guide.html')
        assert response.status_code==200 and 'inline' in response.headers['content-disposition']
        assert 'Print this guide' in response.text
        assert client.get('/api/master-guide.md').text.startswith('# AEGIS Master User Guide')
        assert client.get('/api/project-status').json()['manual']['sha256']==result['sha256']


def test_missing_guide_returns_explicit_unavailable_instead_of_a_fabricated_artifact(tmp_path):
    app=FastAPI();app.include_router(create_project_router(tmp_path))
    with TestClient(app) as client:
        for extension in ('pdf','html','md'):
            assert client.get('/api/master-guide.'+extension).status_code==404
        assert client.get('/api/project-status').json()['manual'] is None


def test_source_chapter_missing_is_reported_before_claiming_a_complete_guide(tmp_path):
    import pytest
    with pytest.raises(ValueError,match='source chapter missing'):
        build(tmp_path)
    assert not (tmp_path/'reports/master_guide_manifest.json').exists()
