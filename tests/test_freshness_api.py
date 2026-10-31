"""Actual HTTP freshness experiments over isolated SQLite and simulated logistics."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import sqlite3

from fastapi.testclient import TestClient
import pytest

import backend.main as api
import backend.freshness as freshness


TOKEN = 'unit-test-freshness-token-' + 'x' * 32
BASELINE = '2026-10-30T08:00:00-05:00'


def freeze_clock(monkeypatch, value='2026-10-30T14:00:00+00:00'):
    """Explicit test clock; gateway freshness must not depend on test-run date."""
    now = datetime.fromisoformat(value).astimezone(timezone.utc)
    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return now.astimezone(tz) if tz is not None else now.replace(tzinfo=None)
    monkeypatch.setattr(freshness,'datetime',FrozenDateTime)


@pytest.fixture
def fresh_api(tmp_path, monkeypatch):
    for key in ('AEGIS_DB_PATH', 'AEGIS_REHEARSAL_ID', 'AEGIS_OFFLINE_DEMO', 'AEGIS_SENSOR_INGEST_TOKEN'):
        monkeypatch.delenv(key, raising=False)
    database = tmp_path / 'data/operator-test.sqlite'
    monkeypatch.setattr(api, 'DB', database)
    monkeypatch.setattr(api, 'ROOT', tmp_path)
    freeze_clock(monkeypatch)
    def no_provider(*args, **kwargs):
        raise AssertionError('These HTTP tests must not call a routing provider')
    monkeypatch.setattr(freshness.OSRMRoutingAdapter, 'route', no_provider)
    with api.db() as connection:
        freshness.ensure_schema(connection)
    with TestClient(api.app) as client:
        yield client, database


def operational(database):
    with sqlite3.connect(database) as connection:
        return {
            'state': connection.execute('SELECT * FROM state ORDER BY id').fetchall(),
            'assignments': connection.execute('SELECT * FROM assignments ORDER BY id').fetchall(),
        }


def fingerprint(database):
    return {suffix or 'sqlite': hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
            for suffix in ('', '-wal', '-shm', '-journal')
            for path in [database.with_name(database.name + suffix)]}


def experiment_rows(database):
    with sqlite3.connect(database) as connection:
        return {
            'sessions': connection.execute('SELECT * FROM freshness_sessions ORDER BY id').fetchall(),
            'frames': connection.execute('SELECT * FROM freshness_frames ORDER BY rowid').fetchall(),
        }


def create(client, **changes):
    body = {'expected_network_revision':0, 'shipment_id':'SH05', **changes}
    response = client.post('/api/freshness/sessions', json=body)
    assert response.status_code == 200, response.text
    return response.json()


def heat(client, snapshot):
    response = client.post(f'/api/freshness/sessions/{snapshot["id"]}/replay', json={'expected_version':snapshot['version'], 'event':'heat_excursion'})
    assert response.status_code == 200, response.text
    return response.json()


def approval(snapshot, **changes):
    return {
        'expected_version':snapshot['version'],
        'expected_network_revision':snapshot['network_revision'],
        'destination_id':snapshot['rescue']['proposed_destination_id'],
        'proposal_hash':snapshot['rescue']['proposal_hash'],
        'actor':'Test dispatcher', 'reason':'Reviewed illustrative quality, receiver and route assumptions',
        'quality_review_confirmed':True, 'recipient_confirmed':True,
        'routing_review_confirmed':True, **changes,
    }


def gateway(client, **changes):
    return create(client, scenario='gateway', devices=[{
        'device_id':'gateway-L05', 'lot_id':'L05',
        'profile':{'started_at':BASELINE, 'initial_equivalent_age_hours':210},
    }], **changes)


def frame(event='sample-0', observed=BASELINE, **changes):
    return {'device_id':'gateway-L05', 'event_id':event, 'observed_at':observed,
            'temperature_c':4.0, 'ambient_temperature_c':30.0,
            'humidity_percent':78.0, 'vibration_g':.03, 'ethylene_ppm':.02, **changes}


def ingest(client, sid, frames, token=TOKEN):
    return client.post('/api/freshness/telemetry', json={'session_id':sid, 'frames':frames},
                       headers={} if token is None else {'Authorization':'Bearer ' + token})


def test_creating_and_replaying_computes_a_real_rescue_without_publishing_it(fresh_api):
    client, database = fresh_api
    before = operational(database)
    baseline = create(client)
    assert baseline['freshness']['status'] == 'estimated'
    assert baseline['freshness']['remaining_reference_hours'] == 9
    assert not baseline['rescue']['triggered']
    warmed = heat(client, baseline)
    assert warmed['rescue']['triggered']
    assert 1 < warmed['freshness']['remaining_quality_hours'] < 2
    assert warmed['rescue']['proposal_hash'] and len(warmed['rescue']['proposal_hash']) == 64
    assert warmed['rescue']['plan_summary']['constraint_violations'] == 0
    assert warmed['rescue']['plan_summary']['assignments_count'] > 0
    assert warmed['rescue']['proposed_destination_id'] != warmed['shipment']['destination']
    assert operational(database) == before
    assert client.get('/api/driver').json() == []
    assert warmed['fefo']['feasible']


def test_context_and_snapshot_gets_are_read_only_and_keep_captured_sensor_times(fresh_api):
    client, database = fresh_api
    baseline = create(client)
    before = fingerprint(database)
    for path in ('/api/freshness/context', f'/api/freshness/sessions/{baseline["id"]}'):
        assert client.get(path).status_code == 200
    assert fingerprint(database) == before
    snapshot = client.get(f'/api/freshness/sessions/{baseline["id"]}').json()
    assert snapshot['version'] == baseline['version']
    assert snapshot['readings'][0]['source_kind'] == 'simulated_replay'
    assert snapshot['gateway']['configured'] is False
    assert snapshot['simulation'] is True


def test_human_approval_updates_the_actual_driver_destination_and_persists_quality_constraints(fresh_api):
    client, database = fresh_api
    warmed = heat(client, create(client))
    response = client.post(f'/api/freshness/sessions/{warmed["id"]}/approve', json=approval(warmed))
    assert response.status_code == 200, response.text
    result = response.json();receipt = result['receipt']
    assert receipt['network_revision'] == 1
    assignments = client.get('/api/driver').json()
    selected = next(row for row in assignments if row['id'] == 'SH05')
    assert selected['destination'] == warmed['rescue']['proposed_destination_id']
    assert selected['destination'] != warmed['shipment']['destination']
    assert selected['freshness_rescue']['session_id'] == warmed['id']
    assert selected['freshness_rescue']['quality_only'] is True
    assert selected['freshness_rescue']['quality_margin_hours'] > 0
    assert 'Save the Load' in selected['instruction']
    driver = client.get('/api/drive/' + selected['truck_id']).json()
    assert driver['network_revision'] == 1
    assert next(row for row in driver['assignments'] if row['id'] == 'SH05')['destination'] == selected['destination']
    network = client.get('/api/network').json()
    lots = {row['id']:row for row in network['lots']}
    trucks = {row['id']:row for row in network['trucks']}
    assert next(row for row in network['shipments'] if row['id'] == 'SH05')['destination'] == selected['destination']
    for trip in assignments:
        lot=lots[trip['lot_id']]
        assert not lot['held'] and not lot['recalled'] and lot['eligible']
        assert trucks[trip['truck_id']]['eligible'] and trucks[trip['truck_id']]['refrigerated']
        assert lot['quality_coverage_complete']
        assert trip['estimated_hours'] + trip['quality_receiving_buffer_hours'] < lot['quality_remaining_hours']
    # Ordinary scenario approval must retain the quality caps from the approved
    # rescue, rather than restoring the longer pre-sensor planning window.
    proposal = client.post('/api/proposals/A').json()
    assert proposal['feasible']
    for trip in proposal['shipments']:
        assert trip['estimated_hours'] + trip['quality_receiving_buffer_hours'] < lots[trip['lot_id']]['quality_remaining_hours']
    audit = client.get('/api/audit').json()
    assert any(row['action'] == 'freshness_rescue_approve' and row['actor'] == 'Test dispatcher' for row in audit)


@pytest.mark.parametrize('field', ['quality_review_confirmed','recipient_confirmed','routing_review_confirmed'])
def test_each_consequential_approval_confirmation_is_required_without_mutation(fresh_api, field):
    client, database = fresh_api
    warmed = heat(client, create(client));before = fingerprint(database)
    response = client.post(f'/api/freshness/sessions/{warmed["id"]}/approve', json=approval(warmed, **{field:False}))
    assert response.status_code == 422
    assert fingerprint(database) == before


@pytest.mark.parametrize('changes', [
    {'actor':' '}, {'reason':' '}, {'quality_review_confirmed':'true'},
    {'expected_version':1}, {'expected_network_revision':1}, {'proposal_hash':'a'*64},
    {'destination_id':'D15'},
])
def test_stale_or_altered_approval_is_rejected_without_publishing(fresh_api, changes):
    client, database = fresh_api
    warmed = heat(client, create(client));before = fingerprint(database)
    response = client.post(f'/api/freshness/sessions/{warmed["id"]}/approve', json=approval(warmed, **changes))
    assert response.status_code in (409,422)
    assert fingerprint(database) == before
    assert client.get('/api/driver').json() == []


@pytest.mark.parametrize('target,field,value', [
    ('lots','held',True), ('lots','recalled',True), ('lots','eligible',False),
    ('lots','inventory_kg',0), ('trucks','eligible',False), ('trucks','refrigerated',False),
])
def test_final_approval_revalidates_current_hard_constraints_even_without_a_revision_change(fresh_api, target, field, value):
    client, database = fresh_api
    warmed = heat(client, create(client))
    with sqlite3.connect(database) as connection:
        network = json.loads(connection.execute('SELECT payload FROM state WHERE id=1').fetchone()[0])
        identity = 'L05' if target == 'lots' else 'T05'
        next(row for row in network[target] if row['id'] == identity)[field] = value
        connection.execute('UPDATE state SET payload=? WHERE id=1', (json.dumps(network),))
    before = fingerprint(database)
    response = client.post(f'/api/freshness/sessions/{warmed["id"]}/approve', json=approval(warmed))
    assert response.status_code == 409, response.text
    assert fingerprint(database) == before
    assert client.get('/api/driver').json() == []


def test_replay_versions_and_network_versions_must_be_current_for_approval(fresh_api):
    client, database = fresh_api
    warmed = heat(client, create(client))
    newer = client.post(f'/api/freshness/sessions/{warmed["id"]}/replay', json={'expected_version':warmed['version'],'event':'normal'})
    assert newer.status_code == 200
    before = fingerprint(database)
    assert client.post(f'/api/freshness/sessions/{warmed["id"]}/approve', json=approval(warmed)).status_code == 409
    assert fingerprint(database) == before
    current = newer.json()
    client.post('/api/events', json={'event':'delivery_delay','shipment_id':'SH01'})
    before = fingerprint(database)
    assert client.post(f'/api/freshness/sessions/{current["id"]}/approve', json=approval(current)).status_code == 409
    assert fingerprint(database) == before


def test_approval_is_not_repeatable_and_rebase_preserves_its_historical_receipt(fresh_api):
    client, database = fresh_api
    warmed = heat(client, create(client))
    response = client.post(f'/api/freshness/sessions/{warmed["id"]}/approve', json=approval(warmed))
    assert response.status_code == 200
    approved = response.json()['snapshot'];before = operational(database)
    repeated = client.post(f'/api/freshness/sessions/{approved["id"]}/approve', json=approval(approved, expected_network_revision=1))
    assert repeated.status_code == 409
    assert operational(database) == before
    rebased = client.post(f'/api/freshness/sessions/{approved["id"]}/rebase', json={'expected_version':approved['version'],'expected_network_revision':1})
    assert rebased.status_code == 200
    assert rebased.json()['approval'] is None
    assert len(rebased.json()['approval_history']) == 1
    assert rebased.json()['approval_history'][0]['network_revision'] == 1
    assert operational(database) == before


def test_use_by_cap_prevents_rescue_even_when_the_modeled_quality_clock_is_positive(fresh_api):
    client, database = fresh_api
    with sqlite3.connect(database) as connection:
        network = json.loads(connection.execute('SELECT payload FROM state WHERE id=1').fetchone()[0])
        next(row for row in network['lots'] if row['id'] == 'L05')['shelf_life_hours'] = .1
        connection.execute('UPDATE state SET payload=? WHERE id=1', (json.dumps(network),))
    warmed = heat(client, create(client))
    assert warmed['freshness']['remaining_quality_hours'] > 0
    assert warmed['rescue']['proposal_hash'] is None
    assert not any(row['dispatchable'] and row['eligible'] for row in warmed['rescue']['options'])
    assert client.get('/api/driver').json() == []


def test_gateway_is_disabled_or_requires_its_server_side_token(fresh_api, monkeypatch):
    client, database = fresh_api
    snapshot = gateway(client);before = fingerprint(database)
    assert ingest(client, snapshot['id'], [frame()]).status_code == 503
    monkeypatch.setenv('AEGIS_SENSOR_INGEST_TOKEN', TOKEN)
    assert ingest(client, snapshot['id'], [frame()], token=None).status_code == 401
    assert ingest(client, snapshot['id'], [frame()], token='wrong-token').status_code == 401
    assert fingerprint(database) == before


def test_gateway_and_simulated_history_cannot_be_mixed(fresh_api, monkeypatch):
    client, database = fresh_api
    simulated = create(client);reported = gateway(client)
    monkeypatch.setenv('AEGIS_SENSOR_INGEST_TOKEN', TOKEN)
    before = experiment_rows(database)
    assert ingest(client, simulated['id'], [frame()]).status_code == 409
    assert client.post(f'/api/freshness/sessions/{reported["id"]}/replay', json={'expected_version':reported['version'],'event':'normal'}).status_code == 409
    assert experiment_rows(database) == before


def test_gateway_preserves_original_time_and_channels_without_claiming_calibration(fresh_api, monkeypatch):
    client, database = fresh_api
    snapshot = gateway(client);operational_before = operational(database)
    monkeypatch.setenv('AEGIS_SENSOR_INGEST_TOKEN', TOKEN)
    response = ingest(client, snapshot['id'], [frame(), frame('sample-1','2026-10-30T14:00:00Z',humidity_percent=83.,vibration_g=.2,ethylene_ppm=.07)])
    assert response.status_code == 200, response.text
    assert response.json()['accepted'] == 2 and response.json()['duplicates'] == 0
    assert response.json()['physical_calibration_verified'] is False
    assert response.json()['operational_state_modified'] is False
    latest = client.get(f'/api/freshness/sessions/{snapshot["id"]}').json()
    assert latest['freshness']['status'] == 'estimated'
    assert latest['provenance']['telemetry'] == 'gateway_reported'
    assert latest['readings'][0]['observed_at'] == BASELINE
    assert latest['readings'][0]['normalized_observed_at'] == '2026-10-30T13:00:00+00:00'
    assert latest['readings'][1]['observed_at'] == '2026-10-30T14:00:00Z'
    assert latest['readings'][1]['humidity_percent'] == 83
    assert latest['readings'][1]['vibration_g'] == .2
    assert latest['readings'][1]['ethylene_ppm'] == .07
    assert latest['readings'][0]['retrieved_at'] != latest['readings'][0]['observed_at']
    assert operational(database) == operational_before


def test_exact_gateway_retries_are_idempotent_but_altered_contents_preserve_the_original(fresh_api, monkeypatch):
    client, database = fresh_api
    snapshot = gateway(client);monkeypatch.setenv('AEGIS_SENSOR_INGEST_TOKEN', TOKEN)
    first = ingest(client, snapshot['id'], [frame()]);assert first.status_code == 200
    before = fingerprint(database)
    repeated = ingest(client, snapshot['id'], [frame()])
    assert repeated.status_code == 200
    assert repeated.json()['accepted'] == 0 and repeated.json()['duplicates'] == 1
    assert repeated.json()['version'] == first.json()['version']
    assert fingerprint(database) == before
    mismatch = ingest(client, snapshot['id'], [frame(temperature_c=7.)])
    assert mismatch.status_code == 409
    assert fingerprint(database) == before


@pytest.mark.parametrize('bad_frame,expected_status', [
    (frame(device_id='unbound-device'),422),
    (frame(observed='2026-10-30T07:59:00-05:00'),422),
    (frame(observed='2026-10-30T08:00:00'),422),
    (frame(observed='2026-10-30T13:00:00Z'),409),
])
def test_invalid_device_time_or_duplicate_instant_is_not_inserted(fresh_api, monkeypatch, bad_frame, expected_status):
    client, database = fresh_api
    snapshot = gateway(client);monkeypatch.setenv('AEGIS_SENSOR_INGEST_TOKEN', TOKEN)
    assert ingest(client, snapshot['id'], [frame()]).status_code == 200
    before = fingerprint(database)
    bad_frame = {**bad_frame,'event_id':'new-event'}
    assert ingest(client, snapshot['id'], [bad_frame]).status_code == expected_status
    assert fingerprint(database) == before


def test_gateway_batch_is_atomic_for_a_late_bad_binding_or_reversed_time(fresh_api, monkeypatch):
    client, database = fresh_api
    snapshot = gateway(client);monkeypatch.setenv('AEGIS_SENSOR_INGEST_TOKEN', TOKEN)
    for batch,expected in [([frame(),frame('unbound','2026-10-30T09:00:00-05:00',device_id='not-bound')],422),
                           ([frame('later','2026-10-30T09:00:00-05:00'),frame('earlier')],409)]:
        before = experiment_rows(database)
        assert ingest(client, snapshot['id'], batch).status_code == expected
        assert experiment_rows(database) == before


@pytest.mark.parametrize('field,value', [('temperature_c',61),('humidity_percent',101),('vibration_g',-1),('ethylene_ppm',-1),('temperature_c',True),('temperature_c','4')])
def test_gateway_units_are_validated_before_any_batch_write(fresh_api, monkeypatch, field, value):
    client, database = fresh_api
    snapshot = gateway(client);monkeypatch.setenv('AEGIS_SENSOR_INGEST_TOKEN', TOKEN)
    before = fingerprint(database)
    assert ingest(client, snapshot['id'], [frame(**{field:value})]).status_code == 422
    assert fingerprint(database) == before


@pytest.mark.parametrize('literal', ['NaN','Infinity','1e999'])
def test_nonfinite_gateway_values_return_a_serializable_error_without_a_write(fresh_api, monkeypatch, literal):
    client, database = fresh_api
    snapshot = gateway(client);monkeypatch.setenv('AEGIS_SENSOR_INGEST_TOKEN', TOKEN)
    body = json.dumps({'session_id':snapshot['id'],'frames':[frame()]})
    body = body.replace('"temperature_c": 4.0', '"temperature_c": ' + literal)
    before = fingerprint(database)
    response = client.post('/api/freshness/telemetry', content=body, headers={'Authorization':'Bearer '+TOKEN,'Content-Type':'application/json'})
    assert response.status_code == 422
    assert response.json()['detail']
    assert fingerprint(database) == before


def test_gateway_missing_temperature_or_coverage_abstains_instead_of_resetting_the_clock(fresh_api, monkeypatch):
    client, database = fresh_api
    snapshot = gateway(client);monkeypatch.setenv('AEGIS_SENSOR_INGEST_TOKEN', TOKEN)
    assert snapshot['freshness']['status'] == 'unscored'
    assert ingest(client,snapshot['id'],[frame(temperature_c=None)]).status_code == 200
    missing = client.get(f'/api/freshness/sessions/{snapshot["id"]}').json()
    assert missing['freshness']['status'] == 'unscored'
    assert missing['freshness']['remaining_quality_hours'] is None
    assert missing['rescue']['proposal_hash'] is None
    freeze_clock(monkeypatch,'2026-10-30T16:00:00+00:00')
    assert ingest(client,snapshot['id'],[frame('gapped','2026-10-30T11:00:00-05:00')]).status_code == 200
    gapped = client.get(f'/api/freshness/sessions/{snapshot["id"]}').json()
    assert gapped['freshness']['status'] == 'unscored'
    assert gapped['freshness']['remaining_quality_hours'] is None


def test_gateway_requires_known_one_to_one_bindings_and_a_selected_lot_device(fresh_api):
    client, database = fresh_api
    good = {'device_id':'gateway-L05','lot_id':'L05','profile':{'started_at':BASELINE}}
    variants = [[],[{**good,'lot_id':'not-a-lot'}],[good,good],
                [good,{**good,'device_id':'other-device'}],
                [{**good,'lot_id':'L06'}],
                [{**good,'profile':{'started_at':'2026-10-30T08:00:00'}}]]
    for devices in variants:
        before = experiment_rows(database)
        response = client.post('/api/freshness/sessions',json={'expected_network_revision':0,'shipment_id':'SH05','scenario':'gateway','devices':devices})
        assert response.status_code == 422
        assert experiment_rows(database) == before


def test_stale_replay_route_choice_and_rebase_do_not_write_or_call_a_provider(fresh_api):
    client, database = fresh_api
    snapshot = heat(client, create(client));before = fingerprint(database)
    requests = [('replay',{'expected_version':1,'event':'normal'}),
                ('routes',{'expected_version':1,'destination_id':'D01','routing':'osrm'}),
                ('proposal',{'expected_version':1,'destination_id':'D01'}),
                ('rebase',{'expected_version':1,'expected_network_revision':0})]
    for endpoint,body in requests:
        assert client.post(f'/api/freshness/sessions/{snapshot["id"]}/{endpoint}',json=body).status_code == 409
        assert fingerprint(database) == before


def test_explicit_estimated_route_is_captured_with_versioning_without_dispatch(fresh_api):
    client, database = fresh_api
    snapshot = heat(client, create(client));before = operational(database)
    response = client.post(f'/api/freshness/sessions/{snapshot["id"]}/routes',json={'expected_version':snapshot['version'],'destination_id':snapshot['rescue']['proposed_destination_id'],'routing':'estimated'})
    assert response.status_code == 200
    updated = response.json()
    assert updated['version'] == snapshot['version']+1
    option = next(row for row in updated['rescue']['options'] if row['destination_id']==snapshot['rescue']['proposed_destination_id'])
    assert option['fallback'] is True and option['geometry']['type']=='LineString'
    assert operational(database) == before


def test_old_approval_receipt_is_not_reported_as_the_current_plan_after_network_changes(fresh_api):
    client, database = fresh_api
    warmed = heat(client, create(client))
    approved = client.post(f'/api/freshness/sessions/{warmed["id"]}/approve',json=approval(warmed))
    assert approved.status_code == 200
    assert client.post('/api/events',json={'event':'delivery_delay','shipment_id':'SH01'}).status_code == 200
    assert client.get('/api/driver').json() == []
    before = fingerprint(database)
    captured = client.get(f'/api/freshness/sessions/{warmed["id"]}').json()
    assert captured['approval']['network_revision'] == 1
    assert captured['current_network_revision'] == 2
    assert captured['status'] in ('stale','review_required')
    assert fingerprint(database) == before


def test_idempotent_gateway_retry_still_works_at_the_retained_history_capacity(fresh_api, monkeypatch):
    client, database = fresh_api
    snapshot = gateway(client)
    monkeypatch.setenv('AEGIS_SENSOR_INGEST_TOKEN',TOKEN)
    monkeypatch.setattr(freshness,'MAX_FRAMES',1)
    assert ingest(client,snapshot['id'],[frame()]).status_code == 200
    before = fingerprint(database)
    repeated = ingest(client,snapshot['id'],[frame()])
    assert repeated.status_code == 200
    assert repeated.json()['accepted'] == 0 and repeated.json()['duplicates'] == 1
    assert fingerprint(database) == before
    assert ingest(client,snapshot['id'],[frame('over-capacity','2026-10-30T09:00:00-05:00')]).status_code == 413
    assert fingerprint(database) == before


@pytest.mark.parametrize('coordinates', [None, 'invalid-line', [[999,999],[999,999]], [[float('nan'),38],[-92,39]]])
def test_malformed_route_geometry_is_rejected_without_replacing_the_previous_capture(fresh_api, monkeypatch, coordinates):
    client, database = fresh_api
    snapshot = heat(client,create(client))
    monkeypatch.setattr(freshness.OSRMRoutingAdapter,'route',lambda *args,**kwargs:{'fallback':False,'payload':{'routes':[{'duration':600,'distance':10000,'geometry':{'type':'LineString','coordinates':coordinates}}]}})
    before = fingerprint(database)
    response = client.post(f'/api/freshness/sessions/{snapshot["id"]}/routes',json={'expected_version':snapshot['version'],'destination_id':snapshot['rescue']['proposed_destination_id'],'routing':'osrm'})
    assert response.status_code == 503
    assert fingerprint(database) == before


def test_current_gateway_clock_ages_between_frames_without_writing_or_changing_observations(fresh_api, monkeypatch):
    client, database = fresh_api
    snapshot = gateway(client);monkeypatch.setenv('AEGIS_SENSOR_INGEST_TOKEN',TOKEN)
    assert ingest(client,snapshot['id'],[frame()]).status_code == 200
    first = client.get(f'/api/freshness/sessions/{snapshot["id"]}').json()
    assert first['freshness']['remaining_reference_hours'] == pytest.approx(29)
    original_readings = deepcopy(first['readings']);before = fingerprint(database)
    freeze_clock(monkeypatch,'2026-10-30T14:30:00+00:00')
    later = client.get(f'/api/freshness/sessions/{snapshot["id"]}').json()
    assert later['freshness']['remaining_reference_hours'] == pytest.approx(28.5)
    assert later['readings'] == original_readings
    assert later['version'] == first['version']
    assert fingerprint(database) == before


def test_stale_gateway_history_abstains_and_preserves_original_records(fresh_api, monkeypatch):
    client, database = fresh_api
    snapshot = gateway(client);monkeypatch.setenv('AEGIS_SENSOR_INGEST_TOKEN',TOKEN)
    assert ingest(client,snapshot['id'],[frame()]).status_code == 200
    before = fingerprint(database)
    freeze_clock(monkeypatch,'2026-10-30T15:00:01+00:00')
    stale = client.get(f'/api/freshness/sessions/{snapshot["id"]}').json()
    assert stale['freshness']['status'] == 'unscored'
    assert stale['freshness']['remaining_quality_hours'] is None
    assert stale['rescue']['proposal_hash'] is None
    assert stale['readings'][0]['observed_at'] == BASELINE
    assert fingerprint(database) == before


def test_gateway_clock_skew_beyond_five_minutes_is_rejected(fresh_api,monkeypatch):
    client, database = fresh_api
    snapshot = gateway(client);monkeypatch.setenv('AEGIS_SENSOR_INGEST_TOKEN',TOKEN)
    before = fingerprint(database)
    future = ingest(client,snapshot['id'],[frame(observed='2026-10-30T14:06:00+00:00')])
    assert future.status_code == 422
    assert fingerprint(database) == before


def gateway_rescue(client):
    snapshot = create(client,scenario='gateway',devices=[{
        'device_id':'gateway-L05','lot_id':'L05',
        'profile':{'started_at':BASELINE,'initial_equivalent_age_hours':235},
    }])
    assert ingest(client,snapshot['id'],[frame(temperature_c=16.)]).status_code == 200
    captured = client.get(f'/api/freshness/sessions/{snapshot["id"]}').json()
    assert captured['rescue']['proposal_hash'],captured['rescue']
    return captured


def test_moving_gateway_clock_keeps_a_still_valid_assignment_token_but_expiry_rejects_it(fresh_api,monkeypatch):
    client, database = fresh_api
    monkeypatch.setenv('AEGIS_SENSOR_INGEST_TOKEN',TOKEN)
    first = gateway_rescue(client)
    before = fingerprint(database)
    freeze_clock(monkeypatch,'2026-10-30T14:01:00+00:00')
    later = client.get(f'/api/freshness/sessions/{first["id"]}').json()
    assert later['freshness']['remaining_quality_hours'] < first['freshness']['remaining_quality_hours']
    assert later['rescue']['proposed_assignments'] == first['rescue']['proposed_assignments']
    assert later['rescue']['proposal_hash'] == first['rescue']['proposal_hash']
    assert fingerprint(database) == before
    freeze_clock(monkeypatch,'2026-10-30T14:30:00+00:00')
    expired = client.get(f'/api/freshness/sessions/{first["id"]}').json()
    assert expired['freshness']['status'] == 'estimated'
    assert expired['freshness']['remaining_quality_hours'] == 0
    assert expired['rescue']['proposal_hash'] is None
    response = client.post(f'/api/freshness/sessions/{first["id"]}/approve',json=approval(first))
    assert response.status_code == 409
    assert fingerprint(database) == before
    assert client.get('/api/driver').json() == []


def test_a_new_gateway_frame_requires_a_new_human_review_version(fresh_api,monkeypatch):
    client, database = fresh_api
    monkeypatch.setenv('AEGIS_SENSOR_INGEST_TOKEN',TOKEN)
    first = gateway_rescue(client)
    freeze_clock(monkeypatch,'2026-10-30T14:01:00+00:00')
    assert ingest(client,first['id'],[frame('new-reading','2026-10-30T14:01:00+00:00',temperature_c=4.)]).status_code == 200
    before = fingerprint(database)
    assert client.post(f'/api/freshness/sessions/{first["id"]}/approve',json=approval(first)).status_code == 409
    assert fingerprint(database) == before
    assert client.get('/api/driver').json() == []


def test_profile_assumptions_are_bound_into_the_proposal_even_if_store_version_is_not_bumped(fresh_api,monkeypatch):
    client, database = fresh_api
    monkeypatch.setenv('AEGIS_SENSOR_INGEST_TOKEN',TOKEN)
    first = gateway_rescue(client)
    with sqlite3.connect(database) as connection:
        stored = json.loads(connection.execute('SELECT payload FROM freshness_sessions WHERE id=?',(first['id'],)).fetchone()[0])
        stored['devices'][0]['profile']['q10_low'] = 1.6
        connection.execute('UPDATE freshness_sessions SET payload=? WHERE id=?',(json.dumps(stored),first['id']))
    before = fingerprint(database)
    changed = client.get(f'/api/freshness/sessions/{first["id"]}').json()
    assert changed['rescue']['proposed_assignments'] == first['rescue']['proposed_assignments']
    assert changed['rescue']['proposal_hash'] != first['rescue']['proposal_hash']
    assert client.post(f'/api/freshness/sessions/{first["id"]}/approve',json=approval(first)).status_code == 409
    assert fingerprint(database) == before


def test_readiness_and_driver_surface_new_sensor_review_without_an_automatic_hold(fresh_api):
    client, database = fresh_api
    warmed = heat(client,create(client))
    response = client.post(f'/api/freshness/sessions/{warmed["id"]}/approve',json=approval(warmed))
    assert response.status_code == 200
    approved = response.json()['snapshot']
    before = operational(database)
    assert client.post(f'/api/freshness/sessions/{approved["id"]}/replay',json={'expected_version':approved['version'],'event':'normal'}).status_code == 200
    assert operational(database) == before
    db_before = fingerprint(database)
    readiness = client.get('/api/readiness').json()
    selected = next(row for row in readiness['assignments'] if row['shipment_id']=='SH05')
    review = next(row for row in selected['checks'] if row['id']=='freshness_telemetry_review')
    assert review['status'] == 'review_required'
    assignment = next(row for row in client.get('/api/driver').json() if row['id']=='SH05')
    driver = client.get('/api/drive/'+assignment['truck_id']).json()
    assert any(row['shipment_id']=='SH05' for row in driver['freshness_reviews'])
    assert fingerprint(database) == db_before
    network = client.get('/api/network').json()
    assert next(row for row in network['lots'] if row['id']=='L05')['held'] is False


def test_readiness_blocks_a_broken_approved_quality_window_without_changing_disposition(fresh_api):
    client, database = fresh_api
    warmed = heat(client,create(client))
    assert client.post(f'/api/freshness/sessions/{warmed["id"]}/approve',json=approval(warmed)).status_code == 200
    with sqlite3.connect(database) as connection:
        network = json.loads(connection.execute('SELECT payload FROM state WHERE id=1').fetchone()[0])
        next(row for row in network['lots'] if row['id']=='L05')['quality_remaining_hours'] = 0
        connection.execute('UPDATE state SET payload=? WHERE id=1',(json.dumps(network),))
    before = fingerprint(database)
    readiness = client.get('/api/readiness').json()
    selected = next(row for row in readiness['assignments'] if row['shipment_id']=='SH05')
    assert selected['status'] == 'blocked'
    assert 'quality_window' in selected['blockers']
    assert fingerprint(database) == before
    assert client.get('/api/driver').json()
    assert next(row for row in client.get('/api/network').json()['lots'] if row['id']=='L05')['held'] is False


def test_rebasing_never_extends_the_captured_use_by_deadline(fresh_api):
    client, database = fresh_api
    with sqlite3.connect(database) as connection:
        network = json.loads(connection.execute('SELECT payload FROM state WHERE id=1').fetchone()[0])
        next(row for row in network['lots'] if row['id']=='L05')['shelf_life_hours'] = 1.5
        connection.execute('UPDATE state SET payload=? WHERE id=1',(json.dumps(network),))
    snapshot = create(client)
    later = client.post(f'/api/freshness/sessions/{snapshot["id"]}/replay',json={'expected_version':snapshot['version'],'event':'recovery'}).json()
    assert later['freshness']['remaining_quality_hours'] > 0
    with sqlite3.connect(database) as connection:
        network = json.loads(connection.execute('SELECT payload FROM state WHERE id=1').fetchone()[0])
        next(row for row in network['lots'] if row['id']=='L05')['shelf_life_hours'] = 500
        connection.execute('UPDATE state SET payload=?,revision=1 WHERE id=1',(json.dumps(network),))
    rebased = client.post(f'/api/freshness/sessions/{snapshot["id"]}/rebase',json={'expected_version':later['version'],'expected_network_revision':1})
    assert rebased.status_code == 200
    captured = rebased.json()
    assert captured['freshness']['remaining_quality_hours'] > 0
    assert captured['rescue']['proposal_hash'] is None
    assert not any(row['eligible'] and row['dispatchable'] for row in captured['rescue']['options'])
    assert all(row['lot_id']!='L05' for row in captured['fefo']['fefo']['picks'])


def test_per_device_model_capacity_rejects_new_frames_but_keeps_retries_and_snapshot_usable(fresh_api,monkeypatch):
    client,database=fresh_api
    snapshot=gateway(client);monkeypatch.setenv('AEGIS_SENSOR_INGEST_TOKEN',TOKEN)
    monkeypatch.setattr(freshness,'MAX_READINGS',2)
    original=[frame(),frame('second','2026-10-30T14:00:00Z')]
    first=ingest(client,snapshot['id'],original)
    assert first.status_code==200 and first.json()['accepted']==2
    before=fingerprint(database)
    retry=ingest(client,snapshot['id'],original)
    assert retry.status_code==200 and retry.json()['duplicates']==2 and retry.json()['accepted']==0
    assert retry.json()['version']==first.json()['version']
    overflow=ingest(client,snapshot['id'],[frame('too-many','2026-10-30T14:01:00Z')])
    assert overflow.status_code==413
    assert 'model limit' in overflow.json()['detail']
    assert 'archive' not in overflow.json()['detail'].lower()
    assert fingerprint(database)==before
    captured=client.get(f'/api/freshness/sessions/{snapshot["id"]}')
    assert captured.status_code==200 and captured.json()['freshness']['status']=='estimated'
    assert captured.json()['readings']==client.get(f'/api/freshness/sessions/{snapshot["id"]}').json()['readings']
    assert fingerprint(database)==before


def test_device_capacity_is_independent_and_overflow_rolls_back_the_whole_batch(fresh_api,monkeypatch):
    client,database=fresh_api
    snapshot=create(client,scenario='gateway',devices=[
        {'device_id':'gateway-L05','lot_id':'L05','profile':{'started_at':BASELINE}},
        {'device_id':'gateway-L06','lot_id':'L06','profile':{'started_at':BASELINE}},
    ])
    monkeypatch.setenv('AEGIS_SENSOR_INGEST_TOKEN',TOKEN);monkeypatch.setattr(freshness,'MAX_READINGS',2)
    first=[frame(),frame('second','2026-10-30T14:00:00Z')]
    assert ingest(client,snapshot['id'],first).status_code==200
    other=frame('other-first',device_id='gateway-L06')
    before=experiment_rows(database)
    rejected=ingest(client,snapshot['id'],[other,frame('too-many','2026-10-30T14:01:00Z')])
    assert rejected.status_code==413
    assert experiment_rows(database)==before
    # At the first device's limit, its exact retry and a different device's new
    # reading can share a batch. Counts apply to devices, not the whole session.
    accepted=ingest(client,snapshot['id'],[first[0],other])
    assert accepted.status_code==200
    assert accepted.json()['accepted']==1 and accepted.json()['duplicates']==1
    assert ingest(client,snapshot['id'],[frame('other-second','2026-10-30T14:00:00Z',device_id='gateway-L06')]).status_code==200
    assert len(experiment_rows(database)['frames'])==4
    assert client.get(f'/api/freshness/sessions/{snapshot["id"]}').status_code==200


def test_fefo_reports_changed_priority_even_when_both_policies_pick_the_same_lots_and_quantities(fresh_api):
    client,database=fresh_api
    with sqlite3.connect(database) as connection:
        network=json.loads(connection.execute('SELECT payload FROM state WHERE id=1').fetchone()[0])
        network['lots']=[row for row in network['lots'] if row['id'] in {'L03','L05'}]
        for lot in network['lots']:lot['inventory_kg']=400
        network['shipments']=[row for row in network['shipments'] if row['id'] in {'SH03','SH05'}]
        # This declared unit-test journey allows the warm lot at the short stop;
        # the other, long journey must use the cold lot to serve both orders.
        short=next(row for row in network['shipments'] if row['id']=='SH03')
        short.update(estimated_hours=.25,estimated_distance_km=16.25,routing_provenance='Explicit unit-test short-journey assumption')
        network['telemetry']=[row for row in network['telemetry'] if row['shipment_id'] in {'SH03','SH05'}]
        connection.execute('UPDATE state SET payload=? WHERE id=1',(json.dumps(network),))
    snapshot=heat(client,create(client))
    fefo,fifo=snapshot['fefo']['fefo'],snapshot['fefo']['fifo']
    first={row['lot_id']:row['picked_kg'] for row in fefo['lot_totals']}
    second={row['lot_id']:row['picked_kg'] for row in fifo['lot_totals']}
    assert first==second=={'L03':400,'L05':400}
    assert {row['lot_id'] for row in fefo['picks']}=={row['lot_id'] for row in fifo['picks']}=={'L03','L05'}
    assert fefo['picks'][0]['lot_id']=='L05'
    assert fifo['picks'][0]['lot_id']=='L03'
    assert snapshot['fefo']['changed_pick_lots']==['L03','L05']
    assert client.get('/api/driver').json()==[]


def test_corrupt_session_is_reported_without_hiding_valid_experiments_or_rewriting_bytes(fresh_api):
    client,database=fresh_api
    good=create(client);bad=create(client)
    with sqlite3.connect(database) as connection:
        connection.execute('UPDATE freshness_sessions SET payload=? WHERE id=?',('{not valid JSON',bad['id']))
    before=fingerprint(database)
    context=client.get('/api/freshness/context')
    assert context.status_code==200
    assert [row['id'] for row in context.json()['sessions']]==[good['id']]
    assert context.json()['session_errors'][0]['session_id']==bad['id']
    assert 'preserved' in context.json()['session_errors'][0]['error'].lower()
    assert client.get('/api/freshness/sessions/'+bad['id']).status_code==503
    rejected=client.post('/api/freshness/sessions/'+bad['id']+'/replay',json={'expected_version':bad['version'],'event':'normal'})
    assert rejected.status_code==503
    assert fingerprint(database)==before


@pytest.mark.parametrize('broken',['{"network":NaN}','{"network":{},"network":{}}','[]'])
def test_nonfinite_duplicate_or_nonobject_stored_context_abstains(fresh_api,broken):
    client,database=fresh_api;snapshot=create(client)
    with sqlite3.connect(database) as connection:
        connection.execute('UPDATE freshness_sessions SET payload=? WHERE id=?',(broken,snapshot['id']))
    before=fingerprint(database)
    assert client.get('/api/freshness/sessions/'+snapshot['id']).status_code==503
    assert fingerprint(database)==before


def test_corrupt_raw_observation_makes_readout_unavailable_without_repairing_it(fresh_api):
    client,database=fresh_api;snapshot=create(client)
    with sqlite3.connect(database) as connection:
        connection.execute('UPDATE freshness_frames SET payload=? WHERE rowid=(SELECT MIN(rowid) FROM freshness_frames)',('{malformed sensor packet',))
    before=fingerprint(database)
    response=client.get('/api/freshness/sessions/'+snapshot['id'])
    assert response.status_code==503
    assert 'preserved' in response.json()['detail'].lower()
    assert fingerprint(database)==before


def test_reviewed_quality_history_cannot_be_reset_by_creating_a_new_demo_or_gateway(fresh_api):
    client,database=fresh_api;snapshot=heat(client,create(client))
    assert client.post('/api/freshness/sessions/'+snapshot['id']+'/approve',json=approval(snapshot)).status_code==200
    before=fingerprint(database)
    for scenario in ('poultry_demo','gateway'):
        rejected=client.post('/api/freshness/sessions',json={'expected_network_revision':1,'shipment_id':'SH05','scenario':scenario})
        assert rejected.status_code==409
        assert 'reset consumed quality age' in rejected.json()['detail']
    context=client.get('/api/freshness/context').json()
    assert next(row for row in context['shipments'] if row['id']=='SH05')['freshness_session_id']==snapshot['id']
    assert fingerprint(database)==before


def test_an_older_counterfactual_cannot_replace_another_experiments_reviewed_exposure_history(fresh_api):
    client,database=fresh_api;older=create(client);reviewed=heat(client,create(client))
    assert client.post('/api/freshness/sessions/'+reviewed['id']+'/approve',json=approval(reviewed)).status_code==200
    before=fingerprint(database)
    rejected=client.post('/api/freshness/sessions/'+older['id']+'/rebase',json={'expected_version':older['version'],'expected_network_revision':1})
    assert rejected.status_code==409
    assert 'older counterfactual readings' in rejected.json()['detail']
    assert fingerprint(database)==before
