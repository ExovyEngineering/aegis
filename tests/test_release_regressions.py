"""Release guards for approval identity and mixed routing-source provenance."""
import json
import pytest
import backend.main as api
from backend.adapters import OSRMRoutingAdapter
from backend.route_lab import plan_routes,estimated_matrix

@pytest.mark.parametrize('body',[
    {'actor':'  ','reason':'Reviewed simulated eligibility'},
    {'actor':'Dispatcher','reason':'     '},
])
def test_whitespace_cannot_authorize_assignments(client,body):
    proposal=client.post('/api/proposals/A').json()
    assert client.post(f"/api/proposals/{proposal['id']}/approve",json=body).status_code==422
    assert client.get('/api/driver').json()==[]
    assert not any(a['action']=='approve' for a in client.get('/api/audit').json())

def test_approval_and_incident_store_trimmed_meaningful_text(client):
    proposal=client.post('/api/proposals/A').json()
    assert client.post(f"/api/proposals/{proposal['id']}/approve",json={'actor':'  Dispatcher  ','reason':'  Reviewed eligibility  '}).status_code==200
    assignment=client.get('/api/driver').json()[0]
    assert client.post('/api/driver/incident',json={'shipment_id':assignment['id'],'description':'     '}).status_code==422
    assert client.post('/api/driver/incident',json={'shipment_id':' '+assignment['id']+' ','description':'  Parked and requesting review  '}).status_code==200
    audit=client.get('/api/audit').json()
    approved=next(a for a in audit if a['action']=='approve')
    incident=next(a for a in audit if a['action']=='incident')
    assert approved['actor']=='Dispatcher' and approved['payload']['reason']=='Reviewed eligibility'
    assert incident['payload']['description']=='Parked and requesting review'

@pytest.mark.parametrize('matrix_fallback,geometry_fallback,missing_distances',[
    (True,False,False),
    (False,True,False),
    (False,False,True),
])
def test_matrix_and_geometry_fallbacks_remain_distinct(monkeypatch,matrix_fallback,geometry_fallback,missing_distances):
    def matrix(self,coordinates):
        result=estimated_matrix(coordinates)
        result['fallback']=matrix_fallback
        result['provenance']='mock matrix source'
        if missing_distances:del result['payload']['distances']
        return result
    def route(self,coordinates):
        return {'fallback':geometry_fallback,'provenance':'mock geometry source','payload':{'routes':[{'distance':123,'duration':45,'geometry':{'type':'LineString','coordinates':coordinates}}]}}
    monkeypatch.setattr(OSRMRoutingAdapter,'matrix',matrix)
    monkeypatch.setattr(OSRMRoutingAdapter,'route',route)
    result=plan_routes(routing='osrm')
    assert result['routes']
    for truck in result['routes']:
        assert truck['travel_time_fallback'] is matrix_fallback
        assert truck['distance_fallback'] is (matrix_fallback or missing_distances)
        assert truck['geometry_fallback'] is geometry_fallback
        assert truck['fallback'] is True
        assert truck['matrix_provenance']=='mock matrix source'
        assert truck['routing_provenance']=='mock geometry source'

def test_route_review_uses_dated_modot_fixture_when_cache_absent(client,tmp_path,monkeypatch):
    monkeypatch.setattr(api,'ROOT',tmp_path)
    fixture=tmp_path/'data/fixtures/modot.json';fixture.parent.mkdir(parents=True)
    fixture.write_text(json.dumps({'retrieved_at':'2020-01-01T00:00:00+00:00','coverage_complete':True,'incident_layers':[{'layer_id':1,'layer_name':'Test incident','payload':{'type':'FeatureCollection','features':[{'type':'Feature','geometry':{'type':'Point','coordinates':[-92,38]},'properties':{'label':'dated fixture event'}}]}}]}))
    monkeypatch.setattr(OSRMRoutingAdapter,'route',lambda self,coordinates,alternatives=False:{'fallback':False,'payload':{'routes':[{'distance':100,'duration':50,'geometry':{'type':'LineString','coordinates':coordinates}}]}})
    response=client.post('/api/route',json={'coordinates':[[-92,38],[-91,38]],'alternatives':True})
    assert response.status_code==200
    review=response.json()['road_review']
    assert review['modot_retrieved_at']=='2020-01-01T00:00:00+00:00'
    assert review['stale'] is True
    assert review['alternatives'][0]['review_required'] is True
    assert review['alternatives'][0]['nearby_events'][0]['properties']['label']=='dated fixture event'
