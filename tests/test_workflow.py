import pytest


APPROVER = {'actor': 'Test dispatcher', 'reason': 'Reviewed constraints and simulated excursion evidence'}


def test_approval_is_required_before_driver_assignment(client):
    assert client.get('/api/health').status_code == 200
    assert client.get('/api/driver').json() == []
    proposal = client.post('/api/proposals/A').json()
    assert client.get('/api/driver').json() == []
    response = client.post(f"/api/proposals/{proposal['id']}/approve", json=APPROVER)
    assert response.status_code == 200
    assignments = client.get('/api/driver').json()
    assert len(assignments) == response.json()['assignments'] > 0
    network = client.get('/api/network').json()
    held = {lot['id'] for lot in network['lots'] if lot['held'] or lot['recalled']}
    assert not any(s['lot_id'] in held for s in assignments)
    assert client.post(f"/api/proposals/{proposal['id']}/approve", json=APPROVER).status_code == 409
    audits = client.get('/api/audit').json()
    assert sum(a['action'] == 'approve' for a in audits) == 1
    assert audits[0]['actor'] == APPROVER['actor']
    assert audits[0]['payload']['reason'] == APPROVER['reason']


@pytest.mark.parametrize('change', ['event', 'reset', 'another_approval'])
def test_stale_proposal_cannot_be_approved(client, change):
    proposal = client.post('/api/proposals/A').json()
    if change == 'event':
        assert client.post('/api/events', json={'event': 'inventory_shortage', 'shipment_id': 'SH03'}).status_code == 200
    elif change == 'reset':
        assert client.post('/api/demo/reset').status_code == 200
    else:
        other = client.post('/api/proposals/B').json()
        assert client.post(f"/api/proposals/{other['id']}/approve", json=APPROVER).status_code == 200
    rejected = client.post(f"/api/proposals/{proposal['id']}/approve", json=APPROVER)
    assert rejected.status_code == 409
    assert 'changed' in rejected.json()['detail'].lower()


def test_holds_take_effect_only_after_human_approval(client):
    proposal = client.post('/api/proposals/C').json()
    proposed = set(proposal['proposed_hold_lots'])
    assert proposed
    before = client.get('/api/network').json()
    assert not any(l['held'] for l in before['lots'] if l['id'] in proposed)
    assert client.post(f"/api/proposals/{proposal['id']}/approve", json=APPROVER).status_code == 200
    after = client.get('/api/network').json()
    assert all(l['held'] for l in after['lots'] if l['id'] in proposed)
    assert not any(s['lot_id'] in proposed for s in client.get('/api/driver').json())


def test_driver_acknowledgment_and_incident_audit(client):
    proposal = client.post('/api/proposals/A').json()
    assert client.post(f"/api/proposals/{proposal['id']}/approve", json=APPROVER).status_code == 200
    assignment = client.get('/api/driver').json()[0]
    assert not assignment['acknowledged']
    assert client.post(f"/api/driver/{assignment['id']}/acknowledge").status_code == 200
    assert next(s for s in client.get('/api/driver').json() if s['id'] == assignment['id'])['acknowledged']
    incident = {'shipment_id': assignment['id'], 'description': 'Refrigerator alarm reported while parked'}
    report_response=client.post('/api/driver/incident', json=incident)
    assert report_response.status_code == 200
    audits = client.get('/api/audit').json()
    assert audits[0]['action'] == 'incident'
    assert audits[0]['payload'] == dict(incident,incident_id=report_response.json()['incident_id'])
    assert client.post('/api/driver/UNKNOWN/acknowledge').status_code == 404


def test_driver_cannot_report_incident_for_unassigned_or_unknown_trip(client):
    assert client.post('/api/driver/incident', json={'shipment_id': 'SH01', 'description': 'Not an approved trip yet'}).status_code == 404
    assert client.post('/api/driver/incident', json={'shipment_id': 'UNKNOWN', 'description': 'This trip does not exist'}).status_code == 404
    assert not any(a['action'] == 'incident' for a in client.get('/api/audit').json())


def test_events_invalidate_dispatch_and_preserve_audit(client):
    proposal = client.post('/api/proposals/A').json()
    client.post(f"/api/proposals/{proposal['id']}/approve", json=APPROVER)
    assert client.get('/api/driver').json()
    event = client.post('/api/events', json={'event': 'refrigeration_fault', 'shipment_id': 'SH03'})
    assert event.status_code == 200
    assert client.get('/api/driver').json() == []
    assert {a['action'] for a in client.get('/api/audit').json()} >= {'approve', 'event'}


def test_invalid_actions_do_not_change_network(client):
    before = client.get('/api/network').json()
    assert client.post('/api/proposals/INVALID').status_code == 400
    assert client.post('/api/events', json={'event': 'verified_recall', 'shipment_id': 'SH01'}).status_code == 400
    assert client.post('/api/events', json={'event': 'road_closure', 'shipment_id': 'UNKNOWN'}).status_code == 400
    assert client.get('/api/network').json() == before
    assert client.post('/api/proposals/missing/approve', json=APPROVER).status_code == 404
    assert client.get('/api/evidence/unrecognized').status_code == 404


@pytest.mark.parametrize('body', [{'actor': '', 'reason': 'reviewed'}, {'actor': 'dispatcher', 'reason': ''}])
def test_approval_needs_operator_and_reason(client, body):
    proposal = client.post('/api/proposals/A').json()
    assert client.post(f"/api/proposals/{proposal['id']}/approve", json=body).status_code == 422
    assert client.get('/api/driver').json() == []
