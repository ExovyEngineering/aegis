import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.road_intelligence as roads
from backend.paths import write_json
from backend.road_geometry import road_geometry


ORIGIN = [-92.34, 38.95]
DESTINATION = [-92.32, 38.95]


def wrapper(features=None):
    return {'retrieved_at': datetime.now(timezone.utc).isoformat(), 'coverage_complete': True,
            'incident_layers': [{'layer_id': 0, 'layer_name': 'Test-only source records',
                                 'payload': {'type': 'FeatureCollection', 'features': features or []}}]}


def feature(geometry=None, identifier=42):
    return {'type': 'Feature', 'id': identifier, 'properties': {'ROUTE': 'Test road',
            'TYPE_CODE': 'Test fixture event', 'EXT_COMMENT': 'Unit test only, not a real incident'},
            'geometry': geometry or {'type': 'Point', 'coordinates': [-92.33, 38.95]}}


@pytest.fixture
def road_client(tmp_path, monkeypatch):
    for key in ('AEGIS_REHEARSAL_ID', 'AEGIS_OFFLINE_DEMO', 'AEGIS_DB_PATH'):
        monkeypatch.delenv(key, raising=False)
    app = FastAPI()
    app.include_router(roads.create_road_intelligence_router(tmp_path / 'data/aegis.sqlite', root=tmp_path))
    with TestClient(app) as client:
        yield client, tmp_path
    assert not (tmp_path / 'data/aegis.sqlite').exists(), 'Read-only road workspace must not open operator DB'


def compare(client, **changes):
    return client.post('/api/road-intelligence/compare', json={
        'origin': ORIGIN, 'destination': DESTINATION, 'routing': 'estimated', 'buffer_m': 250, **changes})


def test_unavailable_sources_are_honest_and_do_not_fetch(road_client, monkeypatch):
    client, _ = road_client
    monkeypatch.setattr(roads.OSRMRoutingAdapter, 'route', lambda *args, **kwargs: pytest.fail('No provider expected'))
    snapshot = client.get('/api/road-intelligence').json()
    assert len(snapshot['sources']) == 2
    assert all(not source['available'] and source['stale'] and not source['coverage_complete']
               for source in snapshot['sources'])
    result = compare(client).json()
    assert result['operational_state_modified'] is False
    assert result['alternatives'][0]['fallback'] and result['alternatives'][0]['review_required']
    assert all(not row['nearby_events'] and not row['coverage_complete']
               for row in result['alternatives'][0]['reviews'])


def test_separate_feeds_fixture_semantics_and_proximity(road_client):
    client, root = road_client
    write_json(root / 'data/fixtures/modot.json', wrapper([feature()]))
    write_json(root / 'data/fixtures/iowa_dot.json', wrapper([
        feature({'type': 'Point', 'coordinates': [-93, 42]})]))
    result = compare(client).json()
    assert all(source['fixture'] and source['stale'] for source in result['sources'])
    assert result['request']['origin'] == ORIGIN
    reviews = result['alternatives'][0]['reviews']
    assert reviews[0]['nearby_event_count'] == 1
    assert reviews[0]['nearby_events'][0]['proximity_m'] == 0
    assert reviews[0]['nearby_events'][0]['source_id'] == 'modot'
    assert reviews[1]['nearby_event_count'] == 0
    assert 'Zero nearby records does not mean a road is clear' in ' '.join(result['limitations'])


@pytest.mark.parametrize('geometry', [None, {}, {'type': 'Point', 'coordinates': [True, 39]},
    {'type': 'Point', 'coordinates': ['-92', 39]}, {'type': 'Point', 'coordinates': [181, 39]},
    {'type': 'LineString', 'coordinates': [[-92, 39], ['wrong']]},
    {'type': 'Polygon', 'coordinates': [[[-92, 39], [-91, 39], [-92, 39]]]},
    {'type': 'Point', 'coordinates': [float('nan'), 39]},
    {'type': 'Point', 'coordinates': [-92, float('inf')]},
    {'type': 'MultiLineString', 'coordinates': [[[-92, 39]]]},
])
def test_invalid_geometry_not_inferred(geometry):
    assert road_geometry(geometry) is None
    item = feature()
    item['geometry'] = geometry
    result, events = roads.normalize_source('modot', wrapper([item]))
    assert events[0]['geometry'] is None
    assert result['unusable_geometry_count'] == 1 and not result['coverage_complete']


def test_missing_geometry_counted_without_erasing_other_records(road_client):
    client, root = road_client
    invalid = feature(identifier=43)
    invalid['geometry'] = None
    write_json(root / 'data/cache/probe_modot.json', wrapper([feature(), invalid]))
    result = compare(client).json()
    assert result['sources'][0]['event_count'] == 2
    assert result['sources'][0]['unusable_geometry_count'] == 1
    assert not result['sources'][0]['coverage_complete']
    assert result['alternatives'][0]['reviews'][0]['nearby_event_count'] == 1


def test_bounded_list_still_screens_all_captured_events(road_client):
    client, root = road_client
    write_json(root / 'data/cache/probe_modot.json', wrapper([feature(identifier=i) for i in range(205)]))
    result = compare(client).json()
    source = result['sources'][0]
    assert source['event_count'] == 205 and source['returned_event_count'] == 200
    assert source['events_truncated'] and len(source['events']) == 200
    review = result['alternatives'][0]['reviews'][0]
    assert review['nearby_event_count'] == 205 and review['hits_truncated']
    assert len(review['nearby_events']) == 100


def test_duplicate_rows_preserved_and_ids_unique():
    result, events = roads.normalize_source('modot', wrapper([feature(), feature()]))
    assert result['event_count'] == 2
    assert len({row['id'] for row in events}) == 2
    assert all(row['provider_id'] == 42 for row in events)


