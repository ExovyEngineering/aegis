"""Activity inspection reports only saved audit facts and never initializes state."""
import base64
from contextlib import closing
import hashlib
import json
import sqlite3

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

import backend.activity as activity


@pytest.fixture
def history(tmp_path, monkeypatch):
    for key in ('AEGIS_REHEARSAL_ID','AEGIS_OFFLINE_DEMO','AEGIS_DB_PATH'):
        monkeypatch.delenv(key,raising=False)
    path=tmp_path/'data'/'operator.sqlite';path.parent.mkdir()
    with closing(sqlite3.connect(path)) as connection,connection:
        connection.execute('CREATE TABLE audit(id INTEGER PRIMARY KEY,timestamp TEXT,actor TEXT,action TEXT,payload TEXT)')
        connection.executemany('INSERT INTO audit VALUES(?,?,?,?,?)',[
            (1,'2026-10-29T09:00:00-05:00','simulator','event',json.dumps({'event':'road_closure','shipment_id':'SH03'})),
            (2,'2026-10-29T14:02:00+00:00','Casey','approve',json.dumps({'scenario':'A','proposal_id':'p1','reason':'Reviewed'})),
            (3,'2026-10-29T14:03:00+00:00','simulated driver','incident',json.dumps({'shipment_id':'SH03','description':'Inspect cargo'})),
            (4,'2026-10-29T14:03:00+00:00','simulated driver','driver_quick_report',json.dumps({'shipment_id':'SH03','incident_id':'report-1','kind':'cargo'})),
            (5,'2026-10-29T14:04:00+00:00','operator','reset','{}'),
        ])
    return tmp_path,path


def client(history):
    root,path=history;app=FastAPI();app.include_router(activity.create_activity_router(lambda:path,root=lambda:root))
    return TestClient(app)


def mutate(history,sql,parameters=()):
    with closing(sqlite3.connect(history[1])) as connection,connection:connection.execute(sql,parameters)


def fingerprint(path):
    return {suffix:(hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None)
            for suffix in ('','-wal','-shm','-journal') for target in [path.with_name(path.name+suffix)]}


def page(history,**params):
    with client(history) as connection:return connection.get('/api/activity',params=params)


def test_saved_entries_are_descending_cited_and_no_effects_are_invented(history):
    before=fingerprint(history[1]);response=page(history);assert response.status_code==200,response.text
    result=response.json()
    assert result['available'] and result['read_only'] and not result['operational_state_modified']
    assert [row['id'] for row in result['records']]==[5,4,3,2,1]
    assert result['snapshot_latest_id']==5 and result['total_matching']==5 and result['next_cursor'] is None
    reset=result['records'][0];assert reset['payload']=={} and 'revision' not in reset['summary'] and '13' not in reset['summary']
    approval=result['records'][3];assert approval['actor']=='Casey' and approval['payload']['scenario']=='A'
    assert 'assignments' not in approval['summary'] and 'safe' not in approval['summary']
    assert approval['citation']=={'label':'Internal audit row 2','path':'audit/2'}
    assert all(len(row['payload_sha256'])==64 for row in result['records'])
    assert any('not authenticated' in text for text in result['limitations'])
    assert any('do not currently create audit' in text for text in result['limitations'])
    assert before==fingerprint(history[1])


def test_known_action_catalog_is_explicit_and_unknown_saved_actions_remain_visible(history):
    mutate(history,'INSERT INTO audit VALUES(6,?,?,?,?)',('2026-10-29T16:00:00+00:00','new actor','future_action','{"claimed_result":"all trucks dispatched"}'))
    result=page(history).json();row=result['records'][0]
    assert row['action']=='future_action' and row['action_label']=='Unrecognized recorded action'
    assert row['payload']['claimed_result']=='all trucks dispatched' and 'dispatched' not in row['summary']
    assert row['suggested_view'] is None
    assert {row['id'] for row in result['actions']}==set(activity.CATALOG)
    assert page(history,action='future_action').status_code==422


@pytest.mark.parametrize('action',list(activity.CATALOG))
def test_every_supported_action_filter_and_label_is_backed_by_its_saved_row(history,action):
    mutate(history,'INSERT INTO audit VALUES(6,?,?,?,?)',('2026-10-29T16:00:00+00:00','Reviewer',action,'{}'))
    result=page(history,action=action).json()
    assert result['records'] and all(row['action']==action for row in result['records'])
    assert result['records'][0]['action_label']==activity.CATALOG[action][0]
    assert result['records'][0]['suggested_view']==activity.CATALOG[action][2]


def test_shipment_filter_never_infers_global_nested_or_lot_relationships(history):
    for identifier,payload in [(6,{'context':{'shipment_id':'SH03'}}),(7,{'invalidated_shipments':['SH03'],'lot_id':'L01'}),(8,{'shipment_id':['SH03']}),(9,{'shipment_id':'SH030'})]:
        mutate(history,'INSERT INTO audit VALUES(?,?,?,?,?)',(identifier,'2026-10-29T16:00:00+00:00','Reviewer','lot_hold',json.dumps(payload)))
    result=page(history,shipment_id='SH03').json()
    assert [row['id'] for row in result['records']]==[4,3,1]
    assert result['total_matching']==3 and result['filters']=={'action':None,'shipment_id':'SH03'}
    filtered=page(history,shipment_id='SH03',action='incident').json()
    assert [row['id'] for row in filtered['records']]==[3]
    assert any('only a valid explicit top-level' in text for text in result['limitations'])


