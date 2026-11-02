"""Read-only, separately attributed road-feed exploration and route comparisons."""
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Literal
from typing import Annotated

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.adapters import MoDOTAdapter, OSRMRoutingAdapter, distance, now
from backend.paths import ROOT, read_json, write_json
from backend.road_geometry import road_geometry
from backend.route_review import review_routes
from backend.runtime import require_valid_runtime

SOURCES = {
    'modot': {
        'name': 'MoDOT traveler information', 'provider': 'Missouri Department of Transportation',
        'state': 'MO', 'ttl': 300,
        'source_url': 'https://mapping.modot.mo.gov/arcgis/rest/services/TravelerInformation/TravelerInformationData/MapServer',
    },
    'iowa_dot': {
        'name': 'Iowa DOT 511 events', 'provider': 'Iowa Department of Transportation',
        'state': 'IA', 'ttl': 600,
        'source_url': 'https://services.arcgis.com/8lRhdTsQyJpO52F1/arcgis/rest/services/CARS511_Iowa_View/FeatureServer',
    },
}
EXAMPLES = [
    {'id': 'missouri', 'name': 'Columbia, MO to St. Louis, MO',
     'origin': [-92.3341, 38.9517], 'destination': [-90.1994, 38.6270]},
    {'id': 'iowa-corridor', 'name': 'Columbia, MO to Des Moines, IA (planning example)',
     'origin': [-92.3341, 38.9517], 'destination': [-93.6250, 41.5868]},
]
LIMITATIONS = [
    'Planning only. This workspace does not change shipments, assignments, inventory, holds or dispatcher approvals.',
    'These are separate Missouri and Iowa feeds. State-boundary containment and complete end-to-end route coverage are not established; other states are not covered.',
    'Proximity can include parallel roads and repeated point/line records. Zero nearby records does not mean a road is clear or an alternative is eligible.',
    'OSRM ordinary driving routes do not incorporate these closures or validate commercial vehicle restrictions. Every alternative requires dispatcher and truck-route review.',
    'Estimated routes are straight-line visualizations with distance factor 1.25 at 65 km/h; proximity against them is illustrative, not road-level closure screening.',
    'Provider event time strings retain their original values. Unverified time zones and missing geometry are not inferred. Feed retrieval time is distinct from event time.',
]
MAX_FEED_BYTES = 32 * 1024 * 1024
MAX_EVENTS = 10000
MAX_LISTED_EVENTS = 200
MAX_LISTED_HITS = 100


