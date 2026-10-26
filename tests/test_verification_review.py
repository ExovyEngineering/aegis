import pytest

CHECKS={'temperature_history_reviewed':True,'packaging_condition_reviewed':True,'simulated_lot_identity_reviewed':True}


def prepare(client):
    proposal=client.post('/api/proposals/B').json()
    assert client.post('/api/proposals/'+proposal['id']+'/approve',json={'actor':'Reviewer','reason':'Reviewed simulated constraints and inspection requirement'}).status_code==200
    snapshot=client.get('/api/dispatch').json()
    shipment=next(s for s in snapshot['assignments'] if s['verification_required'])
    body={'actor':'Reviewer','reason':'Reviewed simulated history, condition and identity','expected_network_revision':snapshot['network_revision'],'expected_verification_version':0,'outcome':'complete','checks':CHECKS}
    return shipment,body


def test_targeted_review_records_context_without_holding_or_mutating_network(client):
    shipment,body=prepare(client); before=client.get('/api/network').json()
    path=f"/api/dispatch/assignments/{shipment['id']}/verification"
    result=client.post(path,json=body)
    assert result.status_code==200,result.text
    assert result.json()['status']=='complete' and result.json()['version']==1
    assert result.json()['context']['lot_id']==shipment['lot_id']
    assert 'not a laboratory result' in result.json()['provenance']
    assert client.get('/api/network').json()==before
    updated=next(s for s in client.get('/api/driver').json() if s['id']==shipment['id'])
    assert updated['verification_status']=='complete' and updated['verification_required']
    assert any(x['action']=='targeted_verification_review' for x in client.get('/api/audit').json())
    assert client.post(path,json=body).status_code==409


def test_incomplete_checks_and_whitespace_cannot_record_completion(client):
    shipment,body=prepare(client);path=f"/api/dispatch/assignments/{shipment['id']}/verification"
    assert client.post(path,json={**body,'checks':{**CHECKS,'temperature_history_reviewed':False}}).status_code==422
    assert client.post(path,json={**body,'actor':'   '}).status_code==422
    assert client.post(path,json={**body,'checks':{**CHECKS,'packaging_condition_reviewed':'yes'}}).status_code==422
    pending=client.post(path,json={**body,'outcome':'review_required','checks':{k:False for k in CHECKS}})
    assert pending.status_code==200 and pending.json()['status']=='review_required'
    assert next(x for x in client.get('/api/network').json()['lots'] if x['id']==shipment['lot_id'])['held'] is False


def test_stale_network_and_removed_assignment_cannot_be_verified(client):
    shipment,body=prepare(client)
    client.post('/api/events',json={'event':'delivery_delay','shipment_id':shipment['id']})
    path=f"/api/dispatch/assignments/{shipment['id']}/verification"
    assert client.post(path,json=body).status_code==409
    body['expected_network_revision']=client.get('/api/network').json()['revision']
    assert client.post(path,json=body).status_code==404


def test_independent_approval_rejects_unsafe_identical_solver_results(client,monkeypatch):
    import backend.main as api
    from backend.optimization import optimize
    from backend.simulation import seed_network
    bad=optimize(seed_network(),'A');bad['shipments'][0]['quantity_kg']=-400
    monkeypatch.setattr(api,'optimize',lambda *args:bad)
    proposal=client.post('/api/proposals/A').json()
    response=client.post('/api/proposals/'+proposal['id']+'/approve',json={'actor':'Reviewer','reason':'Trying an externally corrupted plan'})
    assert response.status_code==409 and 'Independent' in response.json()['detail']
    assert client.get('/api/driver').json()==[]
    assert client.get('/api/network').json()['revision']==0
