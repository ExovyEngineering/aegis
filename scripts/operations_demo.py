"""Exercise the dispatcher/driver loop in a temporary DB, never operator state."""
import sys,tempfile,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
import backend.main as app
from backend.paths import ROOT,write_json

def main():
    original=app.DB
    with tempfile.TemporaryDirectory(prefix='aegis-operations-') as temp:
        app.DB=Path(temp)/'operations.sqlite'
        try:
            with TestClient(app.app) as client:
                identity={'actor':'Operations demo dispatcher','reason':'Reviewed simulated driver report and assignment eligibility'}
                plan=client.post('/api/proposals/A').json()
                client.post(f"/api/proposals/{plan['id']}/approve",json=identity).raise_for_status()
                assignment=client.get('/api/driver').json()[0]
                focus=client.get(f"/api/drive/{assignment['truck_id']}").json()['focus']
                parked=client.post(f"/api/drive/{assignment['truck_id']}/focus",json={'mode':'parked','expected_version':focus['version'],'parked_confirmation':True})
                parked.raise_for_status();assert parked.json()['interaction_allowed']
                report=client.post('/api/driver/incident',json={'shipment_id':assignment['id'],'description':'Parked while checking simulated destination access'})
                report.raise_for_status()
                desk=client.get('/api/dispatch').json();incident=desk['incidents'][0]
                client.post(f"/api/dispatch/incidents/{incident['id']}/review",json={**identity,'status':'in_review','expected_version':incident['version']}).raise_for_status()
                client.post(f"/api/dispatch/assignments/{assignment['id']}/instruction",json={**identity,'instruction':'Remain parked while dispatcher reviews access','expected_instruction_revision':0,'expected_network_revision':desk['network_revision']}).raise_for_status()
                current=next(s for s in client.get('/api/driver').json() if s['id']==assignment['id'])
                revision=current['instruction_revision']
                assert client.post(f"/api/driver/{assignment['id']}/instruction-ack",json={'instruction_revision':revision+1}).status_code==409
                client.post(f"/api/driver/{assignment['id']}/instruction-ack",json={'instruction_revision':revision}).raise_for_status()
                client.post(f"/api/dispatch/lots/{assignment['lot_id']}/hold",json={**identity,'expected_network_revision':desk['network_revision']}).raise_for_status()
                assert not any(s['lot_id']==assignment['lot_id'] for s in client.get('/api/driver').json())
                held=client.get('/api/dispatch').json()
                client.post(f"/api/dispatch/lots/{assignment['lot_id']}/release",json={**identity,'expected_network_revision':held['network_revision']}).raise_for_status()
                assert not any(s['lot_id']==assignment['lot_id'] for s in client.get('/api/driver').json())
                client.post(f"/api/dispatch/incidents/{incident['id']}/review",json={**identity,'status':'resolved','expected_version':incident['version']+1}).raise_for_status()
                actions=[row['action'] for row in client.get('/api/audit').json()]
                result={'passed':True,'simulation':True,'operator_database_modified':False,'driver_report_created':True,'incident_reviewed_and_resolved':True,'instruction_acknowledged':True,'stale_instruction_ack_rejected':True,'held_lot_assignments_removed':True,'release_did_not_redispatch':True,'audit_actions':actions}
                result['parked_confirmation_recorded']='driver_focus' in actions
                write_json(ROOT/'reports/operations_demo.json',result);print(json.dumps(result,indent=2))
        finally:app.DB=original
if __name__=='__main__':main()
