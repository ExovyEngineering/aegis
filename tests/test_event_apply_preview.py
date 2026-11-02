"""An explicitly applied event must match the impact a human just reviewed."""
from copy import deepcopy
import hashlib
import json

import pytest

import backend.main as api


def approve_baseline(client):
    proposal=client.post('/api/proposals/A').json()
    response=client.post(f"/api/proposals/{proposal['id']}/approve",
                         json={'actor':'Integration reviewer',
                               'reason':'Approve simulated assignments for guarded event integration tests'})
    assert response.status_code==200,response.text
    return client.get('/api/network').json(),client.get('/api/driver').json()


def captured_preview(client, network, event='road_closure', shipment_id='SH11'):
    response=client.post('/api/events/preview',json={'event':event,'shipment_id':shipment_id,
                         'expected_network_revision':network['revision']})
    assert response.status_code==200,response.text
    return response.json()


def apply_body(preview, **overrides):
    return {'event':preview['event'],'shipment_id':preview['shipment_id'],
            'expected_network_revision':preview['network_revision'],
            'preview_id':preview['preview_id'],**overrides}


def stored_rows():
    with api.db() as connection:
        return {name:connection.execute('SELECT * FROM '+name+' ORDER BY 1').fetchall()
                for name in ('state','assignments','audit','proposals')}


@pytest.mark.parametrize('event',['road_closure','severe_weather','delivery_delay',
                                 'refrigeration_fault','temperature_excursion','inventory_shortage'])
def test_guarded_apply_matches_captured_changes_and_clears_assignments(client,event):
    network,assignments=approve_baseline(client)
    assert assignments
    preview=captured_preview(client,network,event)
    response=client.post('/api/events',json=apply_body(preview))
    assert response.status_code==200,response.text
    receipt=response.json()
    assert receipt['preview_id']==preview['preview_id']
    assert receipt['network_revision_before']==network['revision']
    assert receipt['revision']==network['revision']+1
    assert receipt['assignments_invalidated'] is True
    assert receipt['assignments_removed']==len(assignments)
    assert receipt['operational_state_modified'] is True
    assert client.get('/api/driver').json()==[]
    current=client.get('/api/network').json()
    assert current['revision']==network['revision']+1
    original=next(row for row in network['shipments'] if row['id']=='SH11')
    changed=next(row for row in current['shipments'] if row['id']=='SH11')
    for key in ('estimated_hours','estimated_distance_km','temperature_c','review_priority'):
        assert changed[key]==preview['shipment']['after'][key]
    assert current['nodes']==network['nodes']
    assert changed['estimated_distance_km']==original['estimated_distance_km']
    assert current['events'][-1]['type']==event and current['events'][-1]['shipment_id']=='SH11'
    assert all(row['held']==old['held'] and row['recalled']==old['recalled']
               for row,old in zip(current['lots'],network['lots']))
    actual={row['scenario']:row for row in client.get('/api/scenarios').json()}
    for comparison in preview['scenarios']:
        observed=actual[comparison['scenario']];expected=comparison['after']
        assert sorted(row['id'] for row in observed['shipments'])==expected['selected_ids']
        assert {row['id']:row['lot_id'] for row in observed['shipments']}==expected['selected_lots']
        for key in ('total_logistics_cost','unmet_demand_kg','review_priority_count','food_waste_kg'):
            assert observed[key]==expected[key]
            assert observed[key]-comparison['before'][key]==comparison['delta'][key]
        assert observed['review']['passed'] is True
    audit=client.get('/api/audit').json()
    assert audit[0]['action']=='event' and audit[0]['actor']=='simulator'
    assert audit[0]['payload']['event']==event
    assert audit[0]['payload']['preview_id']==preview['preview_id']


