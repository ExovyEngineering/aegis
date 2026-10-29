## Command center: understand the current operation

Use **Command center** when you want to see the simulated Missouri distribution network, investigate a shipment, compare operational responses, or propose a dispatcher decision. This is the main control tower. The map combines real geography and public evidence with fictional logistics; the presence of an official facility beside a simulated trip does not establish a supply relationship.

The standard scenario has 3 simulated suppliers, 2 distribution centers, 15 destinations, 8 refrigerated trucks, 12 lots and 24 candidate shipments. These are reproducible planning entities, not a live business account. The scenario reference date is October 26, 2026. An October 26 cargo trace is not today's observed temperature. Different saved operator states can produce different current results.

### Read the four summary cards

| Card | What it tells you | How to use it |
| --- | --- | --- |
| NETWORK SHIPMENTS | Number of candidate simulated shipments and destinations | Understand the size of the current exercise; these are not all approved trips |
| COLD-CHAIN REVIEW | Shipments whose current simulated cargo value exceeds the 4°C review level | Find cases to investigate; this is not an illness probability or a regulatory disposition |
| APPROVED ASSIGNMENTS | Current dispatcher-approved simulated trips, with acknowledgment count | Check whether a proposed plan has actually been approved and whether drivers acknowledged it |
| PUBLIC ENDPOINT PROBES | Successful saved HTTP probes divided by registered probes | Inspect connectivity evidence; a successful documentation page does not prove full or current data coverage |

The **Review queue** combines simulated excursions, active simulated holds and a small preview of dated NWS alerts. Its cards are prompts to inspect evidence. They do not themselves approve a response, impose a hold or send a message. A count can exceed the few cards displayed in the preview.

### Explore the distribution map

Open the **Evidence layers** controls on the map. Their checkboxes change what is drawn; they do not change the underlying operation.

| Layer | What appears | Meaning |
| --- | --- | --- |
| Simulated logistics | Fictional locations, shipment links and truck markers | A distribution-network exercise; dashed links are estimated connections rather than roads |
| FSIS establishments | Coordinates from the supplied official establishment directory | Real source locations; no simulated contract or shipment relationship is implied |
| NWS alert geometry | Captured official alert polygons or points where geometry is supplied | Dated severe-weather evidence; read retrieval and provider times separately |
| MoDOT incident geometry | Captured Missouri road-event points or lines | Independent road evidence; it is not automatically incorporated into a route |
| Route geometry | The displayed OSRM route alternatives or labeled estimated fallback | A route comparison, not a dispatched detour or certified truck route |

Click a simulated shipment line or truck marker to select its associated trip. A truck's Command marker is an illustrative midpoint of an origin-to-destination connection, not GPS. Click a location or evidence geometry for its popup. Zoom and pan to investigate the area. The OpenStreetMap base map needs internet; a missing tile is different from a missing shipment or provider record.

The map can initially show a labeled Columbia-to-St. Louis reference route that is independent of the selected shipment. Check the route label before interpreting it. To request a route for the actual selected trip, use **Request road route** in the trip panel. Changing selection or network revision can invalidate an earlier shipment-specific route.

### Inspect cargo and weather separately

In **Cold-chain & trip detail**, use **Select shipment** to change the truck, destination, cargo quantity, current simulated temperature and displayed temperature history together. The fixed trip estimate uses straight-line distance multiplied by 1.25 at an assumed 65 km/h. Requesting an OSRM road route does not silently replace the allocation model's fixed travel assumptions.

**Request road route** asks OSRM for ordinary-driving geometry and available alternatives. **Route alternatives & road review** then shows each route's distance, travel estimate and captured MoDOT geometries within a 250-meter buffer. Read whether the geometry is estimated, whether road evidence is stale or incomplete, and whether the route label belongs to the selected shipment. Nearby parallel roads and duplicate point/line records can produce matches. Zero matches is not road clearance. OSRM does not validate truck height, weight or other commercial restrictions and does not automatically avoid current DOT closures.

