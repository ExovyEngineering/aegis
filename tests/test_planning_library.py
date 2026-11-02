import hashlib
import json


def run(client, **overrides):
    response=client.post('/api/route-lab',json={'preset':'farm','routing':'estimated',**overrides})
    assert response.status_code==200,response.text
    return response.json()


def test_saved_snapshot_history_and_comparison_inputs_preserve_operator_state(client):
    before=client.get('/api/network').json()
    first=run(client); second=run(client,truck_count=1,delay_minutes=60)
    assert first['run_id']!=second['run_id']
    saved=client.post('/api/planning/projects',json={'name':'Farm baseline','run_id':first['run_id']}).json()
    pid=saved['id']
    assert saved['version']==1
    changed=client.post(f'/api/planning/projects/{pid}/update',json={'name':'Farm constrained','run_id':second['run_id'],'expected_version':1})
    assert changed.json()['version']==2
    stale=client.post(f'/api/planning/projects/{pid}/update',json={'name':'Stale edit','run_id':first['run_id'],'expected_version':1})
    assert stale.status_code==409
    detail=client.get(f'/api/planning/projects/{pid}?version=1').json()
    assert detail['run']['result']==first
    assert detail['run']['request']['delay_minutes']==0
    assert len(detail['history'])==2
    assert client.get('/api/network').json()==before
    assert client.get('/api/driver').json()==[]
    assert detail['run']['dispatchable'] is False


def test_run_checksum_export_and_archive_keep_history(client):
    result=run(client)
    snap=client.get('/api/planning/runs/'+result['run_id']).json()
    raw_result={k:v for k,v in snap['result'].items() if k not in ('run_id','run_created_at','run_checksum')}
    request=json.dumps(snap['request'],sort_keys=True,separators=(',',':'),allow_nan=False)
    output=json.dumps(raw_result,sort_keys=True,separators=(',',':'),allow_nan=False)
    assert hashlib.sha256((request+'\n'+output).encode()).hexdigest()==snap['checksum']
    csv=client.get('/api/planning/runs/'+result['run_id']+'/stops.csv')
    assert csv.status_code==200 and 'not approved dispatch' in csv.text
    project=client.post('/api/planning/projects',json={'name':'Saved trial','run_id':result['run_id']}).json()
    path='/api/planning/projects/'+project['id']
    assert client.post(path+'/archive',json={'expected_version':2}).status_code==409
    assert client.post(path+'/archive',json={'expected_version':1}).json()['history_preserved']
    assert client.get('/api/planning/projects').json()==[]
    assert client.get(path).json()['archived']
    assert client.post(path+'/update',json={'expected_version':1,'name':'Reopen','run_id':result['run_id']}).status_code==409


def test_cannot_save_fabricated_run_or_metrics(client):
    assert client.post('/api/planning/projects',json={'name':'Fake','run_id':'missing'}).status_code==404
    result=run(client)
    assert client.post('/api/planning/projects',json={'name':'Fake','run_id':result['run_id'],'result':{'total_cost':0}}).status_code==422
    assert client.get('/api/planning/projects').json()==[]