def test_quick_report_related_rows_are_not_claimed_as_two_independent_incidents(history):
    rows=page(history,shipment_id='SH03').json()['records']
    quick=next(row for row in rows if row['action']=='driver_quick_report')
    assert 'not an additional independent incident' in quick['summary']


def test_pagination_freezes_older_records_while_new_higher_ids_are_added(history):
    initial=page(history,limit=2).json();assert [row['id'] for row in initial['records']]==[5,4]
    mutate(history,'INSERT INTO audit VALUES(6,?,?,?,?)',('2026-10-29T16:00:00+00:00','operator','reset','{}'))
    second=page(history,limit=2,cursor=initial['next_cursor']).json()
    assert [row['id'] for row in second['records']]==[3,2]
    assert second['snapshot_id']==initial['snapshot_id'] and second['snapshot_latest_id']==5 and second['total_matching']==5
    third=page(history,limit=2,cursor=second['next_cursor']).json()
    assert [row['id'] for row in third['records']]==[1] and third['next_cursor'] is None
    assert page(history).json()['records'][0]['id']==6


@pytest.mark.parametrize('sql,params',[
    ('DELETE FROM audit WHERE id=1',()),
    ('DELETE FROM audit WHERE id=5',()),
    ('UPDATE audit SET payload=? WHERE id=1',('{"shipment_id":"SH99"}',)),
    ('UPDATE audit SET actor=? WHERE id=2',('Changed actor',)),
])
def test_changed_or_removed_captured_records_require_reloading(history,sql,params):
    first=page(history,limit=2).json();mutate(history,sql,params)
    response=page(history,limit=2,cursor=first['next_cursor'])
    assert response.status_code==409 and 'reload' in response.json()['detail']


@pytest.mark.parametrize('filters',[{'action':'event'},{'shipment_id':'SH03'}])
def test_cursor_cannot_be_reused_with_different_filters(history,filters):
    first=page(history,limit=1).json()
    response=page(history,limit=1,cursor=first['next_cursor'],**filters)
    assert response.status_code==422 and 'different filters' in response.json()['detail']


@pytest.mark.parametrize('cursor',['not-base64?','a','eyJ2IjoxfQ','x'*1201,'null'])
def test_bad_cursor_is_rejected_without_state_change(history,cursor):
    before=fingerprint(history[1]);response=page(history,cursor=cursor)
    assert response.status_code==422 and fingerprint(history[1])==before


def test_cursor_modified_context_or_checksum_is_rejected(history):
    first=page(history,limit=1).json();token=first['next_cursor']
    envelope=json.loads(base64.urlsafe_b64decode(token+'='*((-len(token))%4)))
    envelope['context']['before_id']=1
    forged=base64.urlsafe_b64encode(json.dumps(envelope).encode()).decode().rstrip('=')
    assert page(history,cursor=forged).status_code==422
    envelope['checksum']=activity._sha(activity._canonical(envelope['context']))
    envelope['context']['v']=True
    forged=base64.urlsafe_b64encode(json.dumps(envelope).encode()).decode().rstrip('=')
    assert page(history,cursor=forged).status_code==422


def test_unsupported_or_repeated_query_parameters_are_not_silently_ignored(history):
    with client(history) as connection:
        assert connection.get('/api/activity?limit=1&limit=2').status_code==422
        assert connection.get('/api/activity?actor=Casey').status_code==422


def test_unsupported_large_ids_and_empty_metadata_are_explicit(history):
    mutate(history,'UPDATE audit SET actor=?,action=? WHERE id=5',('   ',''))
    row=page(history).json()['records'][0]
    assert row['actor']=='Actor unavailable' and row['action']=='unavailable' and len(row['metadata_errors'])==2
    mutate(history,'INSERT INTO audit VALUES(?,?,?,?,?)',(activity.MAX_ID+1,'2026-10-29T16:00:00+00:00','operator','reset','{}'))
    assert page(history).status_code==503


@pytest.mark.parametrize('params',[{'limit':0},{'limit':101},{'limit':'true'},{'action':"event' OR 1=1 --"},{'action':''},{'shipment_id':"SH03' OR 1=1"},{'shipment_id':'SH03/../SH04'}])
def test_invalid_limits_filters_or_sql_text_are_rejected(history,params):
    before=fingerprint(history[1]);assert page(history,**params).status_code==422
    assert before==fingerprint(history[1])


