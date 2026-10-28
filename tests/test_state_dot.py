from copy import deepcopy
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit

import pytest

from backend.state_dot import (IowaDOTAdapter, IOWA_DOT_IDS_URL,
                               IOWA_DOT_METADATA_URL, normalize_iowa)


def envelope(payload, **updates):
    return dict(payload=payload, retrieved_at='2026-10-28T14:00:00+00:00',
                stale=False, cache=False, **updates)


def source_metadata():
    return envelope({'geometryType': 'esriGeometryPoint', 'objectIdField': 'OBJECTID',
                     'spatialReference': {'wkid': 102100, 'latestWkid': 3857},
                     'dateFieldsTimeReference': {'timeZone': 'UTC'},
                     'fields': [{'name': name, 'type': 'esriFieldTypeDate' if name == 'EditDate' else 'esriFieldTypeString'}
                                for name in ['OBJECTID', 'ID', 'Route', 'headline', 'EditDate']]})


def inventory(ids):
    return envelope({'objectIdFieldName': 'OBJECTID', 'objectIds': ids})


def feature(object_id, event_id='IADOT-EXAMPLE', geometry=None):
    return {'type': 'Feature', 'id': object_id,
            'geometry': geometry if geometry is not None else {'type': 'Point', 'coordinates': [-93.6, 41.6]},
            'properties': {'OBJECTID': object_id, 'ID': event_id, 'Route': 'I 35',
                           'headline': 'Test fixture roadwork', 'EditDate': 1793196000000,
                           'IssueDate': '20261027', 'IssueTime': '133000',
                           'ExpireDate': '20261103', 'ExpireTime': '130000'}}


def page(features, **props):
    return envelope({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:4326'}},
                     'features': features, **props})


def test_complete_layer_preserves_originals_and_does_not_silently_merge_duplicate_cars_ids():
    metadata, ids, pages = source_metadata(), inventory([1, 2]), [page([feature(1), feature(2)])]
    before = deepcopy((metadata, ids, pages))
    result = normalize_iowa(metadata, ids, pages)
    assert result['coverage_complete'] is True
    assert result['query_summary']['duplicate_cars_event_ids'] == {'IADOT-EXAMPLE': 2}
    assert len(result['incident_layers'][0]['payload']['features']) == 2
    assert result['source_pages'] == pages
    assert (metadata, ids, pages) == before
    assert 'winter' in result['coverage_warning']
    assert 'not converted to UTC' in result['coverage_warning']
    assert result['provider_latest_record_edit_at'] == datetime.fromtimestamp(1793196000, timezone.utc).isoformat()
    assert result['incident_layers'][0]['payload']['features'][0]['properties']['ExpireTime'] == '130000'
    assert 'commercial-truck' in result['coverage_warning']
    assert result['query_summary']['atomic_provider_snapshot'] is False


@pytest.mark.parametrize('change', [
    lambda m: m['payload'].update(geometryType='esriGeometryPolyline'),
    lambda m: m['payload'].update(spatialReference={'wkid': 4326}),
    lambda m: m['payload'].update(fields=[]),
    lambda m: m['payload'].update(dateFieldsTimeReference={'timeZone': 'Unknown'}),
    lambda m: m['payload'].update(error={'code': 499, 'message': 'Token required'}),
])
def test_schema_changes_fail_explicitly(change):
    metadata = source_metadata()
    change(metadata)
    with pytest.raises(ValueError, match='Iowa DOT'):
        normalize_iowa(metadata, inventory([]), [])


@pytest.mark.parametrize('ids', [[1, 1], [True], [-1], ['1']])
def test_invalid_object_id_inventory_not_merged(ids):
    with pytest.raises(ValueError, match='object-ID inventory'):
        normalize_iowa(source_metadata(), inventory(ids), [])


def test_query_bound_missing_records_and_nested_transfer_limit_are_visible():
    result = normalize_iowa(source_metadata(), inventory([1, 2, 3, 4]),
                            [page([feature(1)], properties={'exceededTransferLimit': True})], max_records=3)
    assert result['coverage_complete'] is False
    assert result['query_summary']['truncated'] is True
    assert result['query_summary']['missing_object_ids'] == [2, 3]
    assert 'exceededTransferLimit' in result['coverage_warning']
    assert '3 of 4' in result['coverage_warning']


def test_invalid_geometry_is_retained_in_source_but_not_used_for_proximity():
    malformed = feature(1, geometry={'type': 'Point', 'coordinates': [181, 41.6]})
    result = normalize_iowa(source_metadata(), inventory([1]), [page([malformed])])
    assert result['coverage_complete'] is False
    assert result['query_summary']['screenable_records'] == 0
    assert result['incident_layers'][0]['payload']['features'][0]['geometry'] is None
    assert result['source_pages'][0]['payload']['features'][0]['geometry']['coordinates'][1] == 41.6
    assert result['query_summary']['invalid_geometry_object_ids'] == [1]


