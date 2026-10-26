import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import zipfile

import httpx
import pytest

import backend.adapters as adapters
from backend.adapters import CachedHTTP, OSRMRoutingAdapter, NCEIHistoricalAdapter
from scripts.audit_data import inspect_file


def offline(*args, **kwargs):
    raise httpx.ConnectError('Test network disconnected')


def test_osrm_offline_geometry_and_matrix_are_explicit_estimates(monkeypatch):
    monkeypatch.setattr(OSRMRoutingAdapter, 'get', offline)
    coordinates = [(-92.3341, 38.9517), (-90.1994, 38.627)]
    route = OSRMRoutingAdapter().route(coordinates, alternatives=True)
    assert route['fallback'] is True
    assert 'not road geometry' in route['provenance']
    assert route['payload']['routes'][0]['distance'] > 100000
    assert route['payload']['routes'][0]['duration'] > 0
    assert route['payload']['routes'][0]['geometry']['coordinates'] == coordinates
    matrix = OSRMRoutingAdapter().matrix(coordinates)
    assert matrix['fallback'] is True
    durations = matrix['payload']['durations']
    assert durations[0][0] == durations[1][1] == 0
    assert durations[0][1] == pytest.approx(durations[1][0])
    assert durations[0][1] == pytest.approx(route['payload']['routes'][0]['duration'])


@pytest.mark.parametrize('coords', [[], [(-92, 38)], [(-92, 91), (-90, 38)], [(-181, 38), (-90, 38)], [(float('nan'), 38), (-90, 38)]])
@pytest.mark.parametrize('method', ['route', 'matrix'])
def test_invalid_coordinates_never_become_plausible_fallbacks(coords, method, monkeypatch):
    monkeypatch.setattr(OSRMRoutingAdapter, 'get', offline)
    with pytest.raises(ValueError):
        getattr(OSRMRoutingAdapter(), method)(coords)


def test_osrm_request_preserves_lon_lat_and_geojson(monkeypatch):
    seen = []
    def fake_get(self, url):
        seen.append(url)
        return {'payload': {'code': 'Ok', 'routes': [{'distance': 100, 'duration': 50, 'geometry': {'type': 'LineString', 'coordinates': [[-92, 38], [-90, 39]]}}]}}
    monkeypatch.setattr(OSRMRoutingAdapter, 'get', fake_get)
    result = OSRMRoutingAdapter().route([(-92, 38), (-90, 39)], alternatives=True)
    assert result['fallback'] is False
    assert '/route/v1/driving/-92,38;-90,39' in seen[0]
    assert 'geometries=geojson' in seen[0]
    assert 'alternatives=true' in seen[0]
    assert 'truck' in result['provenance'].lower()


def test_stale_cache_preserves_original_retrieval_timestamp_on_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(adapters, 'ROOT', tmp_path)
    monkeypatch.setattr(adapters.httpx, 'get', offline)
    url = 'https://example.test/source'
    timestamp = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    cache = tmp_path / 'data/cache' / (hashlib.sha256(url.encode()).hexdigest() + '.json')
    cache.parent.mkdir(parents=True)
    cache.write_text(json.dumps({'retrieved_at': timestamp, 'payload': {'observation_time': '2024-01-01T00:00:00Z'}}))
    result = CachedHTTP().get(url, ttl=1)
    assert result['stale'] and result['cache']
    assert result['retrieved_at'] == timestamp
    assert result['payload']['observation_time'] == '2024-01-01T00:00:00Z'
    assert 'Test network disconnected' in result['refresh_error']


@pytest.mark.parametrize('payload', [[], {}, [{'DATE': '2024-07-01'}], [{'STATION': 'USW00003945'}]])
def test_ncei_requires_actual_station_observation_schema(payload, monkeypatch):
    monkeypatch.setattr(NCEIHistoricalAdapter, 'get', lambda *args: {'payload': payload})
    with pytest.raises(ValueError, match='NCEI'):
        NCEIHistoricalAdapter().fetch()


def test_audit_csv_counts_complete_file_but_labels_sample_missingness(tmp_path):
    path = tmp_path / 'outbreak.csv'
    body = 'Year,State,Primary Mode,Etiology\n' + '\n'.join(f'2024,MO,Food,{"" if i < 3 else "Salmonella"}' for i in range(250)) + '\n'
    path.write_text(body, encoding='utf-8')
    original = path.read_bytes()
    result = inspect_file(path)
    assert result['row_count'] == 250
    assert result['sample_rows'] == 200
    assert result['sample_missing']['Etiology'] == 3
    assert result['likely_source'] == 'CDC NORS'
    assert result['errors'] == []
    assert path.read_bytes() == original


def test_audit_nested_json_keeps_primary_secondary_counts_separate(tmp_path):
    path = tmp_path / 'ambiguous.json'
    path.write_text(json.dumps([{'metadata': {'description': 'Lab Sampling data'}, 'data': {'primary_table_data': [{'form_id': 'a', 'collection_date': '2024-01-01', 'value': 'NULL'}, {'form_id': 'b', 'collection_date': '2024-01-03', 'value': 1}], 'secondary_table_data': [{'form_id': 'a'}]}}]))
    result = inspect_file(path)
    assert result['object_counts_by_path']['item.data.primary_table_data.item'] == 2
    assert result['object_counts_by_path']['item.data.secondary_table_data.item'] == 1
    assert result['missing_counts']['item.data.primary_table_data.item.value'] == 1
    assert result['timestamp_ranges']['item.data.primary_table_data.item.collection_date'] == ('2024-01-01', '2024-01-03')
    assert result['likely_source'] == 'FSIS laboratory sampling'


def test_audit_corrupt_json_reports_exact_parser_error(tmp_path):
    path = tmp_path / 'partial.json'
    path.write_text('[{"a":1},')
    result = inspect_file(path)
    assert result['errors']
    assert 'IncompleteJSONError' in result['errors'][0]
    assert result['sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()


def test_audit_unreadable_file_is_reported_instead_of_stopping_inventory(tmp_path, monkeypatch):
    path = tmp_path / 'unreadable.csv'
    path.write_text('id\n1\n')
    original = Path.open
    def denied(self, *args, **kwargs):
        if self == path:
            raise PermissionError('Test permission denied for unreadable.csv')
        return original(self, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', denied)
    result = inspect_file(path)
    assert result['errors'] == ['PermissionError: Test permission denied for unreadable.csv']


def test_zip_is_inventoried_without_extracting_members(tmp_path):
    path = tmp_path / 'archive.zip'
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr('../outside.csv', 'id\n1\n')
        archive.writestr('nested/data.csv', 'id\n2\n')
    result = inspect_file(path)
    assert {m['name'] for m in result['members']} == {'../outside.csv', 'nested/data.csv'}
    assert not (tmp_path / 'nested').exists()
    assert not (tmp_path.parent / 'outside.csv').exists()
    assert 'no extraction' in result['coverage_note'].lower()
