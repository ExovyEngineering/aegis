"""Read-only, bounded inspection of recorded local audit entries.

This is an activity history, not an authenticated or complete event-sourcing
ledger. In particular, computed routes and unapplied previews are not inferred
from unrelated records, and historical effects absent from payloads stay absent.
"""
import base64
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request

from backend.paths import ROOT
from backend.runtime import require_valid_runtime

MAX_ROWS = 10000
MAX_PAYLOAD_BYTES = 32 * 1024
MAX_CAPTURE_BYTES = 16 * 1024 * 1024
MAX_METADATA_BYTES = 2048
# JSON numeric IDs must remain exact in the TypeScript client.
MAX_ID = 9007199254740991
IDENTIFIER = re.compile(r'^[A-Za-z0-9_.-]{1,64}$')
CATALOG = {
    'event': ('Simulated event', 'A simulator event was recorded.', 'command'),
    'reset': ('Simulation reset', 'A simulated network reset was recorded.', 'command'),
    'approve': ('Plan approval', 'A simulated plan approval was recorded.', 'command'),
    'acknowledge': ('Trip acknowledgment', 'A simulated driver trip acknowledgment was recorded.', 'drive'),
    'incident': ('Driver incident report', 'A simulated driver incident report was recorded for review.', 'dispatch'),
    'incident_review': ('Incident review', 'A dispatcher review of a simulated incident was recorded.', 'dispatch'),
    'lot_hold': ('Lot hold', 'A human-recorded simulated lot hold was recorded.', 'dispatch'),
    'lot_release': ('Lot release', 'A human-recorded simulated precautionary release was recorded.', 'dispatch'),
    'dispatcher_instruction': ('Dispatcher instruction', 'A versioned dispatcher instruction was recorded.', 'dispatch'),
    'instruction_acknowledge': ('Instruction acknowledgment', 'A simulated driver instruction acknowledgment was recorded.', 'drive'),
    'targeted_verification_review': ('Targeted verification review', 'A human-recorded targeted verification review was recorded.', 'dispatch'),
    'driver_focus': ('Parked-use status', 'A self-declared driver interaction-mode change was recorded.', 'drive'),
    'driver_quick_report': ('Driver quick-report link', 'A quick-report link to an incident record was recorded; it is not an additional independent incident.', 'dispatch'),
    'save_planning_project': ('Planning project saved', 'A separate planning project was saved; this record is not dispatch approval.', 'routes'),
    'update_planning_project': ('Planning project updated', 'A separate planning project update was recorded; this record is not dispatch approval.', 'routes'),
    'archive_planning_project': ('Planning project archived', 'A separate planning project archive action was recorded.', 'routes'),
    'rehearsal_start': ('Rehearsal started', 'A local rehearsal timer start was recorded.', 'brief'),
    'rehearsal_checkpoint': ('Rehearsal checkpoint', 'A local rehearsal checkpoint was recorded; inspect its recorded outcome.', 'brief'),
    'rehearsal_finish': ('Rehearsal finished', 'A local rehearsal timer finish was recorded; this does not prove a timed human presentation.', 'brief'),
}
LIMITATIONS = [
    'Internal local audit records for simulated operations. Actor names are self-declared, not authenticated identities; this is not an immutable or tamper-proof ledger.',
    'The history is incomplete: route requests, scenario recomputation, source refresh, proposal creation and unsaved route calculations do not currently create audit entries. Absence is not proof that a button was unused.',
    'Summaries describe recorded actions only. Historical assignment counts, before/after values, resulting revisions or safety findings are not invented when absent from the saved payload.',
    'Shipment filtering matches only a valid explicit top-level shipment_id in a readable payload. It does not infer nested or lot/truck/global approval relationships, so related activity may be excluded.',
    'A driver quick report can create both an incident row and a quick-report link. Audit row counts are not counts of independent incidents or completed deliveries.',
    'A captured page is not a live update. Newer audit IDs stay outside paged snapshots; editing or deleting captured rows requires reloading. Oversized payloads are represented only by their bounded prefix, size and explicit error.',
]


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def _strict_json(value):
    def invalid(_): raise ValueError('Nonfinite JSON value')
    def unique(pairs):
        result = {}
        for key, item in pairs:
            if key in result: raise ValueError('Duplicate JSON object key')
            result[key] = item
        return result
    return json.loads(value, parse_constant=invalid, object_pairs_hook=unique)


