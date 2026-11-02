"""Iowa DOT's public 511 point-event layer, separate from Missouri evidence.

The original records and response envelopes are retained. Point proximity does
not establish closure extent, current passability or commercial-truck safety.
"""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import math
import time
from urllib.parse import urlencode

from backend.adapters import CachedHTTP


IOWA_DOT_BASE = ('https://services.arcgis.com/8lRhdTsQyJpO52F1/arcgis/rest/'
                 'services/CARS511_Iowa_View/FeatureServer/0')
IOWA_DOT_DOCUMENTATION = 'https://iowadot.gov/travel-tools/iowa-511/511-data-feeds'
IOWA_DOT_ITEM = 'https://www.arcgis.com/sharing/rest/content/items/5e924db11ba94ce4bda1b38dfe0cdcdf?f=pjson'
IOWA_DOT_METADATA_URL = IOWA_DOT_BASE + '?f=json'
IOWA_DOT_IDS_URL = IOWA_DOT_BASE + '/query?where=1%3D1&returnIdsOnly=true&f=json'
IOWA_DOT_QUERY_URL = IOWA_DOT_BASE + '/query?where=1%3D1&outFields=*&outSR=4326&f=geojson&resultRecordCount=1'

IOWA_LIMITATIONS = (
    'Iowa DOT 511 point events only; winter road conditions and local roads are not fully covered. '
    'A complete object-ID query is not complete real-world road coverage. '
    'Repeated CARS event IDs may describe duplicate records; original point records are preserved. '
    'Point proximity does not describe a closure extent, direction or affected carriageway. '
    'Raw issue/expiry/update clock strings have no verified time zone and are not converted to UTC. '
    'EditDate is a provider record-edit timestamp, not a verified event observation or expiry. '
    'Queries are not an atomic provider snapshot; events can change between requests. '
    'No assertion of road clearance, live closure avoidance or commercial-truck suitability.'
)