**Weather exposure** is an Open-Meteo forecast for Columbia. Its first timestep and chart are ambient forecast values, not measurements from the cargo. The selected trip's simulated cargo trace, a weather forecast, historical station observations and the laboratory's temperature projection are four different things. The current system has no validated weather-to-FSIS predictive linkage.

### Compare the four response scenarios

**Compare operational scenarios** is a one-wave allocation exercise. It chooses among fixed candidate shipments subject to stock, demand, truck, supplier and distribution-center constraints. It does not build a multi-stop vehicle itinerary. **Recompute** reloads current scenario calculations; it does not approve them.

| Scenario | Question it explores | What changes relative to the baseline |
| --- | --- | --- |
| A — Baseline distribution | What can be allocated under the present constraints? | Keeps each candidate's original lot; existing holds, recalls and eligibility limits still apply |
| B — Targeted verification | What if selected simulated excursions require recorded dispatcher verification? | Adds an illustrative verification cost and flags selected shipments over the review temperature for a verification checklist |
| C — Precautionary hold pending review | What if excursion-associated lots are withheld pending human review? | Proposes lot-level holds and excludes those lots from this proposed allocation; the holds take effect only on explicit plan approval |
| D — Alternative eligible supply | Can interchangeable eligible simulated lots improve service? | Allows different eligible lots to supply fixed candidate trips, with a substitution cost; it does not itself reroute trucks on new roads |

Scenario B and C serve different purposes. B may publish an approved assignment whose targeted verification is still pending. The driver's acknowledgment does not satisfy that review. C proposes excluding the affected lot entirely; approving C places its proposed holds in the operational state. An excursion score or predicted risk alone never creates a mandatory hold. A more serious operational response is a human decision with recorded rationale.

### Understand the scenario numbers

- **Logistics cost** is an illustrative dollar cost, not a quoted transport price. The allocation uses fixed shipment costs, an added verification cost in B and substitution cost where applicable in D.
- **Unmet demand** is destination demand not served by this selected plan, in kilograms. Compare it alongside cost: a cheaper plan can simply deliver less.
- **Delays** counts selected trips beyond their deadline. Deadline constraints normally exclude such trips, so zero here does not mean every original requested trip was fulfilled on time.
- **Waste** is zero under the present one-wave horizon assumption. Unsent stock remains inventory; it is not silently counted as discarded food.
- **Affected** counts candidate shipments omitted from the selected plan. It is not a count of verified contaminated shipments or illnesses.
- **Review** counts selected shipments with simulated temperatures above the review level. It is an operational attention count, not a learned probability.
- **Violations** is the count of independently checked hard-constraint failures. A missing value is not proof of zero violations.
- **Solver** explains whether a solution was found. OPTIMAL means optimal for this defined mathematical model and objective, not the best possible real-world business decision. FEASIBLE means a valid solution was found without proving global optimality. Inspect failures or absence of a solution before proposing action.

### Look inside the decision

Use **Inspect scenario** in **Look inside the decision** to select A, B, C or D. The difference from baseline A reports both cost and unmet demand.

**Resource utilization** lists planned kilograms, the resource limit or demand, and remaining capacity or unmet demand for lots, trucks, destinations, suppliers and distribution centers. A destination's remaining amount means unmet demand; a truck's remaining amount means unused capacity.

**Proposed shipments** lists trip and lot, truck, origin, destination, load, and whether targeted verification is required. This is the proposed set, not a list of approved driver assignments.

**Excluded candidates** explains why candidates were omitted. Read its qualification: allocation competition or a binding resource limit can exclude a candidate even when that candidate is not intrinsically unsafe. The reasons are diagnostics, not a ranking of real suppliers.

### Review and approve a simulated plan

Use an isolated practice workspace for this walkthrough if you are learning or preparing a presentation. Approval changes that workspace's current assignments.