def _positive(value):
    return type(value) is int and 0 < value <= MAX_ID


def _cursor_encode(snapshot, latest, before, action, shipment_id):
    body = {'v':1, 'snapshot_id':snapshot, 'snapshot_latest_id':latest,
            'before_id':before, 'action':action, 'shipment_id':shipment_id}
    wrapped = {'context':body, 'checksum':_sha(_canonical(body))}
    return base64.urlsafe_b64encode(_canonical(wrapped)).decode('ascii').rstrip('=')


def _cursor_decode(cursor, action, shipment_id):
    try:
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,1200}', cursor): raise ValueError('Unsupported encoding')
        value = _strict_json(base64.b64decode(cursor+'='*((-len(cursor)) % 4), altchars=b'-_', validate=True))
        if not isinstance(value, dict) or set(value) != {'context', 'checksum'}: raise ValueError('Unsupported cursor envelope')
        body = value['context']
        if not isinstance(body, dict) or set(body) != {'v','snapshot_id','snapshot_latest_id','before_id','action','shipment_id'}: raise ValueError('Unsupported cursor context')
        if type(body['v']) is not int or body['v'] != 1 or not re.fullmatch(r'[a-f0-9]{64}', str(body['snapshot_id'])): raise ValueError('Unsupported cursor version or digest')
        if not _positive(body['snapshot_latest_id']) or not _positive(body['before_id']) or body['before_id'] > body['snapshot_latest_id']: raise ValueError('Unsupported cursor ID range')
        if body['action'] != action or body['shipment_id'] != shipment_id: raise ValueError('Cursor belongs to different filters')
        if not isinstance(value['checksum'], str) or value['checksum'] != _sha(_canonical(body)): raise ValueError('Cursor checksum mismatch')
        return body
    except (ValueError, TypeError, UnicodeError, OverflowError, RecursionError) as error:
        raise HTTPException(422, f'Invalid activity cursor: {error}. Reload activity with the current filters.') from error


def _metadata(value, length, label, errors):
    if not isinstance(value, bytes):
        errors.append(f'{label} is not stored as text')
        return None
    try: text = value.decode('utf-8')
    except UnicodeError:
        errors.append(f'{label} is not valid UTF-8 text'); return None
    if length > MAX_METADATA_BYTES:
        errors.append(f'{label} exceeds the {MAX_METADATA_BYTES}-byte display bound')
        return None
    return text


