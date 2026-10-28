"""Verified rehearsal configuration must isolate writes and frozen evidence."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
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
