"""Source identity and partial-download regressions, using isolated raw folders."""
import json
from pathlib import Path
import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.data_explorer import create_data_router
from backend.ingestion.beam import BEAM_SCHEMAS
from backend.ingestion.common import publish_parquet,sha256_file
from backend.ingestion.fsis import FSISPoultryAdapter
from scripts.ingest_evidence import ingest


def csv(path,values):
    path.parent.mkdir(parents=True,exist_ok=True)
    pd.DataFrame([values]).to_csv(path,index=False,sep='\t' if path.suffix=='.tsv' else ',')
    return path


def environment(tmp_path):
    raw=tmp_path/'raw';raw.mkdir()
    output=tmp_path/'data/processed'
    report=tmp_path/'reports/evidence_ingestion.json'
    return raw,output,report


def manifest(output):return json.loads((output/'evidence_manifest.json').read_text())


def client(root):
    app=FastAPI();app.include_router(create_data_router(root));return TestClient(app)


def test_nested_renamed_exports_keep_semantic_identity_and_raw_bytes(tmp_path):
    raw,out,report=environment(tmp_path)
    original={}
    for number,(identity,fields) in enumerate(reversed(list(BEAM_SCHEMAS.items()))):
        path=csv(raw/'nested'/f'arbitrary_{number}.csv',{key:'source literal' for key in sorted(fields)})
        original[path]=path.read_bytes()
    nors=csv(raw/'other'/'not-named-nors.tsv',{'Year':'2025','State':'Missouri','Primary Mode':'Food','Etiology':'Salmonella'})
    original[nors]=nors.read_bytes()
    reports=ingest(raw,out,report)
    assert len(reports)==6 and all(row['status']=='ingested' for row in reports)
    assert set(manifest(out)['datasets'])==set(BEAM_SCHEMAS)|{'nors_0'}
    for identity,fields in BEAM_SCHEMAS.items():assert set(pd.read_parquet(out/f'{identity}.parquet'))==fields
    assert all(path.read_bytes()==body for path,body in original.items())
    with client(tmp_path) as c:
        catalog=c.get('/api/data/catalog').json()
        common=next(row for row in catalog if row['id']=='beam_4')
        assert common['status']=='available' and common['source_key']=='cdc_beam_common_serotypes'
        assert common['input_files'][0]['relative_path']=='nested/arbitrary_0.csv'
        assert common['output_sha256']==common['sha256']


def test_duplicate_downloads_do_not_duplicate_rows_or_relabel_other_tables(tmp_path):
    raw,out,report=environment(tmp_path)
    original=csv(raw/'z.csv',{'Year':'2025','State':'MO','Primary Mode':'Food','Etiology':'Salmonella'})
    (raw/'a.csv').write_bytes(original.read_bytes())
    reports=ingest(raw,out,report)
    assert [row['status'] for row in reports]==['ingested','duplicate']
    assert reports[1]['duplicate_of']=='a.csv'
    assert len(pd.read_parquet(out/'nors_0.parquet'))==1
    assert len(manifest(out)['datasets']['nors_0']['input_files'])==2


def test_different_snapshots_block_browsing_and_preserve_previous_output(tmp_path):
    raw,out,report=environment(tmp_path)
    csv(raw/'one.csv',{'Year':'2024','State':'MO','Primary Mode':'Food','Etiology':'Salmonella'})
    ingest(raw,out,report);previous=(out/'nors_0.parquet').read_bytes()
    csv(raw/'two.csv',{'Year':'2025','State':'MO','Primary Mode':'Food','Etiology':'Salmonella'})
    reports=ingest(raw,out,report)
    assert all(row['status']=='conflict' for row in reports)
    assert (out/'nors_0.parquet').read_bytes()==previous
    with client(tmp_path) as c:
        entry=next(row for row in c.get('/api/data/catalog').json() if row['id']=='nors_0')
        assert entry['status']=='conflict' and 'different exports' in entry['error']
        assert c.get('/api/data/nors_0').status_code==503


def test_unknown_and_corrupt_csv_continue_without_pooling(tmp_path):
    raw,out,report=environment(tmp_path)
    csv(raw/'BEAM_wrong.csv',{'Year':'2025','Pathogen':'Salmonella','meaning':'unsupported'})
    (raw/'partial.csv').write_text('Year,State,"Primary Mode,Etiology\n')
    csv(raw/'valid.csv',{'Year':'2025','State':'MO','Primary Mode':'Food','Etiology':'Salmonella'})
    reports=ingest(raw,out,report)
    byname={row['file']:row for row in reports}
    assert byname['BEAM_wrong.csv']['status']=='unrecognized'
    assert byname['partial.csv']['status']=='failed' and 'ParserError:' in byname['partial.csv']['error']
    assert byname['valid.csv']['status']=='ingested'
    assert list(out.glob('beam_*.parquet'))==[]