class RoadComparison(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    origin: tuple[Annotated[float, Field(strict=True)], Annotated[float, Field(strict=True)]]
    destination: tuple[Annotated[float, Field(strict=True)], Annotated[float, Field(strict=True)]]
    routing: Literal['estimated', 'osrm'] = 'estimated'
    buffer_m: int = Field(default=250, ge=50, le=2000, strict=True)

    @model_validator(mode='after')
    def valid_coordinates(self):
        OSRMRoutingAdapter.validate([self.origin, self.destination])
        if distance(self.origin, self.destination) < 1:
            raise ValueError('Choose distinct origin and destination coordinates at least one meter apart')
        return self


def _age(value):
    try:
        instant = datetime.fromisoformat(value)
        if instant.tzinfo is None:
            return None
        seconds = (datetime.now(timezone.utc) - instant).total_seconds()
        return seconds if math.isfinite(seconds) and seconds >= -60 else None
    except (ValueError, TypeError, OverflowError):
        return None


def _text(properties, *keys, default=''):
    for key in keys:
        value = properties.get(key)
        if isinstance(value, (str, int, float)) and not isinstance(value, bool) and str(value).strip():
            return str(value)[:4000]
    return default


def _event(source_id, layer, feature, index):
    """Keep raw properties; normalized display fields are not new source observations."""
    props = feature.get('properties') if isinstance(feature.get('properties'), dict) else {}
    provider_id = feature.get('id')
    if provider_id is None:
        provider_id = props.get('OBJECTID', props.get('OBJECT_ID'))
    derived_id = provider_id is None
    identifier = str(provider_id) if not derived_id else f'row-{index}'
    return {
        'id': f"{source_id}:{layer.get('layer_id', 'unknown')}:{identifier}",
        'provider_id': provider_id, 'derived_id': derived_id, 'source_id': source_id,
        'title': _text(props, 'EventType', 'EVENTTYPE', 'TYPE_CODE', 'headline', 'Headline',
                       'Description', 'description', default=layer.get('layer_name', 'Road event')),
        'description': _text(props, 'EXT_COMMENT', 'Description', 'description', 'Headline', 'headline'),
        'route_name': _text(props, 'ROUTE', 'RoadwayName', 'Roadway', 'Route', 'RouteName') or None,
        # Provider dates are retained without guessing a timezone or parsing local strings.
        'updated_at': None, 'starts_at': None, 'ends_at': None,
        'provider_times': {key: props[key] for key in (
            'IssueDate', 'ExpireDate', 'UpdateDate', 'START_DATE', 'END_DATE', 'LAST_CHANGED_DATE'
        ) if key in props},
        'geometry': road_geometry(feature.get('geometry')), 'properties': props,
        'layer_id': layer.get('layer_id'), 'layer_name': layer.get('layer_name', 'Road events'),
    }


def normalize_source(source_id, wrapper, *, fixture=False, error=None, limit=MAX_LISTED_EVENTS):
    """Return public metadata and all bounded events for server-side screening."""
    config = SOURCES[source_id]
    result = dict(config, id=source_id, available=False, fixture=fixture, stale=True,
                  retrieved_at=None, coverage_complete=False, event_count=0,
                  unusable_geometry_count=0, returned_event_count=0, events_truncated=False,
                  error=error, warning='No usable captured response; road coverage is unavailable.', events=[])
    result.pop('ttl')
    if not isinstance(wrapper, dict):
        return result, []
    layers = wrapper.get('incident_layers')
    if not isinstance(layers, list) or not layers:
        result['error'] = error or 'Captured response has no supported incident_layers array'
        return result, []
    events, schema_errors = [], []
    for layer in layers:
        if not isinstance(layer, dict):
            schema_errors.append('Invalid layer wrapper')
            continue
        payload = layer.get('payload')
        rows = payload.get('features') if isinstance(payload, dict) else None
        if not isinstance(rows, list) or payload.get('type') != 'FeatureCollection':
            schema_errors.append(f"Layer {layer.get('layer_id')}: expected GeoJSON FeatureCollection")
            continue
        if len(rows) + len(events) > MAX_EVENTS:
            schema_errors.append(f'Feed exceeds the {MAX_EVENTS}-record inspection bound; excess rows not inspected')
            rows = rows[:max(0, MAX_EVENTS - len(events))]
        for index, feature in enumerate(rows):
            if not isinstance(feature, dict):
                feature = {}
            events.append(_event(source_id, layer, feature, index))
    # IDs are row identities, not deduplication keys. Preserve repeated source records.
    seen = {}
    for event in events:
        identifier = event['id']
        seen[identifier] = seen.get(identifier, 0) + 1
        if seen[identifier] > 1:
            event['id'] = f"{identifier}:duplicate-row-{seen[identifier]}"
    invalid = sum(event['geometry'] is None for event in events)
    age = _age(wrapper.get('retrieved_at'))
    layer_stale = any(not isinstance(layer, dict) or layer.get('stale', False)
                      or _age(layer.get('retrieved_at', wrapper.get('retrieved_at'))) is None
                      or (_age(layer.get('retrieved_at', wrapper.get('retrieved_at'))) or 0) > config['ttl']
                      for layer in layers)
    refresh_error = error or wrapper.get('refresh_error')
    warning = str(wrapper.get('coverage_warning') or 'Coverage is limited to captured provider layers.')
    if invalid:
        warning += f' {invalid} records lack supported finite point/line geometry and cannot be screened.'
    if schema_errors:
        warning += ' ' + '; '.join(schema_errors)
    stale = (fixture or bool(wrapper.get('stale')) or age is None or age > config['ttl']
             or layer_stale or bool(refresh_error))
    result.update(available=not schema_errors or bool(events), retrieved_at=wrapper.get('retrieved_at'),
                  stale=stale, error=refresh_error,
                  coverage_complete=bool(wrapper.get('coverage_complete')) and not invalid and not schema_errors,
                  event_count=len(events), unusable_geometry_count=invalid,
                  returned_event_count=min(len(events), limit), events_truncated=len(events) > limit,
                  warning=warning, events=events[:limit], age_seconds=age,
                  cache=bool(wrapper.get('cache')),
                  attribution=wrapper.get('attribution'), license_url=wrapper.get('license_url'),
                  terms_url=wrapper.get('terms_url'),
                  provider_latest_record_edit_at=wrapper.get('provider_latest_record_edit_at'),
                  provider_time_warning=wrapper.get('provider_time_warning'),
                  query_summary=wrapper.get('query_summary'))
    return result, events


def create_road_intelligence_router(db_path, root=ROOT):
    router = APIRouter()
    refresh_lock = Lock()

    def workspace():
        return Path(root() if callable(root) else root)

    def runtime():
        return require_valid_runtime(db_path() if callable(db_path) else db_path, root=workspace())

    def bounded_json(path):
        with path.open('rb') as stream:
            body=stream.read(MAX_FEED_BYTES+1)
        if len(body) > MAX_FEED_BYTES:
            raise ValueError('Captured road response exceeds the 32 MiB read bound')
        def invalid_constant(value):
            raise ValueError(f'Captured road response contains a nonfinite JSON value: {value}')
        return json.loads(body,parse_constant=invalid_constant)

    def snapshot():
        context = runtime()
        offline = bool(context['isolated'] and context['offline'])
        statuses = {}
        status_path = workspace() / 'data/cache/road_refresh_status.json'
        if not offline and status_path.exists():
            try:
                value = bounded_json(status_path)
                statuses = value if isinstance(value, dict) else {}
            except (OSError, ValueError, TypeError):
                pass
        sources, all_events = [], {}
        for source_id in SOURCES:
            fixture = workspace() / f'data/fixtures/{source_id}.json'
            cache = workspace() / f'data/cache/probe_{source_id}.json'
            selected = fixture if offline or not cache.exists() else cache
            wrapper, failure = None, None
            if selected.exists():
                try:
                    wrapper = bounded_json(selected)
                    if not isinstance(wrapper, dict) or not isinstance(wrapper.get('incident_layers'), list):
                        raise ValueError('Captured response is not a supported road-feed wrapper')
                except (OSError, ValueError, TypeError) as error:
                    failure = f'{type(error).__name__}: {error}'
                    if selected == cache and fixture.exists():
                        try:
                            wrapper = bounded_json(fixture)
                            selected = fixture
                        except (OSError, ValueError, TypeError) as fixture_error:
                            failure += f'; fixture: {type(fixture_error).__name__}: {fixture_error}'
                            wrapper = None
            attempt = statuses.get(source_id, {})
            failure = failure or (attempt.get('error') if isinstance(attempt, dict) else None)
            public, events = normalize_source(source_id, wrapper, fixture=selected == fixture, error=failure)
            if isinstance(attempt, dict) and attempt:
                public['last_refresh_attempt'] = attempt
            sources.append(public)
            all_events[source_id] = events
        return {'generated_at': now(), 'offline': offline, 'sources': sources,
                'examples': EXAMPLES, 'limitations': LIMITATIONS}, all_events

    @router.get('/api/road-intelligence')
    def get_snapshot():
        return snapshot()[0]

    @router.post('/api/road-intelligence/refresh')
    def refresh():
        context = runtime()
        if context['isolated'] and context['offline']:
            raise HTTPException(403, 'Offline rehearsal uses dated road fixtures; provider refresh is disabled')
        if not refresh_lock.acquire(blocking=False):
            raise HTTPException(409, 'A road-feed refresh is already running; wait for its result')
        try:
            from backend.state_dot import IowaDOTAdapter
            statuses = {}
            for source_id, adapter in (('modot', MoDOTAdapter), ('iowa_dot', IowaDOTAdapter)):
                try:
                    result = adapter().fetch()
                    public, _ = normalize_source(source_id, result)
                    if not public['available']:
                        raise ValueError(public['error'] or public['warning'])
                    write_json(workspace() / f'data/cache/probe_{source_id}.json', result)
                    statuses[source_id] = {'attempted_at': now(), 'error': result.get('refresh_error'),
                                           'new_provider_response': not result.get('cache', False),
                                           'cache': bool(result.get('cache')), 'stale': public['stale']}
                except Exception as error:
                    statuses[source_id] = {'attempted_at': now(), 'error': f'{type(error).__name__}: {error}',
                                           'new_provider_response': False, 'stale': True}
            write_json(workspace() / 'data/cache/road_refresh_status.json', statuses)
            return snapshot()[0]
        finally:
            refresh_lock.release()

    @router.post('/api/road-intelligence/compare')
    def compare(request: RoadComparison):
        public, events = snapshot()
        coordinates = [request.origin, request.destination]
        if request.routing == 'osrm':
            routing = OSRMRoutingAdapter().route(coordinates, alternatives=True)
        else:
            meters = distance(*coordinates) * 1.25
            routing = {'fallback': True, 'provenance': 'Estimated travel; requested planning estimate',
                       'payload': {'routes': [{'geometry': {'type': 'LineString', 'coordinates': coordinates},
                                               'distance': meters, 'duration': meters / (65000 / 3600)}]}}
        rows = routing.get('payload', {}).get('routes', [])
        if not isinstance(rows, list) or not 1 <= len(rows) <= 10:
            raise HTTPException(502, 'Routing response must contain between one and ten alternatives')
        # Reject malformed route output rather than drawing an invented replacement.
        for row in rows:
            geom = road_geometry(row.get('geometry')) if isinstance(row, dict) else None
            if not geom or geom['type'] != 'LineString' or any(
                    not isinstance(row.get(key), (int, float)) or isinstance(row.get(key), bool)
                    or not math.isfinite(row[key]) or row[key] < 0 for key in ('distance', 'duration')):
                raise HTTPException(502, 'Routing response has invalid geometry, distance or duration')
        alternatives = [dict(index=index, distance_m=row['distance'], duration_seconds=row['duration'],
                             geometry=road_geometry(row['geometry']), fallback=bool(routing.get('fallback')),
                             review_required=True, reviews=[]) for index, row in enumerate(rows)]
        for source in public['sources']:
            source_events = events[source['id']]
            lookup = {event['id']: event for event in source_events}
            feed = {'retrieved_at': source['retrieved_at'], 'stale': source['stale'],
                    'coverage_complete': source['coverage_complete'], 'incident_layers': []}
            if source['available']:
                feed['incident_layers'] = [{'layer_id': source['id'], 'layer_name': source['name'],
                    'payload': {'features': [{'geometry': event['geometry'],
                                              'properties': {'aegis_event_id': event['id']}}
                                             for event in source_events]}}]
            screened = review_routes(routing, feed, request.buffer_m)
            for alternative, result in zip(alternatives, screened['alternatives']):
                hits = [dict(lookup[hit['properties']['aegis_event_id']], proximity_m=hit['proximity_m'])
                        for hit in result['nearby_events']]
                alternative['reviews'].append({
                    'source_id': source['id'], 'source_name': source['name'],
                    'coverage_complete': source['coverage_complete'], 'stale': source['stale'],
                    'nearby_events': hits[:MAX_LISTED_HITS], 'nearby_event_count': len(hits),
                    'hits_truncated': len(hits) > MAX_LISTED_HITS,
                    'unusable_geometry_count': source['unusable_geometry_count'],
                })
        return {'compared_at': now(), 'request': request.model_dump(mode='json'),
                'sources': public['sources'], 'alternatives': alternatives, 'limitations': LIMITATIONS,
                'routing_provenance': routing.get('provenance'), 'routing_error': routing.get('error'),
                'routing_retrieved_at': routing.get('retrieved_at'),
                'routing_stale': bool(routing.get('stale')), 'routing_cache': bool(routing.get('cache')),
                'routing_refresh_error': routing.get('refresh_error'),
                'offline': public['offline'], 'operational_state_modified': False}

    return router
