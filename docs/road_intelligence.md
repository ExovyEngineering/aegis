# Road intelligence workspace

October 28, 2026. Open **Road intelligence** in Command. This is a read-only
planning workspace, separate from the simulated Missouri dispatch network.

Inspect MoDOT and [Iowa DOT 511](state_dot.md) independently. Source cards show
retrieval time, dated-fixture/cache status, failures, captured records, and
geometry gaps. Each source preview lists at most 200 rows. Filtering searches
that preview, not a claim to search every provider record. Select a record for
its original provider fields and raw time values. Iowa attribution and license
links remain visible.

Choose Columbia–St. Louis, Columbia–Des Moines, or two coordinates. The estimated
default makes no provider request. OSRM requests up to its available ordinary
driving alternatives and falls back visibly when unavailable. Compare distance,
duration and the separately attributed nearby events; change the proximity
buffer from 50 to 2,000 meters. Input or source changes mark the prior comparison
as stale until rerun. Download the captured comparison as JSON for team review.

The screen uses a real OpenStreetMap base map and captured provider geometries.
Estimated travel draws a straight connection and uses distance × 1.25 at
65 km/h. It is unsuitable for asserting a specific road is affected. OSRM's
ordinary driving profile does not include current DOT closures or commercial
truck restrictions. No alternative is automatically eligible or dispatched.
Parallel roads, opposite carriageways and repeated source records can match a
buffer. Zero matching geometries does not establish a clear road.

## Backend and provenance

- `GET /api/road-intelligence` reads bounded saved responses. It does not refresh
  public providers or open the operator database.
- `POST /api/road-intelligence/refresh` checks both adapters with existing cache
  cadences. It records each result and preserves the prior response on failure.
  A TTL cache is labeled separately from a new provider response. Duplicate
  concurrent refreshes are rejected. Offline rehearsal rejects refresh entirely.
- `POST /api/road-intelligence/compare` accepts `origin`, `destination` in
  longitude/latitude order, `routing` (`estimated` or `osrm`) and `buffer_m`.
  It uses one captured source snapshot, screens all its bounded supported
  geometries and returns up to 100 matching records per source per alternative,
  with total-match/truncation counts. The workspace caps source reads at 32 MiB
  and 10,000 records per feed; Iowa acquisition is independently capped at 2,000.

Malformed, absent, unsupported or nonfinite geometry is counted and excluded;
remaining valid records can still be inspected. The existing Missouri route
review now also handles these cases and missing/naive/future retrieval times
conservatively. No missing observation, geometry or timestamp is invented.

`coverage_complete` describes the captured queried layers, not end-to-end
geographic coverage. The interface does not verify state-boundary containment,
road-event schedules, real-world road clearance or an effect on delay duration.
Retrieval, provider edit and unverified event clocks remain separate. The
Columbia–Des Moines corridor is a planning example, not a simulated supply
contract added to the operational model.

Offline rehearsal uses only immutable dated fixtures, ignoring mutable caches.
Its OSRM requests reach the existing offline guard and return labeled estimates.
Browser map tiles and deliberately opened provider links can still use internet.
No route comparison modifies inventory, assignments, holds, approvals or audit
records. Executed tests and Chrome evidence belong in the dated verification
reports; screenshots do not establish present provider freshness.
