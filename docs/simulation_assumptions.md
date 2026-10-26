# Simulation and optimization assumptions

All logistics entities and relationships are fictional. Seed `20261026` determines the network and telemetry. City coordinates provide Missouri geographic context; destination coordinates are seeded offsets, not verified customer locations.

| Item | Assumption |
|---|---|
| Suppliers | Three simulated suppliers near Columbia, Kansas City, Jefferson City; 6,000 kg nominal capacity each |
| DCs | Columbia 12,000 kg; Springfield 10,000 kg |
| Destinations | 15 seeded locations around five Missouri cities; each demands 500 kg per wave |
| Trucks | Eight refrigerated trucks, each with 1,500 kg one-wave capacity |
| Lots | 12 lots with 1,500 kg each, 72-hour nominal remaining shelf life; L01 begins held |
| Shipment candidates | 24 candidates, each 400 kg; fixed origin, destination, truck, and initial lot |
| Travel | Haversine distance × 1.25, divided by 65 km/h for default allocation estimates |
| Deadline | Six hours per candidate; shipments exceeding deadline or remaining shelf life are ineligible |
| Temperature | 12 readings per shipment, ten-minute intervals from October 26, 2026 at 08:00 America/Chicago; SH03 and SH08 have excursions |
| Review threshold | Above 4°C raises review priority in the demo; this is a scenario assumption, not a validated product disposition rule |
| Cost | Simulated dollars: fixed dispatch plus distance; verification and substitute-lot surcharges |

The supply inventory is treated as available to the dispatch wave. The prototype does not model supplier-to-DC replenishment legs, DC-specific lot placement, trailer compartment interactions, loading labor, multiple sequential trips, product-specific thermal kinetics, or commercial-truck restrictions. Substitution assumes simulated lots are interchangeable; actual alternative supply requires product, specification, traceability, facility, and handling approval.

## Four response scenarios

| Scenario | Behavior |
|---|---|
| A — Baseline | Allocate original candidate lots under hard constraints |
| B — Targeted verification | Add verification flags and cost for selected excursion shipments |
| C — Precautionary hold | Propose holding lots associated with temperature excursions; exclusions affect the proposed plan, while persistent hold state changes only after approval |
| D — Alternative eligible supply | Permit eligible simulated substitute lots with a cost surcharge; route alternatives require separate route review |

The solver maximizes served kilograms with a high service reward less simulated logistics cost. This expresses a demo preference, not an empirically fitted economic objective. Hard constraints exclude held, recalled, ineligible, over-capacity, unavailable, expired, or late choices regardless of objective weights. A model score cannot itself create a mandatory hold.

Food waste is zero within the present six-hour wave because stock does not expire within that horizon. Unsent stock stays inventory; it is not relabeled as waste. Unmet demand is destination demand less assigned quantity. Affected shipments count candidates not selected; this is not a count of confirmed unsafe products. Supplier capacity limits are enforced in the allocation; a full upstream replenishment model remains outstanding.

## Farm and fleet route laboratory

The separate farm preset has one fictional Columbia-area dispatch origin, eight 300-kg destinations and three nominal refrigerated trucks. FD08 begins held. The regional preset uses two fictional DCs, fifteen 500-kg destinations and eight nominal trucks; D01 begins held. Users can vary available trucks (1–10), capacity (100–5,000 kg), route horizon (0.25–16 hours), ambient assumption and additional departure delay. These are shared planning presets, not separate account modes.

Each active truck returns to its own origin. Stops have ten-minute service and six-hour completion deadlines. Per-origin stock is limited; unreachable OD arcs remain unusable. No held, recalled or ineligible stop is served; nonrefrigerated/ineligible trucks remain unused. Unserved destinations and unmet kilograms are explicit. The deterministic descent heuristic finds feasible routes, without a global-optimality claim. Travel distance, driving time, service/delay-inclusive duration and route geometry estimates are separate quantities.

Temperature projection uses `T(t) = T_equilibrium + (T_initial - T_equilibrium) exp(-t/tau)`. Fault scenarios assume an uncalibrated 120-minute thermal response toward ambient; normal control assumes 20 minutes toward 2°C with a small ambient penalty above 30°C. Bands vary parameters and are sensitivity ranges, not confidence intervals. The model has not been calibrated to actual truck/cargo sensors and supplies no failure probability, microbial growth estimate or automatic hold. Measured telemetry remains explicitly simulated; projections never substitute for real measurements.

## Event semantics

Road closure, severe weather, and delivery delay add a simulated two-hour delay. Refrigeration fault marks the assigned truck ineligible and sets cargo temperature to 9°C. Temperature excursion sets the shipment to 9°C and high review priority. Inventory shortage removes the candidate lot's available stock. These events are labeled simulated and invalidate existing assignments. They do not establish that a real MoDOT event or weather alert caused a real shipment delay.

No verified recall event is synthesized as an official match. Real recall data may be displayed, while recall-to-lot matching remains unavailable without genuine traceability fields.