def test_failed_known_export_does_not_publish_partial_table(tmp_path):
    raw,out,report=environment(tmp_path)
    path=csv(raw/'one.csv',{'Year':'2024','State':'MO','Primary Mode':'Food','Etiology':'Salmonella'})
    ingest(raw,out,report);previous=(out/'nors_0.parquet').read_bytes()
    path.write_text('Year,State,Primary Mode,Etiology\n2025,MO,Food,Salmonella\n2025,"unclosed\n')
    reports=ingest(raw,out,report)
    assert reports[0]['status']=='failed' and 'ParserError:' in reports[0]['error']
    assert (out/'nors_0.parquet').read_bytes()==previous
    with client(tmp_path) as c:assert c.get('/api/data/nors_0').status_code==503


def test_output_tampering_or_swapped_beam_identity_is_not_presented_as_source(tmp_path):
    raw,out,report=environment(tmp_path)
    csv(raw/'one.csv',{key:'x' for key in BEAM_SCHEMAS['beam_0']})
    ingest(raw,out,report)
    pd.DataFrame({'Year':['2025'],'unexpected':['value']}).to_parquet(out/'beam_0.parquet',index=False)
    with client(tmp_path) as c:
        assert c.get('/api/data/beam_0').status_code==503
        entry=next(row for row in c.get('/api/data/catalog').json() if row['id']=='beam_0')
        assert entry['status']=='unreadable'
    (out/'evidence_manifest.json').unlink()
    with client(tmp_path) as c:assert c.get('/api/data/beam_0').status_code==503


def test_missing_new_input_does_not_claim_old_output_is_latest(tmp_path):
    raw,out,report=environment(tmp_path)
    path=csv(raw/'one.csv',{'Year':'2024','State':'MO','Primary Mode':'Food','Etiology':'Salmonella'})
    ingest(raw,out,report);path.unlink();ingest(raw,out,report)
    assert (out/'nors_0.parquet').exists()
    with client(tmp_path) as c:
        entry=next(row for row in c.get('/api/data/catalog').json() if row['id']=='nors_0')
        assert entry['status']=='not in latest ingestion'
        assert c.get('/api/data/nors_0').status_code==503


def test_atomic_parquet_failure_preserves_previous_bytes(tmp_path,monkeypatch):
    path=tmp_path/'table.parquet';publish_parquet(pd.DataFrame({'a':[1]}),path);previous=path.read_bytes()
    def broken(self,destination,**kwargs):Path(destination).write_bytes(b'partial');raise OSError('disk interrupted')
    monkeypatch.setattr(pd.DataFrame,'to_parquet',broken)
    with pytest.raises(OSError,match='disk interrupted'):publish_parquet(pd.DataFrame({'a':[2]}),path)
    assert path.read_bytes()==previous and list(tmp_path.glob('*.tmp'))==[]


def observation(sample='1',**overrides):
    return {'form_id':sample,'sample_number':sample,'establishment_id':'P1','establishment_state':'MO','project_code':'HC_CH_CARC01',
            'collection_date':'2025-01-01','salmonella_sp_analysis':'Negative','salmonella_sp_analysis_canceled':'NULL',**overrides}


def fsis(path,rows,declared=None):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps([{'metadata':{'data_product_name':'Raw Poultry Product Sampling','creation_date':'March 19, 2026','data_records':{'primary':len(rows) if declared is None else declared}},'data':{'primary_table_data':rows,'secondary_table_data':[{'typing':'not an outcome'}]}}]))
    return path


def test_fsis_corrupt_unrelated_json_is_reported_while_valid_rows_continue(tmp_path):
    raw,out,_=environment(tmp_path);report=tmp_path/'reports/fsis_ingestion.json'
    good=fsis(raw/'nested'/'arbitrary.json',[observation()]);original=good.read_bytes()
    (raw/'bad.json').write_text('[{"metadata":')
    (raw/'other.json').write_text(json.dumps({'unrelated':'not FSIS'}))
    frame=FSISPoultryAdapter().ingest(raw,out,report)
    assert len(frame)==1 and frame.source_file.tolist()==['nested/arbitrary.json']
    saved=json.loads(report.read_text());assert saved['status']=='partial'
    assert len(saved['errors'])==1 and 'IncompleteJSONError:' in saved['errors'][0]['error']
    provenance=json.loads((out/'fsis_provenance.json').read_text())
    assert provenance['sources'][0]['sha256']==sha256_file(good)
    assert provenance['sources'][0]['parsed_primary_rows']==1
    assert good.read_bytes()==original


def test_fsis_partial_primary_payload_is_excluded_as_a_whole(tmp_path):
    raw,out,_=environment(tmp_path);report=tmp_path/'reports/fsis_ingestion.json'
    fsis(raw/'good.json',[observation('good')]);fsis(raw/'partial.json',[observation('partial')],declared=10)
    frame=FSISPoultryAdapter().ingest(raw,out,report)
    assert frame.form_id.tolist()==['good']
    error=json.loads(report.read_text())['errors'][0]
    assert error['file']=='partial.json' and 'declared 10, parsed 1' in error['error']