1. Compare A through D and inspect resources, selected shipments and exclusions.
2. Click **Review** on the desired scenario. This saves a pending proposal and opens its review dialog; it does not yet publish driver trips.
3. Inspect cost, unmet demand, checked violations and any proposed lot holds. Enter **Dispatcher name** and **Reason for approval**. Names are self-declared in this local demonstrator, not authenticated enterprise accounts.
4. Choose **Keep under review** to close the dialog without approval. This is not an approval or rejection record.
5. Choose **Approve simulated plan** only after reviewing the proposed action. The server checks the current network revision, recomputes the plan and independently rechecks constraints. A stale or changed proposal is rejected and must be recreated.
6. On accepted approval, the app replaces the current assignment set with this plan, records an audit entry, applies scenario C's proposed holds if applicable and updates Drive. It does not physically dispatch a vehicle or consume real inventory.

The present one-wave model does not decrement the simulated stock as a warehouse shipment transaction when a plan is approved. Stock quantities are constraints for the current allocation exercise, not a continuously reconciled warehouse ledger. Approving another plan replaces the current assignment set rather than appending a second independent wave.

Held, recalled and ineligible lots remain excluded regardless of cost preferences. The hard constraints cannot be traded away for a cheaper solution. A precautionary release is handled separately in Dispatcher desk; it cannot clear a confirmed recall.

### Exercise a disruption and see its consequences

In **Exercise the response workflow**, select a shipment, choose **Event type**, then click **Introduce event**. These are deliberately simulated events. They alter the current network, advance its revision and invalidate all current assignments so a fresh plan can be reviewed. Repeated clicks can accumulate changes; they are not a replay of a single official incident.

| Event type | Present simulator effect | What it does not establish |
| --- | --- | --- |
| road closure | Adds two hours to the selected trip's fixed travel estimate | No real road is closed and no MoDOT record is created |
| severe weather | Adds two hours to that trip estimate | No official weather warning is issued |
| delivery delay | Adds two hours to that trip estimate | No real vehicle progress or arrival is measured |
| refrigeration fault | Changes current simulated cargo temperature to 9°C and makes its assigned truck ineligible | No physical refrigeration diagnosis or sensor stream |
| temperature excursion | Changes the current simulated cargo temperature to 9°C and raises review priority | No laboratory finding, illness estimate or automatic lot hold |
| inventory shortage | Sets the affected lot's available stock to zero | No actual inventory transaction |

**Reset demo** restores the deterministic network and removes current approved assignments. It records the reset in audit history; it does not erase all historical records or saved route projects. Original public/raw datasets are unchanged. Seeded temperature-history points are not a physical real-time sensor feed; an injected current event is not proof of new observed telemetry.

## Route laboratory: test a farm or a multi-location fleet

Use **Route laboratory** for the question, “How could this operation serve these delivery stops with these trucks and planning assumptions?” It is a planning sandbox. Its returning, multi-stop routes are different from Command's one-wave allocation scenarios. A laboratory run does not become a dispatcher-approved plan, even when feasible.

### Choose the operational scale

**Single-farm dispatch** starts with one simulated Columbia-area farm, eight delivery stops and three trucks. One stop is deliberately held so the example demonstrates an exclusion. **Multi-location fleet** starts with two simulated distribution centers, fifteen destinations and eight trucks, including a held delivery assumption. Preset labels can be presented with slightly different capitalization; choose them by their farm or fleet description.

**Your operation** opens **Build your operation**. Selecting it can copy the current preset as a planning template. You may enter real location coordinates, but customer relationships, cargo, lots, capacities and demand remain user-entered planning assumptions. There is no address search, geocoding, customer verification, farm account registration or enterprise tenant isolation.

For presets, set **Available trucks** and **Capacity per truck (kg)**. The bounds are 1–10 trucks and 100–5,000 kg each. For a custom exercise, set each truck's origin and capacity in the editor instead. **Maximum route duration (hours)** bounds a truck's full planned route, including its return to origin and modeled service/delay time; the allowed range is 0.25–16 hours.

Choose **Travel-time source**:

- **Offline estimated travel** uses straight-line distance multiplied by 1.25 and an assumed 65 km/h. Map lines connect stops; they are not actual roads.
- **Public OSRM road service** requests an origin–destination matrix and route geometry. Cache reuse or partial failures can mean that time, distance and geometry have different provenance. Read the separate source labels rather than assuming the whole run is equally current or road-based.

