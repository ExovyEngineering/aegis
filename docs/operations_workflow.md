# Custom planning and dispatcher review

All operations remain a local research demonstration. User-entered locations are planning inputs; trips, inventory, demand, safety flags and relationships are scenarios rather than verified commercial records. Dispatcher identity is self-declared, not production authorization.

## Custom routes

Route laboratory accepts one to three origins, one to twenty stops and one to ten trucks. Start from a farm or regional example, then edit longitude/latitude, stock, demand, deadlines, shelf life, truck origin and capacity. IDs must be unique, coordinates finite/in range, truck origins valid, and each stop must have its own planning lot key. Shared-lot stock/traceability is not modeled in this editor.

Custom operations are sent to `POST /api/route-lab` with `preset: custom` and `custom_operation`. Preset-only truck-count/capacity overrides are rejected instead of silently ignored. Capacity, stock, eligibility, holds/recalls, service completion, shelf life, route duration and return-to-origin constraints apply. Inadequate resources produce explicit unmet demand. A flagged recall in this editor is a scenario flag, not a verified match to an official recall.

Route experiments do not mutate the Command network or publish driver assignments. They retain separate travel-time, distance and geometry provenance. OSRM ordinary driving routes do not certify commercial-truck restrictions or incorporate current closures automatically. MoDOT evidence is Missouri-specific and proximity remains a review signal.

## Dispatcher desk and Drive

1. Review and approve a Command scenario before a trip appears in Drive.
2. While parked, select the relevant trip and submit a report. New reports enter the structured inbox; earlier audit-only reports remain in the existing audit trail without invented historical review states.
3. A dispatcher supplies an actor and reason, then starts review or resolves an inbox report. The original reporting network revision and assignment snapshot are retained so a later reset or reused trip ID cannot rewrite historical context.
4. The dispatcher can issue instructions to an approved eligible assignment. Instructions do not themselves change a route, stock quantity or lot disposition. The driver acknowledges the exact current instruction version separately from acknowledging the original assignment.
5. A human hold decision changes lot state and removes only affected approved assignments. Earlier proposals become stale. Release cannot override a recall or automatically recreate assignments; a fresh scenario must be reviewed and approved.

Every decision is transactional and audited. Stale network, incident or instruction versions are rejected. Instruction counters persist across replanning so an acknowledgment of an old instruction cannot acknowledge a new one with a reused trip ID. Resolving an inbox report is an operational workflow action, not a verified food-safety finding.

The desk and Drive check local state every fifteen seconds. This polling does not refresh external APIs or establish live weather/road coverage. Source timestamps and stale warnings still control interpretation. The parked-use instruction remains visible.

## Dispatch readiness review

The Dispatcher desk includes a read-only checklist for approved simulated trips.
Choose a status filter and trip to inspect the actual constraints and outstanding
workflow records. **Refresh readiness** repeats the local read; it does not
refresh weather, road incidents or official recall data. `GET /api/readiness`
returns the same diagnostic for API clients.

Each trip has sixteen checks:

- Thirteen hard checks: known canonical shipment, unchanged shipment assumptions,
  lot eligibility/disposition, truck eligibility, refrigeration configuration,
  positive quantity, deadline, shelf life, and aggregate lot inventory, truck
  capacity, origin capacity, supplier capacity and destination demand.
- Three workflow checks: driver assignment acknowledgment, acknowledgment of
  the current versioned instruction, and complete matching targeted verification
  when the approved scenario requests it.

The backend recomputes aggregate use across all approved trips from one SQLite
snapshot. A hard failure reports **Blocked by a constraint**. Otherwise missing
workflow evidence reports **Review outstanding**. **Listed checks passed** means
the listed records permit final human review; it is not departure authorization,
food-safety certification or commercial-truck route clearance. The checklist
does not dispatch a truck, decrement stock or impose a hold. Predictive scores
do not create hard blocks.

Results include the checked time and network revision. A revision mismatch
between the desk and checklist suppresses the displayed results until refreshed.
Review and acknowledgment mutations continue through their existing audited,
version-checked endpoints. See [the backend](../backend/readiness.py),
[read-only and concurrent-snapshot tests](../tests/test_readiness.py) and
[the interface](../frontend/src/DispatchReadiness.tsx).

## Reproduce safely

Run `.venv/Scripts/python scripts/operations_demo.py` for an isolated temporary-database exercise covering report, review, instruction, stale acknowledgment rejection, hold, release and resolution. It writes `reports/operations_demo.json` and leaves the operator database unchanged.

The runtime adds `incidents` and `dispatch_instruction_versions` tables idempotently to the existing SQLite file. It does not reset existing lots or assignments. Historical incidents and audit records are retained across scenario resets; reporting snapshots identify their original context.