def _read_records(path, root, latest=None, row_limit=None):
    require_valid_runtime(path, root=root)
    selected = Path(path).resolve()
    if not selected.is_file():
        raise HTTPException(503, 'Activity database is unavailable; history will not create or seed it')
    try:
        with closing(sqlite3.connect(selected.as_uri()+'?mode=ro', uri=True, timeout=5)) as connection:
            connection.execute('PRAGMA query_only=ON')
            connection.execute('PRAGMA trusted_schema=OFF')
            connection.execute('BEGIN')
            high, count = connection.execute('SELECT COALESCE(MAX(id),0),COUNT(*) FROM audit WHERE (? IS NULL OR id<=?)', (latest, latest)).fetchone()
            if row_limit is not None and (type(row_limit) is not int or not 1 <= row_limit <= 100):
                raise ValueError('Legacy activity limit must be an integer from 1 to 100')
            if type(high) is not int or not 0 <= high <= MAX_ID or (row_limit is None and count > MAX_ROWS):
                raise ValueError(f'Activity history exceeds the {MAX_ROWS}-row inspection bound or has unsupported IDs')
            upper = high if latest is None else latest
            rows = connection.execute('''SELECT id,
                substr(CAST(timestamp AS BLOB),1,?),length(CAST(timestamp AS BLOB)),typeof(timestamp),
                substr(CAST(actor AS BLOB),1,?),length(CAST(actor AS BLOB)),typeof(actor),
                substr(CAST(action AS BLOB),1,?),length(CAST(action AS BLOB)),typeof(action),
                substr(CAST(payload AS BLOB),1,?),length(CAST(payload AS BLOB)),typeof(payload)
                FROM audit WHERE id<=? ORDER BY id DESC LIMIT ?''',
                (MAX_METADATA_BYTES+1,MAX_METADATA_BYTES+1,MAX_METADATA_BYTES+1,MAX_PAYLOAD_BYTES+1,upper,row_limit or MAX_ROWS+1))
            output=[];identity=[];captured=0
            for row in rows:
                identifier, raw_time, time_length, time_type, raw_actor, actor_length, actor_type, raw_action, action_length, action_type, raw_payload, payload_length, payload_type = row
                if not _positive(identifier): raise ValueError('Activity history contains an unsupported audit ID')
                captured += sum(len(value) for value in (raw_time,raw_actor,raw_action,raw_payload) if isinstance(value,bytes))
                if captured > MAX_CAPTURE_BYTES: raise ValueError('Activity history exceeds the 16 MiB bounded capture budget')
                # Hash the exact bounded stored representation, including storage
                # types and full lengths; never label a prefix as a full hash.
                identity.append([identifier, *[(kind,length,_sha(value) if isinstance(value,bytes) else None)
                    for value,length,kind in ((raw_time,time_length,time_type),(raw_actor,actor_length,actor_type),
                        (raw_action,action_length,action_type),(raw_payload,payload_length,payload_type))]])
                errors=[]
                timestamp_raw=_metadata(raw_time,time_length,'Timestamp',errors)
                actor=_metadata(raw_actor,actor_length,'Actor',errors) if actor_type=='text' else None
                action=_metadata(raw_action,action_length,'Action',errors) if action_type=='text' else None
                if actor_type!='text': errors.append('Actor is not stored as text')
                if action_type!='text': errors.append('Action is not stored as text')
                if actor is not None and not actor.strip(): errors.append('Actor text is empty'); actor=None
                if action is not None and not action.strip(): errors.append('Action text is empty'); action=None
                timestamp=None
                if time_type=='text' and timestamp_raw is not None:
                    try:
                        instant=datetime.fromisoformat(timestamp_raw)
                        if instant.tzinfo is None: raise ValueError('Naive timestamp')
                        timestamp=timestamp_raw
                    except (ValueError,OverflowError): errors.append('Timestamp is invalid or lacks an explicit time zone; original text is preserved separately')
                elif time_type!='text': errors.append('Timestamp is not stored as text')
                payload=None;payload_error=None;payload_sha=None;prefix_sha=None
                if payload_type!='text' or not isinstance(raw_payload,bytes):
                    payload_error='Payload is not stored as JSON text'
                elif payload_length > MAX_PAYLOAD_BYTES:
                    payload_error=f'Payload exceeds the {MAX_PAYLOAD_BYTES}-byte inspection bound; full bytes were not read'
                    prefix_sha=_sha(raw_payload)
                else:
                    payload_sha=_sha(raw_payload)
                    try:
                        payload=_strict_json(raw_payload)
                        if not isinstance(payload,dict): raise ValueError('Expected a JSON object')
                    except (ValueError,TypeError,UnicodeError,OverflowError,RecursionError) as error:
                        payload=None;payload_error=f'{type(error).__name__}: {error}'
                explicit=payload.get('shipment_id') if payload is not None else None
                if not isinstance(explicit,str) or not IDENTIFIER.fullmatch(explicit): explicit=None
                known=CATALOG.get(action)
                label,summary,view = known or ('Unrecognized recorded action','An unrecognized local audit action was recorded; inspect its raw metadata and payload.',None)
                if explicit: summary += f' Explicit shipment: {explicit}.'
                if payload_error: summary += ' Detailed payload is unavailable; historical effects are not reconstructed.'
                output.append({'id':identifier,'timestamp':timestamp,'timestamp_raw':timestamp_raw,
                    'actor':actor if actor is not None else 'Actor unavailable','action':action if action is not None else 'unavailable',
                    'action_label':label,'summary':summary,'scope':'Recorded local simulated activity; current operational state may differ',
                    'payload':payload,'payload_error':payload_error,'payload_sha256':payload_sha,
                    'payload_prefix_sha256':prefix_sha,'payload_bytes':payload_length,'metadata_errors':errors,
                    'explicit_shipment_id':explicit,'suggested_view':view,
                    'citation':{'label':f'Internal audit row {identifier}','path':f'audit/{identifier}'}})
            return output, upper, _sha(_canonical(identity))
    except (sqlite3.Error,ValueError,TypeError,OverflowError) as error:
        raise HTTPException(503, f'Activity history unavailable: {type(error).__name__}: {error}') from error


