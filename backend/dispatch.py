"""Local simulated dispatcher review, explicit lot holds, and versioned instructions.

Actor names are self-declared demo identities, not authenticated permissions.
This module never sends messages to an external service or dispatches real cargo.
Reports retain their reporting network revision and assignment snapshot even when
reset/reapproval reuses a shipment ID. Reviewing a historical report never rewrites
that snapshot or certifies that it describes a later assignment.
"""
import json
import uuid
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from backend.adapters import now


def ensure_dispatch_schema(connection):
    connection.execute(
        'CREATE TABLE IF NOT EXISTS incidents '
        '(id TEXT PRIMARY KEY, shipment_id TEXT NOT NULL, payload TEXT NOT NULL, '
        'status TEXT NOT NULL, version INTEGER NOT NULL)'
    )
    # Persist counters independently of assignments, which scenario approval can replace.
    # This prevents an old acknowledgment from matching a reused instruction version.
    connection.execute(
        'CREATE TABLE IF NOT EXISTS dispatch_instruction_versions '
        '(shipment_id TEXT PRIMARY KEY, version INTEGER NOT NULL)'
    )


def _begin(connection):
    ensure_dispatch_schema(connection)
    if not connection.in_transaction:
        connection.execute('BEGIN IMMEDIATE')


def create_driver_incident(connection, shipment_id, description, record):
    """Called inside main's db context; commit/rollback belongs to that context."""
    _begin(connection)
    assignment_row = connection.execute('SELECT payload FROM assignments WHERE id=?', (shipment_id,)).fetchone()
    if not assignment_row:
        raise HTTPException(404, 'No approved assignment')
    assignment = json.loads(assignment_row[0])
    state_revision = connection.execute('SELECT revision FROM state WHERE id=1').fetchone()[0]
    incident_id = str(uuid.uuid4())
    payload = {
        'description': description,
        'reported_at': now(),
        'provenance': 'simulated driver report; dispatcher review required',
        'reported_network_revision': state_revision,
        'reporting_assignment': {key: assignment.get(key) for key in
                                 ('id', 'lot_id', 'truck_id', 'origin', 'destination')},
    }
    connection.execute(
        'INSERT INTO incidents VALUES (?,?,?,?,0)',
        (incident_id, shipment_id, json.dumps(payload), 'open'),
    )
    record(connection, 'simulated driver', 'incident', {
        'incident_id': incident_id, 'shipment_id': shipment_id, 'description': description,
    })
    return {'status': 'recorded for dispatcher review', 'incident_id': incident_id}