@pytest.mark.parametrize('features', [[feature(2)], [feature(1), feature(1)]])
def test_unexpected_or_duplicate_object_ids_are_rejected(features):
    with pytest.raises(ValueError, match='OBJECTID'):
        normalize_iowa(source_metadata(), inventory([1]), [page(features)])


def test_wrong_returned_crs_is_not_reinterpreted():
    data = page([feature(1)])
    data['payload']['crs']['properties']['name'] = 'EPSG:3857'
    with pytest.raises(ValueError, match='returned coordinate reference'):
        normalize_iowa(source_metadata(), inventory([1]), [data])


def test_nonfinite_json_is_reported_as_corrupt_not_exported():
    with pytest.raises(ValueError, match='not finite JSON'):
        normalize_iowa(source_metadata(), inventory([1]),
                       [page([feature(1, geometry={'type': 'Point', 'coordinates': [float('nan'), 41.6]})])])


def test_stale_page_and_oldest_data_timestamp_propagate():
    old = page([feature(1)])
    old.update(stale=True, cache=True, refresh_error='ConnectTimeout: provider unavailable',
               retrieved_at='2026-10-27T14:00:00+00:00')
    result = normalize_iowa(source_metadata(), inventory([1]), [old])
    assert result['stale'] is True
    assert result['coverage_complete'] is True  # Content coverage differs from freshness.
    assert result['retrieved_at'] == '2026-10-27T14:00:00+00:00'
    assert 'ConnectTimeout' in result['refresh_error']


@pytest.mark.parametrize('stamp', [None, 'invalid', '2026-10-28T14:00:00'])
def test_missing_or_naive_retrieval_timestamp_prevents_fresh_claim(stamp):
    data = page([feature(1)])
    data['retrieved_at'] = stamp
    result = normalize_iowa(source_metadata(), inventory([1]), [data])
    assert result['stale'] is True
    assert result['coverage_complete'] is False
    assert 'retrieval timestamp' in result['coverage_warning']


def test_fetch_queries_bounded_ids_instead_of_offset_pagination(monkeypatch):
    seen = []
    monkeypatch.setattr(IowaDOTAdapter, 'PAGE_SIZE', 2)
    monkeypatch.setattr(IowaDOTAdapter, 'MAX_RECORDS', 3)
    def fake_get(self, url, ttl):
        seen.append((url, ttl))
        if url == IOWA_DOT_METADATA_URL:
            return source_metadata()
        if url == IOWA_DOT_IDS_URL:
            return inventory([4, 3, 2, 1])
        query = parse_qs(urlsplit(url).query)
        assert query['outSR'] == ['4326']
        assert query['f'] == ['geojson']
        assert query['outFields'] == ['*']
        assert 'resultOffset' not in query
        return page([feature(int(i)) for i in query['objectIds'][0].split(',')])
    monkeypatch.setattr(IowaDOTAdapter, 'get', fake_get)
    result = IowaDOTAdapter().fetch()
    assert len(seen) == 4  # Metadata, ID inventory and two bounded event pages.
    assert result['query_summary']['returned_records'] == 3
    assert result['query_summary']['truncated'] is True
    assert [f['properties']['OBJECTID'] for f in result['incident_layers'][0]['payload']['features']] == [1, 2, 3]


def test_partial_page_failure_retains_other_records_and_exact_error(monkeypatch):
    monkeypatch.setattr(IowaDOTAdapter, 'PAGE_SIZE', 1)
    def fake_get(self, url, ttl):
        if url == IOWA_DOT_METADATA_URL:
            return source_metadata()
        if url == IOWA_DOT_IDS_URL:
            return inventory([1, 2])
        if parse_qs(urlsplit(url).query)['objectIds'] == ['2']:
            raise TimeoutError('Test Iowa provider page timeout')
        return page([feature(1)])
    monkeypatch.setattr(IowaDOTAdapter, 'get', fake_get)
    result = IowaDOTAdapter().fetch()
    assert result['coverage_complete'] is False
    assert result['query_summary']['returned_records'] == 1
    assert result['query_summary']['missing_object_ids'] == [2]
    assert result['layer_failures'][0]['error'] == 'TimeoutError: Test Iowa provider page timeout'
    assert 'page requests failed' in result['coverage_warning']


def test_offline_rehearsal_inherited_guard_prevents_provider_requests(tmp_path, monkeypatch):
    import backend.adapters as adapters
    monkeypatch.setattr(adapters, 'ROOT', tmp_path)
    rehearsal_id = 'd10adb52-3e75-471b-91c5-7129972a836a'
    monkeypatch.setenv('AEGIS_REHEARSAL_ID', rehearsal_id)
    monkeypatch.setenv('AEGIS_DB_PATH', str(tmp_path / 'data/rehearsals' / f'{rehearsal_id}.sqlite'))
    monkeypatch.setenv('AEGIS_OFFLINE_DEMO', '1')
    monkeypatch.setattr(adapters.httpx, 'get', lambda *args, **kwargs: pytest.fail('Offline rehearsal contacted provider'))
    with pytest.raises(RuntimeError, match='Offline rehearsal disables provider requests'):
        IowaDOTAdapter().fetch()