def test_fsis_revised_non_outcome_fields_cannot_silently_deduplicate(tmp_path):
    raw,out,_=environment(tmp_path);report=tmp_path/'reports/fsis_ingestion.json'
    fsis(raw/'one.json',[observation()]);FSISPoultryAdapter().ingest(raw,out,report)
    previous=(out/'fsis_poultry.parquet').read_bytes()
    fsis(raw/'two.json',[observation(collection_date='2025-01-02')])
    with pytest.raises(ValueError,match='conflicting repeated'):FSISPoultryAdapter().ingest(raw,out,report)
    assert (out/'fsis_poultry.parquet').read_bytes()==previous
    with client(tmp_path) as c:assert c.get('/api/data/fsis_poultry').status_code==503


def test_fsis_exact_duplicate_does_not_inflate_primary_rows(tmp_path):
    raw,out,_=environment(tmp_path);report=tmp_path/'reports/fsis_ingestion.json'
    path=fsis(raw/'one.json',[observation()]);(raw/'copy.json').write_bytes(path.read_bytes())
    frame=FSISPoultryAdapter().ingest(raw,out,report)
    assert len(frame)==1
    saved=json.loads(report.read_text());assert sorted(row['status'] for row in saved['files'])==['duplicate','ingested']


def test_directory_reports_excluded_coordinate_rows(tmp_path):
    raw,out,report=environment(tmp_path)
    table=pd.DataFrame([{'establishment_id':'P1','establishment_name':'Example','state':'MO','latitude':'38','longitude':'-92','activities':'Poultry'},
                        {'establishment_id':'P2','establishment_name':'Bad coordinate','state':'MO','latitude':'999','longitude':'-92','activities':'Poultry'},
                        {'establishment_id':'P3','establishment_name':'Elsewhere','state':'KS','latitude':'38','longitude':'-95','activities':'Poultry'}])
    table.to_csv(raw/'directory.csv',index=False)
    reports=ingest(raw,out,report)
    assert reports[0]['rows']==1 and reports[0]['adapter_counts']=={'input_rows':3,'missouri_rows':2,'excluded_invalid_coordinates':1}


def test_missing_input_directory_cannot_replace_existing_manifest(tmp_path):
    raw,out,report=environment(tmp_path)
    csv(raw/'one.csv',{'Year':'2024','State':'MO','Primary Mode':'Food','Etiology':'Salmonella'})
    ingest(raw,out,report);previous=(out/'evidence_manifest.json').read_bytes()
    with pytest.raises(FileNotFoundError,match='Data directory does not exist'):ingest(tmp_path/'nonexistent',out,report)
    assert (out/'evidence_manifest.json').read_bytes()==previous


def test_private_runtime_subfolders_are_not_source_inputs(tmp_path):
    raw,out,_=environment(tmp_path);report=tmp_path/'reports/fsis_ingestion.json'
    fsis(raw/'good.json',[observation()])
    for directory in ('.aws','.codex','.agents','.tools'):
        path=raw/directory/'session.json';path.parent.mkdir();path.write_text('not a dataset')
    FSISPoultryAdapter().ingest(raw,out,report)
    assert [row['file'] for row in json.loads(report.read_text())['files']]==['good.json']


def test_explorer_parses_the_exact_bytes_verified_before_a_concurrent_replace(tmp_path,monkeypatch):
    import backend.data_explorer as explorer
    raw,out,report=environment(tmp_path)
    csv(raw/'one.csv',{'Year':'2024','State':'MO','Primary Mode':'Food','Etiology':'Salmonella'})
    ingest(raw,out,report)
    path=out/'nors_0.parquet';original_hash=sha256_file(path)
    replacement=tmp_path/'replacement.parquet'
    pd.DataFrame([{'Year':2026,'State':'MO','Primary Mode':'Food','Etiology':'different snapshot'}]).to_parquet(replacement,index=False)
    actual_read=explorer.pq.read_table
    def replace_before_parse(source,*args,**kwargs):
        path.write_bytes(replacement.read_bytes())
        return actual_read(source,*args,**kwargs)
    monkeypatch.setattr(explorer.pq,'read_table',replace_before_parse)
    with client(tmp_path) as c:
        response=c.get('/api/data/nors_0');assert response.status_code==200
        payload=response.json()
        assert payload['rows'][0]['Year']==2024 and payload['snapshot_sha256']==original_hash
        assert sha256_file(path)!=payload['snapshot_sha256']


def test_absent_cancellation_column_cannot_be_reinterpreted_as_not_canceled(tmp_path):
    raw,out,_=environment(tmp_path);report=tmp_path/'reports/fsis_ingestion.json'
    fsis(raw/'good.json',[observation('good')])
    incomplete=observation('unknown');incomplete.pop('salmonella_sp_analysis_canceled')
    fsis(raw/'missing-column.json',[incomplete])
    frame=FSISPoultryAdapter().ingest(raw,out,report)
    assert frame.form_id.tolist()==['good']
    error=json.loads(report.read_text())['errors'][0]
    assert 'salmonella_sp_analysis_canceled' in error['error']