class HumanDecision(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    actor: str = Field(min_length=2, max_length=100)
    reason: str = Field(min_length=5, max_length=1000)


class IncidentReview(HumanDecision):
    status: Literal['in_review', 'resolved']
    expected_version: int = Field(ge=0)


class LotDecision(HumanDecision):
    expected_network_revision: int = Field(ge=0)


class InstructionDecision(HumanDecision):
    instruction: str = Field(min_length=3, max_length=2000)
    expected_instruction_revision: int = Field(ge=0)
    expected_network_revision: int = Field(ge=0)


class InstructionAcknowledgment(BaseModel):
    model_config = ConfigDict(extra='forbid')
    instruction_revision: int = Field(ge=1)


def _assignments(connection):
    assignments = []
    for row in connection.execute('SELECT id,payload,acknowledged FROM assignments ORDER BY id'):
        payload = json.loads(row[1])
        assignments.append(dict(
            payload, acknowledged=bool(row[2]),
            instruction_revision=payload.get('instruction_revision', 0),
            instruction_acknowledged=payload.get('instruction_acknowledged', bool(row[2])),
        ))
    return assignments


def create_dispatch_router(db, load, record):
    router = APIRouter(tags=['Dispatcher workflow'])

    @router.get('/api/dispatch')
    def snapshot():
        with db() as connection:
            ensure_dispatch_schema(connection)
            if not connection.in_transaction:
                connection.execute('BEGIN')  # Read all panels from one consistent snapshot.
            network, revision = load(connection)
            incidents = [dict(json.loads(row[2]), id=row[0], shipment_id=row[1],
                              status=row[3], version=row[4])
                         for row in connection.execute(
                             'SELECT id,shipment_id,payload,status,version FROM incidents ORDER BY rowid DESC')]
            return {
                'network_revision': revision,
                'lots': network['lots'],
                'incidents': incidents,
                'assignments': _assignments(connection),
                'mode': 'local simulated workflow; dispatcher identity is self-declared',
            }

    @router.post('/api/dispatch/incidents/{incident_id}/review')
    def review_incident(incident_id: str, request: IncidentReview):
        with db() as connection:
            _begin(connection)
            row = connection.execute(
                'SELECT payload,status,version,shipment_id FROM incidents WHERE id=?',
                (incident_id,),
            ).fetchone()
            if not row:
                raise HTTPException(404, 'Unknown incident')
            if row[2] != request.expected_version:
                raise HTTPException(409, 'Incident changed; refresh before reviewing')
            if row[1] == 'resolved' or row[1] == request.status:
                raise HTTPException(409, 'Incident is already resolved or already has this status')
            payload = json.loads(row[0])
            payload['review'] = {
                'actor': request.actor, 'reason': request.reason,
                'reviewed_at': now(), 'status': request.status,
            }
            connection.execute(
                'UPDATE incidents SET payload=?,status=?,version=? WHERE id=?',
                (json.dumps(payload), request.status, row[2] + 1, incident_id),
            )
            record(connection, request.actor, 'incident_review', {
                **request.model_dump(), 'incident_id': incident_id, 'shipment_id': row[3],
                'version': row[2] + 1,
            })
            return dict(payload, id=incident_id, shipment_id=row[3],
                        status=request.status, version=row[2] + 1)

    def change_hold(lot_id, request, held):
        with db() as connection:
            _begin(connection)
            network, revision = load(connection)
            if revision != request.expected_network_revision:
                raise HTTPException(409, 'Network changed; refresh before deciding')
            lot = next((lot for lot in network['lots'] if lot['id'] == lot_id), None)
            if not lot:
                raise HTTPException(404, 'Unknown lot')
            if not held and lot.get('recalled'):
                raise HTTPException(409, 'A recalled lot cannot be released by a precautionary hold decision')
            if bool(lot.get('held')) == held:
                raise HTTPException(409, 'Lot already has this hold status')
            lot['held'] = held
            lot['hold_review'] = {
                'actor': request.actor, 'reason': request.reason,
                'reviewed_at': now(), 'held': held,
            }
            removed = []
            if held:
                for assignment in _assignments(connection):
                    if assignment['lot_id'] == lot_id:
                        connection.execute('DELETE FROM assignments WHERE id=?', (assignment['id'],))
                        removed.append(assignment['id'])
            connection.execute('UPDATE state SET payload=?,revision=? WHERE id=1',
                               (json.dumps(network), revision + 1))
            record(connection, request.actor, 'lot_hold' if held else 'lot_release', {
                **request.model_dump(), 'lot_id': lot_id, 'held': held,
                'network_revision': revision + 1, 'invalidated_shipments': removed,
            })
            return {'lot_id': lot_id, 'held': held, 'network_revision': revision + 1,
                    'invalidated_shipments': removed,
                    'assignments_republished': False}

    @router.post('/api/dispatch/lots/{lot_id}/hold')
    def hold_lot(lot_id: str, request: LotDecision):
        return change_hold(lot_id, request, True)

    @router.post('/api/dispatch/lots/{lot_id}/release')
    def release_lot(lot_id: str, request: LotDecision):
        return change_hold(lot_id, request, False)

    @router.post('/api/dispatch/assignments/{shipment_id}/instruction')
    def issue_instruction(shipment_id: str, request: InstructionDecision):
        with db() as connection:
            _begin(connection)
            network, revision = load(connection)
            if revision != request.expected_network_revision:
                raise HTTPException(409, 'Network changed; refresh before issuing an instruction')
            row = connection.execute('SELECT payload FROM assignments WHERE id=?', (shipment_id,)).fetchone()
            if not row:
                raise HTTPException(404, 'No approved assignment')
            assignment = json.loads(row[0])
            if assignment.get('instruction_revision', 0) != request.expected_instruction_revision:
                raise HTTPException(409, 'Instruction changed; refresh before issuing another')
            lot = next((lot for lot in network['lots'] if lot['id'] == assignment['lot_id']), None)
            truck = next((truck for truck in network['trucks'] if truck['id'] == assignment['truck_id']), None)
            if not lot or lot.get('held') or lot.get('recalled') or not lot.get('eligible', True):
                raise HTTPException(409, 'Assigned lot is unavailable, held, recalled or ineligible')
            if not truck or not truck.get('eligible', True) or not truck.get('refrigerated', False):
                raise HTTPException(409, 'Assigned truck is not eligible for refrigerated cargo')
            if assignment['quantity_kg'] > min(lot['inventory_kg'], truck['capacity_kg']):
                raise HTTPException(409, 'Assigned stock or truck capacity is no longer sufficient')
            previous = connection.execute(
                'SELECT version FROM dispatch_instruction_versions WHERE shipment_id=?',
                (shipment_id,),
            ).fetchone()
            next_revision = max(previous[0] if previous else 0,
                                assignment.get('instruction_revision', 0)) + 1
            connection.execute(
                'INSERT INTO dispatch_instruction_versions VALUES (?,?) '
                'ON CONFLICT(shipment_id) DO UPDATE SET version=excluded.version',
                (shipment_id, next_revision),
            )
            assignment.update(
                instruction=request.instruction,
                instruction_revision=next_revision,
                instruction_acknowledged=False,
                instruction_actor=request.actor,
                instruction_reason=request.reason,
                instruction_issued_at=now(),
            )
            connection.execute('UPDATE assignments SET payload=? WHERE id=?',
                               (json.dumps(assignment), shipment_id))
            record(connection, request.actor, 'dispatcher_instruction', {
                **request.model_dump(), 'shipment_id': shipment_id,
                'instruction_revision': next_revision,
            })
            return {'shipment_id': shipment_id, 'instruction': request.instruction,
                    'instruction_revision': next_revision,
                    'instruction_acknowledged': False}

    @router.post('/api/driver/{shipment_id}/instruction-ack')
    def acknowledge_instruction(shipment_id: str, request: InstructionAcknowledgment):
        with db() as connection:
            _begin(connection)
            row = connection.execute('SELECT payload FROM assignments WHERE id=?', (shipment_id,)).fetchone()
            if not row:
                raise HTTPException(404, 'No approved assignment')
            assignment = json.loads(row[0])
            if assignment.get('instruction_revision', 0) != request.instruction_revision:
                raise HTTPException(409, 'Instruction changed; read the current instruction before acknowledging')
            if assignment.get('instruction_acknowledged'):
                return {'status': 'already acknowledged', 'instruction_revision': request.instruction_revision}
            assignment['instruction_acknowledged'] = True
            assignment['instruction_acknowledged_at'] = now()
            connection.execute('UPDATE assignments SET payload=? WHERE id=?',
                               (json.dumps(assignment), shipment_id))
            record(connection, 'simulated driver', 'instruction_acknowledge', {
                'shipment_id': shipment_id, 'instruction_revision': request.instruction_revision,
            })
            return {'status': 'acknowledged', 'instruction_revision': request.instruction_revision}

    return router
