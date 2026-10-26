from fastapi import FastAPI
from fastapi.testclient import TestClient
import pandas as pd
import pytest
from backend.data_explorer import create_data_router


@pytest.fixture
def explorer(tmp_path):
    out=tmp_path/'data/processed';out.mkdir(parents=True)
    pd.DataFrame({'collection_date':pd.to_datetime(['2025-01-01','2025-01-02',None]),'establishment_state':['MO','KY','MO'],'result':['Negative','Positive',None],'original_year':['2,025','2,025','2,026']}).to_parquet(out/'fsis_poultry.parquet',index=False)
    app=FastAPI();app.include_router(create_data_router(tmp_path))
    with TestClient(app) as client:yield client,out


def test_source_catalog_does_not_silently_merge_missing_sources(explorer):
    c,_=explorer;catalog=c.get('/api/data/catalog').json()
    available=[s for s in catalog if s['status']=='available']
    assert len(available)==1 and available[0]['rows']==3
    assert len(available[0]['sha256'])==64
    assert any(x['status']=='not ingested' for x in catalog)
    assert c.get('/api/data/nors_0').status_code==404
    assert c.get('/api/data/unrecognized_file').status_code==404


def test_bounded_filtering_nulls_and_provider_formats(explorer):
    c,_=explorer
    first=c.get('/api/data/fsis_poultry?limit=1').json()
    assert first['matching_rows']==3 and first['next_offset']==1
    assert first['rows'][0]['original_year']=='2,025'
    assert first['rows'][0]['collection_date'].startswith('2025-01-01T')
    page=c.get('/api/data/fsis_poultry',params={'field':'establishment_state','contains':'mo','limit':1,'offset':1}).json()
    assert page['matching_rows']==2 and page['rows'][0]['result'] is None
    assert page['page_null_counts']['result']==1
    assert 'page only' in page['provenance']
    empty=c.get('/api/data/fsis_poultry',params={'field':'result','contains':'[.*]'}).json()
    assert empty['rows']==[] and empty['matching_rows']==0  # Literal substring, not regex.


@pytest.mark.parametrize('params',[{'limit':101},{'offset':10001},{'offset':-1},{'field':'result'},{'contains':'MO'},{'field':'password','contains':'x'}])
def test_reject_invalid_or_unbounded_queries(explorer,params):
    c,_=explorer;assert c.get('/api/data/fsis_poultry',params=params).status_code==422


def test_corrupt_source_is_reported_and_other_sources_continue(explorer):
    c,out=explorer;(out/'nors_0.parquet').write_bytes(b'partial download')
    catalog=c.get('/api/data/catalog').json()
    assert next(x for x in catalog if x['id']=='nors_0')['status']=='unreadable'
    assert c.get('/api/data/nors_0').status_code==503
    assert c.get('/api/data/fsis_poultry').status_code==200
