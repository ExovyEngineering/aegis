"""Freshness monitoring is a read-only diagnostic, not an automatic hold/reroute."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import sqlite3

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

import backend.drive as drive
import backend.readiness as readiness
from backend.simulation import seed_network


NOW = datetime(2026, 10, 30, 18, 0, tzinfo=timezone.utc)
SESSION = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
OTHER = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'


def approved_rows(network, identities=('SH02', 'SH14')):
    return [(row['id'], json.dumps(row), 1) for row in network['shipments'] if row['id'] in identities]


def assignment_report(report, shipment='SH02'):
    return next(row for row in report['assignments'] if row['shipment_id'] == shipment)


def quality_network():
    network = seed_network()
    lot = next(row for row in network['lots'] if row['id'] == 'L02')
    lot.update(quality_remaining_hours=12, quality_coverage_complete=True)
    for row in network['shipments']:
        if row['lot_id'] == 'L02': row['quality_receiving_buffer_hours'] = .5
    return network


def session_payload(*, source='simulated_replay', revision=17, approved=5, lot='L02', gap=60):
    return {'shipment_id': 'SH02', 'source': source, 'evaluation_at': (NOW - timedelta(minutes=15)).isoformat(),
        'approval': {'network_revision': revision, 'sensor_version': approved},
        'devices': [{'device_id': 'device-' + lot, 'lot_id': lot, 'profile': {'max_gap_minutes': gap}}]}


@pytest.fixture
def monitor(tmp_path, monkeypatch):
    database = tmp_path / 'freshness-readiness.sqlite'
    traces = []
    @contextmanager
    def db():
        connection = sqlite3.connect(database)
        connection.set_trace_callback(traces.append)
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback(); raise
        finally:
            connection.close()
    with db() as connection:
        connection.execute('CREATE TABLE state (id INTEGER PRIMARY KEY,payload TEXT,revision INTEGER)')
        connection.execute('CREATE TABLE assignments (id TEXT PRIMARY KEY,payload TEXT,acknowledged INTEGER)')
        connection.execute('INSERT INTO state VALUES (1,?,17)', (json.dumps(seed_network()),))
        connection.executemany('INSERT INTO assignments VALUES (?,?,?)', approved_rows(seed_network()))
    def load(connection):
        payload, revision = connection.execute('SELECT payload,revision FROM state WHERE id=1').fetchone()
        return json.loads(payload), revision
    def record(*args, **kwargs):
        raise AssertionError('Read-only monitoring must never record a decision')
    monkeypatch.setattr(readiness, '_utc_now', lambda: NOW)
    monkeypatch.setattr(drive, '_utc_now', lambda: NOW)
    app = FastAPI()
    app.include_router(readiness.create_readiness_router(db, load))
    app.include_router(drive.create_drive_router(db, load, record))
    with TestClient(app) as client:
        yield client, db, database, traces


def store_session(db, payload=None, *, version=6, session_id=SESSION, frames=True):
    payload = session_payload() if payload is None else payload
    with db() as connection:
        connection.execute('CREATE TABLE IF NOT EXISTS freshness_sessions (id TEXT PRIMARY KEY,payload TEXT,version INTEGER,created_at TEXT,updated_at TEXT)')
        connection.execute('INSERT INTO freshness_sessions VALUES (?,?,?,?,?)',
            (session_id, json.dumps(payload), version, NOW.isoformat(), NOW.isoformat()))
        if frames:
            connection.execute('CREATE TABLE IF NOT EXISTS freshness_frames (session_id TEXT,device_id TEXT,observed_at TEXT)')
            connection.executemany('INSERT INTO freshness_frames VALUES (?,?,?)',
                [(session_id, device['device_id'], (NOW - timedelta(minutes=15)).isoformat()) for device in payload.get('devices', [])])


def replace_state(db, network, revision=17, *, keep_assignments=False):
    with db() as connection:
        connection.execute('UPDATE state SET payload=?,revision=? WHERE id=1', (json.dumps(network), revision))
        if not keep_assignments:
            connection.execute('DELETE FROM assignments')
            connection.executemany('INSERT INTO assignments VALUES (?,?,?)', approved_rows(network))


def test_uninstrumented_baseline_keeps_exactly_sixteen_checks_and_adds_no_freshness_clearance():
    network = seed_network()
    before = deepcopy(network)
    report = readiness.build_readiness(network, 17, approved_rows(network))
    assert network == before
    assert all(len(row['checks']) == 16 for row in report['assignments'])
    assert all(row['status'] == 'ready_for_review' for row in report['assignments'])
    assert 'freshness_reviews' not in report


def test_valid_quality_budget_adds_one_planning_check_not_a_safety_finding():
    network = quality_network()
    report = readiness.build_readiness(network, 17, approved_rows(network))
    for row in report['assignments']:
        check = next(item for item in row['checks'] if item['id'] == 'quality_window')
        assert len(row['checks']) == 17 and check['status'] == 'pass'
        assert 'not a hold or food-safety clearance' in check['detail']
        assert row['status'] == 'ready_for_review'


@pytest.mark.parametrize('change', ['exact_boundary', 'short', 'unknown', 'coverage', 'negative', 'bool', 'infinite', 'bad_buffer'])
def test_quality_window_or_coverage_failure_is_a_planning_block_without_changing_disposition(change):
    network = quality_network(); lot = next(row for row in network['lots'] if row['id'] == 'L02')
    shipment = next(row for row in network['shipments'] if row['id'] == 'SH02')
    if change == 'exact_boundary': lot['quality_remaining_hours'] = shipment['estimated_hours'] + .5
    if change == 'short': lot['quality_remaining_hours'] = .1
    if change == 'unknown': lot['quality_remaining_hours'] = None
    if change == 'coverage': lot['quality_coverage_complete'] = False
    if change == 'negative': lot['quality_remaining_hours'] = -1
    if change == 'bool': lot['quality_remaining_hours'] = True
    if change == 'infinite': lot['quality_remaining_hours'] = float('inf')
    if change == 'bad_buffer': shipment['quality_receiving_buffer_hours'] = None
    before = deepcopy(network)
    report = readiness.build_readiness(network, 17, approved_rows(network, ('SH02',)))
    row = assignment_report(report)
    assert row['status'] == 'blocked' and 'quality_window' in row['blockers']
    assert next(item for item in row['checks'] if item['id'] == 'quality_window')['category'] == 'hard_constraint'
    assert network == before and lot['held'] is False and lot['recalled'] is False


def test_tampered_approved_buffer_cannot_silently_replace_the_canonical_buffer():
    network = quality_network(); rows = approved_rows(network, ('SH02',))
    assignment = json.loads(rows[0][1]); assignment['quality_receiving_buffer_hours'] = 0
    report = readiness.build_readiness(network, 17, [(assignment['id'], json.dumps(assignment), 1)])
    assert 'canonical_fields' in assignment_report(report)['blockers']


def test_no_optional_tables_keeps_both_gets_read_only_and_drive_locked(monitor):
    client, db, database, traces = monitor
    before = database.read_bytes(); traces.clear()
    result = client.get('/api/readiness').json()
    driver = client.get('/api/drive/T02').json()
    assert all(len(row['checks']) == 16 for row in result['assignments'])
    assert 'freshness_reviews' not in result and 'freshness_reviews' not in driver
    assert driver['focus']['mode'] == 'locked' and driver['focus']['interaction_allowed'] is False
    assert database.read_bytes() == before
    assert all(statement.startswith(('BEGIN', 'SELECT', 'PRAGMA', 'COMMIT')) for statement in traces)
    with db() as connection:
        assert connection.execute("SELECT name FROM sqlite_master WHERE name IN ('freshness_sessions','driver_focus')").fetchall() == []


def test_postapproval_context_version_requires_review_for_all_assignments_using_mapped_lot(monitor):
    client, db, database, traces = monitor
    store_session(db, version=6)
    before = database.read_bytes(); traces.clear()
    report = client.get('/api/readiness').json()
    assert report['summary'] == {'total_assignments': 2, 'blocked': 0, 'review_required': 2, 'ready_for_review': 0}
    assert {row['shipment_id'] for row in report['freshness_reviews']} == {'SH02', 'SH14'}
    for row in report['assignments']:
        assert 'freshness_telemetry_review' in row['reviews_required'] and row['blockers'] == []
    driver = client.get('/api/drive/T02').json()
    assert len(driver['freshness_reviews']) == 1
    pending = driver['freshness_reviews'][0]
    assert pending['shipment_id'] == 'SH02' and pending['lot_id'] == 'L02'
    assert pending['latest_version'] == 6 and pending['approved_version'] == 5
    assert pending['context'] == 'current_approval' and pending['source'] == 'simulated_replay'
    assert not any('temperature' in key or 'humidity' in key for key in pending)
    assert database.read_bytes() == before
    assert all(statement.startswith(('BEGIN', 'SELECT', 'PRAGMA', 'COMMIT')) for statement in traces)


def test_current_unchanged_replay_does_not_age_out_using_real_wallclock(monitor):
    client, db, _, _ = monitor
    payload = session_payload(); payload['evaluation_at'] = '2020-01-01T00:00:00Z'
    store_session(db, payload, version=5)
    report = client.get('/api/readiness').json()
    assert all(row['status'] == 'ready_for_review' for row in report['assignments'])
    assert 'freshness_reviews' not in report


def test_an_older_unrelated_approval_cannot_clear_or_tag_current_assignments(monitor):
    client, db, _, _ = monitor
    store_session(db, session_payload(revision=3), version=100)
    report = client.get('/api/readiness').json()
    assert 'freshness_reviews' not in report
    assert all(len(row['checks']) == 16 for row in report['assignments'])
    assert 'freshness_reviews' not in client.get('/api/drive/T02').json()


def test_retained_assignment_link_survives_an_unrelated_network_revision(monitor):
    client, db, _, _ = monitor
    network = seed_network(); rows = approved_rows(network, ('SH02',))
    assignment = json.loads(rows[0][1]); assignment['freshness_rescue'] = {'session_id': SESSION, 'source_version': 5}
    with db() as connection:
        connection.execute('UPDATE assignments SET payload=? WHERE id=?', (json.dumps(assignment), assignment['id']))
    store_session(db, session_payload(revision=3), version=6)
    review = assignment_report(client.get('/api/readiness').json())['freshness_reviews'][0]
    assert review['context'] == 'assignment_link' and review['latest_version'] == 6


def test_lot_source_link_persists_after_normal_command_reapproval_removes_assignment_rescue_marker(monitor):
    client, db, database, _ = monitor
    network = quality_network(); lot = next(row for row in network['lots'] if row['id'] == 'L02')
    lot.update(quality_session_id=SESSION, quality_source_version=5)
    replace_state(db, network, revision=24)
    store_session(db, session_payload(revision=17, approved=5), version=6)
    before = database.read_bytes()
    report = client.get('/api/readiness').json()
    assert all(row['status'] == 'review_required' for row in report['assignments'])
    assert all(row['context'] == 'lot_quality_link' for row in report['freshness_reviews'])
    assert all(row['approved_version'] == 5 and row['latest_version'] == 6 for row in report['freshness_reviews'])
    assert client.get('/api/drive/T02').json()['freshness_reviews'][0]['context'] == 'lot_quality_link'
    assert database.read_bytes() == before


def test_lot_quality_source_version_takes_precedence_over_a_newer_unrelated_approval_receipt(monitor):
    client, db, _, _ = monitor
    network = quality_network(); next(row for row in network['lots'] if row['id'] == 'L02').update(quality_session_id=SESSION, quality_source_version=4)
    replace_state(db, network)
    store_session(db, session_payload(approved=6), version=6)
    assert all(row['approved_version'] == 4 for row in client.get('/api/readiness').json()['freshness_reviews'])


def test_missing_source_version_or_linked_session_remains_an_explicit_review(monitor):
    client, db, _, _ = monitor
    network = quality_network(); lot = next(row for row in network['lots'] if row['id'] == 'L02')
    lot['quality_session_id'] = SESSION
    replace_state(db, network)
    missing = client.get('/api/readiness').json()['freshness_reviews']
    assert all('unavailable' in row['reason'] for row in missing)
    store_session(db, version=5)
    reviews = client.get('/api/readiness').json()['freshness_reviews']
    assert all(row['approved_version'] is None for row in reviews)
    assert all('cannot be verified' in row['reason'] for row in reviews)


def test_gateway_staleness_reappears_without_a_new_frame_version_and_never_deletes_assignments(monitor):
    client, db, database, _ = monitor
    payload = session_payload(source='gateway_reported', gap=10)
    store_session(db, payload, version=5)
    before = database.read_bytes()
    report = client.get('/api/readiness').json()
    reviews = report['freshness_reviews']
    assert len(reviews) == 2 and all(row['latest_version'] == row['approved_version'] == 5 for row in reviews)
    assert all(row['telemetry_age_minutes'] == 15 and row['max_gap_minutes'] == 10 for row in reviews)
    assert all('older than' in row['reason'] for row in reviews)
    driver = client.get('/api/drive/T02').json()
    assert len(driver['assignments']) == 1 and driver['focus']['interaction_allowed'] is False
    assert driver['freshness_reviews'][0]['timestamp_basis'] == 'gateway_reported_observation'
    assert database.read_bytes() == before


def test_fresh_gateway_observations_do_not_invent_an_extra_clearance_check(monitor):
    client, db, _, _ = monitor
    store_session(db, session_payload(source='gateway_reported', gap=60), version=5)
    report = client.get('/api/readiness').json()
    assert 'freshness_reviews' not in report
    assert all(len(row['checks']) == 16 for row in report['assignments'])


def test_unrelated_lot_fresh_frame_cannot_mask_the_mapped_devices_old_observation(monitor):
    client, db, _, _ = monitor
    payload = session_payload(source='gateway_reported', gap=10)
    payload['devices'].append({'device_id': 'device-L03', 'lot_id': 'L03', 'profile': {'max_gap_minutes': 60}})
    payload['evaluation_at'] = NOW.isoformat()
    store_session(db, payload, version=5)
    with db() as connection:
        connection.execute('UPDATE freshness_frames SET observed_at=? WHERE device_id=?', (NOW.isoformat(), 'device-L03'))
    reviews = client.get('/api/readiness').json()['freshness_reviews']
    assert all(row['telemetry_age_minutes'] == 15 for row in reviews)


def test_device_age_and_gap_are_reported_as_a_real_pair_not_synthesized_across_devices(monitor):
    client, db, _, _ = monitor
    payload = session_payload(source='gateway_reported', gap=120)
    payload['devices'].append({'device_id': 'second-L02', 'lot_id': 'L02', 'profile': {'max_gap_minutes': 20}})
    store_session(db, payload, version=6)
    with db() as connection:
        connection.execute('UPDATE freshness_frames SET observed_at=? WHERE device_id=?', ((NOW - timedelta(minutes=100)).isoformat(), 'device-L02'))
        connection.execute('UPDATE freshness_frames SET observed_at=? WHERE device_id=?', ((NOW - timedelta(minutes=30)).isoformat(), 'second-L02'))
    review = client.get('/api/readiness').json()['freshness_reviews'][0]
    assert review['telemetry_age_minutes'] == 30 and review['max_gap_minutes'] == 20


@pytest.mark.parametrize('change', ['missing_frames', 'missing_observation', 'bad_gap', 'bad_evaluation', 'future_observation'])
def test_unknown_gateway_coverage_remains_reviewable_without_fabricated_sensor_values(monitor, change):
    client, db, database, _ = monitor
    payload = session_payload(source='gateway_reported')
    if change == 'bad_gap': payload['devices'][0]['profile']['max_gap_minutes'] = None
    if change == 'bad_evaluation': payload['evaluation_at'] = 'not-an-observation'
    store_session(db, payload, version=5, frames=change != 'missing_frames')
    with db() as connection:
        if change in ('missing_observation', 'bad_evaluation'):
            connection.execute('DELETE FROM freshness_frames')
        if change == 'future_observation':
            connection.execute('UPDATE freshness_frames SET observed_at=?', ((NOW + timedelta(minutes=10)).isoformat(),))
    before = database.read_bytes()
    report = client.get('/api/readiness').json()
    assert len(report['freshness_reviews']) == 2
    assert all(row['status'] == 'review_required' for row in report['assignments'])
    assert all(not any(key in review for key in ('temperature_c', 'humidity_percent', 'ethylene_ppm')) for review in report['freshness_reviews'])
    assert database.read_bytes() == before


@pytest.mark.parametrize('change', ['bad_json', 'deep_json', 'oversized_payload', 'missing_device_mapping', 'invalid_version'])
def test_a_linked_but_uninspectable_context_fails_to_review_not_to_false_clearance(monitor, change):
    client, db, _, _ = monitor
    network = quality_network(); next(row for row in network['lots'] if row['id'] == 'L02').update(quality_session_id=SESSION, quality_source_version=5)
    replace_state(db, network)
    payload = session_payload()
    if change == 'missing_device_mapping': payload['devices'] = []
    store_session(db, payload, version=0 if change == 'invalid_version' else 5)
    if change in ('bad_json', 'deep_json', 'oversized_payload'):
        encoded = '{invalid-json' if change == 'bad_json' else '[' * 1200 + '0' + ']' * 1200 if change == 'deep_json' else json.dumps({'padding': 'x' * (2 * 1024 * 1024)})
        with db() as connection: connection.execute('UPDATE freshness_sessions SET payload=?', (encoded,))
    result = client.get('/api/readiness')
    assert result.status_code == 200
    assert all(row['status'] == 'review_required' for row in result.json()['assignments'])


def test_more_than_forty_rows_cannot_silently_clear_a_linked_session_outside_the_bounded_snapshot(monitor):
    client, db, _, _ = monitor
    network = quality_network(); next(row for row in network['lots'] if row['id'] == 'L02').update(quality_session_id=SESSION, quality_source_version=5)
    replace_state(db, network)
    store_session(db, version=5)
    with db() as connection:
        connection.executemany('INSERT INTO freshness_sessions VALUES (?,?,?,?,?)',
            [(f'other-{index}', json.dumps(session_payload(revision=0)), 5, NOW.isoformat(), NOW.isoformat()) for index in range(40)])
    reviews = client.get('/api/readiness').json()['freshness_reviews']
    assert all(row['session_id'] == SESSION and 'bounded' in row['reason'] for row in reviews)
