"""Light UI previews retain provider order, complete caches and freshness flags."""
from datetime import datetime, timezone
import json

from fastapi.testclient import TestClient
import pytest

import backend.main as api


@pytest.fixture
def evidence_client(tmp_path,monkeypatch):
    monkeypatch.setattr(api,'ROOT',tmp_path)
    with TestClient(api.app) as client:
        yield client,tmp_path


def cache(root,source,payload,**metadata):
    path=root/'data/cache'/f'probe_{source}.json';path.parent.mkdir(parents=True,exist_ok=True)
    body={'source_url':'https://example.test/official-source','retrieved_at':datetime.now(timezone.utc).isoformat(),
          'payload':payload,'cache':False,'stale':False,**metadata}
    path.write_text(json.dumps(body),encoding='utf-8')
    return path,body


@pytest.mark.parametrize('container',[None,'results','data','recalls','items'])
def test_limited_recalls_preserve_order_schema_metadata_and_full_cache(evidence_client,container):
    client,root=evidence_client
    records=[{'id':identity,'date':date,'original_column':'unchanged'} for identity,date in [(3,'2021-01-01'),(1,'2026-10-27'),(2,'2024-03-03')]]
    payload=records if container is None else {container:records,'provider_count':3,'provider_metadata':{'units':'not reinterpreted'}}
    path,original=cache(root,'fsis_recalls',payload)
    raw=path.read_bytes()
    response=client.get('/api/evidence/fsis_recalls?limit=2')
    assert response.status_code==200,response.text
    result=response.json()
    limited=result['payload'] if container is None else result['payload'][container]
    assert limited==records[:2]  # Original provider order, not date order.
    if container is not None:
        assert result['payload']['provider_count']==3
        assert result['payload']['provider_metadata']==payload['provider_metadata']
    assert result['total_records']==3 and result['returned_records']==2 and result['truncated']
    assert 'not sorted by date' in result['pagination_notice']
    assert result['retrieved_at']==original['retrieved_at'] and result['source_url']==original['source_url']
    assert result['live'] is False and result['fixture'] is False
    assert path.read_bytes()==raw
    full=client.get('/api/evidence/fsis_recalls').json()
    assert full['payload']==payload
    assert 'truncated' not in full and 'total_records' not in full
    assert path.read_bytes()==raw


def test_complete_or_empty_preview_does_not_claim_truncation(evidence_client):
    client,root=evidence_client
    for records in ([],[{'id':'one'}]):
        cache(root,'fsis_recalls',records)
        result=client.get('/api/evidence/fsis_recalls?limit=20').json()
        assert result['returned_records']==len(records)==result['total_records']
        assert result['truncated'] is False


@pytest.mark.parametrize('limit',['0','101','-1','not-a-number','1.5'])
def test_out_of_bounds_limits_are_rejected(evidence_client,limit):
    client,_=evidence_client
    assert client.get('/api/evidence/fsis_recalls',params={'limit':limit}).status_code==422


def test_unsupported_sources_and_unknown_recall_schemas_are_explicit(evidence_client):
    client,root=evidence_client
    assert client.get('/api/evidence/openmeteo?limit=2').status_code==422
    assert client.get('/api/evidence/unrecognized?limit=2').status_code==404
    for payload in ({'unrecognized_records':[{'id':1}]},{'data':[],'items':[]},None):
        path,_=cache(root,'fsis_recalls',payload)
        raw=path.read_bytes()
        assert client.get('/api/evidence/fsis_recalls?limit=2').status_code==400
        assert client.get('/api/evidence/fsis_recalls').json()['payload']==payload
        assert path.read_bytes()==raw


def test_limited_stale_fixture_keeps_its_original_failure_and_retrieval_time(evidence_client):
    client,root=evidence_client
    path=root/'data/fixtures/fsis_recalls.json';path.parent.mkdir(parents=True)
    path.write_text(json.dumps({'payload':[{'id':1},{'id':2}],'retrieved_at':'2024-01-01T00:00:00Z',
                                'cache':True,'stale':True,'refresh_error':'ReadTimeout: provider failed'}))
    raw=path.read_bytes()
    result=client.get('/api/evidence/fsis_recalls?limit=1').json()
    assert result['fixture'] and result['stale'] and result['cache']
    assert result['refresh_error']=='ReadTimeout: provider failed'
    assert result['retrieved_at']=='2024-01-01T00:00:00Z'
    assert result['total_records']==2 and path.read_bytes()==raw


