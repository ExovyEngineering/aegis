"""Dispatcher decisions are atomic, versioned and independent of driver reports."""
import json

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import backend.main as api
from backend.dispatch import (
    create_dispatch_router, create_driver_incident, ensure_dispatch_schema,
)


IDENTITY = {'actor': ' Test dispatcher ', 'reason': ' Reviewed simulated shipment evidence '}


@pytest.fixture
def dispatch_client(tmp_path, monkeypatch):
    monkeypatch.setattr(api, 'DB', tmp_path / 'dispatch.sqlite')
    with api.db() as connection:
        ensure_dispatch_schema(connection)
        network, _ = api.load(connection)
        for shipment_id in ['SH03', 'SH04']:
            shipment = next(s for s in network['shipments'] if s['id'] == shipment_id)
            connection.execute('INSERT INTO assignments VALUES (?,?,0)',
                               (shipment_id, json.dumps(shipment)))
    app = FastAPI()
    app.include_router(create_dispatch_router(api.db, api.load, api.record))
    with TestClient(app) as client:
        yield client


def report_incident(shipment_id='SH03'):
    with api.db() as connection:
        return create_driver_incident(connection, shipment_id,
                                      'Parked; refrigeration alarm needs dispatcher review', api.record)


def snapshot(client):
    response = client.get('/api/dispatch')
    assert response.status_code == 200
    return response.json()


def instruction(client, shipment_id='SH03', **overrides):
    state = snapshot(client)
    assigned = next(a for a in state['assignments'] if a['id'] == shipment_id)
    body = dict(IDENTITY, instruction='Remain parked pending dispatcher review',
                expected_network_revision=state['network_revision'],
                expected_instruction_revision=assigned['instruction_revision'])
    body.update(overrides)
    return client.post(f'/api/dispatch/assignments/{shipment_id}/instruction', json=body)


def test_driver_report_is_open_until_identified_dispatcher_reviews(dispatch_client):
    result = report_incident()
    state = snapshot(dispatch_client)
    assert len(state['incidents']) == 1
    incident = state['incidents'][0]
    assert incident['id'] == result['incident_id']
    assert incident['status'] == 'open' and incident['version'] == 0
    assert incident['reported_at'] and 'simulated' in incident['provenance']
    response = dispatch_client.post(f"/api/dispatch/incidents/{incident['id']}/review", json={
        **IDENTITY, 'status': 'in_review', 'expected_version': 0,
    })
    assert response.status_code == 200
    assert response.json()['review']['actor'] == 'Test dispatcher'
    assert response.json()['version'] == 1
    stale = dispatch_client.post(f"/api/dispatch/incidents/{incident['id']}/review", json={
        **IDENTITY, 'status': 'resolved', 'expected_version': 0,
    })
    assert stale.status_code == 409
    resolved = dispatch_client.post(f"/api/dispatch/incidents/{incident['id']}/review", json={
        **IDENTITY, 'status': 'resolved', 'expected_version': 1,
    })
    assert resolved.status_code == 200 and resolved.json()['version'] == 2
    with api.db() as connection:
        actions = [r[0] for r in connection.execute('SELECT action FROM audit')]
    assert actions.count('incident') == 1 and actions.count('incident_review') == 2


def test_unknown_or_unassigned_report_cannot_enter_dispatch_inbox(dispatch_client):
    with pytest.raises(HTTPException) as error:
        report_incident('SH24')
    assert error.value.status_code == 404
    assert snapshot(dispatch_client)['incidents'] == []


def test_incident_preserves_reporting_revision_and_trip_when_assignment_is_reused(dispatch_client):
    incident_id = report_incident()['incident_id']
    first = snapshot(dispatch_client)['incidents'][0]
    assert first['reported_network_revision'] == 0
    assert first['reporting_assignment'] == {
        'id': 'SH03', 'lot_id': 'L03', 'truck_id': 'T03',
        'origin': 'DC1', 'destination': 'D03',
    }
    with api.db() as connection:
        assignment = json.loads(connection.execute('SELECT payload FROM assignments WHERE id=?', ('SH03',)).fetchone()[0])
        assignment.update(lot_id='L04', truck_id='T04', destination='D04')
        connection.execute('UPDATE assignments SET payload=? WHERE id=?', (json.dumps(assignment), 'SH03'))
        connection.execute('UPDATE state SET revision=revision+1 WHERE id=1')
    state = snapshot(dispatch_client)
    assert state['network_revision'] == 1
    historical = next(i for i in state['incidents'] if i['id'] == incident_id)
    assert historical['reported_network_revision'] == 0
    assert historical['reporting_assignment'] == first['reporting_assignment']
    response = dispatch_client.post(f'/api/dispatch/incidents/{incident_id}/review', json={
        **IDENTITY, 'status': 'resolved', 'expected_version': 0,
    })
    assert response.status_code == 200
    assert response.json()['reporting_assignment'] == first['reporting_assignment']


@pytest.mark.parametrize('field,value', [('actor', '  '), ('reason', '     ')])
def test_human_decisions_reject_blank_identity_or_reason(dispatch_client, field, value):
    state = snapshot(dispatch_client)
    response = dispatch_client.post('/api/dispatch/lots/L03/hold', json={
        **IDENTITY, field: value, 'expected_network_revision': state['network_revision'],
    })
    assert response.status_code == 422
    assert snapshot(dispatch_client)['network_revision'] == state['network_revision']


