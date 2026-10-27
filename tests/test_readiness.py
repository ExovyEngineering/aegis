"""Readiness diagnostics never replace approval, dispatch or safety decisions."""
from contextlib import contextmanager
from datetime import datetime
import json
import sqlite3

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from backend.readiness import build_readiness, create_readiness_router
from backend.simulation import seed_network


@pytest.fixture
def readiness_client(tmp_path):
    database = tmp_path / 'readiness.sqlite'
    traces, reads = [], []

    @contextmanager
    def db():
        connection = sqlite3.connect(database)
        connection.set_trace_callback(traces.append)
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    with db() as connection:
        connection.execute('CREATE TABLE state (id INTEGER PRIMARY KEY,payload TEXT,revision INTEGER)')
        connection.execute('CREATE TABLE assignments (id TEXT PRIMARY KEY,payload TEXT,acknowledged INTEGER)')
        connection.execute('INSERT INTO state VALUES (1,?,17)', (json.dumps(seed_network()),))

    def load(connection):
        reads.append(connection.in_transaction)
        payload, revision = connection.execute('SELECT payload,revision FROM state WHERE id=1').fetchone()
        return json.loads(payload), revision

    app = FastAPI()
    app.include_router(create_readiness_router(db, load))
    with TestClient(app) as client:
        yield client, db, database, traces, reads


def rows(network, *shipment_ids, acknowledged=True):
    return [(item['id'], json.dumps(item), int(acknowledged))
            for item in network['shipments'] if item['id'] in shipment_ids]


def check(report, identity, shipment='SH02'):
    item = next(item for item in report['assignments'] if item['shipment_id'] == shipment)
    return next(item for item in item['checks'] if item['id'] == identity)


def test_endpoint_is_consistent_read_only_and_does_not_require_parked(readiness_client):
    client, db, database, traces, reads = readiness_client
    with db() as connection:
        connection.executemany('INSERT INTO assignments VALUES (?,?,?)', rows(seed_network(), 'SH02'))
    before = database.read_bytes()
    traces.clear()
    response = client.get('/api/readiness')
    assert response.status_code == 200
    result = response.json()
    assert result['network_revision'] == 17
    assert result['summary'] == dict(total_assignments=1, blocked=0, review_required=0, ready_for_review=1)
    assert result['assignments'][0]['status'] == 'ready_for_review'
    assert reads == [True]
    assert datetime.fromisoformat(result['checked_at']).tzinfo is not None
    assert all(statement.startswith(('BEGIN', 'SELECT', 'COMMIT')) for statement in traces)
    assert database.read_bytes() == before
    assert 'not that a shipment is safe' in ' '.join(result['limitations'])
    assert 'does not dispatch cargo' in ' '.join(result['limitations'])


def test_no_approved_assignments_is_empty_not_invented_work(readiness_client):
    client, _, _, _, _ = readiness_client
    result = client.get('/api/readiness').json()
    assert result['assignments'] == []
    assert result['summary'] == dict(total_assignments=0, blocked=0, review_required=0, ready_for_review=0)
    assert all(item['used_kg'] == 0 for item in result['resources'])


def test_snapshot_does_not_mix_state_and_assignments_during_a_concurrent_commit(tmp_path):
    database = tmp_path / 'snapshot.sqlite'
    network = seed_network()
    with sqlite3.connect(database) as connection:
        connection.execute('PRAGMA journal_mode=WAL')
        connection.execute('CREATE TABLE state (payload TEXT,revision INTEGER)')
        connection.execute('CREATE TABLE assignments (id TEXT PRIMARY KEY,payload TEXT,acknowledged INTEGER)')
        connection.execute('INSERT INTO state VALUES (?,1)', (json.dumps(network),))
        connection.executemany('INSERT INTO assignments VALUES (?,?,?)', rows(network, 'SH02'))

    @contextmanager
    def db():
        connection = sqlite3.connect(database)
        try:
            yield connection
        finally:
            connection.close()

    def load(connection):
        encoded, revision = connection.execute('SELECT payload,revision FROM state').fetchone()
        # Commit a different network and assignment after the read snapshot began.
        with sqlite3.connect(database) as writer:
            current = json.loads(encoded)
            next(item for item in current['lots'] if item['id'] == 'L02')['held'] = True
            writer.execute('UPDATE state SET payload=?,revision=2', (json.dumps(current),))
            replacement = current['shipments'][1].copy()
            replacement['lot_id'] = 'L01'
            writer.execute('UPDATE assignments SET payload=?', (json.dumps(replacement),))
        return json.loads(encoded), revision

    app = FastAPI()
    app.include_router(create_readiness_router(db, load))
    with TestClient(app) as client:
        result = client.get('/api/readiness').json()
    assert result['network_revision'] == 1
    assert result['assignments'][0]['lot_id'] == 'L02'
    assert result['assignments'][0]['status'] == 'ready_for_review'
    with db() as connection:
        assert connection.execute('SELECT revision FROM state').fetchone()[0] == 2
        assert json.loads(connection.execute('SELECT payload FROM assignments').fetchone()[0])['lot_id'] == 'L01'