@pytest.mark.parametrize('timestamp', [None, 'not a time', '2026-10-28T00:00:00',
    (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()])
def test_invalid_naive_or_future_retrieval_is_stale(timestamp):
    item = wrapper()
    item['retrieved_at'] = timestamp
    result, _ = roads.normalize_source('modot', item)
    assert result['stale'] and result['age_seconds'] is None


def test_old_layer_ages_independently():
    item = wrapper()
    item['incident_layers'][0]['retrieved_at'] = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    result, _ = roads.normalize_source('modot', item)
    assert result['stale']


def test_corrupt_cache_falls_back_to_dated_fixture_with_exact_error(road_client):
    client, root = road_client
    write_json(root / 'data/fixtures/modot.json', wrapper([feature()]))
    cache = root / 'data/cache/probe_modot.json'
    cache.parent.mkdir(parents=True)
    cache.write_text('{partial')
    source = client.get('/api/road-intelligence').json()['sources'][0]
    assert source['available'] and source['fixture'] and source['stale']
    assert 'JSONDecodeError' in source['error']


def test_nonfinite_captured_json_reported_without_invalid_response(road_client):
    client, root = road_client
    cache = root / 'data/cache/probe_modot.json'
    cache.parent.mkdir(parents=True)
    cache.write_text('{"incident_layers":[],"bad":NaN}')
    source = client.get('/api/road-intelligence').json()['sources'][0]
    assert not source['available'] and 'nonfinite JSON' in source['error']


@pytest.mark.parametrize('changes', [
    {'origin': [181, 39]}, {'destination': [-92, -91]}, {'origin': [0]},
    {'buffer_m': 49}, {'buffer_m': 2001}, {'buffer_m': True}, {'buffer_m': 250.1},
    {'routing': 'truck'}, {'destination': ORIGIN}, {'dispatch': True},
    {'origin': [True, 39]}, {'destination': ['-92', 39]},
])
def test_invalid_request_rejected_before_any_provider_call(road_client, monkeypatch, changes):
    client, _ = road_client
    monkeypatch.setattr(roads.OSRMRoutingAdapter, 'route', lambda *args, **kwargs: pytest.fail('Invalid request fetched'))
    assert compare(client, **changes).status_code == 422


def test_osrm_alternatives_are_preserved_with_independent_source_reviews(road_client, monkeypatch):
    client, root = road_client
    write_json(root / 'data/cache/probe_modot.json', wrapper([feature()]))
    monkeypatch.setattr(roads.OSRMRoutingAdapter, 'route', lambda *args, **kwargs: {
        'fallback': False, 'provenance': 'Test OSRM response, not real service', 'payload': {'routes': [
            {'distance': 2000, 'duration': 180, 'geometry': {'type': 'LineString', 'coordinates': [ORIGIN, DESTINATION]}},
            {'distance': 2500, 'duration': 220, 'geometry': {'type': 'LineString', 'coordinates': [[-92.34, 39], [-92.32, 39]]}},
        ]}})
    result = compare(client, routing='osrm').json()
    assert len(result['alternatives']) == 2 and not result['alternatives'][0]['fallback']
    assert result['alternatives'][0]['reviews'][0]['nearby_event_count'] == 1
    assert result['alternatives'][1]['reviews'][0]['nearby_event_count'] == 0
    assert all(row['review_required'] for row in result['alternatives'])


def test_malformed_routing_output_rejected_instead_of_fabricated(road_client, monkeypatch):
    client, _ = road_client
    monkeypatch.setattr(roads.OSRMRoutingAdapter, 'route', lambda *args, **kwargs: {
        'payload': {'routes': [{'geometry': None, 'distance': 42, 'duration': 4}]}})
    assert compare(client, routing='osrm').status_code == 502


def test_refresh_failures_preserve_last_captured_bytes(road_client, monkeypatch):
    import backend.state_dot as state_dot
    client, root = road_client
    path = root / 'data/cache/probe_modot.json'
    write_json(path, wrapper([feature()]))
    original = path.read_bytes()
    def fail(*args):
        raise RuntimeError('Test-only provider outage')
    monkeypatch.setattr(roads.MoDOTAdapter, 'fetch', fail)
    monkeypatch.setattr(state_dot.IowaDOTAdapter, 'fetch', fail)
    response = client.post('/api/road-intelligence/refresh', json={})
    assert response.status_code == 200 and path.read_bytes() == original
    assert all('Test-only provider outage' in source['error'] for source in response.json()['sources'])
    assert all(source['stale'] for source in response.json()['sources'])


def test_offline_rehearsal_never_borrows_mutable_cache_or_refreshes(tmp_path, monkeypatch):
    identifier = str(uuid4())
    selected = tmp_path / f'data/rehearsals/{identifier}.sqlite'
    monkeypatch.setenv('AEGIS_REHEARSAL_ID', identifier)
    monkeypatch.setenv('AEGIS_DB_PATH', str(selected))
    monkeypatch.setenv('AEGIS_OFFLINE_DEMO', '1')
    write_json(tmp_path / 'data/cache/probe_modot.json', wrapper([feature()]))
    app = FastAPI()
    app.include_router(roads.create_road_intelligence_router(selected, root=tmp_path))
    with TestClient(app) as client:
        response = client.get('/api/road-intelligence').json()
        assert response['offline'] and not response['sources'][0]['available']
        assert client.post('/api/road-intelligence/refresh', json={}).status_code == 403
        assert compare(client).json()['alternatives'][0]['fallback']
    assert not selected.exists()