def read_legacy_audit(path, root=ROOT):
    """Bounded legacy shape with explicit per-row errors, never raw json.loads."""
    records, _, _ = _read_records(path, root, row_limit=100)
    result=[]
    for row in records:
        entry={key:row[key] for key in ('id','timestamp','actor','action','payload')}
        if row['payload_error']:
            entry.update(payload_error=row['payload_error'],payload_sha256=row['payload_sha256'],
                         payload_prefix_sha256=row['payload_prefix_sha256'],payload_bytes=row['payload_bytes'])
        if row['metadata_errors']: entry['metadata_errors']=row['metadata_errors']
        result.append(entry)
    return result


def create_activity_router(db_path, root=ROOT):
    router=APIRouter(tags=['Read-only operational activity'])

    @router.get('/api/activity')
    def activity(request:Request,limit:Annotated[int,Query(ge=1,le=100)]=25,
                 action:Annotated[str|None,Query(max_length=80)]=None,
                 shipment_id:Annotated[str|None,Query(pattern=r'^[A-Za-z0-9_.-]{1,64}$')]=None,
                 cursor:Annotated[str|None,Query(max_length=1200)]=None):
        allowed={'limit','action','shipment_id','cursor'}
        if any(key not in allowed for key in request.query_params) or any(len(request.query_params.getlist(key))>1 for key in allowed):
            raise HTTPException(422,'Unsupported or repeated activity query parameter; use one value per supported filter')
        if action is not None and action not in CATALOG:
            raise HTTPException(422,'Unsupported activity action filter; choose an action from the recorded-action catalog')
        context=_cursor_decode(cursor,action,shipment_id) if cursor is not None else None
        workspace=Path(root() if callable(root) else root)
        path=db_path() if callable(db_path) else db_path
        rows,latest,snapshot=_read_records(path,workspace,context['snapshot_latest_id'] if context else None)
        if context and context['snapshot_id']!=snapshot:
            raise HTTPException(409,'Captured activity changed or was removed; reload the activity snapshot before paging')
        matching=[row for row in rows if (action is None or row['action']==action)
                  and (shipment_id is None or row['explicit_shipment_id']==shipment_id)]
        remaining=[row for row in matching if context is None or row['id']<context['before_id']]
        selected=remaining[:limit]
        next_cursor=_cursor_encode(snapshot,latest,selected[-1]['id'],action,shipment_id) if len(remaining)>limit else None
        return {'available':True,'generated_at':datetime.now(timezone.utc).isoformat(),
                'read_only':True,'operational_state_modified':False,'records':selected,
                'actions':[{'id':key,'label':value[0]} for key,value in CATALOG.items()],
                'snapshot_id':snapshot,'snapshot_latest_id':latest,'total_matching':len(matching),
                'returned_records':len(selected),'next_cursor':next_cursor,
                'filters':{'action':action,'shipment_id':shipment_id},'limitations':LIMITATIONS}

    return router