def test_status_summary_keeps_hard_blocks_separate_from_workflow_review():
    network = seed_network()
    next(item for item in network['lots'] if item['id'] == 'L04')['held'] = True
    approved = rows(network, 'SH02') + rows(network, 'SH03', 'SH04', acknowledged=False)
    result = build_readiness(network, 1, approved)
    assert result['summary'] == dict(total_assignments=3, blocked=1, review_required=1, ready_for_review=1)
    blocked = next(item for item in result['assignments'] if item['shipment_id'] == 'SH04')
    assert blocked['blockers'] == ['lot_eligibility']
    assert blocked['reviews_required'] == ['assignment_acknowledged']


@pytest.mark.parametrize(('entity', 'field', 'value', 'check_id'), [
    ('lot', 'held', True, 'lot_eligibility'),
    ('lot', 'recalled', True, 'lot_eligibility'),
    ('lot', 'eligible', False, 'lot_eligibility'),
    ('truck', 'eligible', False, 'truck_eligibility'),
    ('truck', 'refrigerated', False, 'refrigeration'),
    ('lot', 'shelf_life_hours', 0, 'shelf_life'),
])
def test_current_hard_constraints_block_even_previously_approved_cargo(entity, field, value, check_id):
    network = seed_network()
    approved = rows(network, 'SH02')
    resource = next(item for item in network['lots' if entity == 'lot' else 'trucks']
                    if item['id'] == ('L02' if entity == 'lot' else 'T02'))
    resource[field] = value
    result = build_readiness(network, 5, approved)
    assert result['assignments'][0]['status'] == 'blocked'
    assert check(result, check_id)['status'] == 'blocked'
    assert check(result, check_id)['category'] == 'hard_constraint'


@pytest.mark.parametrize(('kind', 'resource_id', 'limit_field', 'shipment_ids', 'check_id'), [
    ('lot', 'L02', 'inventory_kg', ('SH02', 'SH14'), 'aggregate_lot_inventory'),
    ('truck', 'T02', 'capacity_kg', ('SH02', 'SH10'), 'aggregate_truck_capacity'),
    ('origin', 'DC2', 'capacity_kg', ('SH02', 'SH14'), 'aggregate_origin_capacity'),
    ('supplier', 'SUP2', 'capacity_kg', ('SH02', 'SH14'), 'aggregate_supplier_capacity'),
    ('destination', 'D02', 'demand_kg', ('SH02', 'SH17'), 'aggregate_destination_demand'),
])
def test_shared_resources_are_checked_across_assignments_not_just_individually(kind, resource_id, limit_field, shipment_ids, check_id):
    network = seed_network()
    collection = network['lots' if kind == 'lot' else 'trucks' if kind == 'truck' else 'nodes']
    next(item for item in collection if item['id'] == resource_id)[limit_field] = 700
    result = build_readiness(network, 1, rows(network, *shipment_ids))
    assert all(item['status'] == 'blocked' for item in result['assignments'])
    assert all(check(result, check_id, shipment)['status'] == 'blocked' for shipment in shipment_ids)
    resource = next(item for item in result['resources'] if item['kind'] == kind and item['id'] == resource_id)
    assert resource['used_kg'] == 800
    assert resource['limit_kg'] == 700
    assert resource['remaining_kg'] == -100


def test_workflow_acknowledgments_request_review_without_creating_safety_hold():
    network = seed_network()
    assignment = next(item for item in network['shipments'] if item['id'] == 'SH02')
    assignment.update(instruction_revision=3, instruction_acknowledged=False)
    result = build_readiness(network, 1, rows(network, 'SH02', acknowledged=False))
    item = result['assignments'][0]
    assert item['status'] == 'review_required'
    assert item['blockers'] == []
    assert set(item['reviews_required']) == {'assignment_acknowledged', 'instruction_acknowledged'}
    assert check(result, 'instruction_acknowledged')['category'] == 'workflow'
    assert 'v3' in check(result, 'instruction_acknowledged')['detail']
    assignment['instruction_acknowledged'] = True
    assert build_readiness(network, 1, rows(network, 'SH02'))['assignments'][0]['status'] == 'ready_for_review'
    # A new instruction must independently be acknowledged, even after the trip ack.
    assignment.update(instruction_revision=4, instruction_acknowledged=False)
    result = build_readiness(network, 1, rows(network, 'SH02'))
    assert result['assignments'][0]['reviews_required'] == ['instruction_acknowledged']


