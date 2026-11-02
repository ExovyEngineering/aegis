# Read-only food-volume and destination-service decision study

Preserve eligible food volume, reduce modeled short-clock inventory exposure, and examine equal destination demand service under shared safety and logistics constraints.

**Computed simulation. Every proposal requires human review. No operator state was accessed or changed.**

The status-quo comparator takes the first feasible input candidate. The volume policy first maximizes kg, then the kg delivered from lots with modeled quality clocks ending within six hours. The balanced policy first maximizes equal destination service credit (capped at 50% of each destination demand), then kg and short-clock delivery. Every policy receives the same constraints and passes independent arithmetic review.

National FSIS selected-sample prevalence is shared context only. Quality guidance comes from declared illustrative temperature histories and the existing Q10 quality model; it is not pathogen-risk reduction. Historical USDA county context supplies no need weights because the fictional destinations have no verified county crosswalk.

| Scenario | Policy | Distributed kg | Unmet kg | Retained inventory kg | Quality-budget exposure kg | Destinations served | At least 50% served | Temperature reviews | Shipment hours |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline quality-constrained wave | First feasible candidate | 4400 | 3100 | 13600 | 4800 | 11 | 11 | 2 | 28.903 |
| Baseline quality-constrained wave | Quality-guided volume preservation | 4400 | 3100 | 13600 | 4800 | 11 | 11 | 1 | 18.604 |
| Baseline quality-constrained wave | Quality-guided balanced service | 4400 | 3100 | 13600 | 4800 | 11 | 11 | 1 | 18.604 |
| Fleet scarcity and heterogeneous demand | First feasible candidate | 2800 | 6200 | 15200 | 5600 | 6 | 6 | 2 | 19.92 |
| Fleet scarcity and heterogeneous demand | Quality-guided volume preservation | 3200 | 5800 | 14800 | 4400 | 7 | 7 | 1 | 16.83 |
| Fleet scarcity and heterogeneous demand | Quality-guided balanced service | 3200 | 5800 | 14800 | 4800 | 8 | 8 | 1 | 19.482 |
| Delay and supply restriction | First feasible candidate | 3200 | 4300 | 13700 | 4800 | 8 | 8 | 0 | 24.834 |
| Delay and supply restriction | Quality-guided volume preservation | 3200 | 4300 | 13700 | 4800 | 8 | 8 | 0 | 24.834 |
| Delay and supply restriction | Quality-guided balanced service | 3200 | 4300 | 13700 | 4800 | 8 | 8 | 0 | 24.834 |

Retained inventory includes stock protected by a hold/recall; it is not all dispatchable. Quality-budget exposure counts eligible unsent stock whose illustrative quality clock ends within the six-hour horizon. Unsent inventory is not labeled waste. Temperature review counts measure workload, not contamination.

All policies dispatch **zero kg from held/recalled lots** and have **zero independent constraint violations** in the generated artifact.

The full JSON includes each scenario input network, quality model inputs and sensitivity results, each selected candidate, per-destination demand fulfillment, safety exclusions, priority diagnostics, lexicographic solver stages and comparison deltas. CSV exports one row per scenario/policy and a separate row per destination.

## Scenario assumptions

**Baseline quality-constrained wave**

- Canonical seeded candidates, inventory and demand.
- All lot quality clocks come from declared synthetic Q10 histories; held L01 remains excluded.

**Fleet scarcity and heterogeneous demand**

- Every truck has 400 kg available one-wave capacity.
- Every third candidate is 200 kg rather than 400 kg.
- Every third destination demands 200 kg; other destinations demand 800 kg. These are declared stress inputs.

**Delay and supply restriction**

- Every candidate incurs two additional estimated journey hours.
- L03 is recalled in this simulation; L04 inventory is 400 kg; truck capacity is 800 kg.
- The recall is an existing scenario input, never inferred from a score or imposed on operator state.

## Unresolved scientific limitations

- Every supply-chain entity, demand, capacity, temperature, quality profile and stress scenario is simulated. These are computed policy results, not observed operational outcomes.
- The FSIS model estimates selected surveillance-sample positivity; it cannot identify contaminated shipments or consumer illness. Its national historical prevalence is identical context for all fictional candidates and does not alter allocation.
- Quality guidance uses the existing illustrative Q10 model on declared simulated temperatures. Its forward clocks are neither calibrated poultry shelf life nor pathogen-growth predictions, and cannot extend use-by dates.
- Hard safety measures count held/recalled/ineligible exclusions and review workload. They are not estimated infections prevented or causal food-safety risk reduction.
- Unsent stock remains inventory. Projected quality-budget exposure is unsent stock whose illustrative forward clock ends within six hours; it is not observed waste or a guaranteed quantity saved.
- Food security is represented by preserving eligible food volume and reporting destination demand fulfillment. No vulnerable-population, household-food-security or nutritional outcome is inferred.
- Historical USDA county need is not used as a destination weight: fictional jittered destinations lack a verified county crosswalk. Balanced service treats destinations equally, not people, and is not proof of equitable access.
- The first-feasible comparator is an explicit rule, not an estimate of actual status-quo operator performance. All policies receive the same candidate assignments and hard constraints.
- One-wave fixed truck/candidate allocation omits truck sequencing, live roads, loading labor and temperature uncertainty. Distances are haversine-based simulation estimates, not truck-safe routes.
- All actions are review proposals. No dispatch, hold, recall, reservation, inventory write, operational database access or human approval is performed by this study.

Prospective individual-shipment FSIS risk is unavailable. Quality-guided allocation and hard safety exclusions demonstrate decision mechanics without claiming validated pathogen-risk personalization.