def test_hold_removes_only_affected_assignments_and_release_does_not_republish(dispatch_client):
    state = snapshot(dispatch_client)
    response = dispatch_client.post('/api/dispatch/lots/L03/hold', json={
        **IDENTITY, 'expected_network_revision': state['network_revision'],
    })
    assert response.status_code == 200 and response.json()['invalidated_shipments'] == ['SH03']
    after = snapshot(dispatch_client)
    assert [a['id'] for a in after['assignments']] == ['SH04']
    assert next(l for l in after['lots'] if l['id'] == 'L03')['held']
    assert after['network_revision'] == state['network_revision'] + 1
    stale_release = dispatch_client.post('/api/dispatch/lots/L03/release', json={
        **IDENTITY, 'expected_network_revision': state['network_revision'],
    })
    assert stale_release.status_code == 409
    release = dispatch_client.post('/api/dispatch/lots/L03/release', json={
        **IDENTITY, 'expected_network_revision': after['network_revision'],
    })
    assert release.status_code == 200 and release.json()['assignments_republished'] is False
    assert [a['id'] for a in snapshot(dispatch_client)['assignments']] == ['SH04']


def test_precautionary_release_cannot_clear_a_recall(dispatch_client):
    with api.db() as connection:
        network, revision = api.load(connection)
        lot = next(l for l in network['lots'] if l['id'] == 'L01')
        lot['recalled'] = True
        connection.execute('UPDATE state SET payload=? WHERE id=1', (json.dumps(network),))
    response = dispatch_client.post('/api/dispatch/lots/L01/release', json={
        **IDENTITY, 'expected_network_revision': revision,
    })
    assert response.status_code == 409
    lot = next(l for l in snapshot(dispatch_client)['lots'] if l['id'] == 'L01')
    assert lot['held'] and lot['recalled']


def test_instructions_require_current_approved_eligible_assignment(dispatch_client):
    assert dispatch_client.post('/api/dispatch/assignments/UNKNOWN/instruction', json={
        **IDENTITY, 'instruction': 'Remain parked',
        'expected_network_revision': 0, 'expected_instruction_revision': 0,
    }).status_code == 404
    assert instruction(dispatch_client, expected_network_revision=999).status_code == 409
    with api.db() as connection:
        network, _ = api.load(connection)
        next(l for l in network['lots'] if l['id'] == 'L03')['held'] = True
        connection.execute('UPDATE state SET payload=? WHERE id=1', (json.dumps(network),))
    assert instruction(dispatch_client).status_code == 409
    assert next(a for a in snapshot(dispatch_client)['assignments'] if a['id'] == 'SH03')['instruction_revision'] == 0


def test_new_instruction_requires_its_own_versioned_acknowledgment(dispatch_client):
    first = instruction(dispatch_client)
    assert first.status_code == 200 and first.json()['instruction_revision'] == 1
    assignment = next(a for a in snapshot(dispatch_client)['assignments'] if a['id'] == 'SH03')
    assert not assignment['instruction_acknowledged']
    assert not assignment['acknowledged']  # Separate from accepting the original trip.
    assert instruction(dispatch_client, expected_instruction_revision=0).status_code == 409
    second = instruction(dispatch_client, instruction='Park at the next suitable safe location')
    assert second.status_code == 200 and second.json()['instruction_revision'] == 2
    path = '/api/driver/SH03/instruction-ack'
    assert dispatch_client.post(path, json={'instruction_revision': 1}).status_code == 409
    assert dispatch_client.post(path, json={'instruction_revision': 2}).status_code == 200
    assert dispatch_client.post(path, json={'instruction_revision': 2}).json()['status'] == 'already acknowledged'
    assignment = next(a for a in snapshot(dispatch_client)['assignments'] if a['id'] == 'SH03')
    assert assignment['instruction_acknowledged'] and not assignment['acknowledged']
    with api.db() as connection:
        assert connection.execute("SELECT COUNT(*) FROM audit WHERE action='instruction_acknowledge'").fetchone()[0] == 1


def test_replaced_assignment_does_not_reuse_an_old_instruction_revision(dispatch_client):
    assert instruction(dispatch_client).json()['instruction_revision'] == 1
    with api.db() as connection:
        original = json.loads(connection.execute('SELECT payload FROM assignments WHERE id=?', ('SH03',)).fetchone()[0])
        for key in list(original):
            if key.startswith('instruction'): original.pop(key)
        connection.execute('UPDATE assignments SET payload=? WHERE id=?', (json.dumps(original), 'SH03'))
    response = instruction(dispatch_client)
    assert response.status_code == 200 and response.json()['instruction_revision'] == 2
    assert dispatch_client.post('/api/driver/SH03/instruction-ack', json={'instruction_revision': 1}).status_code == 409


def test_hold_serializes_against_instruction_and_retains_history(dispatch_client):
    assert instruction(dispatch_client).status_code == 200
    state = snapshot(dispatch_client)
    assert dispatch_client.post('/api/dispatch/lots/L03/hold', json={
        **IDENTITY, 'expected_network_revision': state['network_revision'],
    }).status_code == 200
    assert dispatch_client.post('/api/driver/SH03/instruction-ack', json={'instruction_revision': 1}).status_code == 404
    with api.db() as connection:
        actions = [r[0] for r in connection.execute('SELECT action FROM audit')]
    assert 'dispatcher_instruction' in actions and 'lot_hold' in actions
