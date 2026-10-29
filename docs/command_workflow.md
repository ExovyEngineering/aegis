# Understanding Command actions

Command is a working simulator and decision-support workflow. Public evidence
and real road geography are distinct from fictional shipments, cargo, costs and
resource assumptions. The controls below perform their named operation; an
inspection or comparison never silently becomes an approved dispatch.

| Control | Produced result | What changes |
| --- | --- | --- |
| Map allocation / Show on map | Selected candidate, scenario or approved connection overlay | Map display only; dashed links are not road geometry |
| Request road route | Selected trip's OSRM ordinary-driving geometry or labeled estimated fallback, distance and duration | A separate comparison; fixed allocation inputs stay unchanged |
| Highlight alternative / Focus route map | Selected alternative and focused map | Comparison display only; enable Route geometry if hidden |
| Export route comparison JSON | Captured route, attribution and selected index | A downloaded file; no dispatch |
| Recompute | All four current response plans and a completion receipt | Recomputed comparison; identical results are a valid result |
| Review | Pending proposal and its actual selected trips/lots | Proposal record; no approved assignment yet |
| Approve simulated plan | Revalidated allocation and audit record | Human-approved simulated assignments; proposed C holds applied |
| Preview event impact | Exact direct changes, shared-resource effects and four before/after allocations | Nothing in operational storage |
| Apply previewed event | Matched-revision/hash event receipt | Simulation revision advances and every approved assignment is cleared |
| Export confirmed event JSON / Dismiss confirmed receipt | Retains the confirmed result even if the following network reload fails | File download or message visibility only; no repeated event |
| Reset demo / Confirm reset simulation | Seed restored and assignments cleared | Simulation only; existing proposals become stale |
| Bell / queue inspection | Relevant review region, selected candidate or evidence workspace | Navigation only |

## A first read-only walkthrough

1. Read **What you are looking at** and expand **How this connects**.
2. Select a shipment in **Cold-chain & trip detail**. Its candidate truck and
   lot are not necessarily a current approved assignment. The seeded chart is
   historical simulated telemetry; an injected current reading is separate.
3. Request a road route. The result is focused below the trip cards; inspect
   travel values, provenance and road-review limitations. Select an alternative
   and focus the map. These ordinary-driving routes do not certify truck
   restrictions, current closure avoidance or a reduction in actual travel time.
4. Inspect each allocation with **Show on map**. The overlay reveals selected
   candidate connections, including exclusions and empty approved state. It does
   not optimize new road geometry. Scenario D substitutes eligible lots on fixed
   trips; the Route laboratory computes separate planning designs and stop order.
5. Choose a simulated event and click **Preview event impact**. Read the direct
   field differences and all four solver comparisons. Export if useful. Stop
   here to leave operations unchanged.

## Applying an exercise deliberately

Read the assignment-clear warning, confirm the checkbox and apply the preview.
The server rejects a stale revision or changed context before mutation. Current
outcomes are then recomputed. Review a fresh proposal, inspect its trips/lots,
enter a reviewer and reason, and explicitly approve it to update Drive. An
approval failure is visible inside the dialog; it creates no optimistic success.

Road closure, weather and delivery-delay exercises add the simulator's fixed
two-hour planning delay. Refrigeration faults make the shared truck ineligible
and set simulated cargo to 9°C. An excursion sets that current cargo value and
review priority; shortage zeros shared original-lot stock. None creates an
official incident, verified recall or automatic reroute. Applying the same
temperature setting again can leave direct values identical while still
advancing revision and clearing assignments; the preview reports that explicitly.

The map layers, Road intelligence, Sources, Model evaluation and Evidence
assistant support inspection. They cannot independently redesign an approved
trip. Use the per-page guide to see scope and the next connected workspace.

Executed test/browser evidence is recorded separately in
`reports/session_verification.json` and the dated Command browser report. Test
counts measure software behavior, not prospective scientific model accuracy.
