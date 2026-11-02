# Road workspace visual review

October 28, 2026. Actual Chrome screenshots from the successful final 58-check
run were opened and inspected after execution. The earlier 56-check result is
retained separately as `prior-fix.results.json`.

- `desktop-cross-state-comparison.png`: separate MoDOT and Iowa review cards,
  explicit estimated-connection label, distances/durations and source/truck
  limitations are visible. Four nearby MoDOT geometries are review signals;
  zero nearby Iowa records is explicitly not a clear-road conclusion.
- `mobile-route-comparison.png`: the 390-pixel layout stacks route and source
  review cards with readable text, export control and review requirement.
- `mobile-provider-fields.png`: literal Iowa properties remain readable within
  the event detail, with retrieval time separate from unavailable interpreted
  event times. The mobile navigation remains visible.
- `desktop-offline-routing-provenance.png`: the requested public OSRM source,
  absent provider retrieval timestamp, estimated route geometry and exact
  offline-runtime fallback reason are visible together. The mobile comparison
  also retains its own travel-source block without horizontal overflow.

No application JavaScript error, unexpected application HTTP failure, external
resource failure or horizontal document overflow was recorded in this run.
The one HTTP 503 was deliberately injected in the browser to verify recovery;
it was not an actual provider outage. The offline OSRM request exercised the
server's network guard and visibly labeled estimate, not the public router.

Exact hashes of both official fixture files and the initialized isolated
SQLite database/sidecars were unchanged. This script performs no provider
refresh, reset, approval, hold or dispatch action. See `results.json` for actual
timestamps, checks and fingerprints; this note does not establish future
provider availability or a genuine human presentation rehearsal.