@pytest.mark.parametrize('payload,error',[
    ('not json','JSONDecodeError'),('[]','Expected a JSON object'),('null','Expected a JSON object'),
    ('{"a":NaN}','Nonfinite'),('{"shipment_id":"SH03","shipment_id":"SH04"}','Duplicate'),
])
def test_corrupt_payload_remains_explicit_and_does_not_hide_other_records(history,payload,error):
    mutate(history,'UPDATE audit SET payload=? WHERE id=5',(payload,))
    result=page(history).json();row=result['records'][0]
    assert row['payload'] is None and error in row['payload_error'] and len(row['payload_sha256'])==64
    assert len(result['records'])==5 and result['records'][1]['payload'] is not None
    assert row['explicit_shipment_id'] is None


def test_oversized_payload_is_not_loaded_or_claimed_as_a_full_hash(history):
    payload=json.dumps({'shipment_id':'SH03','description':'x'*activity.MAX_PAYLOAD_BYTES})
    mutate(history,'UPDATE audit SET payload=? WHERE id=5',(payload,))
    row=page(history).json()['records'][0]
    assert row['payload'] is None and 'full bytes were not read' in row['payload_error']
    assert row['payload_sha256'] is None and len(row['payload_prefix_sha256'])==64
    assert row['payload_bytes']==len(payload.encode())
    assert [row['id'] for row in page(history,shipment_id='SH03').json()['records']]==[4,3,1]


def test_blob_payload_and_invalid_metadata_are_not_silently_reinterpreted(history):
    mutate(history,'UPDATE audit SET timestamp=?,actor=?,action=?,payload=? WHERE id=5',
           ('2026-10-29T10:00:00','a'*3000,sqlite3.Binary(b'event'),sqlite3.Binary(b'{"shipment_id":"SH03"}')))
    row=page(history).json()['records'][0]
    assert row['timestamp'] is None and row['timestamp_raw']=='2026-10-29T10:00:00'
    assert row['actor']=='Actor unavailable' and row['action']=='unavailable'
    assert len(row['metadata_errors'])>=3 and row['payload'] is None and 'not stored as JSON text' in row['payload_error']


def test_exact_original_time_zone_is_preserved(history):
    row=page(history,action='event').json()['records'][0]
    assert row['timestamp']==row['timestamp_raw']=='2026-10-29T09:00:00-05:00'


def test_empty_history_has_no_fabricated_events(history):
    mutate(history,'DELETE FROM audit')
    result=page(history).json()
    assert result['records']==[] and result['total_matching']==0 and result['snapshot_latest_id']==0 and result['next_cursor'] is None


def test_missing_database_never_creates_directory_or_seed(tmp_path,monkeypatch):
    for key in ('AEGIS_REHEARSAL_ID','AEGIS_OFFLINE_DEMO','AEGIS_DB_PATH'):monkeypatch.delenv(key,raising=False)
    path=tmp_path/'missing'/'operator.sqlite';response=page((tmp_path,path))
    assert response.status_code==503 and not path.parent.exists()


@pytest.mark.parametrize('kind',['schema','corrupt'])
def test_missing_schema_or_corrupt_database_reports_error_without_repair(tmp_path,monkeypatch,kind):
    for key in ('AEGIS_REHEARSAL_ID','AEGIS_OFFLINE_DEMO','AEGIS_DB_PATH'):monkeypatch.delenv(key,raising=False)
    path=tmp_path/'operator.sqlite'
    if kind=='corrupt':path.write_bytes(b'not SQLite')
    else:
        with closing(sqlite3.connect(path)) as connection:connection.execute('CREATE TABLE unrelated(value TEXT)')
    before=fingerprint(path);response=page((tmp_path,path))
    assert response.status_code==503 and 'Activity history unavailable' in response.json()['detail'] and fingerprint(path)==before


def test_history_bounds_are_explicit_instead_of_partial_counts(history,monkeypatch):
    monkeypatch.setattr(activity,'MAX_ROWS',4)
    assert page(history).status_code==503
    monkeypatch.setattr(activity,'MAX_ROWS',10000);monkeypatch.setattr(activity,'MAX_CAPTURE_BYTES',10)
    response=page(history);assert response.status_code==503 and 'capture budget' in response.json()['detail']


def test_sql_is_read_only_and_does_not_contact_providers(history,monkeypatch):
    import httpx
    statements=[];real_connect=sqlite3.connect
    def connect(*args,**kwargs):
        assert args[0].endswith('?mode=ro') and kwargs['uri'] is True
        connection=real_connect(*args,**kwargs);connection.set_trace_callback(statements.append)
        return connection
    def forbidden(*args,**kwargs):raise AssertionError('Activity must not contact providers')
    monkeypatch.setattr(activity.sqlite3,'connect',connect)
    monkeypatch.setattr(httpx,'get',forbidden);monkeypatch.setattr(httpx,'post',forbidden)
    before=fingerprint(history[1]);assert page(history).status_code==200
    assert any('query_only=ON' in value for value in statements) and 'BEGIN' in statements
    assert not any(repr(value).upper().find(word)>=0 for value in statements for word in ('CREATE TABLE','INSERT INTO','UPDATE AUDIT','DELETE FROM','COMMIT'))
    assert before==fingerprint(history[1])
