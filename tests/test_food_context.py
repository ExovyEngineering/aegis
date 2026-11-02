import csv
import hashlib
import io
import json
from pathlib import Path

import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.food_context import create_food_context_router


@pytest.fixture
def county_context(tmp_path):
    (tmp_path/'data/processed').mkdir(parents=True)
    (tmp_path/'reports').mkdir()
    table = tmp_path/'data/processed/usda_food_environment_missouri.parquet'
    pd.DataFrame([{'FIPS':'29019','State':'MO','County':'Boone','county_display_name':'Boone','GROC20':None},
                  {'FIPS':'29510','State':'MO','County':'St. Louis','county_display_name':'St. Louis city','GROC20':8.0}]).to_parquet(table,index=False)
    report = {'status':'available','source_id':'usda_food_environment','processed_file':{'sha256':hashlib.sha256(table.read_bytes()).hexdigest()},'source_file':{'sha256':'source-checksum'},'variables':[{'code':'GROC20','year':2020,'unit':'stores'}],'geography':{'county_count':2},'records':[{'invented':'must never be served'}]}
    path=tmp_path/'reports/usda_food_environment.json'
    path.write_text(json.dumps(report))
    app=FastAPI();app.include_router(create_food_context_router(tmp_path))
    with TestClient(app) as client:
        yield client,table,path,report


def test_context_uses_checked_table_preserves_fips_nulls_and_city(county_context):
    client,*_=county_context
    response=client.get('/api/food-access')
    assert response.status_code==200
    body=response.json()
    assert body['integrity_verified']
    assert body['records'][0]['FIPS']=='29019' and body['records'][0]['GROC20'] is None
    assert body['records'][1]['county_display_name']=='St. Louis city'
    assert 'invented' not in str(body['records'])
    assert 'no location assignment' in body['interpretation']


def test_export_retains_null_and_source_hash(county_context):
    client,*_=county_context
    response=client.get('/api/food-access.csv')
    assert response.status_code==200
    rows=list(csv.DictReader(io.StringIO(response.text)))
    assert len(rows)==2 and rows[0]['GROC20']==''
    assert rows[0]['FIPS']=='29019' and rows[0]['source_sha256']=='source-checksum'
    assert 'attachment' in response.headers['content-disposition']


@pytest.mark.parametrize('change',['hash','identity','count','status','corrupt'])
def test_invalid_provenance_is_explicitly_unavailable(county_context,change):
    client,table,path,report=county_context
    if change=='hash':report['processed_file']['sha256']='incorrect'
    if change=='identity':report['source_id']='unrecognized'
    if change=='count':report['geography']['county_count']=3
    if change=='status':report['status']='failed'
    path.write_text('broken json' if change=='corrupt' else json.dumps(report))
    response=client.get('/api/food-access')
    assert response.status_code==503
    assert response.json()['detail']


def test_missing_source_does_not_invent_county_values(county_context):
    client,table,*_=county_context
    table.unlink()
    assert client.get('/api/food-access').status_code==404


def test_served_values_are_the_same_bytes_that_passed_the_checksum(county_context,monkeypatch):
    client,table,*_=county_context
    read_bytes=Path.read_bytes
    replaced=False
    def replace_after_read(path):
        nonlocal replaced
        body=read_bytes(path)
        if path==table and not replaced:
            replaced=True
            changed=pd.read_parquet(io.BytesIO(body))
            changed.loc[0,'GROC20']=999
            changed.to_parquet(table,index=False)
        return body
    monkeypatch.setattr(Path,'read_bytes',replace_after_read)
    response=client.get('/api/food-access')
    assert response.status_code==200
    assert response.json()['integrity_verified']
    assert response.json()['records'][0]['GROC20'] is None
    assert client.get('/api/food-access').status_code==503
