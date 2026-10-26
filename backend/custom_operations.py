"""Bounded user-entered route experiments, separate from dispatch/real traceability."""
import math
from collections import Counter
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.simulation import SEED

Identifier = Annotated[str, Field(min_length=1, max_length=32, pattern=r'^[A-Za-z][A-Za-z0-9_-]*$')]
LotIdentifier = Annotated[str, Field(min_length=1, max_length=48, pattern=r'^[A-Za-z][A-Za-z0-9_-]*$')]
Label = Annotated[str, Field(min_length=1, max_length=120)]
Longitude = Annotated[float, Field(ge=-180, le=180)]
Latitude = Annotated[float, Field(ge=-90, le=90)]
Coordinates = tuple[Longitude, Latitude]


class PlanningInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid', allow_inf_nan=False)


class LocatedInput(PlanningInput):
    id: Identifier
    name: Label
    coordinates: Coordinates

    @field_validator('coordinates', mode='before')
    @classmethod
    def numeric_coordinate_pair(cls, value):
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise ValueError('Coordinates require exactly [longitude, latitude]')
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in value):
            raise ValueError('Longitude and latitude must be finite numeric values')
        return value


class CustomOrigin(LocatedInput):
    kind: Literal['farm', 'dc'] = 'farm'
    inventory_kg: int = Field(ge=0, le=1_000_000, strict=True)


class CustomStop(LocatedInput):
    kind: Literal['destination'] = 'destination'
    demand_kg: int = Field(ge=1, le=5000, strict=True)
    deadline_hours: float = Field(default=6, gt=0, le=16, strict=True)
    shelf_life_hours: float = Field(default=72, gt=0, le=168, strict=True)
    lot_id: LotIdentifier | None = None
    held: bool = Field(default=False, strict=True)
    recalled: bool = Field(default=False, strict=True)
    eligible: bool = Field(default=True, strict=True)

    @property
    def planning_lot_id(self):
        # An explicit planning identifier, never a manufactured observation or recall match.
        return self.lot_id or f'PLAN-{self.id}'


class CustomTruck(PlanningInput):
    id: Identifier
    origin_id: Identifier
    capacity_kg: int = Field(ge=100, le=5000, strict=True)
    refrigerated: bool = Field(default=True, strict=True)
    eligible: bool = Field(default=True, strict=True)


class CustomOperation(PlanningInput):
    name: Label
    description: str = Field(default='User-entered route-planning experiment.', max_length=500)
    origins: list[CustomOrigin] = Field(min_length=1, max_length=3)
    stops: list[CustomStop] = Field(min_length=1, max_length=20)
    trucks: list[CustomTruck] = Field(min_length=1, max_length=10)

    @model_validator(mode='after')
    def unique_entities_and_valid_origins(self):
        identifiers = [entry.id for group in (self.origins, self.stops, self.trucks) for entry in group]
        duplicates = sorted(key for key, count in Counter(identifiers).items() if count > 1)
        if duplicates:
            raise ValueError('Origin, stop and truck IDs must be globally unique: '+', '.join(duplicates))
        origin_ids = {origin.id for origin in self.origins}
        unknown = sorted({truck.origin_id for truck in self.trucks} - origin_ids)
        if unknown:
            raise ValueError('Truck origin_id must reference a listed origin: '+', '.join(unknown))
        lots = [stop.planning_lot_id for stop in self.stops]
        if len(lots) != len(set(lots)):
            raise ValueError('Each delivery needs a distinct planning lot_id; shared-lot stock and traceability are not modeled')
        return self

    def build_operation(self):
        data = self.model_dump(mode='json')
        for stop, model in zip(data['stops'], self.stops):
            stop['lot_id'] = model.planning_lot_id
        data.update(
            id='custom',
            nodes=data['origins']+data['stops'],
            seed=SEED,
            simulation=True,
            provenance='User-entered planning locations, stock, delivery demand, trucks and safety flags; simulated operations, not verified contracts, observations or recall matches.',
            limitations=[
                'Custom locations and safety flags are user-entered planning inputs, not independently verified source evidence.',
                'Generated PLAN-prefixed lot identifiers are fictional planning keys, not actual traceability fields.',
                'Each delivery has a distinct planning lot; shared-lot inventory and real recall matching are not modeled.',
                'The official MoDOT road-incident layer covers Missouri, not every possible custom location.',
            ],
        )
        return data


def build_operation(value: CustomOperation | dict):
    return (value if isinstance(value, CustomOperation) else CustomOperation.model_validate(value)).build_operation()
