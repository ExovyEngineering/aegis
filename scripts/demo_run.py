"""Accelerated workflow validation in owned temporary state; never a timed human run."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
import backend.main as application
from backend.paths import ROOT, write_json


def database_fingerprints(databases):
    """Read exact SQLite/sidecar bytes without opening an operational connection."""
    fingerprints = {}
    for base in sorted({Path(path).resolve() for path in databases}):
        for suffix in ('', '-wal', '-shm', '-journal'):
            path = Path(str(base) + suffix)
            try:
                digest = hashlib.sha256()
                size = 0
                with path.open('rb') as stream:
                    for block in iter(lambda: stream.read(1024 * 1024), b''):
                        digest.update(block)
                        size += len(block)
                fingerprints[str(path)] = {'exists':True, 'bytes':size, 'sha256':digest.hexdigest()}
            except FileNotFoundError:
                fingerprints[str(path)] = {'exists':False}
            except OSError as error:
                fingerprints[str(path)] = {'error':f'{type(error).__name__}: {error}'}
    return fingerprints


def run_demo(report_path=None):
    original = application.DB
    # This is a standalone scripted check, never an HTTP handler. A terminal may
    # retain a rehearsal profile; suspend it only in this process while its owned
    # temporary database is in use, then restore every value in finally.
    profile_keys = ('AEGIS_DB_PATH', 'AEGIS_REHEARSAL_ID', 'AEGIS_OFFLINE_DEMO')
    original_profile = {key: os.environ.get(key) for key in profile_keys}
    protected = [original, ROOT / 'data/aegis.sqlite']
    before = database_fingerprints(protected)
    result = {
        'mode':'Accelerated scripted validation of five-minute demo narrative; no real shipments or five-minute wall-clock claim',
        'simulation':True,
        'passed':False,
        'started_at':datetime.now(timezone.utc).isoformat(),
        'human_timed_rehearsal':False,
    }
    try:
        for key in profile_keys:
            os.environ.pop(key, None)
        owned_temp = (ROOT / '.tools/demo-runs').resolve()
        if not owned_temp.is_relative_to(ROOT.resolve()):
            raise ValueError('Demo temporary directory resolves outside the workspace')
        owned_temp.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='aegis-demo-', dir=owned_temp) as temporary:
            folder = Path(temporary).resolve()
            if not folder.is_relative_to(owned_temp):
                raise ValueError('Demo temporary database escaped its owned directory')
            application.DB = folder / 'demo.sqlite'
            with TestClient(application.app) as client:
                network = client.get('/api/network').json()
                baseline = client.get('/api/scenarios').json()
                client.post('/api/events', json={'event':'road_closure', 'shipment_id':'SH12'}).raise_for_status()
                client.post('/api/events', json={'event':'temperature_excursion', 'shipment_id':'SH11'}).raise_for_status()
                comparison = client.get('/api/scenarios').json()
                assert baseline != comparison, 'Chosen events must create observable plan changes'
                proposed = client.post('/api/proposals/D')
                proposed.raise_for_status()
                proposal = proposed.json()
                assert not client.get('/api/driver').json(), 'No assignment before approval'
                client.post(f"/api/proposals/{proposal['id']}/approve", json={
                    'actor':'Demo dispatcher',
                    'reason':'Reviewed simulated alternatives and lot eligibility for this one-wave exercise',
                }).raise_for_status()
                assignments = client.get('/api/driver').json()
                assert assignments
                first = assignments[0]
                focus = client.get(f"/api/drive/{first['truck_id']}").json()['focus']
                parked = client.post(f"/api/drive/{first['truck_id']}/focus", json={
                    'mode':'parked', 'expected_version':focus['version'], 'parked_confirmation':True,
                })
                parked.raise_for_status()
                assert parked.json()['interaction_allowed']
                revision = client.get('/api/network').json()['revision']
                client.post(f"/api/driver/{first['id']}/acknowledge", json={
                    'expected_network_revision':revision,
                }).raise_for_status()
                client.post('/api/driver/incident', json={
                    'shipment_id':first['id'],
                    'description':'Parked at simulated stop; dispatcher review requested',
                    'expected_network_revision':revision,
                }).raise_for_status()
                audit = client.get('/api/audit').json()
                def metrics(plans):
                    keys = ['scenario', 'solver_status', 'total_logistics_cost', 'unmet_demand_kg',
                            'affected_shipments', 'review_priority_count', 'constraint_violations']
                    return [{key:plan[key] for key in keys} for plan in plans]
                result.update(
                    passed=True,
                    seed=network['seed'],
                    baseline=metrics(baseline),
                    after_events=metrics(comparison),
                    approved_assignments=len(assignments),
                    acknowledgment_recorded=any(row['action']=='acknowledge' for row in audit),
                    incident_recorded=any(row['action']=='incident' for row in audit),
                    parked_confirmation_recorded=any(row['action']=='driver_focus' for row in audit),
                    contextual_network_revision=revision,
                    audit_actions=[row['action'] for row in audit],
                    timeline=[
                        {'minute':0, 'action':'Source coverage, real map and simulated network'},
                        {'minute':1, 'action':'Forecast/alerts, dated recall and historical observations'},
                        {'minute':2, 'action':'Road delay and cargo excursion events'},
                        {'minute':3, 'action':'Compare A-D response scenarios; inspect constraints'},
                        {'minute':4, 'action':'Dispatcher approval, parked driver acknowledgment and audit trail'},
                    ],
                )
    except Exception as error:
        result.update(passed=False, error=f'{type(error).__name__}: {error}')
    finally:
        application.DB = original
        for key, value in original_profile.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        after = database_fingerprints(protected)
        verified = not any('error' in entry for mapping in (before, after) for entry in mapping.values())
        modified = before != after if verified else None
        result.update(
            production_database_modified=modified,
            production_preservation_verified=verified,
            production_database_fingerprints_before=before,
            production_database_fingerprints_after=after,
            production_preservation_method='SHA-256 and byte length of original configured and canonical operator SQLite files plus -wal/-shm/-journal sidecars, before/after. Observed changes are not attributed to a particular process.',
            finished_at=datetime.now(timezone.utc).isoformat(),
        )
        if not verified or modified:
            result.update(passed=False, error='Operator database preservation could not be verified' if not verified
                          else 'Protected operator database or sidecar bytes changed during accelerated validation')
        write_json(report_path or ROOT/'reports/demo_results.json', result)
    return result


def main():
    result = run_demo()
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