Neither option validates commercial-truck restrictions or incorporates current MoDOT closures into the optimization. Independent road review is provided as a separate attention signal.

### Build a custom operation

The custom editor supports up to 3 origins, 20 delivery stops and 10 trucks. At least one of each must remain. Use the **Copy** template buttons if a simulated layout is easier than starting from a blank exercise. Copying replaces the current unsaved editor inputs.

For **Dispatch origins**, enter a unique ID, name, type (farm or distribution center), longitude, latitude and available stock in kilograms. **Add origin** and its remove control change the draft. If an origin is renamed, the editor updates truck origin references. If an origin is removed, its trucks are reassigned to the first remaining origin; review those assignments rather than assuming they remain unchanged.

For **Delivery stops**, enter a unique ID and name, longitude/latitude, demand, deadline hours, remaining shelf-life hours and an optional planning lot ID. Demand is 1–5,000 kg per stop. Deadlines are up to 16 hours and remaining shelf life up to 168 hours. A blank lot ID receives a fictional PLAN-prefixed key. Each delivery has its own distinct planning lot key; this is not a claim of real traceability. The **Held**, **Recalled (scenario)** and **Eligible** flags explicitly exclude delivery assumptions when appropriate.

For **Trucks**, enter a unique truck ID, dispatch origin, capacity, **Refrigerated** flag and **Eligible** flag. A truck needs an existing origin and 100–5,000 kg capacity. An unqualified or nonrefrigerated truck cannot be used to bypass the planning constraints. Add/remove controls edit this draft only.

Coordinate order is always longitude then latitude. Missouri values look like longitude −92 and latitude 39. Entering these in reverse can place a point incorrectly or fail validation. Names and IDs must be distinct where required; validation messages identify missing or invalid inputs. No map dragging silently replaces coordinates.

### Add a stress assumption, then run

**Ambient temperature assumption (°C)** is a user-specified value between −30 and 55°C, not an automatic read from the weather forecast. **Additional road delay (minutes)** allows 0–360 minutes of modeled delay. **Simulate refrigeration failure** changes the illustrative cargo thermal calculation. It does not diagnose a real truck or create an official hold.

Click **Test dispatch plan**. This runs the constrained route exercise and stores a completed run in local planning storage. Inspect the result before naming/saving a project. If you edit inputs while or after a run completes, the page marks the displayed result as belonging to earlier assumptions; rerun before interpreting or saving it as the new exercise.

Read **SOLVER STATUS**, **TRAVEL DISTANCE**, **SIMULATED COST** and **UNSERVED STOPS** together. The unmet-demand panel lists kilograms and stop IDs that were not served, including held/recalled/ineligible exclusions. Those deliveries are not dispatched and their quantities are not assumed to be waste. The displayed cost uses an illustrative fixed cost per used truck plus a distance term. It excludes many real business costs.

**Truck-by-truck plan** shows each truck's origin, stop sequence, planned load versus capacity, journey duration, source provenance, cold-chain review signal and nearby road geometries. Click **Inspect** on a row to change the cargo projection panel to that truck. The plan includes a ten-minute service assumption at each served stop and returns each used truck to its dispatch origin.

### Read the cold-chain projection correctly

The **cold-chain exposure** panel shows initial cargo assumption, projected final temperature and modeled time above the review level. Its curve is an illustrative physical calculation over that route duration. It is not learned from physical sensors and is not a validated probability of loss of temperature control, contamination or illness.

The shaded **Parameter sensitivity range** varies assumed thermal parameters. It is not a statistical confidence interval. The plotted review level prompts investigation; it does not certify that product is safe below it or automatically condemn product above it. Inspect the listed assumptions before presenting the result.

Road review beneath the results uses captured Missouri evidence; do not assume the laboratory already incorporates the separate Iowa Road intelligence workspace or complete route/state coverage. Saved results retain the source times from their original run.

### Save, reopen and compare route experiments

Use **Saved route experiments** before leaving the laboratory. A draft name alone does not save an operation.

