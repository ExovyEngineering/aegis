"""Local Drive snapshots and a parked-attestation interaction gate.

Fuel/position have no GPS, vehicle-speed or physical-sensor connection. A parked
declaration is self-reported and expires after ten minutes; it cannot prove a
vehicle is stopped or prevent interaction with another application. Optional
freshness-review metadata refers to the separate declared replay/gateway workflow,
not independently verified physical sensing.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator

from backend.readiness import freshness_review_records

PARKED_WINDOW_SECONDS = 600
SCENARIO_OBSERVED_AT = '2026-10-26T08:00:00-05:00'
FOCUS_PROVENANCE = (
    'Self-declared parked confirmation in a local simulated application; '
    'no vehicle-motion sensing or operating-system distraction prevention.'
)
VEHICLE_PROVENANCE = (
    'DETERMINISTIC SIMULATION: fuel level, tank size and consumption are scenario '
    'assumptions. Position is a dispatch-origin reference, not live GPS. '
    'These values do not advance as a trip proceeds.'
)


def _utc_now():
    """Separate clock makes expiration independently testable."""
    return datetime.now(timezone.utc)


def ensure_drive_schema(connection):
    connection.execute(
        'CREATE TABLE IF NOT EXISTS driver_focus ('
        'truck_id TEXT PRIMARY KEY, '
        "mode TEXT NOT NULL CHECK(mode IN ('parked','driving')), "
        'version INTEGER NOT NULL CHECK(version >= 1), '
        'parked_until TEXT, updated_at TEXT NOT NULL)'
    )


def _focus(connection, truck_id, instant=None):
    instant = instant or _utc_now()
    exists = connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='driver_focus'").fetchone()
    row = connection.execute(
        'SELECT mode,version,parked_until,updated_at FROM driver_focus WHERE truck_id=?',
        (truck_id,),
    ).fetchone() if exists else None
    active = False
    if row and row[0] == 'parked' and row[2]:
        try:
            expires = datetime.fromisoformat(row[2])
            active = expires.tzinfo is not None and expires > instant
        except (ValueError, TypeError):
            active = False
    return {
        'mode': 'parked' if active else 'driving' if row and row[0] == 'driving' else 'locked',
        'version': row[1] if row else 0,
        'parked_until': row[2] if row else None,
        'parked_confirmed_at': row[3] if active else None,
        'interaction_allowed': active,
        'expired': bool(row and row[0] == 'parked' and not active),
        'server_time': instant.isoformat(),
        'provenance': FOCUS_PROVENANCE,
    }


def require_parked(connection, truck_id):
    """Call inside the mutation transaction; return active focus or reject it."""
    focus = _focus(connection, truck_id)
    if not focus['interaction_allowed']:
        raise HTTPException(
            423,
            'Drive interactions are locked. Stop safely, then confirm that you are parked; '
            'the confirmation expires after ten minutes.',
        )
    return focus


def _begin(connection):
    ensure_drive_schema(connection)
    if not connection.in_transaction:
        connection.execute('BEGIN IMMEDIATE')


def _truck(network, truck_id):
    truck = next((item for item in network['trucks'] if item['id'] == truck_id), None)
    if not truck:
        raise HTTPException(404, 'Unknown simulated truck')
    return truck


def _assignments(connection, truck_id):
    result = []
    for payload, acknowledged in connection.execute(
        'SELECT payload,acknowledged FROM assignments ORDER BY id'
    ):
        assignment = json.loads(payload)
        if assignment['truck_id'] == truck_id:
            result.append(dict(assignment, acknowledged=bool(acknowledged)))
    return result


def _vehicle(network, truck_id, assignments):
    digest = hashlib.sha256(f"{network['seed']}:{truck_id}:fuel".encode()).digest()
    fuel_percent = 35 + digest[0] % 56
    tank_capacity_liters = 180
    consumption = 28
    fuel_liters = round(tank_capacity_liters * fuel_percent / 100, 1)
    origin_id = assignments[0]['origin'] if assignments else 'DC1'
    origin = next((node for node in network['nodes'] if node['id'] == origin_id), None)
    return {
        'fuel_percent': fuel_percent,
        'fuel_liters': fuel_liters,
        'tank_capacity_liters': tank_capacity_liters,
        'estimated_range_km': round(fuel_liters / consumption * 100, 1),
        'consumption_l_per_100km': consumption,
        'coordinates': list(origin['coordinates']) if origin else None,
        'position_label': (
            f"Simulated dispatch-origin snapshot: {origin['name']}"
            if origin else 'Simulated dispatch origin unavailable'
        ),
        'origin_id': origin_id,
        'observed_at': SCENARIO_OBSERVED_AT,
        'provenance': VEHICLE_PROVENANCE,
        'simulation': True,
    }


class FocusDecision(BaseModel):
    model_config = ConfigDict(extra='forbid')
    mode: Literal['parked', 'driving']
    expected_version: int = Field(ge=0, strict=True)
    parked_confirmation: StrictBool = False

    @model_validator(mode='after')
    def confirm_parked(self):
        if self.mode == 'parked' and not self.parked_confirmation:
            raise ValueError('Explicitly confirm that the vehicle is safely parked')
        return self


class QuickReport(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    shipment_id: str = Field(min_length=1, max_length=100)
    kind: Literal['refrigeration', 'road_delay', 'vehicle_issue', 'cargo_issue']
    expected_network_revision: int | None = Field(default=None, ge=0, strict=True)


QUICK_REPORTS = {
    'refrigeration': 'Refrigeration concern',
    'road_delay': 'Road or delivery delay',
    'vehicle_issue': 'Vehicle concern',
    'cargo_issue': 'Cargo or packaging concern',
}


def create_drive_router(db, load, record):
    router = APIRouter(tags=['AEGIS Drive visual trip and parked-use workflow'])

    @router.get('/api/drive/{truck_id}')
    def snapshot(truck_id: str):
        with db() as connection:
            if not connection.in_transaction:
                connection.execute('BEGIN')
            network, revision = load(connection)
            truck = _truck(network, truck_id)
            assignments = _assignments(connection, truck_id)
            freshness_reviews = freshness_review_records(connection, revision, assignments, _utc_now(), network=network)
            selected_ids = {item['id'] for item in assignments}
            return {
                'truck_id': truck_id,
                'truck': truck,
                'network_revision': revision,
                'focus': _focus(connection, truck_id),
                'assignments': assignments,
                **({'freshness_reviews': freshness_reviews} if freshness_reviews else {}),
                'vehicle': _vehicle(network, truck_id, assignments),
                'events': [item for item in network['events'] if item['shipment_id'] in selected_ids],
                'source': 'Approved local simulated assignments and deterministic scenario telemetry',
                'limitations': [
                    'Parked status is self-declared, expires after ten minutes, and is not inferred from GPS or speed.',
                    'The app interaction gate does not prevent device use outside AEGIS or prove the vehicle is stopped.',
                    'Fuel, consumption, range and dispatch-origin position are simulated. Optional freshness reviews refer to a separate declared replay/gateway context; no physical feed is independently verified.',
                    'Only current approved trips and their simulated events are included. Missing events do not prove real roads are clear.',
                    'Trip acknowledgment and operational review do not certify food safety or authorize an unapproved detour.',
                ],
            }

    @router.post('/api/drive/{truck_id}/focus')
    def focus(truck_id: str, request: FocusDecision):
        with db() as connection:
            _begin(connection)
            network, _ = load(connection)
            _truck(network, truck_id)
            instant = _utc_now()
            current = _focus(connection, truck_id, instant)
            if current['version'] != request.expected_version:
                raise HTTPException(409, 'Drive focus changed; refresh before changing it again')
            version = current['version'] + 1
            parked_until = (
                (instant + timedelta(seconds=PARKED_WINDOW_SECONDS)).isoformat()
                if request.mode == 'parked' else None
            )
            connection.execute(
                'INSERT INTO driver_focus VALUES (?,?,?,?,?) '
                'ON CONFLICT(truck_id) DO UPDATE SET mode=excluded.mode,version=excluded.version,'
                'parked_until=excluded.parked_until,updated_at=excluded.updated_at',
                (truck_id, request.mode, version, parked_until, instant.isoformat()),
            )
            record(connection, 'simulated driver', 'driver_focus', {
                'truck_id': truck_id, 'mode': request.mode, 'version': version,
                'parked_until': parked_until, 'parked_confirmation': request.parked_confirmation,
                'provenance': FOCUS_PROVENANCE,
            })
            return _focus(connection, truck_id, instant)

    @router.post('/api/drive/{truck_id}/quick-report')
    def quick_report(truck_id: str, request: QuickReport):
        with db() as connection:
            _begin(connection)
            network, _ = load(connection)
            _truck(network, truck_id)
            require_parked(connection, truck_id)
            row = connection.execute(
                'SELECT payload FROM assignments WHERE id=?', (request.shipment_id,),
            ).fetchone()
            if not row:
                raise HTTPException(404, 'No approved assignment')
            assignment = json.loads(row[0])
            if assignment['truck_id'] != truck_id:
                raise HTTPException(409, 'The selected trip is not assigned to this truck')
            # Import lazily: dispatch can also import require_parked for its own mutations.
            from backend.dispatch import create_driver_incident
            response = create_driver_incident(
                connection, request.shipment_id,
                QUICK_REPORTS[request.kind] +
                ' reported while parked. Simulated operational quick report; dispatcher review required.',
                record,
                expected_network_revision=request.expected_network_revision,
            )
            record(connection, 'simulated driver', 'driver_quick_report', {
                'truck_id': truck_id, 'shipment_id': request.shipment_id,
                'kind': request.kind, 'incident_id': response['incident_id'],
            })
            return dict(response, truck_id=truck_id, kind=request.kind,
                        provenance='simulated driver report; no external alert or real shipment action')

    return router
