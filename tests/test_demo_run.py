import json
import os
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from scripts import demo_run as demo


@pytest.fixture
def protected_state(tmp_path,monkeypatch):
    root=tmp_path/'project';(root/'data').mkdir(parents=True)
    original=root/'data/configured.sqlite'
    canonical=root/'data/aegis.sqlite'
    for index,path in enumerate((original,canonical)):
        path.write_bytes(f'operator bytes {index}'.encode())
        Path(str(path)+'-wal').write_bytes(f'operator WAL {index}'.encode())
        Path(str(path)+'-shm').write_bytes(f'operator SHM {index}'.encode())
    monkeypatch.setattr(demo,'ROOT',root)
    monkeypatch.setattr(demo.application,'DB',original)
    return root,original,canonical


def test_accelerated_demo_measures_preservation_and_uses_displayed_trip_context(protected_state,monkeypatch):
    root,original,canonical=protected_state
    before=demo.database_fingerprints([original,canonical])
    requests=[]
    class CapturingClient(TestClient):
        def post(self,path,*args,**kwargs):
            requests.append((path,kwargs.get('json')))
            return super().post(path,*args,**kwargs)
    monkeypatch.setattr(demo,'TestClient',CapturingClient)
    result=demo.run_demo()
    assert result['passed'] and result['production_preservation_verified']
    assert result['production_database_modified'] is False
    assert result['human_timed_rehearsal'] is False
    assert result['production_database_fingerprints_before']==before
    assert result['production_database_fingerprints_after']==before
    assert demo.application.DB==original
    assert not any((root/'.tools/demo-runs').iterdir())
    assert result['parked_confirmation_recorded'] and result['acknowledgment_recorded'] and result['incident_recorded']
    acknowledgment=next((path,body) for path,body in requests if path.endswith('/acknowledge'))
    incident=next(body for path,body in requests if path=='/api/driver/incident')
    assert acknowledgment[1]['expected_network_revision']==result['contextual_network_revision']
    assert incident['expected_network_revision']==result['contextual_network_revision']
    assert result['baseline']!=result['after_events']
    assert json.loads((root/'reports/demo_results.json').read_text())['passed']


def test_script_failure_restores_database_and_reports_real_failure(protected_state,monkeypatch):
    root,original,_=protected_state
    class FailingClient:
        def __init__(self,*args,**kwargs):pass
        def __enter__(self):raise RuntimeError('isolated workflow failed')
        def __exit__(self,*args):pass
    monkeypatch.setattr(demo,'TestClient',FailingClient)
    result=demo.run_demo()
    assert result['passed'] is False and result['production_database_modified'] is False
    assert result['error']=='RuntimeError: isolated workflow failed'
    assert demo.application.DB==original
    assert (root/'reports/demo_results.json').exists()


def test_canonical_operator_sidecar_change_can_never_be_reported_as_preserved(protected_state,monkeypatch):
    _,original,canonical=protected_state
    class ChangedStateClient:
        def __init__(self,*args,**kwargs):pass
        def __enter__(self):
            Path(str(canonical)+'-journal').write_bytes(b'external change detected')
            raise RuntimeError('do not hide changed state')
        def __exit__(self,*args):pass
    monkeypatch.setattr(demo,'TestClient',ChangedStateClient)
    result=demo.run_demo()
    assert result['production_database_modified'] is True
    assert result['production_preservation_verified'] is True
    assert result['passed'] is False
    assert 'bytes changed' in result['error']
    assert demo.application.DB==original


def test_unreadable_originals_are_unknown_preservation_not_false_success(protected_state,monkeypatch):
    _,original,_=protected_state
    monkeypatch.setattr(demo,'database_fingerprints',lambda paths:{'protected-file':{'error':'PermissionError: denied'}})
    class FailingClient:
        def __init__(self,*args,**kwargs):pass
        def __enter__(self):raise RuntimeError('not relevant')
        def __exit__(self,*args):pass
    monkeypatch.setattr(demo,'TestClient',FailingClient)
    result=demo.run_demo()
    assert result['production_database_modified'] is None
    assert result['production_preservation_verified'] is False
    assert result['passed'] is False
    assert demo.application.DB==original


def test_accelerated_check_restores_an_inherited_rehearsal_profile(protected_state,monkeypatch):
    _,original,_=protected_state
    profile={'AEGIS_REHEARSAL_ID':'ed16cd7d-382f-49d9-846e-f1fe0fe27fe3',
             'AEGIS_DB_PATH':str(original),'AEGIS_OFFLINE_DEMO':'1'}
    for key,value in profile.items():monkeypatch.setenv(key,value)
    result=demo.run_demo()
    assert result['passed'] and result['production_database_modified'] is False
    assert {key:os.environ.get(key) for key in profile}==profile
    assert demo.application.DB==original


def test_failure_also_restores_inherited_rehearsal_environment(protected_state,monkeypatch):
    _,original,_=protected_state
    monkeypatch.setenv('AEGIS_REHEARSAL_ID','original-invalid-profile')
    monkeypatch.setenv('AEGIS_OFFLINE_DEMO','1')
    class FailingClient:
        def __init__(self,*args,**kwargs):pass
        def __enter__(self):raise RuntimeError('workflow interrupted')
        def __exit__(self,*args):pass
    monkeypatch.setattr(demo,'TestClient',FailingClient)
    result=demo.run_demo()
    assert not result['passed']
    assert os.environ['AEGIS_REHEARSAL_ID']=='original-invalid-profile'
    assert os.environ['AEGIS_OFFLINE_DEMO']=='1'
    assert demo.application.DB==original