| Control | What happens | Persistence |
| --- | --- | --- |
| Experiment name | Names the project you intend to save | Draft text until a save succeeds |
| Save as new project | Links the completed run to a new named local project | Stored in this app's SQLite database |
| Save next version | Adds the current completed run to an opened project's history | Earlier versions retained; stale concurrent updates rejected |
| Open project | Loads the saved inputs and results into the editor | Replaces unsaved draft inputs on screen |
| Saved version | Reopens a historical project version | Shows its original saved assumptions and source times |
| Export snapshot JSON | Downloads a run's request, result and checksum | A portable snapshot file, not a live refresh or approved plan |
| Export stop sequence CSV | Downloads the saved route's stop sequence | A planning export, not driver instructions |
| Compare selected experiments | Opens a side-by-side comparison of exactly two selected projects | Describes the saved runs; does not recompute them |

Choose the comparison checkboxes for two projects, then click **Compare selected experiments**. Compare fleet size, capacities, travel source, ambient assumption, delay, refrigeration-fault setting, route limit, cost, unmet demand, distance, solver status, violations, fallback status and run date. Different operation definitions are a descriptive comparison, not a controlled claim that one method performs better.

Save is disabled until there is a completed run, the name is long enough, and the displayed run matches the edited assumptions. Unsaved drafts can be lost when leaving/reloading. Local projects are not shared cloud accounts and do not automatically appear in a teammate's separate local database.

### Farm and fleet practice use cases

**A farm tests whether two trucks are enough.** Start with the farm preset and estimated travel. Run and save a three-truck reference project. Change to two trucks while keeping other assumptions fixed, rerun and save another project. Compare distance, unmet demand and constraint checks. The results can remain the same if the third available truck was unused; that is itself useful planning information. Explain any excluded held delivery separately from a vehicle-capacity shortage. No actual farm operation is changed.

**A regional operator compares dispatch origins.** Copy the fleet template into **Your operation**. Review stock at each origin and every truck's assigned origin. Save a reference run. Change a truck's origin or origin stock, rerun, and save a distinct project/version. Inspect how returning routes and unserved stops differ. This illustrates multiple locations without claiming enterprise account functionality.

**A planner explores a delay with refrigeration failure.** Save an unstressed reference. Add a delay and the simulated refrigeration-failure assumption; rerun with the same delivery operation. Inspect route feasibility and the thermal projection. Describe the changed temperature as a modeled consequence of assumptions, not observed evidence that a real shipment is unsafe.

## Road intelligence: inspect independent road evidence

Use **Road intelligence** when you want a separately attributed Missouri/Iowa road-event view or a route comparison between two locations. It does not select cargo, allocate a fleet, dispatch a driver or alter an approved assignment. A corridor's real locations do not create a supply contract.

### Start with source cards

The cards identify **MoDOT traveler information** and **Iowa DOT 511 events**. They show captured record counts, source retrieval times, fixture/stale/unavailable states, query completeness and unusable-geometry counts. A completed provider query is not complete real-world road coverage. Iowa's inspected dated fixture contains 599 point records; that number describes the captured response and can differ from a future refresh. Repeated source event IDs are retained and can lead to repeated proximity matches.

**Inspect MO events** or **Inspect IA events** selects that feed and clears the event filter. **Recheck saved road evidence** rereads saved evidence without deliberately refreshing public providers. **Refresh official road feeds** requests the adapters, subject to their cache cadence; it can reuse a valid saved response. Read retrieval times and any error rather than assuming every click is a new provider download. Refresh is disabled and rejected in an offline rehearsal.

### Browse original event details

Use **Official road feed** to choose the source and **Filter captured road events** to search the listed preview by route, description or identifier. At most 200 records per feed are returned in the source preview. Filtering searches those listed rows, not every provider record. The map displays up to 100 filtered event geometries. Empty search results do not establish that a state has no incidents.

Select an event to open its provider text, route name, identifier, geometry availability and source retrieval time. **Original provider fields** exposes literal saved properties. **Original provider time values** preserves raw clock values without guessing an unverified timezone. An Iowa record-edit timestamp is different from an event's actual occurrence or expiry; a missing interpreted start/end is not silently filled in from retrieval time. Provider attribution, license and terms links identify the original source, not agency endorsement of AEGIS.

