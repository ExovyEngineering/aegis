"""Accelerated validation of the five-minute narrative; isolated DB, no live dispatch."""
import sys,json,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
import backend.main as application
from backend.paths import ROOT,write_json

def main():
    original=application.DB
    with tempfile.TemporaryDirectory(prefix='aegis-demo-') as temp:
        application.DB=Path(temp)/'demo.sqlite'
        try:
            with TestClient(application.app) as client:
                network=client.get('/api/network').json()
                baseline=client.get('/api/scenarios').json()
                event=client.post('/api/events',json={'event':'road_closure','shipment_id':'SH12'});event.raise_for_status()
                event=client.post('/api/events',json={'event':'temperature_excursion','shipment_id':'SH11'});event.raise_for_status()
                comparison=client.get('/api/scenarios').json()
                assert baseline!=comparison,'Chosen events must create observable plan changes'
                proposed=client.post('/api/proposals/D');proposed.raise_for_status();proposal=proposed.json()
                assert not client.get('/api/driver').json(),'No assignment before approval'
                approved=client.post(f"/api/proposals/{proposal['id']}/approve",json={'actor':'Demo dispatcher','reason':'Reviewed simulated alternatives and lot eligibility for this one-wave exercise'});approved.raise_for_status()
                assignments=client.get('/api/driver').json();assert assignments
                first=assignments[0]
                focus=client.get(f"/api/drive/{first['truck_id']}").json()['focus']
                parked=client.post(f"/api/drive/{first['truck_id']}/focus",json={'mode':'parked','expected_version':focus['version'],'parked_confirmation':True})
                parked.raise_for_status();assert parked.json()['interaction_allowed']
                client.post(f"/api/driver/{first['id']}/acknowledge").raise_for_status()
                client.post('/api/driver/incident',json={'shipment_id':first['id'],'description':'Parked at simulated stop; dispatcher review requested'}).raise_for_status()
                audit=client.get('/api/audit').json()
                def metrics(plans):return [{k:p[k] for k in ['scenario','solver_status','total_logistics_cost','unmet_demand_kg','affected_shipments','review_priority_count','constraint_violations']} for p in plans]
                result={'mode':'Accelerated scripted validation of five-minute demo narrative; no real shipments or five-minute wall-clock claim','seed':network['seed'],'baseline':metrics(baseline),'after_events':metrics(comparison),'approved_assignments':len(assignments),'acknowledgment_recorded':any(a['action']=='acknowledge' for a in audit),'incident_recorded':any(a['action']=='incident' for a in audit),'audit_actions':[a['action'] for a in audit],'production_database_modified':False,'timeline':[{'minute':0,'action':'Source coverage, real map and simulated network'},{'minute':1,'action':'Forecast/alerts, dated recall and historical observations'},{'minute':2,'action':'Road delay and cargo excursion events'},{'minute':3,'action':'Compare A–D response scenarios; inspect constraints'},{'minute':4,'action':'Dispatcher approval, driver acknowledgment and audit trail'}]}
                result['parked_confirmation_recorded']=any(a['action']=='driver_focus' for a in audit)
                write_json(ROOT/'reports/demo_results.json',result);print(json.dumps(result,indent=2))
        finally:application.DB=original
if __name__=='__main__':main()