def test_targeted_verification_requires_complete_matching_context_and_checks():
    network = seed_network()
    assignment = next(item for item in network['shipments'] if item['id'] == 'SH02')
    assignment.update(verification_required=True, verification_status='complete', verification_version=1)
    result = build_readiness(network, 1, rows(network, 'SH02'))
    assert check(result, 'targeted_verification')['status'] == 'review_required'
    assignment['verification_review'] = {
        'status': 'complete', 'version': 1,
        'checks': dict(temperature_history_reviewed=True, packaging_condition_reviewed=True,
                       simulated_lot_identity_reviewed=True),
        'context': {key: assignment[key] for key in ('id', 'lot_id', 'truck_id', 'origin', 'destination')},
    }
    result = build_readiness(network, 1, rows(network, 'SH02'))
    assert check(result, 'targeted_verification')['status'] == 'pass'
    assignment['verification_review']['context']['lot_id'] = 'L12'
    assert check(build_readiness(network, 1, rows(network, 'SH02')), 'targeted_verification')['status'] == 'review_required'
    assignment['verification_review']['context']['lot_id'] = assignment['lot_id']
    assignment['verification_review']['checks']['packaging_condition_reviewed'] = False
    assert check(build_readiness(network, 1, rows(network, 'SH02')), 'targeted_verification')['status'] == 'review_required'


def test_score_and_temperature_alone_do_not_create_hard_block_or_hold():
    network = seed_network()
    assignment = next(item for item in network['shipments'] if item['id'] == 'SH03')
    assignment.update(predictive_score=0.99999, review_priority='high', temperature_c=12)
    result = build_readiness(network, 1, rows(network, 'SH03'))
    assert result['assignments'][0]['status'] == 'ready_for_review'
    assert not next(item for item in network['lots'] if item['id'] == 'L03')['held']
    assert 'predictive score alone never creates a hard block' in ' '.join(result['limitations'])


def test_stale_or_tampered_canonical_assignment_is_blocked():
    network = seed_network()
    approved = rows(network, 'SH02')
    assignment = next(item for item in network['shipments'] if item['id'] == 'SH02')
    assignment['estimated_hours'] += 1
    result = build_readiness(network, 2, approved)
    assert check(result, 'canonical_fields')['status'] == 'blocked'
    assert 'estimated_hours' in check(result, 'canonical_fields')['detail']
    del network['shipments'][network['shipments'].index(assignment)]
    assert check(build_readiness(network, 3, approved), 'canonical_assignment')['status'] == 'blocked'


def test_eligible_lot_substitution_is_not_misrepresented_as_invalid():
    network = seed_network()
    assignment = next(item for item in network['shipments'] if item['id'] == 'SH02').copy()
    assignment['lot_id'] = 'L04'
    result = build_readiness(network, 1, [('SH02', json.dumps(assignment), 1)])
    assert result['assignments'][0]['status'] == 'ready_for_review'
    assert check(result, 'canonical_fields')['status'] == 'pass'


@pytest.mark.parametrize('encoded', ['{broken', '[]', 'null'])
def test_unreadable_assignment_is_reported_blocked_instead_of_silently_skipped(encoded):
    result = build_readiness(seed_network(), 1, [('SH02', encoded, 0)])
    assert result['summary']['blocked'] == 1
    assert check(result, 'canonical_assignment')['status'] == 'blocked'
    assert 'cannot be evaluated' in check(result, 'canonical_assignment')['detail']


@pytest.mark.parametrize('quantity', [None, -4, 0, True, float('nan'), float('inf'), 10**400])
def test_invalid_quantities_are_blocked_and_report_remains_json_serializable(quantity):
    network = seed_network()
    assignment = next(item for item in network['shipments'] if item['id'] == 'SH02').copy()
    assignment['quantity_kg'] = quantity
    result = build_readiness(network, 1, [('SH02', json.dumps(assignment), 1)])
    assert check(result, 'shipment_quantity')['status'] == 'blocked'
    json.dumps(result, allow_nan=False)


def test_unknown_lot_disposition_is_not_treated_as_clear():
    network = seed_network()
    approved = rows(network, 'SH02')
    lot = next(item for item in network['lots'] if item['id'] == 'L02')
    del lot['held']
    assert check(build_readiness(network, 1, approved), 'lot_eligibility')['status'] == 'blocked'


def test_missing_resources_and_expired_planning_deadline_block():
    network = seed_network()
    assignment = next(item for item in network['shipments'] if item['id'] == 'SH02').copy()
    assignment.update(lot_id='missing', truck_id='missing', estimated_hours=7, deadline_hours=6)
    result = build_readiness(network, 1, [('SH02', json.dumps(assignment), 1)])
    for identity in ('lot_eligibility', 'truck_eligibility', 'refrigeration', 'delivery_deadline',
                     'aggregate_lot_inventory', 'aggregate_truck_capacity', 'aggregate_supplier_capacity'):
        assert check(result, identity)['status'] == 'blocked'
    assert result['summary']['blocked'] == 1
