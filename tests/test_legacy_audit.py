import hashlib
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from backend.activity import MAX_PAYLOAD_BYTES, read_legacy_audit


def database(tmp_path, rows):
    path=tmp_path/'audit.sqlite'
    with sqlite3.connect(path) as connection:
        connection.execute('CREATE TABLE audit(id INTEGER PRIMARY KEY,timestamp TEXT,actor TEXT,action TEXT,payload TEXT)')
        connection.executemany('INSERT INTO audit VALUES (?,?,?,?,?)',rows)
    return path


def row(identity,payload):
    return (identity,'2026-10-29T20:00:00+00:00','Reviewer','event',payload)


def test_legacy_valid_shape_is_preserved_and_corrupt_rows_do_not_hide_other_history(tmp_path):
    path=database(tmp_path,[row(1,'{"shipment_id":"SH01"}'),row(2,'broken json')])
    before=path.read_bytes()
    records=read_legacy_audit(path,tmp_path)
    assert records[1]=={'id':1,'timestamp':'2026-10-29T20:00:00+00:00','actor':'Reviewer','action':'event','payload':{'shipment_id':'SH01'}}
    assert records[0]['id']==2 and records[0]['payload'] is None and records[0]['payload_error']
    assert records[0]['payload_sha256']==hashlib.sha256(b'broken json').hexdigest()
    assert path.read_bytes()==before


@pytest.mark.parametrize('payload',['{"value":NaN}','{"x":1,"x":2}','[]','null'])
def test_legacy_invalid_json_contracts_are_per_row_errors(tmp_path,payload):
    path=database(tmp_path,[row(1,payload)])
    record=read_legacy_audit(path,tmp_path)[0]
    assert record['payload'] is None and record['payload_error']


def test_legacy_only_reads_latest_100_even_when_full_history_exceeds_activity_bound(tmp_path):
    path=database(tmp_path,[row(identity,'{}') for identity in range(1,10003)])
    records=read_legacy_audit(path,tmp_path)
    assert len(records)==100 and records[0]['id']==10002 and records[-1]['id']==9903


def test_legacy_oversized_payload_is_explicitly_a_prefix_not_a_full_hash(tmp_path):
    payload=json.dumps({'text':'x'*(MAX_PAYLOAD_BYTES+1000)})
    path=database(tmp_path,[row(1,payload)])
    record=read_legacy_audit(path,tmp_path)[0]
    assert record['payload'] is None and record['payload_sha256'] is None
    assert record['payload_prefix_sha256'] and record['payload_bytes']==len(payload)
    assert record['payload_error']


def test_main_legacy_endpoint_returns_readable_rows_with_a_corrupt_row(tmp_path,monkeypatch):
    import backend.main as main
    monkeypatch.setattr(main,'DB',tmp_path/'operator.sqlite')
    with TestClient(main.app) as client:
        assert client.get('/api/network').status_code==200
        with sqlite3.connect(main.DB) as connection:
            connection.executemany('INSERT INTO audit(timestamp,actor,action,payload) VALUES (?,?,?,?)',[item[1:] for item in [row(1,'{}'),row(2,'not json')]])
        response=client.get('/api/audit')
        assert response.status_code==200
        assert response.json()[0]['payload_error'] and response.json()[1]['payload']=={}