def test_stale_network_revision_cannot_apply_old_preview(client):
    network,_=approve_baseline(client);preview=captured_preview(client,network)
    # An independent explicit simulator action changes revision while preserving
    # the captured receipt as an obsolete input to this second request.
    assert client.post('/api/events',json={'event':'delivery_delay','shipment_id':'SH03'}).status_code==200
    before=stored_rows()
    response=client.post('/api/events',json=apply_body(preview))
    assert response.status_code==409 and stored_rows()==before


@pytest.mark.parametrize('override',[
    {'preview_id':'0'*64}, {'event':'delivery_delay'}, {'shipment_id':'SH12'},
])
def test_changed_digest_or_selected_event_context_does_not_mutate(client,override):
    network,_=approve_baseline(client);preview=captured_preview(client,network)
    before=stored_rows();before_hash=hashlib.sha256(api.DB.read_bytes()).hexdigest()
    response=client.post('/api/events',json=apply_body(preview,**override))
    assert response.status_code==409
    assert stored_rows()==before
    assert hashlib.sha256(api.DB.read_bytes()).hexdigest()==before_hash


def test_acknowledgment_change_invalidates_preview_at_same_network_revision(client):
    network,assignments=approve_baseline(client);preview=captured_preview(client,network)
    response=client.post(f"/api/driver/{assignments[0]['id']}/acknowledge",
                         json={'expected_network_revision':network['revision']})
    assert response.status_code==200,response.text
    assert client.get('/api/network').json()['revision']==network['revision']
    before=stored_rows()
    response=client.post('/api/events',json=apply_body(preview))
    assert response.status_code==409 and stored_rows()==before


@pytest.mark.parametrize('changes',[
    {'event':'verified_recall'}, {'shipment_id':'SH999'},
])
def test_unsupported_legacy_event_context_fails_without_applying(client,changes):
    approve_baseline(client);before=stored_rows()
    response=client.post('/api/events',json={'event':'road_closure','shipment_id':'SH11',**changes})
    assert response.status_code==400 and stored_rows()==before


@pytest.mark.parametrize('changes',[
    {'expected_network_revision':True}, {'expected_network_revision':-1},
    {'preview_id':'bad-hash'},
])
def test_bad_guards_rejected_without_operational_changes(client,changes):
    approve_baseline(client);before=stored_rows()
    response=client.post('/api/events',json={'event':'road_closure','shipment_id':'SH11',**changes})
    assert response.status_code==422 and stored_rows()==before


def test_preview_digest_requires_explicit_revision(client):
    network,_=approve_baseline(client);preview=captured_preview(client,network)
    body=apply_body(preview);del body['expected_network_revision']
    before=stored_rows()
    response=client.post('/api/events',json=body)
    assert response.status_code==422 and stored_rows()==before


def test_legacy_call_without_guards_still_applies_existing_simulation(client):
    network,assignments=approve_baseline(client)
    response=client.post('/api/events',json={'event':'road_closure','shipment_id':'SH11'})
    assert response.status_code==200,response.text
    result=response.json()
    assert result['revision']==network['revision']+1
    assert result['assignments_removed']==len(assignments)
    assert result['operational_state_modified'] is True
    assert client.get('/api/driver').json()==[]


def test_preview_and_apply_preserve_existing_held_and_recalled_flags(client):
    client.get('/api/network')
    with api.db() as connection:
        network,revision=api.load(connection);network['lots'][1]['recalled']=True
        connection.execute('UPDATE state SET payload=?,revision=? WHERE id=1',
                           (json.dumps(network),revision+1))
    network,_=approve_baseline(client)
    flags=deepcopy([(lot['id'],lot['held'],lot['recalled']) for lot in network['lots']])
    preview=captured_preview(client,network,event='inventory_shortage')
    response=client.post('/api/events',json=apply_body(preview))
    assert response.status_code==200,response.text
    after=client.get('/api/network').json()
    assert [(lot['id'],lot['held'],lot['recalled']) for lot in after['lots']]==flags
    for scenario in client.get('/api/scenarios').json():
        assert not {'L01','L02'} & {row['lot_id'] for row in scenario['shipments']}
        assert scenario['review']['passed']