### Compare a corridor

1. Select **Planning corridor**, such as Columbia–St. Louis or the Columbia–Des Moines planning example, or enter custom origin/destination coordinates.
2. Use longitude first, then latitude. Choose two different locations. This screen compares endpoints; it is not a fleet allocation or multi-stop itinerary builder.
3. Choose **Road comparison travel source**: **Offline estimated connection** or **Public OSRM ordinary driving**.
4. Set **Event proximity buffer (meters)** between 50 and 2,000. A larger buffer can include parallel roads, other carriageways or nearby unrelated works.
5. Click **Compare planning routes**. Inspect the captured comparison date, each route's distance/duration and difference from the first alternative, and its separate Missouri/Iowa review cards.
6. Select **Route 1**, **Route 2** or another available alternative to change the focused route/review. Click a nearby event to inspect its exact comparison-snapshot details and geometry.
7. Read **Travel source and retrieval** for requested source, actual provenance, provider retrieval, saved-response reuse, stale status or exact fallback reason.
8. Use **Export comparison JSON** to retain the captured request, source evidence and result for review. The export does not authorize a detour or update Drive.

The default estimate draws a straight endpoint connection with an illustrative road factor and speed. It is useful for demonstrating the workflow offline, not determining which real road segment is closed. OSRM may return several ordinary-driving alternatives or fall back to an estimate if unavailable. A route labeled OSRM still lacks commercial restrictions and current closure-aware routing.

Each source/route review shows the total nearby captured geometries, with at most 100 matches listed. Screening uses all supported geometries within the bounded captured feed, including rows beyond the 200-record preview. Missing, malformed or unsupported geometry is counted and excluded. A nearby point may be on another road; it does not describe a closure's extent, direction or current passability.

When inputs or saved evidence change, the displayed routes remain an explicitly older comparison until rerun. A selected **COMPARISON SNAPSHOT RECORD** belongs to that captured comparison; a **SOURCE PREVIEW RECORD** belongs to the source preview you browsed. Their retrieval times and geometry can differ. This distinction prevents a newer-looking preview from silently rewriting a previously exported comparison.

### Cross-state planning use case

A dispatcher wants to review a potential Columbia-to-Des Moines journey. Open the corridor example, read both source cards, choose OSRM if network access is available, and compare. Review Missouri matches and Iowa matches separately for each alternative, inspect event text and source age, then export the comparison for discussion. A route with fewer listed matches is not automatically safer or eligible. Other states, local-road coverage, event schedules and commercial restrictions still need appropriate validation. If an operational decision is needed, return to the separate human dispatcher workflow; Road intelligence does not approve it.

### Common misunderstandings to avoid

- **“The map shows a truck, so we track it.”** Command markers are illustrative; Drive's position is a simulated dispatch-origin reference. No physical GPS feed is connected.
- **“Scenario D rerouted the truck.”** D substitutes eligible simulated lots on fixed candidate trips. Road alternatives are a separate comparison.
- **“Scenario B approval completes inspection.”** It can create assignments with verification pending. A dispatcher must record the separate review; the checklist is not laboratory testing.
- **“A saved farm plan appears in Drive.”** Planning runs and projects do not publish driver assignments. Command approval governs the current operational assignment set.
- **“Zero waste means the business will never waste food.”** It reflects the present planning horizon and treatment of unsent inventory.
- **“The lower-cost scenario is always better.”** It may leave more demand unmet. Read quantities and exclusions alongside cost.
- **“Freshly opened means freshly observed.”** A saved project, captured comparison, fixture or cached provider response retains its original source time.
- **“No nearby road events means the route is clear.”** Coverage, geometry, event schedules, reported-event completeness and truck eligibility remain limited.

These chapters were checked against the current Command, planning, optimization and road-workspace implementations. Use the dated execution reports elsewhere in this guide for what was actually tested; the walkthrough descriptions themselves do not certify new provider success or a live operational deployment.
