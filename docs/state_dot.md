# Iowa DOT road evidence

Added October 28, 2026. This is the first additional state road-event adapter.
It supports a planning question such as a fictional Columbia, Missouri to
Des Moines, Iowa refrigerated trip. These locations do not establish actual
suppliers, customers, transport contracts or shipments.

## Official source and measured acquisition

The [Iowa DOT 511 data-feed page](https://iowadot.gov/travel-tools/iowa-511/511-data-feeds)
links its public ArcGIS feature service and states that credentials are not
required for those feature services. The linked
[Iowa 511 item](https://data.iowadot.gov/datasets/5e924db11ba94ce4bda1b38dfe0cdcdf_0/explore)
was resolved through its actual ArcGIS item metadata, not a similarly named
third-party dataset. The inspected owner was `IowaDOT_SODA`, marked
`public_authoritative`, with Iowa Department of Transportation attribution.

The inspected layer is
[`CARS511_Iowa_View/FeatureServer/0`](https://services.arcgis.com/8lRhdTsQyJpO52F1/arcgis/rest/services/CARS511_Iowa_View/FeatureServer/0).
Its metadata and actual bounded query responses succeeded with HTTP 200.
The metadata describes updates every ten minutes; this is a source description,
not a guaranteed freshness or availability service-level agreement. The official
feed page also says events change when activated, updated or expired.

The frozen official response is `data/fixtures/iowa_dot.json`:

- Oldest data-request retrieval: `2026-10-28T19:00:34.881670+00:00`.
- 599 inventoried and returned point records, in six pages; no missing or
  invalid point geometries in this captured response.
- 294 repeated CARS event-ID groups were observed. Every original point record
  and property remains available; the adapter does not silently merge records.
- Latest record-edit timestamp: `2026-10-28T18:58:29.393000+00:00`.
  This is an ArcGIS edit time, not a verified event observation time.
- Frozen fixture size: 2,108,723 bytes. SHA-256:
  `a4c3b69e32b0bf3755684e21b24e8264de9efb8fca63e6dccde129722e89a445`.

A real first attempt using 500 encoded object IDs exceeded the provider's
observed GET URL limit and returned HTTP 404 for that page. Its incomplete
99-record result and exact error are retained in
`reports/iowa_dot_initial_partial_attempt.json`. The working adapter uses
100-record pages and 0.2-second spacing between pages. This is an actual
integration failure and fix, not a claim that every request succeeded.

## Adapter contract

`backend/state_dot.py` provides `IowaDOTAdapter.fetch()` using the existing
`CachedHTTP` request, cache, timeout and offline-runtime guard. It first inspects
layer metadata, then queries a unique object-ID inventory. It requests at most
2,000 records in bounded object-ID groups. It does not rely on shifting result
offsets to claim a stable snapshot. A provider can still change records between
these requests; `atomic_provider_snapshot` stays false.

The return value follows the Missouri road-evidence shape: `source_url`,
`retrieved_at`, `stale`, `cache`, `incident_layers`, `layer_failures`,
`coverage_complete` and `coverage_warning`. Original response envelopes are
retained as `source_metadata`, `source_inventory` and `source_pages`.
`query_summary` reports bounds, missing IDs, invalid geometry IDs, repeated
event-ID groups and actual returned records. Content completeness is separate
from freshness. A stale cached page cannot become fresh because normalization
ran again.

Metadata uses a one-day cache and the data requests use a ten-minute cache.
Failed data-page requests retain other successful pages and their exact errors.
Unexpected schema, coordinate reference, date-field timezone, duplicate
OBJECTIDs, malformed/nonfinite JSON or records outside the requested inventory
are explicit failures. No provider failure is converted to an empty clear-road
result. A record with absent/invalid finite point geometry is retained in its
original response, excluded from geometry screening, and counted as a coverage
gap.

## Coordinate and time semantics

The native layer is Web Mercator, ArcGIS 102100 / EPSG:3857. Every event query
explicitly requests `outSR=4326` and GeoJSON. Valid screening coordinates are
longitude, latitude; unexpected declared coordinate systems are rejected.

The actual metadata identifies `EditDate` as an ArcGIS date field and declares
the date-field timezone as UTC. The adapter preserves the original epoch
milliseconds and provides the latest valid edit as a separate UTC value. A
changed/unknown date-field timezone is rejected. `IssueDate`, `IssueTime`,
`ExpireDate`, `ExpireTime`, `UpdateDate`, `UpdateTime` and `gisupdated` are
preserved literally: their event-clock timezone and interpretation have not
been independently established. They are not silently converted to UTC or
used to declare an event active/expired.

`retrieved_at` is the oldest valid data-response retrieval instant, retaining
individual request timestamps as well. Missing, naive, invalid or implausibly
future retrieval times prevent a fresh claim.

## Operational boundaries and attribution

The layer covers reported Iowa 511 point events. It excludes winter road
conditions, which are a separate Iowa feed. It is not an inventory of every
local road or every actual disruption. A complete queried layer is therefore
not complete real-world route coverage.

The new layer remains separate from MoDOT and the simulated operating network.
Point proximity can flag a nearby parallel road or wrong carriageway and does
not describe a closure's full extent, direction, schedule or delay duration.
OSRM ordinary driving geometry does not incorporate these events or establish
commercial-vehicle eligibility. Review flags do not dispatch trucks or impose
holds. Alternative routes require dispatcher review and suitable truck-route
validation.

The item declares [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) and
references [Iowa GIS terms](https://iowadot.gov/policies_and_statements/terms-of-use#gis)
and [Iowa 511 feed terms](https://iowadot.gov/policies_and_statements/511-data-feed-terms-and-conditions).
Retain attribution: **Iowa Department of Transportation — Office of Traffic
Operations**. Provider attribution does not imply agency endorsement of AEGIS.
