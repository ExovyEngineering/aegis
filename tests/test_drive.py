"""Drive gates and scenario telemetry use isolated state, never operator data."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
import sqlite3

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest

import backend.drive as drive
from backend.dispatch import ensure_dispatch_schema
from backend.simulation import seed_network


@pytest.fixture
def drive_client(tmp_path):
    database = tmp_path / 'drive.sqlite'

    @contextmanager
    def db():
        connection = sqlite3.connect(database)
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    network = seed_network()
    with db() as connection:
        connection.execute('CREATE TABLE state (id INTEGER PRIMARY KEY,payload TEXT,revision INTEGER)')
        connection.execute('CREATE TABLE assignments (id TEXT PRIMARY KEY,payload TEXT,acknowledged INTEGER)')
        connection.execute('CREATE TABLE audit (id INTEGER PRIMARY KEY,timestamp TEXT,actor TEXT,action TEXT,payload TEXT)')
        connection.execute('INSERT INTO state VALUES (1,?,0)', (json.dumps(network),))
        ensure_dispatch_schema(connection)
        drive.ensure_drive_schema(connection)
        for sid in ('SH03', 'SH04', 'SH11'):
            shipment = next(item for item in network['shipments'] if item['id'] == sid)
            connection.execute('INSERT INTO assignments VALUES (?,?,?)', (sid, json.dumps(shipment), int(sid == 'SH11')))

    def load(connection):
        payload, revision = connection.execute('SELECT payload,revision FROM state WHERE id=1').fetchone()
        return json.loads(payload), revision

    def record(connection, actor, action, payload):
        connection.execute('INSERT INTO audit(timestamp,actor,action,payload) VALUES (?,?,?,?)',
                           (drive._utc_now().isoformat(), actor, action, json.dumps(payload)))

    app = FastAPI()
    app.include_router(drive.create_drive_router(db, load, record))
    with TestClient(app) as client:
        yield client, db, network


def park(client, truck='T03', version=0):
    response = client.post(f'/api/drive/{truck}/focus', json={
        'mode': 'parked', 'expected_version': version, 'parked_confirmation': True,
    })
    assert response.status_code == 200, response.text
    return response.json()


def test_snapshot_is_locked_and_fuel_position_are_deterministic_simulations(drive_client):
    client, db, original = drive_client
    first = client.get('/api/drive/T03').json()
    second = client.get('/api/drive/T03').json()
    assert first['focus']['mode'] == 'locked'
    assert first['focus']['version'] == 0 and not first['focus']['interaction_allowed']
    assert {item['id'] for item in first['assignments']} == {'SH03', 'SH11'}
    assert next(item for item in first['assignments'] if item['id'] == 'SH11')['acknowledged']
    assert first['vehicle'] == second['vehicle']
    assert first['vehicle']['simulation'] is True
    assert first['vehicle']['observed_at'] == '2026-10-26T08:00:00-05:00'
    assert 'not live GPS' in first['vehicle']['provenance']
    assert 'SIMULATION' in first['vehicle']['provenance']
    assert first['vehicle']['coordinates'] == next(n['coordinates'] for n in original['nodes'] if n['id'] == 'DC1')
    assert 'not inferred from GPS' in ' '.join(first['limitations'])
    with db() as connection:
        assert json.loads(connection.execute('SELECT payload FROM state').fetchone()[0]) == original
        assert connection.execute('SELECT COUNT(*) FROM driver_focus').fetchone()[0] == 0
    empty = client.get('/api/drive/T08').json()
    assert empty['assignments'] == [] and empty['vehicle']['origin_id'] == 'DC1'


def test_parked_confirmation_is_explicit_and_driving_locks_again(drive_client):
    client, db, _ = drive_client
    assert client.post('/api/drive/T03/focus', json={'mode': 'parked', 'expected_version': 0}).status_code == 422
    assert client.post('/api/drive/T03/focus', json={'mode': 'parked', 'expected_version': 0, 'parked_confirmation': 'yes'}).status_code == 422
    assert client.post('/api/drive/T03/focus', json={'mode': 'parked', 'expected_version': True, 'parked_confirmation': True}).status_code == 422
    active = park(client)
    assert active['mode'] == 'parked' and active['interaction_allowed'] and active['version'] == 1
    assert active['parked_until'] and active['parked_confirmed_at']
    with db() as connection:
        assert drive.require_parked(connection, 'T03')['version'] == 1
        with pytest.raises(HTTPException) as caught:
            drive.require_parked(connection, 'T04')
        assert caught.value.status_code == 423
    locked = client.post('/api/drive/T03/focus', json={'mode': 'driving', 'expected_version': 1}).json()
    assert locked['mode'] == 'driving' and locked['version'] == 2
    assert locked['parked_until'] is None and not locked['interaction_allowed']
    response = client.post('/api/drive/T03/quick-report', json={'shipment_id': 'SH03', 'kind': 'road_delay'})
    assert response.status_code == 423


def test_expiration_preserves_version_and_requires_new_confirmation(drive_client, monkeypatch):
    client, _, _ = drive_client
    instant = datetime(2026, 10, 27, 15, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(drive, '_utc_now', lambda: instant)
    active = park(client)
    monkeypatch.setattr(drive, '_utc_now', lambda: instant + timedelta(seconds=600))
    expired = client.get('/api/drive/T03').json()['focus']
    assert expired['mode'] == 'locked' and expired['expired'] and expired['version'] == 1
    assert expired['parked_until'] == active['parked_until']
    assert client.post('/api/drive/T03/quick-report', json={'shipment_id': 'SH03', 'kind': 'cargo_issue'}).status_code == 423
    assert park(client, version=1)['version'] == 2
    assert client.post('/api/drive/T03/focus', json={'mode': 'driving', 'expected_version': 1}).status_code == 409


def test_malformed_legacy_expiration_fails_closed(drive_client):
    client, db, _ = drive_client
    with db() as connection:
        connection.execute('INSERT INTO driver_focus VALUES (?,?,?,?,?)', ('T03', 'parked', 1, 'bad timestamp', '2026-10-27T00:00:00Z'))
    assert client.get('/api/drive/T03').json()['focus']['mode'] == 'locked'
    assert client.post('/api/drive/T03/quick-report', json={'shipment_id': 'SH03', 'kind': 'vehicle_issue'}).status_code == 423


@pytest.mark.parametrize('kind', ['refrigeration', 'road_delay', 'vehicle_issue', 'cargo_issue'])
def test_canned_reports_reach_standard_incident_inbox_without_network_mutation(drive_client, kind):
    client, db, original = drive_client
    park(client)
    response = client.post('/api/drive/T03/quick-report', json={'shipment_id': 'SH11', 'kind': kind})
    assert response.status_code == 200, response.text
    output = response.json()
    assert output['kind'] == kind and output['truck_id'] == 'T03'
    with db() as connection:
        sid, payload, status, version = connection.execute('SELECT shipment_id,payload,status,version FROM incidents WHERE id=?', (output['incident_id'],)).fetchone()
        report = json.loads(payload)
        assert sid == 'SH11' and status == 'open' and version == 0
        assert report['reporting_assignment']['truck_id'] == 'T03'
        assert report['reporting_assignment']['lot_id'] == 'L11'
        assert 'while parked' in report['description']
        assert 'simulated driver report' in report['provenance']
        actions = [r[0] for r in connection.execute('SELECT action FROM audit')]
        assert actions == ['driver_focus', 'incident', 'driver_quick_report']
        assert json.loads(connection.execute('SELECT payload FROM state').fetchone()[0]) == original


def test_quick_report_cannot_target_another_truck_or_an_unapproved_trip(drive_client):
    client, db, _ = drive_client
    park(client)
    assert client.post('/api/drive/T03/quick-report', json={'shipment_id': 'SH04', 'kind': 'vehicle_issue'}).status_code == 409
    assert client.post('/api/drive/T03/quick-report', json={'shipment_id': 'SH01', 'kind': 'cargo_issue'}).status_code == 404
    assert client.post('/api/drive/T03/quick-report', json={'shipment_id': 'SH03', 'kind': 'call_police'}).status_code == 422
    with db() as connection:
        assert connection.execute('SELECT COUNT(*) FROM incidents').fetchone()[0] == 0


def test_unknown_trucks_and_stale_focus_updates_do_not_create_sessions(drive_client):
    client, db, _ = drive_client
    assert client.get('/api/drive/UNKNOWN').status_code == 404
    assert client.post('/api/drive/UNKNOWN/focus', json={'mode': 'parked', 'expected_version': 0, 'parked_confirmation': True}).status_code == 404
    assert client.post('/api/drive/UNKNOWN/quick-report', json={'shipment_id': 'SH03', 'kind': 'road_delay'}).status_code == 404
    park(client)
    assert client.post('/api/drive/T03/focus', json={'mode': 'driving', 'expected_version': 0}).status_code == 409
    with db() as connection:
        assert connection.execute('SELECT COUNT(*) FROM driver_focus').fetchone()[0] == 1
        assert connection.execute('SELECT COUNT(*) FROM audit').fetchone()[0] == 1


def test_event_snapshot_excludes_other_truck_and_unapproved_trip(drive_client):
    client, db, original = drive_client
    original['events'] = [
        {'type': 'delivery_delay', 'shipment_id': 'SH03', 'provenance': 'simulated'},
        {'type': 'road_closure', 'shipment_id': 'SH04', 'provenance': 'simulated'},
        {'type': 'temperature_excursion', 'shipment_id': 'SH19', 'provenance': 'simulated'},
    ]
    with db() as connection:
        connection.execute('UPDATE state SET payload=?,revision=2', (json.dumps(original),))
    snapshot = client.get('/api/drive/T03').json()
    assert snapshot['network_revision'] == 2
    assert [event['shipment_id'] for event in snapshot['events']] == ['SH03']
