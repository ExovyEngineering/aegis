import math

import pytest

from backend.route_review import intersects, proximity, review_routes


ROUTE = [[-92.34, 38.95], [-92.32, 38.95]]


@pytest.mark.parametrize('geometry', [
    {'type': 'Point', 'coordinates': [-92.33, 38.95]},
    {'type': 'MultiPoint', 'coordinates': [[-91, 37], [-92.33, 38.95]]},
    {'type': 'LineString', 'coordinates': [[-92.33, 38.94], [-92.33, 38.96]]},
    {'type': 'MultiLineString', 'coordinates': [[[-91, 37], [-90, 37]], [[-92.33, 38.94], [-92.33, 38.96]]]},
])
def test_supported_point_and_line_events_intersect_route(geometry):
    assert proximity(ROUTE, geometry) == pytest.approx(0)


def test_proximity_is_meters_and_accepts_nearby_parallel_road():
    # 0.001 latitude degree is approximately 111 m at Missouri latitudes.
    result = proximity(ROUTE, {'type': 'LineString', 'coordinates': [[-92.34, 38.951], [-92.32, 38.951]]})
    assert result == pytest.approx(111.32, abs=1)
    assert proximity(ROUTE, {'type': 'Point', 'coordinates': [-92.33, 39]}) > 5000


def test_line_intersection_handles_shared_endpoint_collinearity_and_disjoint_lines():
    assert intersects([0, 0], [2, 0], [1, 0], [3, 0])
    assert intersects([0, 0], [1, 1], [1, 1], [2, 0])
    assert not intersects([0, 0], [1, 0], [2, 0], [3, 0])
    assert not intersects([0, 0], [1, 0], [0, 1], [1, 1])


def test_no_geometry_or_unsupported_geometry_does_not_invent_intersection():
    assert math.isinf(proximity([], {'type': 'Point', 'coordinates': [-92, 38]}))
    assert math.isinf(proximity(ROUTE, {}))


def routing(fallback=False):
    return {'fallback': fallback, 'payload': {'routes': [
        {'distance': 2000, 'duration': 200, 'geometry': {'type': 'LineString', 'coordinates': ROUTE}},
        {'distance': 2400, 'duration': 220, 'geometry': {'type': 'LineString', 'coordinates': [[-92.34, 38.98], [-92.32, 38.98]]}},
    ]}}


def incidents(complete=True):
    return {'retrieved_at': '2026-10-26T12:00:00Z', 'coverage_complete': complete, 'incident_layers': [
        {'layer_id': 1, 'layer_name': 'Official road incidents', 'payload': {'features': [
            {'type': 'Feature', 'properties': {'id': 'REAL-SOURCE-FIXTURE-ID', 'description': 'Fixture for unit test only'}, 'geometry': {'type': 'Point', 'coordinates': [-92.33, 38.95]}},
        ]}},
    ]}


def test_route_review_compares_alternatives_without_claiming_truck_safety():
    result = review_routes(routing(), incidents())
    assert len(result['alternatives']) == 2
    assert result['alternatives'][0]['review_required']
    assert len(result['alternatives'][0]['nearby_events']) == 1
    assert not result['alternatives'][1]['nearby_events']
    assert result['coverage_complete'] is True
    assert result['modot_retrieved_at'] == '2026-10-26T12:00:00Z'
    assert 'no truck-safe assertion' in result['warning']
    assert 'nearby parallel roads' in result['warning']


@pytest.mark.parametrize('modot', [None, {}, {'incident_layers': [], 'coverage_complete': False}])
def test_missing_road_feed_requires_review_even_without_reported_events(modot):
    result = review_routes(routing(), modot)
    assert result['coverage_complete'] is False
    assert all(r['review_required'] for r in result['alternatives'])


def test_partial_road_feed_requires_review_even_for_alternative_without_known_hit():
    result = review_routes(routing(), incidents(complete=False))
    assert result['coverage_complete'] is False
    assert all(r['review_required'] for r in result['alternatives'])


def test_estimated_fallback_requires_review_despite_complete_road_feed():
    result = review_routes(routing(fallback=True), incidents())
    assert all(r['review_required'] for r in result['alternatives'])
