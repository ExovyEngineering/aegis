"""Verified rehearsal configuration must isolate writes and frozen evidence."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import uuid

import pytest
from fastapi.testclient import TestClient

import backend.adapters as adapters
import backend.main as api
import backend.runtime as runtime


ENVIRONMENT = ('AEGIS_REHEARSAL_ID', 'AEGIS_DB_PATH', 'AEGIS_OFFLINE_DEMO')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def fingerprints(path):
    return {suffix: digest(Path(str(path) + suffix))
            for suffix in ('', '-wal', '-shm', '-journal')}


@pytest.fixture
def isolated_root(tmp_path, monkeypatch):
    for key in ENVIRONMENT:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(api, 'ROOT', tmp_path)
    monkeypatch.setattr(api, 'DB', tmp_path / 'data/aegis.sqlite')
    monkeypatch.setattr(adapters, 'ROOT', tmp_path)
    monkeypatch.setattr(runtime, 'ROOT', tmp_path)
    return tmp_path


def configure_rehearsal(root, monkeypatch):
    identity = str(uuid.uuid4())
    path = root / 'data/rehearsals' / f'{identity}.sqlite'
    monkeypatch.setenv('AEGIS_REHEARSAL_ID', identity)
    monkeypatch.setenv('AEGIS_DB_PATH', str(path))
    monkeypatch.setenv('AEGIS_OFFLINE_DEMO', '1')
    monkeypatch.setattr(api, 'DB', path)
    return path


def save_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding='utf-8')


START = {'presenter': 'Automated integration check',
         'purpose': 'Exercise isolated rehearsal workflow and provenance',
         'run_kind': 'automated_check'}


def test_operator_runtime_status_and_rejected_rehearsal_are_read_only(isolated_root):
    with TestClient(api.app) as client:
        assert client.get('/api/network').status_code == 200
        original = fingerprints(api.DB)
        assert client.get('/api/runtime-context').json()['mode'] == 'operator'
        body = client.get('/api/rehearsal').json()
        assert body['runtime']['mode'] == 'operator' and body['active'] is None
        assert client.post('/api/rehearsal/start', json=START).status_code == 403
        assert fingerprints(api.DB) == original
        assert not (isolated_root / 'data/rehearsals').exists()


@pytest.mark.parametrize('initial_database', ['absent', 'empty_reservation', 'seeded_without_runs'])
def test_isolated_inspection_preserves_bytes_before_start_and_after_freezing(
        isolated_root, monkeypatch, initial_database):
    path = configure_rehearsal(isolated_root, monkeypatch)
    operator = isolated_root / 'data/aegis.sqlite'
    operator.parent.mkdir(parents=True, exist_ok=True)
    operator.write_bytes(b'Original operator state must never be opened as SQLite')
    original_operator = fingerprints(operator)
    if initial_database == 'empty_reservation':
        path.parent.mkdir(parents=True)
        path.touch()
    with TestClient(api.app) as client:
        if initial_database == 'seeded_without_runs':
            assert client.get('/api/network').status_code == 200
            with sqlite3.connect(path) as connection:
                assert connection.execute("SELECT 1 FROM sqlite_master WHERE name='rehearsal_runs'").fetchone() is None
        before = fingerprints(path)
        for _ in range(2):
            response = client.get('/api/rehearsal')
            assert response.status_code == 200
            assert response.json()['active'] is None and response.json()['runs'] == []
            assert client.get('/api/rehearsal/unknown').status_code == 404
            assert client.get('/api/rehearsal/unknown/export').status_code == 404
        assert fingerprints(path) == before
        assert fingerprints(operator) == original_operator
        if initial_database == 'absent':
            assert not path.exists() and not path.parent.exists()
        elif initial_database == 'empty_reservation':
            assert path.read_bytes() == b''

        # Only an explicit POST start may initialize and persist a rehearsal.
        response = client.post('/api/rehearsal/start', json=START)
        assert response.status_code == 200, response.text
        run = response.json()
        with sqlite3.connect(path) as connection:
            assert connection.execute('SELECT COUNT(*) FROM rehearsal_runs').fetchone()[0] == 1
        active_bytes = fingerprints(path)
        assert client.get('/api/rehearsal').json()['active']['id'] == run['id']
        assert client.get('/api/rehearsal/' + run['id']).json()['version'] == 1
        assert client.get('/api/rehearsal/' + run['id'] + '/export').status_code == 409
        assert client.get('/api/rehearsal/unknown').status_code == 404
        assert client.get('/api/rehearsal/unknown/export').status_code == 404
        assert fingerprints(path) == active_bytes

        response = client.post('/api/rehearsal/' + run['id'] + '/finish', json={
            'expected_version': 1, 'outcome': 'aborted',
            'notes': 'End the automated read-only inspection regression.',
        })
        assert response.status_code == 200, response.text
        frozen_bytes = fingerprints(path)
        export = client.get('/api/rehearsal/' + run['id'] + '/export')
        assert export.status_code == 200
        assert export.headers['X-AEGIS-Snapshot-SHA256'] == hashlib.sha256(export.content).hexdigest()
        assert client.get('/api/rehearsal').json()['active'] is None
        assert client.get('/api/rehearsal/' + run['id']).json()['status'] == 'aborted'
        assert client.get('/api/rehearsal/' + run['id'] + '/export').content == export.content
        assert fingerprints(path) == frozen_bytes
        assert fingerprints(operator) == original_operator


@pytest.mark.parametrize('configuration', ['wrong_path', 'bad_uuid', 'offline_only', 'id_only'])
def test_misconfiguration_rejects_mutations_before_creating_any_database(
        isolated_root, monkeypatch, configuration):
    path = isolated_root / 'uncreated/subfolder/operator.sqlite'
    identity = str(uuid.uuid4())
    monkeypatch.setattr(api, 'DB', path)
    if configuration != 'offline_only':
        monkeypatch.setenv('AEGIS_REHEARSAL_ID', 'invalid-uuid' if configuration == 'bad_uuid' else identity)
    if configuration != 'id_only':
        monkeypatch.setenv('AEGIS_DB_PATH', str(path))
        monkeypatch.setenv('AEGIS_OFFLINE_DEMO', '1')
    with TestClient(api.app) as client:
        assert client.get('/api/runtime-context').json()['mode'] == 'misconfigured'
        for endpoint, payload in (
            ('/api/rehearsal/start', START), ('/api/demo/reset', {}),
            ('/api/events', {'event': 'road_closure', 'shipment_id': 'SH11'}),
            ('/api/proposals/A', {}),
        ):
            response = client.post(endpoint, json=payload)
            assert response.status_code == 503, (endpoint, response.text)
    assert not path.parent.exists() and not path.exists()


@pytest.mark.parametrize('cache_content', ['valid', 'malformed'])
def test_offline_http_guard_precedes_mutable_cache_and_network(
        isolated_root, monkeypatch, cache_content):
    configure_rehearsal(isolated_root, monkeypatch)
    url = 'https://example.invalid/should-never-be-requested'
    cache = isolated_root / 'data/cache' / (hashlib.sha256(url.encode()).hexdigest() + '.json')
    save_json(cache, {'retrieved_at': datetime.now(timezone.utc).isoformat(), 'payload': {'fresh': True}})
    if cache_content == 'malformed':
        cache.write_bytes(b'not valid JSON')
    original = cache.read_bytes()
    calls = []
    def request(*args, **kwargs):
        calls.append(args)
        raise AssertionError('Offline rehearsal attempted HTTP')
    monkeypatch.setattr(adapters.httpx, 'get', request)
    with pytest.raises(Exception, match='(?i)offline|rehearsal'):
        adapters.CachedHTTP().get(url)
    assert not calls and cache.read_bytes() == original


def test_offline_sources_never_borrow_cache_or_rewrite_evidence(isolated_root, monkeypatch):
    configure_rehearsal(isolated_root, monkeypatch)
    cache = isolated_root / 'data/cache/probe_openmeteo.json'
    fixture = isolated_root / 'data/fixtures/openmeteo.json'
    save_json(cache, {'retrieved_at': '2099-01-01T00:00:00+00:00', 'payload': {'source': 'mutable cache'}})
    save_json(fixture, {'retrieved_at': '2026-10-26T08:00:00+00:00', 'payload': {'source': 'dated fixture'}})
    cached_bytes, fixture_bytes = cache.read_bytes(), fixture.read_bytes()
    calls = []
    monkeypatch.setattr(adapters.httpx, 'get', lambda *args, **kwargs: calls.append(args))
    with TestClient(api.app) as client:
        response = client.get('/api/evidence/openmeteo')
        assert response.status_code == 200
        body = response.json()
        assert body['fixture'] and body['live'] is False and body['stale']
        assert body['payload']['source'] == 'dated fixture'
        assert body['retrieved_at'] == '2026-10-26T08:00:00+00:00'
        assert client.post('/api/refresh/openmeteo', json={}).status_code == 403
        fixture.unlink()
        unavailable = client.get('/api/evidence/openmeteo').json()
        assert unavailable['status'] == 'unavailable' and 'payload' not in unavailable
    assert not calls and cache.read_bytes() == cached_bytes
    assert fixture_bytes


def test_offline_route_uses_estimate_and_dated_modot_fixture_without_http(
        isolated_root, monkeypatch):
    configure_rehearsal(isolated_root, monkeypatch)
    cached_modot = isolated_root / 'data/cache/probe_modot.json'
    save_json(cached_modot, {'retrieved_at': '2099-01-01T00:00:00+00:00', 'incident_layers': []})
    save_json(isolated_root / 'data/fixtures/modot.json', {
        'retrieved_at': '2026-10-26T08:00:00+00:00', 'incident_layers': [], 'coverage_complete': False,
    })
    original_cache = cached_modot.read_bytes()
    calls = []
    monkeypatch.setattr(adapters.httpx, 'get', lambda *args, **kwargs: calls.append(args))
    with TestClient(api.app) as client:
        response = client.post('/api/route', json={
            'coordinates': [[-92.3341, 38.9517], [-90.1994, 38.6270]], 'alternatives': True,
        })
        assert response.status_code == 200
        body = response.json()
        assert body['fallback'] and 'estimated' in body['provenance']
        assert body['road_review']['modot_retrieved_at'] == '2026-10-26T08:00:00+00:00'
        assert body['road_review']['stale']
        plan = client.post('/api/route-lab', json={'preset': 'farm', 'routing': 'osrm'})
        assert plan.status_code == 200 and plan.json()['routes']
    assert not calls and cached_modot.read_bytes() == original_cache


def test_completed_export_is_frozen_after_new_events_and_report_changes(
        isolated_root, monkeypatch):
    configure_rehearsal(isolated_root, monkeypatch)
    save_json(isolated_root / 'reports/model_evaluation.json', {'status': 'dated measured evaluation'})
    with TestClient(api.app) as client:
        started = client.post('/api/rehearsal/start', json=START)
        assert started.status_code == 200, started.text
        run = started.json()
        run_id = run['id']
        def checkpoint(stage_id):
            nonlocal run
            response = client.post(f'/api/rehearsal/{run_id}/checkpoint', json={
                'expected_version': run['version'], 'stage_id': stage_id,
                'outcome': 'covered', 'notes': 'Automated API integration check; no genuine presenter claim.',
            })
            assert response.status_code == 200, response.text
            run = response.json()
        checkpoint('overview')
        checkpoint('evidence_science')
        assert client.post('/api/events', json={'event': 'temperature_excursion', 'shipment_id': 'SH11'}).status_code == 200
        checkpoint('disruption')
        proposal = client.post('/api/proposals/D').json()
        assert client.post(f"/api/proposals/{proposal['id']}/approve", json={
            'actor': 'Automated integration dispatcher', 'reason': 'Inspect isolated simulated allocation and hard constraints',
        }).status_code == 200
        checkpoint('approval')
        assignment = client.get('/api/driver').json()[0]
        truck = assignment['truck_id']
        focus = client.get(f'/api/drive/{truck}').json()['focus']
        assert client.post(f'/api/drive/{truck}/focus', json={
            'mode': 'parked', 'expected_version': focus['version'], 'parked_confirmation': True,
        }).status_code == 200
        revision = client.get('/api/network').json()['revision']
        assert client.post(f"/api/driver/{assignment['id']}/acknowledge", json={'expected_network_revision': revision}).status_code == 200
        assert client.post('/api/driver/incident', json={
            'shipment_id': assignment['id'], 'description': 'Automated parked report in an isolated rehearsal.',
            'expected_network_revision': revision,
        }).status_code == 200
        checkpoint('driver')
        checkpoint('closing')
        finished = client.post(f'/api/rehearsal/{run_id}/finish', json={
            'expected_version': run['version'], 'outcome': 'completed',
            'notes': 'Automated integration completed; this is not a human timed rehearsal.',
        })
        assert finished.status_code == 200, finished.text
        before = client.get(f'/api/rehearsal/{run_id}/export')
        assert before.status_code == 200 and 'automated_check' in before.text
        assert client.post('/api/demo/reset', json={}).status_code == 200
        save_json(isolated_root / 'reports/model_evaluation.json', {'status': 'new unrelated report'})
        after = client.get(f'/api/rehearsal/{run_id}/export')
        assert after.content == before.content
    assert not (isolated_root / 'data/aegis.sqlite').exists()


def rehearsal_checkpoint(client, run, stage):
    return client.post(f'/api/rehearsal/{run["id"]}/checkpoint', json={
        'expected_version': run['version'], 'stage_id': stage, 'outcome': 'covered',
        'notes': 'Automated isolated freshness integration; no human presentation claim.',
    })


def freshness_rehearsal(client):
    run = client.post('/api/rehearsal/start', json=START).json()
    for stage in ('overview', 'evidence_science'):
        response = rehearsal_checkpoint(client, run, stage)
        assert response.status_code == 200, response.text
        run = response.json()
    response = client.post('/api/freshness/sessions', json={
        'expected_network_revision': client.get('/api/network').json()['revision'],
        'shipment_id': 'SH05', 'scenario': 'poultry_demo',
    })
    assert response.status_code == 200, response.text
    return run, response.json()


def freshness_heat(client, snapshot):
    response = client.post(f'/api/freshness/sessions/{snapshot["id"]}/replay', json={
        'expected_version': snapshot['version'], 'event': 'heat_excursion',
    })
    assert response.status_code == 200, response.text
    return response.json()


def freshness_approve(client, snapshot):
    response = client.post(f'/api/freshness/sessions/{snapshot["id"]}/approve', json={
        'expected_version': snapshot['version'], 'expected_network_revision': snapshot['network_revision'],
        'proposal_hash': snapshot['rescue']['proposal_hash'],
        'destination_id': snapshot['rescue']['proposed_destination_id'],
        'actor': 'Automated freshness integration dispatcher',
        'reason': 'Review simulated quality disposition, recipient acceptance and route restrictions separately',
        'quality_review_confirmed': True, 'recipient_confirmed': True, 'routing_review_confirmed': True,
    })
    assert response.status_code == 200, response.text
    return response.json()


def test_freshness_only_rehearsal_requires_real_approval_and_complete_parked_driver_chain(
        isolated_root, monkeypatch):
    database = configure_rehearsal(isolated_root, monkeypatch)
    with TestClient(api.app) as client:
        run, baseline = freshness_rehearsal(client)
        snapshot = freshness_heat(client, baseline)
        response = rehearsal_checkpoint(client, run, 'disruption')
        assert response.status_code == 200, response.text
        run = response.json()
        disruption = run['milestones'][-1]['evidence']
        assert disruption['actions'][0]['action'] == 'freshness_replay'
        assert disruption['freshness_context']['session_id'] == snapshot['id']
        assert disruption['freshness_context']['event'] == 'heat_excursion'
        assert rehearsal_checkpoint(client, run, 'approval').status_code == 409
        approved = freshness_approve(client, snapshot)
        response = rehearsal_checkpoint(client, run, 'approval')
        assert response.status_code == 200, response.text
        run = response.json()
        decision = run['milestones'][-1]['evidence']
        assert decision['actions'][0]['action'] == 'freshness_rescue_approve'
        assert decision['freshness_context']['network_revision'] == approved['receipt']['network_revision']
        provenance = decision['freshness_context']
        assert provenance['captured_version'] == approved['snapshot']['version']
        assert provenance['stored_frame_count'] > 0
        assert len(provenance['stored_session_sha256']) == len(provenance['stored_frames_sha256']) == len(provenance['profiles_sha256']) == 64
        selected = next(row for row in client.get('/api/driver').json() if row['id'] == 'SH05')
        assert selected['destination'] == approved['receipt']['selected_destination_id']
        truck = selected['truck_id']
        focus = client.get(f'/api/drive/{truck}').json()['focus']
        assert client.post(f'/api/drive/{truck}/focus', json={
            'expected_version': focus['version'], 'mode': 'parked', 'parked_confirmation': True,
        }).status_code == 200
        assert rehearsal_checkpoint(client, run, 'driver').status_code == 409
        revision = approved['receipt']['network_revision']
        assert client.post('/api/driver/SH05/acknowledge', json={'expected_network_revision': revision}).status_code == 200
        assert rehearsal_checkpoint(client, run, 'driver').status_code == 409
        assert client.post('/api/driver/incident', json={
            'shipment_id': 'SH05', 'description': 'Automated parked receiving check for the reviewed rescue.',
            'expected_network_revision': revision,
        }).status_code == 200
        response = rehearsal_checkpoint(client, run, 'driver')
        assert response.status_code == 200, response.text
        run = response.json()
        proof = run['milestones'][-1]['evidence']
        assert [item['action'] for item in proof['actions']] == ['driver_focus', 'acknowledge', 'incident']
        assert proof['assignment_context']['id'] == 'SH05'
        assert proof['assignment_context']['destination'] == approved['receipt']['selected_destination_id']
        run = rehearsal_checkpoint(client, run, 'closing').json()
        response = client.post(f'/api/rehearsal/{run["id"]}/finish', json={
            'expected_version': run['version'], 'outcome': 'completed',
            'notes': 'Automated integration only; actual presenter timing remains unverified.',
        })
        assert response.status_code == 200, response.text
        exported = client.get(f'/api/rehearsal/{run["id"]}/export').json()
        assert exported['run']['run_kind'] == 'automated_check'
        assert exported['five_minute_presentation_verified'] is False
        assert exported['genuine_kiro_execution_verified'] is False
        assert all(item['outcome'] == 'covered' for item in exported['run']['milestones'])
        frozen = client.get(f'/api/rehearsal/{run["id"]}/export').content
        assert client.post(f'/api/freshness/sessions/{snapshot["id"]}/replay', json={
            'expected_version': approved['snapshot']['version'], 'event': 'normal',
        }).status_code == 200
        assert client.get(f'/api/rehearsal/{run["id"]}/export').content == frozen
    assert database.exists() and not (isolated_root / 'data/aegis.sqlite').exists()


@pytest.mark.parametrize('case', ['normal_frame', 'audit_only', 'old_frames', 'missing_frames'])
def test_freshness_disruption_requires_actual_disruptive_frames_during_this_run(
        isolated_root, monkeypatch, case):
    database = configure_rehearsal(isolated_root, monkeypatch)
    with TestClient(api.app) as client:
        run, baseline = freshness_rehearsal(client)
        if case == 'normal_frame':
            assert client.post(f'/api/freshness/sessions/{baseline["id"]}/replay', json={
                'expected_version': baseline['version'], 'event': 'normal',
            }).status_code == 200
        elif case == 'audit_only':
            device_count = len(client.get('/api/network').json()['lots'])
            with api.db() as connection:
                api.record(connection, 'Unverified claim', 'freshness_replay', {
                    'session_id': baseline['id'], 'shipment_id': 'SH05', 'event': 'heat_excursion',
                    'frames_added': 2 * device_count,
                    'operational_state_modified': False,
                })
        else:
            freshness_heat(client, baseline)
            with sqlite3.connect(database) as connection:
                if case == 'old_frames':
                    rows = connection.execute('SELECT event_id,payload FROM freshness_frames').fetchall()
                    for identity, encoded in rows:
                        row = json.loads(encoded)
                        row['retrieved_at'] = '2020-01-01T00:00:00+00:00'
                        connection.execute('UPDATE freshness_frames SET payload=? WHERE session_id=? AND event_id=?',
                                           (json.dumps(row), baseline['id'], identity))
                else:
                    connection.execute('DELETE FROM freshness_frames WHERE event_id LIKE ?', ('v1-%',))
        response = rehearsal_checkpoint(client, run, 'disruption')
        assert response.status_code == 409, response.text
    assert not (isolated_root / 'data/aegis.sqlite').exists()


@pytest.mark.parametrize('case', ['audit_only', 'new_reading', 'assignment_changed', 'network_changed', 'hash_changed', 'old_receipt', 'other_session', 'command_approval'])
def test_freshness_approval_requires_matching_persisted_decision_and_current_plan(
        isolated_root, monkeypatch, case):
    database = configure_rehearsal(isolated_root, monkeypatch)
    with TestClient(api.app) as client:
        run, baseline = freshness_rehearsal(client)
        snapshot = freshness_heat(client, baseline)
        response = rehearsal_checkpoint(client, run, 'disruption')
        assert response.status_code == 200, response.text
        run = response.json()
        if case == 'command_approval':
            proposal = client.post('/api/proposals/A', json={}).json()
            assert client.post(f'/api/proposals/{proposal["id"]}/approve', json={
                'actor': 'Automated Command dispatcher', 'reason': 'Command allocation is separate from the stored freshness experiment',
            }).status_code == 200
        elif case == 'other_session':
            other = client.post('/api/freshness/sessions', json={
                'expected_network_revision': 0, 'shipment_id': 'SH05', 'scenario': 'poultry_demo',
            }).json()
            freshness_approve(client, freshness_heat(client, other))
        elif case == 'audit_only':
            with api.db() as connection:
                api.record(connection, 'Unverified claim', 'freshness_rescue_approve', {
                    'session_id': snapshot['id'], 'shipment_id': 'SH05',
                    'proposal_hash': snapshot['rescue']['proposal_hash'],
                })
        else:
            approved = freshness_approve(client, snapshot)
            if case == 'new_reading':
                current = approved['snapshot']
                assert client.post(f'/api/freshness/sessions/{current["id"]}/replay', json={
                    'expected_version': current['version'], 'event': 'normal',
                }).status_code == 200
            elif case == 'network_changed':
                assert client.post('/api/events', json={'event': 'road_closure', 'shipment_id': 'SH11'}).status_code == 200
            else:
                with sqlite3.connect(database) as connection:
                    if case == 'assignment_changed':
                        encoded = connection.execute("SELECT payload FROM assignments WHERE id='SH05'").fetchone()[0]
                        row = json.loads(encoded)
                        row['destination'] = 'D01'
                        connection.execute("UPDATE assignments SET payload=? WHERE id='SH05'", (json.dumps(row),))
                    elif case == 'old_receipt':
                        encoded = connection.execute('SELECT payload FROM freshness_sessions WHERE id=?', (snapshot['id'],)).fetchone()[0]
                        row = json.loads(encoded)
                        row['approval']['approved_at'] = '2020-01-01T00:00:00+00:00'
                        connection.execute('UPDATE freshness_sessions SET payload=? WHERE id=?', (json.dumps(row), snapshot['id']))
                    else:
                        identity, encoded = connection.execute("SELECT id,payload FROM audit WHERE action='freshness_rescue_approve'").fetchone()
                        row = json.loads(encoded)
                        row['proposal_hash'] = '0' * 64
                        connection.execute('UPDATE audit SET payload=? WHERE id=?', (json.dumps(row), identity))
        response = rehearsal_checkpoint(client, run, 'approval')
        assert response.status_code == 409, response.text
    assert not (isolated_root / 'data/aegis.sqlite').exists()
