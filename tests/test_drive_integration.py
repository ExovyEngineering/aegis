"""Real app integration: driver mutations require a current parked declaration."""
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
import pytest

import backend.drive as drive
import backend.main as api

IDENTITY = {'actor':'Drive integration dispatcher', 'reason':'Reviewed simulated trip constraints and handling requirements'}


@pytest.fixture
def unparked_client(tmp_path, monkeypatch):
    monkeypatch.setattr(api, 'DB', tmp_path / 'drive-integration.sqlite')
    with TestClient(api.app) as client:
        yield client


def approve_trip(client):
    proposal=client.post('/api/proposals/A').json()
    response=client.post(f"/api/proposals/{proposal['id']}/approve",json=IDENTITY)
    assert response.status_code==200,response.text
    shipment=client.get('/api/driver').json()[0]
    revision=client.get('/api/network').json()['revision']
    instruction=client.post(f"/api/dispatch/assignments/{shipment['id']}/instruction",json={
        **IDENTITY, 'instruction':'Remain parked while reviewing this test trip',
        'expected_instruction_revision':0,'expected_network_revision':revision,
    })
    assert instruction.status_code==200,instruction.text
    return shipment,instruction.json()['instruction_revision']


def action(client, kind, shipment, instruction_revision):
    sid=shipment['id']
    if kind=='acknowledge':return client.post(f'/api/driver/{sid}/acknowledge')
    if kind=='incident':return client.post('/api/driver/incident',json={'shipment_id':sid,'description':'Parked driver reported a simulated access concern'})
    return client.post(f'/api/driver/{sid}/instruction-ack',json={'instruction_revision':instruction_revision})


def parked(client, truck_id):
    focus=client.get(f'/api/drive/{truck_id}').json()['focus']
    response=client.post(f'/api/drive/{truck_id}/focus',json={'mode':'parked','expected_version':focus['version'],'parked_confirmation':True})
    assert response.status_code==200,response.text
    return response.json()


@pytest.mark.parametrize('kind',['acknowledge','incident','instruction_ack'])
def test_legacy_mutations_lock_by_default_and_allow_explicitly_parked_driver(unparked_client,kind):
    client=unparked_client;shipment,version=approve_trip(client)
    assert client.get(f"/api/drive/{shipment['truck_id']}").json()['focus']['mode']=='locked'
    before=client.get('/api/audit').json()
    denied=action(client,kind,shipment,version)
    assert denied.status_code==423,denied.text
    assert client.get('/api/audit').json()==before
    parked(client,shipment['truck_id'])
    assert action(client,kind,shipment,version).status_code==200


@pytest.mark.parametrize('kind',['acknowledge','incident','instruction_ack'])
def test_expired_parked_confirmation_cannot_authorize_legacy_mutation(unparked_client,monkeypatch,kind):
    client=unparked_client;shipment,version=approve_trip(client)
    instant=datetime(2026,10,27,15,0,tzinfo=timezone.utc)
    monkeypatch.setattr(drive,'_utc_now',lambda:instant)
    parked(client,shipment['truck_id'])
    monkeypatch.setattr(drive,'_utc_now',lambda:instant+timedelta(seconds=600))
    assert action(client,kind,shipment,version).status_code==423


@pytest.mark.parametrize('kind',['acknowledge','incident','instruction_ack'])
def test_driving_focus_locks_existing_mutations_again(unparked_client,kind):
    client=unparked_client;shipment,version=approve_trip(client)
    focus=parked(client,shipment['truck_id'])
    locked=client.post(f"/api/drive/{shipment['truck_id']}/focus",json={'mode':'driving','expected_version':focus['version']})
    assert locked.status_code==200 and not locked.json()['interaction_allowed']
    assert action(client,kind,shipment,version).status_code==423


@pytest.mark.parametrize('kind',['acknowledge','incident','instruction_ack'])
def test_unknown_or_held_assignment_returns_404_before_focus_gate(unparked_client,kind):
    client=unparked_client;shipment,version=approve_trip(client)
    assert action(client,kind,{**shipment,'id':'UNKNOWN'},version).status_code==404
    revision=client.get('/api/network').json()['revision']
    held=client.post(f"/api/dispatch/lots/{shipment['lot_id']}/hold",json={**IDENTITY,'expected_network_revision':revision})
    assert held.status_code==200
    assert action(client,kind,shipment,version).status_code==404


def test_focus_and_simulated_vehicle_snapshot_do_not_change_network_or_assignments(unparked_client):
    client=unparked_client;shipment,_=approve_trip(client)
    network=client.get('/api/network').json();assignments=client.get('/api/driver').json()
    snapshot=client.get(f"/api/drive/{shipment['truck_id']}").json()
    parked(client,shipment['truck_id'])
    assert snapshot['vehicle']['simulation']
    assert client.get('/api/network').json()==network
    assert client.get('/api/driver').json()==assignments
