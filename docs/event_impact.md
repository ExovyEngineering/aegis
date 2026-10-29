# Simulated disruption impact comparison

`backend/event_impact.py` calculates the current simulator's actual before/after
effects and runs the existing one-wave optimizer for all four responses. It
does not generate a new prediction, fetch a road/weather feed or create an
assignment. A preview is a read-only experiment over copies of the captured
simulated network.

## Preview contract

`create_event_impact_router(db_path, root=ROOT)` mounts
`POST /api/events/preview`:

```json
{
  "event": "road_closure",
  "shipment_id": "SH11",
  "expected_network_revision": 7
}
```

Supported events are `road_closure`, `severe_weather`, `delivery_delay`,
`refrigeration_fault`, `temperature_excursion` and `inventory_shortage`.
Revision is required and must be a nonnegative integer, excluding booleans.
Unknown fields and event types are rejected. A verified official recall cannot
be manufactured as a simulator event.

The endpoint uses the assistant's bounded, strict JSON/SQLite snapshot reader:
`mode=ro`, `query_only=ON`, a read transaction, and no schema initialization or
seeding. Network and assignment fields share that transaction. There are no
report-file or provider inputs to this calculation. Missing/corrupt state gives
an explicit unavailable response. Comparisons are limited to 50 candidates,
24 lots and 20 trucks; this covers the standard 24-candidate demo and bounds the
eight optimizer calls. Each call retains the optimizer's ten-second solve limit;
this is not a low-latency production service guarantee.

After computation, a second read checks the semantic network/assignment digest.
A changed revision or changed captured state returns HTTP 409. Preview does not
lock out other human actions, so review it before choosing a separate action.

The response includes:

| Field | Meaning |
| --- | --- |
| `preview_id` | SHA-256 of the exact comparison and captured semantic identity, excluding the wall-clock generation timestamp |
| `snapshot_id`, `network_revision` | Captured network/revision/normalized approved-assignment identity |
| `event`, `event_label`, `shipment_id` | Explicit event and selected fictional candidate |
| `simulation`, `read_only`, `operational_state_modified` | True, true and false for this preview |
| `requires_explicit_apply` | Preview has not applied the disruption |
| `shipment.before`, `shipment.after` | Planning duration, deadline margin, cargo value, original-lot stock/flags and truck eligibility |
| `shipment.changes` | Actual changed scalar fields with units and numeric differences where appropriate |
| `route_effects` | Explicit unchanged road geometry, distance and stop order, plus any planning-duration change |
| `resource_effects`, `candidate_effects` | Shared truck/lot changes and direct original-lot eligibility checks for affected candidates |
| `assignments` | Current count and count the existing simulator would invalidate if explicitly applied |
| `scenarios` | All four actual optimizer comparisons and resulting selected-candidate/lot/verification/hold-proposal differences |
| `limitations`, `next_steps`, `generated_at` | Meaning, limits and UTC calculation timestamp |

Scenario summaries include simulated logistics cost, unmet demand, selected
shipments, supplied kilograms, affected/review-priority/delayed counts, modeled
waste, feasibility, solver status and independent constraint review. Deltas are
`after - before`; a positive unmet-demand difference is worse coverage. Selected
IDs and lots are included because equal totals can hide a different allocation.

## What the events actually change

| Event | Current simulator effect | Does a new road route result? |
| --- | --- | --- |
| Road closure, severe weather, delivery delay | Add a fixed two-hour planning delay to the selected candidate | No; no closure avoidance or geometry calculation |
| Temperature excursion | Set selected simulated cargo to 9°C and review priority to high | No |
| Refrigeration fault | Same cargo/review change and make the shared truck ineligible | No; other candidates sharing that truck can also become unavailable |
| Inventory shortage | Set the original shared lot's stock to zero | No; scenario D may choose another eligible fictional lot on a fixed trip |

Travel duration and deadline margin are relative hours. They are not departure
or arrival timestamps, live ETAs, observed road delays or commercial-truck
clearance. A changed duration may leave the allocation unchanged if the same
candidates remain feasible under the fixed constraints. Current logistics cost
depends on distance/verification/substitution assumptions, not on a new delay
penalty. Unsent inventory is not automatically waste.

Scenario C proposes holds; preview does not impose them. Temperature and model
scores cannot create mandatory holds. Existing held or recalled lots remain
excluded under all scenarios. Direct candidate checks use the original lot;
aggregate allocation and scenario-D lot substitutions are shown separately.

## Reuse by the explicit event handler

The pure helper
`build_event_impact(network, revision, assignments, event, shipment_id)` does not
mutate its network or assignment inputs. A write handler can call it inside its
existing event transaction, compare the supplied `preview_id`/revision with the
recomputed value, then explicitly apply the selected simulator event. Pass parsed
assignment payloads with their `acknowledged` value (boolean or SQL 0/1). Hashing
normalizes only assignment identity, lot, truck, quantity, acknowledgment and
targeted-verification state; database JSON whitespace and irrelevant payload
serialization do not change the semantic identity.

The integrated `/api/events` handler accepts `expected_network_revision` and
`preview_id` from Command. When a preview is supplied, both are checked inside
the same immediate write transaction before any mutation. It returns the actual
revision before/after, `assignments_removed`, `assignments_invalidated`, the
accepted preview hash and `operational_state_modified: true`. The UI preserves
this confirmed receipt even if the following full refresh fails. Legacy API
callers may still apply directly; preview is not a mandatory regulatory rule.

The existing event handler clears **all** approved assignments, not only the
selected trip. Preview reports that consequence without doing it. Approval,
dispatch-readiness and driver handoff remain separate reviewed workflows. An
applied receipt must be labeled by the caller as applied; the pure helper's
default flags always describe its non-mutating preview calculation.

## Verification

`tests/test_event_impact.py` checks each event against the real simulator and
optimizer; shared truck/stock impacts; unchanged routes; stable semantic hashes;
input preservation; exact read-only SQL; stale/context races; no implicit
seeding; invalid inputs; bounded work; and no provider/model requests. These are
software correctness tests over simulated data, not scientific validation of
the two-hour or 9°C assumptions.

`tests/test_event_apply_preview.py` verifies matching guarded application,
unchanged storage on rejection, same-revision acknowledgment changes, exact
post-event solver results and preservation of held/recalled protections.
