import pytest

CUSTOM={
    'name':'My farm planning test',
    'origins':[{'id':'F1','name':'Farm planning origin','coordinates':[-92.4,39],'inventory_kg':1000}],
    'stops':[{'id':'S1','name':'Customer planning stop','coordinates':[-92.35,39.02],'demand_kg':300}],
    'trucks':[{'id':'T1','origin_id':'F1','capacity_kg':1000}],
}

def test_custom_route_request_uses_entered_location_and_does_not_dispatch(client):
    before=client.get('/api/network').json()
    r=client.post('/api/route-lab',json={'preset':'custom','custom_operation':CUSTOM})
    assert r.status_code==200
    result=r.json();assert result['preset']['id']=='custom'
    assert result['routes'][0]['origin_id']=='F1'
    assert result['routes'][0]['stop_ids']==['S1']
    assert client.get('/api/network').json()==before
    assert not client.get('/api/driver').json()

@pytest.mark.parametrize('body',[
    {'preset':'custom'},
    {'preset':'farm','custom_operation':CUSTOM},
    {'preset':'custom','custom_operation':CUSTOM,'truck_count':2},
    {'preset':'custom','custom_operation':CUSTOM,'truck_capacity_kg':2000},
])
def test_custom_inputs_never_silently_ignored(client,body):
    assert client.post('/api/route-lab',json=body).status_code==422

def test_driver_report_dispatcher_instruction_and_lot_hold_are_connected(client):
    identity={'actor':'Integration dispatcher','reason':'Reviewed the simulated assignment and driver report'}
    proposal=client.post('/api/proposals/A').json()
    client.post(f"/api/proposals/{proposal['id']}/approve",json=identity).raise_for_status()
    assignment=client.get('/api/driver').json()[0]
    r=client.post('/api/driver/incident',json={'shipment_id':assignment['id'],'description':'Parked at destination; request dispatcher guidance'})
    assert r.status_code==200
    desk=client.get('/api/dispatch').json();report=desk['incidents'][0]
    assert report['shipment_id']==assignment['id'] and report['status']=='open'
    client.post(f"/api/dispatch/incidents/{report['id']}/review",json={**identity,'status':'in_review','expected_version':report['version']}).raise_for_status()
    client.post(f"/api/dispatch/assignments/{assignment['id']}/instruction",json={**identity,'instruction':'Remain parked while dispatcher reviews destination access','expected_instruction_revision':0,'expected_network_revision':desk['network_revision']}).raise_for_status()
    updated=next(s for s in client.get('/api/driver').json() if s['id']==assignment['id'])
    assert not updated['instruction_acknowledged'] and updated['instruction_revision']>0
    client.post(f"/api/driver/{assignment['id']}/instruction-ack",json={'instruction_revision':updated['instruction_revision']}).raise_for_status()
    client.post(f"/api/dispatch/lots/{assignment['lot_id']}/hold",json={**identity,'expected_network_revision':desk['network_revision']}).raise_for_status()
    assert not any(s['lot_id']==assignment['lot_id'] for s in client.get('/api/driver').json())
    current=client.get('/api/dispatch').json()
    client.post(f"/api/dispatch/lots/{assignment['lot_id']}/release",json={**identity,'expected_network_revision':current['network_revision']}).raise_for_status()
    assert not any(s['lot_id']==assignment['lot_id'] for s in client.get('/api/driver').json()),'Release must not silently republish removed assignments'
