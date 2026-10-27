"""A reused shipment ID must not transfer an old displayed action to a new lot."""
import pytest

IDENTITY={'actor':'Context test dispatcher','reason':'Reviewed changed simulated stock and assignment context'}


def approve(client,scenario):
    proposal=client.post('/api/proposals/'+scenario).json()
    response=client.post('/api/proposals/'+proposal['id']+'/approve',json=IDENTITY)
    assert response.status_code==200,response.text
    return client.get('/api/driver').json()


def request_action(client,kind,shipment,revision):
    context={} if revision is None else {'expected_network_revision':revision}
    if kind=='acknowledge':
        return client.post(f"/api/driver/{shipment['id']}/acknowledge",json=context)
    if kind=='incident':
        return client.post('/api/driver/incident',json={**context,'shipment_id':shipment['id'],'description':'Displayed trip has a simulated cargo concern'})
    return client.post(f"/api/drive/{shipment['truck_id']}/quick-report",json={**context,'shipment_id':shipment['id'],'kind':'cargo_issue'})


@pytest.mark.parametrize('kind',['acknowledge','incident','quick_report'])
def test_stale_reapproved_shipment_context_cannot_acknowledge_or_report_for_new_lot(client,kind):
    first=approve(client,'A')
    displayed=next(s for s in first if s['id']=='SH14')
    old_revision=client.get('/api/network').json()['revision']
    held=client.post(f"/api/dispatch/lots/{displayed['lot_id']}/hold",json={**IDENTITY,'expected_network_revision':old_revision})
    assert held.status_code==200
    second=approve(client,'D')
    current=next(s for s in second if s['id']==displayed['id'])
    assert current['lot_id']!=displayed['lot_id']
    current_revision=client.get('/api/network').json()['revision']
    assert current_revision>old_revision
    assert client.get(f"/api/drive/{current['truck_id']}").json()['focus']['interaction_allowed']
    audit_before=client.get('/api/audit').json()
    assignments_before=client.get('/api/driver').json()
    denied=request_action(client,kind,displayed,old_revision)
    assert denied.status_code==409,denied.text
    assert 'Network changed' in denied.json()['detail']
    assert client.get('/api/audit').json()==audit_before
    assert client.get('/api/driver').json()==assignments_before
    assert client.get('/api/dispatch').json()['incidents']==[]

    accepted=request_action(client,kind,current,current_revision)
    assert accepted.status_code==200,accepted.text
    if kind=='acknowledge':
        assert next(s for s in client.get('/api/driver').json() if s['id']==current['id'])['acknowledged']
    else:
        incident=client.get('/api/dispatch').json()['incidents'][0]
        assert incident['reporting_assignment']['lot_id']==current['lot_id']
        assert incident['reporting_assignment']['lot_id']!=displayed['lot_id']
        assert incident['reported_network_revision']==current_revision


@pytest.mark.parametrize('kind',['acknowledge','incident','quick_report'])
def test_revisionless_legacy_clients_remain_supported_while_parked(client,kind):
    shipment=approve(client,'A')[0]
    assert request_action(client,kind,shipment,None).status_code==200


def test_bodyless_legacy_acknowledgment_remains_supported(client):
    shipment=approve(client,'A')[0]
    assert client.post(f"/api/driver/{shipment['id']}/acknowledge").status_code==200


@pytest.mark.parametrize('kind',['acknowledge','incident','quick_report'])
def test_negative_context_revision_is_rejected_without_writes(client,kind):
    shipment=approve(client,'A')[0]
    before=client.get('/api/audit').json()
    assert request_action(client,kind,shipment,-1).status_code==422
    assert client.get('/api/audit').json()==before