def _payload(response, name):
    payload = response.get('payload')
    if not isinstance(payload, dict):
        raise ValueError(f'Iowa DOT {name}: expected an object response')
    if 'error' in payload:
        raise ValueError(f'Iowa DOT {name}: ArcGIS error {payload["error"]}')
    try:
        json.dumps(payload, allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise ValueError(f'Iowa DOT {name}: response is not finite JSON: {exc}') from exc
    return payload


def _instant(value):
    if not isinstance(value, str):
        return None
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return result.astimezone(timezone.utc) if result.tzinfo else None
    except ValueError:
        return None


def _valid_point(geometry):
    if not isinstance(geometry, dict) or geometry.get('type') != 'Point':
        return False
    coords = geometry.get('coordinates')
    return (isinstance(coords, list) and len(coords) >= 2
            and all(isinstance(v, (int, float)) and not isinstance(v, bool)
                    and math.isfinite(v) for v in coords[:2])
            and -180 <= coords[0] <= 180 and -90 <= coords[1] <= 90)


def normalize_iowa(metadata, ids_response, pages, *, max_records=2000):
    """Validate envelopes and retain all original data; screen only valid points.

    ``pages`` contains successfully decoded CachedHTTP envelopes. Failed page
    requests are attached by the adapter as explicit layer failures afterwards.
    No missing record or date is replaced by an invented value.
    """
    meta = _payload(metadata, 'metadata')
    identity = _payload(ids_response, 'object-ID inventory')
    fields = {field.get('name'): field.get('type') for field in meta.get('fields', [])
              if isinstance(field, dict)}
    if (meta.get('geometryType') != 'esriGeometryPoint'
            or meta.get('objectIdField') != 'OBJECTID'
            or not {'OBJECTID', 'ID', 'Route', 'headline', 'EditDate'} <= fields.keys()
            or fields['EditDate'] != 'esriFieldTypeDate'):
        raise ValueError('Iowa DOT metadata: expected point-event fields OBJECTID, ID, Route, headline and date EditDate')
    native = meta.get('spatialReference', {})
    if not isinstance(native, dict) or not ({native.get('wkid'), native.get('latestWkid')} & {3857, 102100}):
        raise ValueError('Iowa DOT metadata: unexpected native coordinate reference system; expected Web Mercator')
    time_reference = meta.get('dateFieldsTimeReference') or {}
    if not isinstance(time_reference, dict) or time_reference.get('timeZone') not in {'UTC', 'Etc/UTC'}:
        raise ValueError('Iowa DOT metadata: date-field timezone is not verified as UTC')
    object_ids = identity.get('objectIds')
    if (identity.get('objectIdFieldName') != 'OBJECTID' or not isinstance(object_ids, list)
            or any(not isinstance(i, int) or isinstance(i, bool) or i < 0 for i in object_ids)
            or len(object_ids) != len(set(object_ids))):
        raise ValueError('Iowa DOT object-ID inventory: expected unique nonnegative integer OBJECTID values')
    selected_ids = set(sorted(object_ids)[:max_records])
    records = []
    invalid_geometry = []
    received_ids = []
    event_ids = []
    edit_instants = []
    page_issues = []
    for page in pages:
        body = _payload(page, 'event page')
        if body.get('type') != 'FeatureCollection' or not isinstance(body.get('features'), list):
            raise ValueError('Iowa DOT event page: expected a GeoJSON FeatureCollection')
        crs = body.get('crs')
        if crs is not None:
            if (not isinstance(crs, dict) or crs.get('type') != 'name'
                    or crs.get('properties', {}).get('name') not in
                    {'EPSG:4326', 'urn:ogc:def:crs:OGC:1.3:CRS84', 'urn:ogc:def:crs:EPSG::4326'}):
                raise ValueError('Iowa DOT event page: unexpected returned coordinate reference system')
        if body.get('exceededTransferLimit') or body.get('properties', {}).get('exceededTransferLimit'):
            page_issues.append('Provider marked an event page exceededTransferLimit')
        if len(records) + len(body['features']) > max_records:
            raise ValueError('Iowa DOT event pages exceeded the configured record bound')
        for feature in body['features']:
            if not isinstance(feature, dict) or feature.get('type') != 'Feature' or not isinstance(feature.get('properties'), dict):
                raise ValueError('Iowa DOT event page: malformed feature or properties')
            properties = feature['properties']
            object_id = properties.get('OBJECTID')
            if not isinstance(object_id, int) or isinstance(object_id, bool) or object_id not in selected_ids:
                raise ValueError('Iowa DOT event page: unexpected OBJECTID outside the bounded inventory')
            if object_id in received_ids:
                raise ValueError('Iowa DOT event page: duplicate OBJECTID; snapshot cannot be safely combined')
            received_ids.append(object_id)
            event_id = properties.get('ID')
            if isinstance(event_id, str) and event_id:
                event_ids.append(event_id)
            edit = properties.get('EditDate')
            if isinstance(edit, (int, float)) and not isinstance(edit, bool) and math.isfinite(edit):
                try:
                    edit_instants.append(datetime.fromtimestamp(edit / 1000, timezone.utc))
                except (ValueError, OverflowError, OSError):
                    pass
            clean = deepcopy(feature)
            if not _valid_point(feature.get('geometry')):
                invalid_geometry.append(object_id)
                # Original invalid geometry remains in source_pages. A null here
                # prevents downstream proximity code from treating it as valid.
                clean['geometry'] = None
            records.append(clean)
    missing_ids = sorted(selected_ids - set(received_ids))
    truncated = len(object_ids) > max_records
    if missing_ids:
        page_issues.append(f'{len(missing_ids)} inventoried OBJECTIDs were not returned; the provider may have changed or a page failed')
    if truncated:
        page_issues.append(f'Bounded query returned at most {max_records} of {len(object_ids)} inventoried records')
    if invalid_geometry:
        page_issues.append(f'{len(invalid_geometry)} records have absent/invalid point geometry and cannot be screened')
    responses = [ids_response, *pages]
    instants = [_instant(response.get('retrieved_at')) for response in responses]
    all_responses = [metadata, *responses]
    timestamp_problem = any(instant is None or instant > datetime.now(timezone.utc) + timedelta(minutes=5)
                            for instant in instants)
    stale = any(response.get('stale', False) for response in all_responses) or timestamp_problem
    errors = [response['refresh_error'] for response in all_responses if response.get('refresh_error')]
    oldest = min((instant for instant in instants if instant is not None), default=None)
    if timestamp_problem:
        page_issues.append('A source retrieval timestamp is missing, invalid, in the future or has no timezone')
    payload = {'type': 'FeatureCollection', 'features': records}
    duplicate_ids = {event_id: count for event_id, count in Counter(event_ids).items() if count > 1}
    return {
        'provider': 'Iowa Department of Transportation', 'state': 'IA',
        'source_url': IOWA_DOT_BASE, 'documentation_url': IOWA_DOT_DOCUMENTATION,
        'retrieved_at': oldest.isoformat() if oldest else None,
        'cache': all(response.get('cache', False) for response in all_responses),
        'stale': stale, 'refresh_error': '; '.join(errors) or None,
        'payload': meta, 'source_metadata': deepcopy(metadata),
        'source_inventory': deepcopy(ids_response), 'source_pages': deepcopy(pages),
        'incident_layers': [{
            'layer_id': 0, 'layer_name': 'Iowa DOT 511 point events',
            'source_url': IOWA_DOT_BASE, 'retrieved_at': oldest.isoformat() if oldest else None,
            'payload': payload, 'stale': stale,
        }],
        'layer_failures': [],
        'coverage_complete': not (missing_ids or truncated or invalid_geometry or page_issues),
        'coverage_warning': ('; '.join(page_issues) + '. ' if page_issues else '') + IOWA_LIMITATIONS,
        'provenance': 'official Iowa DOT 511 point-event records; independent road evidence',
        'geographic_scope': 'Iowa; queried 511 event layer only',
        'native_coordinate_reference': 'EPSG:3857 (ArcGIS 102100)',
        'returned_coordinate_reference': 'EPSG:4326 longitude, latitude; explicitly requested outSR=4326',
        'provider_latest_record_edit_at': max(edit_instants).isoformat() if edit_instants else None,
        'provider_time_warning': 'EditDate is an ArcGIS record edit in epoch milliseconds; other event time strings retain an unverified timezone.',
        'attribution': 'Iowa Department of Transportation - Office of Traffic Operations; CC BY 4.0; Iowa GIS and 511 data terms apply.',
        'license_url': 'https://creativecommons.org/licenses/by/4.0/',
        'terms_url': 'https://iowadot.gov/policies_and_statements/511-data-feed-terms-and-conditions',
        'query_summary': {
            'inventoried_records': len(object_ids), 'returned_records': len(records),
            'screenable_records': len(records) - len(invalid_geometry),
            'missing_object_ids': missing_ids, 'invalid_geometry_object_ids': invalid_geometry,
            'duplicate_cars_event_ids': duplicate_ids, 'pages': len(pages),
            'max_records': max_records, 'truncated': truncated,
            'atomic_provider_snapshot': False,
        },
    }


class IowaDOTAdapter(CachedHTTP):
    """Bounded, cached official 511 queries; offline guard is inherited unchanged."""
    # Larger percent-encoded OBJECTID lists exceeded the provider's GET URL
    # limit in a real probe; small pages keep requests below that observed limit.
    PAGE_SIZE = 100
    MAX_RECORDS = 2000

    def fetch(self):
        metadata = self.get(IOWA_DOT_METADATA_URL, 86400)
        inventory = self.get(IOWA_DOT_IDS_URL, 600)
        # Validate discovery before making event requests. An empty page list
        # intentionally reports missing records but still validates the schema.
        normalize_iowa(metadata, inventory, [], max_records=self.MAX_RECORDS)
        selected = sorted(inventory['payload']['objectIds'])[:self.MAX_RECORDS]
        pages, failures = [], []
        for start in range(0, len(selected), self.PAGE_SIZE):
            if start:
                time.sleep(.2)
            chunk = selected[start:start + self.PAGE_SIZE]
            params = dict(objectIds=','.join(map(str, chunk)), outFields='*', outSR=4326,
                          f='geojson', resultRecordCount=self.PAGE_SIZE)
            url = IOWA_DOT_BASE + '/query?' + urlencode(params)
            try:
                response = self.get(url, 600)
                _payload(response, 'event page')
                pages.append(response)
            except Exception as exc:
                failures.append({'layer_id': 0, 'page_start': start,
                                 'error': f'{type(exc).__name__}: {exc}'})
        result = normalize_iowa(metadata, inventory, pages, max_records=self.MAX_RECORDS)
        result['layer_failures'] = failures
        if failures:
            result['coverage_complete'] = False
            result['coverage_warning'] = f'{len(failures)} event page requests failed. ' + result['coverage_warning']
            result['refresh_error'] = '; '.join(filter(None, [result['refresh_error'], *[f['error'] for f in failures]]))
        return result
