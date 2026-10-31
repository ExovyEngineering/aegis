## Save the Load: exposure, remaining quality and reviewed rescue

**Save the Load** connects a stored sensor history, a conditional shelf-life
calculation, closer receiving options, warehouse FEFO and a human-approved driver
handoff. No physical sensors are connected in the current demo. The replay and
the separately authenticated ingestion endpoint exercise the same calculation
pipeline with explicit source labels.

### A two-minute walkthrough

1. Open **Save the Load** in the sidebar. Generic entry selects the documented
   SH05 demonstration; **Model this lot’s shelf life** in Command instead carries
   the candidate you explicitly selected.
2. Click **Start rescue experiment**. The seeded lot has a declared 240-hour
   reference budget and 230 hours of assumed prior equivalent age. After the
   initial normal hour, its modeled remaining budget is nine hours. This is an
   illustrative starting condition, not a recommended ten-day poultry life.
3. Click **Replay heat excursion** immediately after creation. Stored product
   readings hold 16°C for two hours, then record restored 4°C control. The point
   forward estimate becomes about 4.39 hours; the minimum forward estimate across the chosen Q10 cases gives
   about 1.51 hours. The range is parameter sensitivity, not a confidence bound.
   **Play sensor replay** includes an extra normal frame, so its clocks differ
   from this manual example. It pauses when a checked rescue plan is available.
4. Inspect the original trip and receiving buffer against the conservative
   quality clock. The engine automatically ranks closer simulated recipients.
   Select a candidate to see its route, travel time, quality margin and exclusions.
   Expand **Show all N candidates and exclusions** to inspect blocked options.
5. An estimated connection stays labeled. **Check road route** deliberately
   requests an ordinary-driving OSRM route when available; offline rehearsal uses
   a visible estimate. Neither method verifies truck restrictions or closure
   avoidance. A DC contingency is review-only, with no invented receiving space.
6. **Prepare selected rescue** computes a concrete plan when changing the chosen
   recipient. **Review** opens its complete proposed assignment list, cost, unmet
   demand and checked constraints. The original destination can lose supply; a
   rescue is not presented as a cost-free improvement.
7. Add the reviewer and reason, confirm the three separate quality/disposition,
   receiving and routing reviews, then **Approve simulated rescue plan**. This
   replaces the entire checked simulated assignment set and advances the network
   revision. It never releases held/recalled stock. **Open approved driver
   assignments** carries the rescued truck and trip into Drive.
8. A later replay or gateway frame flags the earlier decision for review. Drive
   and dispatch readiness show the pending freshness review without silently
   rerouting, holding stock or publishing another plan. **Refresh plan for new
   review** retains all exposure history and original use-by caps.

### What FEFO changes

FIFO prioritizes receipt order. Predictive FEFO prioritizes the smallest usable
modeled quality window among eligible warehouse lots. Both policies first
maximize demand fulfillment under the same stock, truck, warehouse, destination,
deadline and quality constraints. The second priority is lexicographic lot order,
not a weighted score that can quietly sacrifice the preceding priority.

The picking table shows the actual solver's lot/warehouse/destination quantities
and quality margin. A newer warm lot can precede an older cold lot. Compare the
two policies' picks and stock exposed to modeled expiry within the declared
planning horizon. Exposure is not observed food waste, a pathogen result or a
guaranteed amount of food saved. Pick recommendations do not debit a WMS ledger.
Warehouse placement and receiving acceptance are declared simulation assumptions.

### What each channel contributes

| Channel | Use in this implementation | Boundary |
| --- | --- | --- |
| Product temperature, °C | Drives the Q10 equivalent-age calculation | Uncalibrated parameters and a declared bounded hold between samples |
| Ambient temperature, °C | Contextual reefer environment | Never silently substituted for product/core temperature |
| Relative humidity, % | Retained and displayed | Not product water activity; no invented poultry coefficient |
| Vibration, g | Retained and displayed | Sensor definition and damage relationship need validation |
| Ethylene, ppm | Retained and displayed | Commodity-specific response; no invented poultry spoilage coefficient |

Cooling cannot reverse accumulated quality age. Supplied label/use-by caps keep
decreasing and cannot be extended by cooling, a new forecast or rebasing. Missing
history, stale gateway coverage or out-of-domain readings make the quality clock
unscored. Unknown quality is excluded from model-driven picking and rescue.

### Captures, hardware and scientific limits

Stored frames are append-only within an experiment. Original observation times
and server retrieval times remain separate. Duplicate event IDs are idempotent
only when their contents match; conflicting, reversed or unsupported frames are
rejected. The browser can follow the stored stream every five seconds. Refreshing
the page can reopen an experiment; it does not manufacture another observation.

After an approved rescue, **Continue lot's exposure history** reopens the linked
experiment. A second experiment cannot reset that lot's consumed quality age.
Older counterfactual experiments cannot overwrite the reviewed exposure record.
Use a fresh isolated rehearsal for another demonstration from the beginning.

**Export captured freshness experiment** preserves the full received snapshot,
source labels, profiles, clocks, routing and picking results. New readings or
planning inputs invalidate older approval context. A confirmed decision receipt
survives a subsequent incomplete application refresh.

The optional gateway needs a server-side bearer token, registered device/lot
bindings, a declared baseline and valid units. Authentication does not establish
physical calibration or genuine lot traceability. The application remains a
loopback research demonstrator; it is not production IoT tenancy or hardware
certification. See `docs/freshness_gateway.md` for the bounded protocol.

The model is mechanistic quality estimation plus mathematical optimization. No
trained AI decay model, measured molecular freshness, actual spoilage rate or
microbiological safety clearance is claimed. The historical FSIS sampling model
remains separate. Equations and primary references are in
`docs/freshness_science.md`.