def test_unknown_cache_wrapper_returns_explicit_limit_error_without_rewriting_it(evidence_client):
    client,root=evidence_client
    path=root/'data/cache/probe_fsis_recalls.json';path.parent.mkdir(parents=True)
    path.write_text(json.dumps([{'id':'not a supported evidence wrapper'}]))
    raw=path.read_bytes()
    assert client.get('/api/evidence/fsis_recalls?limit=2').status_code==400
    assert path.read_bytes()==raw


def test_refresh_summary_omits_bulk_data_but_writes_full_actual_cache(evidence_client,monkeypatch):
    client,root=evidence_client
    body={'payload':[{'id':i,'long_text':'x'*100} for i in range(1000)],'source_url':'https://example.test/recalls',
          'retrieved_at':'2026-10-27T07:00:00Z','cache':False,'stale':False,'provenance':'official recalls'}
    monkeypatch.setattr(api.FSISRecallAdapter,'fetch',lambda self:body)
    response=client.post('/api/refresh/fsis_recalls?summary=true')
    assert response.status_code==200
    result=response.json()
    assert result['summary_only'] and result['payload_present'] and result['record_count']==1000
    assert 'payload' not in result and 'incident_layers' not in result
    assert result['retrieved_at']==body['retrieved_at'] and result['cache'] is False and result['stale'] is False
    cached=json.loads((root/'data/cache/probe_fsis_recalls.json').read_text())
    assert cached==body and 'summary_only' not in cached
    assert client.post('/api/refresh/fsis_recalls').json()==body


def test_refresh_summary_retains_partial_stale_layer_evidence(evidence_client,monkeypatch):
    client,root=evidence_client
    body={'payload':{'layers':[{'id':1},{'id':2}]},'incident_layers':[{'layer_id':1,'payload':{'features':[{'id':5}]}}],
          'retrieved_at':'2026-10-26T07:00:00Z','source_url':'https://example.test/modot','cache':True,'stale':True,
          'refresh_error':'One incident layer timed out','coverage_complete':False,'coverage_warning':'Partial coverage',
          'layer_failures':[{'layer_id':2,'error':'ReadTimeout: query failed'}]}
    monkeypatch.setattr(api.MoDOTAdapter,'fetch',lambda self:body)
    result=client.post('/api/refresh/modot?summary=true').json()
    assert result['incident_layer_count']==1 and result['payload_present']
    assert result['stale'] and result['cache'] and not result['coverage_complete']
    assert result['refresh_error']==body['refresh_error'] and result['layer_failures']==body['layer_failures']
    assert result['retrieved_at']==body['retrieved_at']
    assert 'payload' not in result and 'incident_layers' not in result and 'record_count' not in result
    assert json.loads((root/'data/cache/probe_modot.json').read_text())==body


@pytest.mark.parametrize('summary',[False,True])
def test_failed_refresh_preserves_exact_error_and_prior_full_cache(evidence_client,monkeypatch,summary):
    client,root=evidence_client
    path,_=cache(root,'fsis_recalls',[{'id':'preserved'}]);raw=path.read_bytes()
    def fail(self):raise RuntimeError('Provider unavailable in this deliberate test')
    monkeypatch.setattr(api.FSISRecallAdapter,'fetch',fail)
    result=client.post('/api/refresh/fsis_recalls',params={'summary':str(summary).lower()}).json()
    assert result['status']=='failed' and result['error']=='RuntimeError: Provider unavailable in this deliberate test'
    assert result['source']=='fsis_recalls' and path.read_bytes()==raw
    if summary:
        assert result['summary_only'] and result['payload_present'] is False
        assert result['incident_layer_count']==0 and 'payload' not in result
    else:assert 'summary_only' not in result
