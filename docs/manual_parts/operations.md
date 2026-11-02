## Command center: understand the current operation

Use **Command center** when you want to see the simulated Missouri distribution network, investigate a shipment, compare operational responses, or propose a dispatcher decision. This is the main control tower. The map combines real geography and public evidence with fictional logistics; the presence of an official facility beside a simulated trip does not establish a supply relationship.

The standard scenario has 3 simulated suppliers, 2 distribution centers, 15 destinations, 8 refrigerated trucks, 12 lots and 24 candidate shipments. These are reproducible planning entities, not a live business account. The scenario reference date is October 26, 2026. An October 26 cargo trace is not today's observed temperature. Different saved operator states can produce different current results.

### Start with the delivery outlook

**Where could this delivery plan run into trouble?** calculates a read-only planning estimate when Command opens. Read **Unserved demand**, **Deadline pressure** and **Cargo checks**, then use **Inspect SH...** to open a candidate's trip detail. **Check road alternatives** opens the separate Road intelligence workspace; it does not apply a detour.

Choose **Extra road delay**, then **Estimate impact**, or use **Try a 1-hour delay**. The interface offers 0, 30, 60, 120 or 240 added minutes. Delay is applied uniformly to every candidate's planning duration, including trips the allocation never selects. It is your assumption, not a delay inferred from a closure or weather warning. **Check current inputs** resets the additional assumptions to no extra delay, 30°C ambient and no additional fault.

Expand **Cargo assumptions** to set ambient temperature from −20 to 45°C and optionally assume a refrigeration fault on a simulated truck. A fault also excludes that truck from the preview allocation. Previously recorded simulated faults remain in effect. Ambient temperature is a chosen assumption, not fetched weather; cargo readings are simulated. Each thermal calculation checks the earlier of modeled arrival and six hours. A trip beyond six hours is explicitly labeled **at six hours; not yet arrived**. Review flags describe the modeled window, not measured cargo failure.

The backend recomputes current-input scenario A and the four A–D responses under the chosen assumptions using the actual allocation solver. Stock, capacity, demand, deadlines, holds, recalls and eligibility still constrain the results. **Compare the four preview responses** shows solver status, cost, selected trips, unmet demand and constraint checks. The comparison baseline is recomputed scenario A, not the approved driver-assignment list. **Which destinations have unmet demand?** identifies the remaining service gaps; **Why?** on an unselected candidate explains recorded exclusions.

This is a deterministic what-if calculation using uncalibrated thermal assumptions. No prospective delay or cargo-failure prediction skill has been established. The saved FSIS sampling-model evaluation is separate. Projected temperatures do not replace current cargo readings, impose holds or become newly observed excursions in scenario C. No result changes routes, inventory or driver assignments.

**Export outlook JSON** saves the captured assumptions and result. Editing inputs leaves that result and its export unchanged until a new estimate succeeds; an older network revision is labeled. Read **How this estimate works** before presenting it as evidence. A failed calculation is reported; reload the current plan when requested rather than presenting an older estimate as current.

### Read the four summary cards

| Card | What it tells you | How to use it |
| --- | --- | --- |
| NETWORK SHIPMENTS | Number of candidate simulated shipments and destinations | Understand the size of the current exercise; these are not all approved trips |
| COLD-CHAIN REVIEW | Shipments whose current simulated cargo value exceeds the 4°C review level | Find cases to investigate; this is not an illness probability or a regulatory disposition |
| APPROVED ASSIGNMENTS | Current dispatcher-approved simulated trips, with acknowledgment count | Check whether a proposed plan has actually been approved and whether drivers acknowledged it |
| PUBLIC ENDPOINT PROBES | Successful saved HTTP probes divided by registered probes | Inspect connectivity evidence; a successful documentation page does not prove full or current data coverage |

The **Review queue** combines simulated excursions, active simulated holds and a small preview of dated NWS alerts. **Inspect SH...** selects the corresponding candidate and brings its trip detail into view. **Open lot review** navigates to Dispatcher desk. **Inspect official evidence** opens Sources & evidence. The header bell, **Open review queue**, returns to this queue from another Command workspace. These are navigation actions; they do not approve a response, impose a hold or send a message. A count can exceed the five cards displayed in the preview.

### Explore the distribution map

Start with a map view: **Plan deliveries** focuses on logistics and any requested route; **Check weather** adds warning areas; **Review roads** adds captured road incidents; **View facilities** compares official locations with the fictional network. These presets change visibility only. They do not recalculate or approve a delivery plan.

Below the map, **What is on this map?** gives each layer's purpose, available counts or missing-data message. Use its checkboxes for a custom view and **What is this for?** for one layer's explanation and available source times. A layer switch cannot download missing evidence or generate a road route. The compact symbol guide explains the fictional locations and dashed shipment links.

Use **Show allocation on map** to choose which simulated origin-destination links are drawn. The selector is labeled **Map allocation** for accessibility. **All ... candidate shipments** shows the available candidate set; **Scenario A/B/C/D** shows that response's proposed trips; **Current approved assignments** shows the recorded assignment set. The caption reports the displayed scope and count. A proposed or approved lot can differ from the candidate's original lot, so inspect the popup and assignment detail before reading a line as the original candidate. If there are no approved assignments, the approved overlay is empty rather than silently showing candidates.

Changing an overlay selects a view of an allocation, not a road route. The dashed connections still join fixed origins and destinations. If the currently selected candidate is outside the chosen overlay, the caption explains why its connection is hidden. A scenario row's **Show on map** control changes to that scenario's overlay and brings the map into view; it does not approve the scenario.

| Layer | What appears | Meaning |
| --- | --- | --- |
| Simulated deliveries | Fictional locations, shipment links and truck markers | A distribution-network exercise; dashed links join origins and destinations rather than following roads |
| FSIS facilities | Coordinates from the supplied official establishment directory | Real source locations; no simulated contract or shipment relationship is implied |
| Weather warnings | Captured official alert polygons or points where geometry is supplied | Dated public warnings, not measurements of cargo temperature |
| Road incidents | Captured Missouri road-event points or lines | Independent road evidence; proximity does not establish that a route is blocked |
| Requested route | The requested OSRM alternatives or labeled estimated fallback | A route comparison, not a dispatched detour or certified truck route |

Click a simulated shipment line or truck marker to select its associated trip. A truck's Command marker is an illustrative midpoint of an origin-to-destination connection, not GPS. Click a location or evidence geometry for its popup. Zoom and pan to investigate the area. The OpenStreetMap base map needs internet; a missing tile is different from a missing shipment or provider record.

A fresh Command view starts without an automatically loaded cached reference road route. Its dashed logistics links are not road geometry. To produce road geometry for the selected trip, use **Request road route** in the trip panel. Changing the selected shipment or network revision clears an earlier shipment-specific road comparison; request the current trip again. The map focuses on the selected candidate's origin and destination when it has no usable road comparison.

### Inspect cargo and weather separately

In **Cold-chain & trip detail**, use **Select shipment** to change the candidate truck, destination, cargo quantity, current simulated temperature and displayed seeded temperature history together. A context message states whether that candidate currently has an approved driver assignment and identifies the approved truck and lot separately from the candidate's original lot. A candidate is not an assigned trip simply because it is selected.

The fixed trip estimate uses straight-line distance multiplied by 1.25 at an assumed 65 km/h. Requesting an OSRM road route does not silently replace the allocation model's fixed travel assumptions. The chart is the seeded historical simulation trace. An injected event can change the current cargo reading without rewriting those history points; the chart is not a newly acquired sensor stream.

**Request road route** asks OSRM for ordinary-driving geometry and available alternatives. While it runs, the button says **Finding road route...** and a nearby status explains what is being computed. A successful result brings **Route alternatives & road review** into view. A failure is reported by the trip control; unusable geometry is not presented as a successful comparison. An estimated fallback is visibly labeled when that is what was returned.

The result shows distances, travel estimates and captured MoDOT geometries within a 250-meter buffer. **Highlight alternative 1/2/...** changes the comparison selected for the map. **Focus route map** brings that map into view; enable **Requested route** if you previously hid it. **Export route comparison JSON** downloads the captured comparison and selected alternative without creating an assignment. No alternative button changes a lot, stop order, fixed allocation estimate or driver instruction.

Read whether geometry is estimated, whether road evidence is stale or incomplete, and whether the route label belongs to the selected shipment. The comparison displays Command's planning duration separately from the road-service estimate; a difference is not a measured time saving. Nearby parallel roads and duplicate point/line records can produce matches. Zero matches is not road clearance. OSRM does not validate truck height, weight or other commercial restrictions, incorporate the simulated event delay, or automatically avoid current DOT closures.

**Weather exposure** is an Open-Meteo forecast for Columbia. Its first timestep and chart are ambient forecast values, not measurements from the cargo. The selected trip's simulated cargo trace, a weather forecast, historical station observations and the laboratory's temperature projection are four different things. The current system has no validated weather-to-FSIS predictive linkage.

### Compare the four response scenarios

**Compare operational scenarios** is a one-wave allocation exercise. It chooses among fixed candidate shipments subject to stock, demand, truck, supplier and distribution-center constraints. It does not build a multi-stop vehicle itinerary. **Recompute** runs the current scenario calculations and reports a completion time, network revision and result count below the table. It explicitly says when totals and selected trips match the previous run. That is a valid deterministic result when inputs are unchanged; it does not mean the button was inactive. Failed or incomplete recomputations show an error instead of a successful receipt. Nothing is approved by recomputing.

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
3. Inspect cost, unmet demand, checked violations and any proposed lot holds. Expand **Inspect ... proposed assignments and lots** to read each trip, truck, proposed lot, destination and load. A substituted lot is labeled. Enter **Dispatcher name** and **Reason for approval**. Names are self-declared in this local demonstrator, not authenticated enterprise accounts.
4. Choose **Keep under review** to close the dialog without approval. This is not an approval or rejection record.
5. Choose **Approve simulated plan** only after reviewing the proposed action. The server checks the current network revision, recomputes the plan and independently rechecks constraints. A stale or changed proposal is rejected and must be recreated.
6. On accepted approval, the app replaces the current assignment set with this plan, records an audit entry, applies scenario C's proposed holds if applicable and updates Drive. It does not physically dispatch a vehicle or consume real inventory.

If approval fails, **Approval did not complete** appears inside the still-open dialog, where the decision was being made. Do not treat an attempted click as an approval. A stale proposal needs a fresh review of the current network rather than a repeated approval of old inputs. After success, select **Current approved assignments** on the map or open Dispatcher desk and Drive to inspect the actual published set.

The present one-wave model does not decrement the simulated stock as a warehouse shipment transaction when a plan is approved. Stock quantities are constraints for the current allocation exercise, not a continuously reconciled warehouse ledger. Approving another plan replaces the current assignment set rather than appending a second independent wave.

Held, recalled and ineligible lots remain excluded regardless of cost preferences. The hard constraints cannot be traded away for a cheaper solution. A precautionary release is handled separately in Dispatcher desk; it cannot clear a confirmed recall.

### Follow the next action in Dispatcher desk

**Handle a delivery decision in three steps** starts with the actual approved-trip count. With no approved trips, **Choose a response plan** opens Command; otherwise the first step can open the approved driver view. Next, **Add name and reason** takes you to the required decision-record fields. Identity is self-declared in this local demonstration.

The final step points to outstanding driver reports first, then targeted verification, then instructions and acknowledgment readiness. Its buttons focus the relevant section; they do not submit a decision. Disabled controls explain which information is missing. To change operational state, review and submit the specific report, hold, verification or instruction form. A projected temperature or an assistant suggestion never submits it for you.

### Exercise a disruption and see its consequences

In **Preview a disruption before applying it**, choose the candidate with **Select shipment**, then choose **Event type**. The panel produces a before/after experiment before you decide whether to alter this workspace. These are deliberately simulated effects, not live incidents or observations.

| Event type | Present simulator effect | What it does not establish |
| --- | --- | --- |
| Road closure | Adds two planning hours and reduces the selected candidate's deadline margin by two hours | No real road is closed, no MoDOT record is created and no road path is recomputed |
| Severe weather | Adds the same fixed two-hour planning delay and reduces deadline margin | No official warning or weather-derived delay estimate is produced |
| Delivery delay | Adds two planning hours and reduces deadline margin | No physical progress or arrival timestamp is measured |
| Refrigeration fault | Sets current simulated cargo to 9°C, raises review priority to high and makes the shared truck ineligible | No physical diagnosis; other candidates using that truck can also be affected |
| Cargo temperature excursion | Sets current simulated cargo to 9°C and raises review priority to high | No laboratory finding, illness probability or automatic lot hold |
| Inventory shortage | Sets the candidate's original shared lot inventory to zero | No warehouse transaction; other candidates using that lot can also be affected |

1. Click **Preview event impact**. The server reads the current simulation and computes all four allocation scenarios before and after a copy of the selected event. This step does not write an event, clear assignments or create a proposal.
2. Read **direct changes**: only changed fields are listed, with before, after and numeric delta where applicable. The supported fields include planning travel duration, deadline margin, simulated cargo temperature, shared lot inventory, truck eligibility and operational review priority. These relative hours are not a departure clock or a live ETA.
3. Read **Allocation outcomes: before → after**. Compare selected trips, simulated logistics cost, unmet demand, solver status and violations. Expand **Inspect changed shipments, resources and limitations** for shared resources, added/removed trips, lot substitutions and changed proposed holds. The same totals can hide different trip choices. An optimizer difference is not proof of why it made that choice.
4. Inspect the warning that road geometry and stop order stay unchanged, and the count of **all ... approved assignments** that applying would clear. Unrelated trips are included. Use **Export event impact JSON** if you want a captured read-only comparison for discussion.
5. If changing this simulation is intended, check **I intend to change this simulation and clear all approved assignments.** Then click **Apply previewed event**. The checkbox and apply control remain unavailable for an older comparison after the event, selected shipment or network has changed. The server checks the displayed revision and preview checksum against the actual state before applying; it does not trust consent to an obsolete comparison.
6. Read the applied-event receipt: affected candidate, new revision and actual assignment-removal count. **Compare refreshed response plans** brings the recomputed allocation table into view. Command also retains a separate **Confirmed event receipt** even if the entire network becomes unavailable and the simulator panel disappears. **Export confirmed event JSON** saves that exact result; **Dismiss confirmed receipt** only hides the message. Reload application data before another action after a refresh failure. A failed or unverified apply is not shown as successful.
7. Review and propose a fresh allocation, then use the separate human approval workflow to publish new assignments. Applying an event does not create replacement assignments or a dispatcher-approved detour. An export after a successful apply includes the recorded receipt and identifies that stage separately from a read-only preview.

Repeated delay events accumulate two-hour increments. Some other repeated events can produce no further direct field changes because cargo is already 9°C, the truck already ineligible or stock already zero. The panel explicitly warns when its direct values are unchanged. Applying even that event still records another event, advances the revision and clears every approved assignment; do not click Apply just to make a chart move.

**Reset demo** first opens **Reset the simulated network?** Read its assignment count and stale-proposal warning. **Keep current network** cancels. **Confirm reset simulation** restores the deterministic network, removes approved assignments and advances the revision; a failed reset remains visible inside the dialog. The reset is recorded in audit history. It does not erase all historical records or saved route projects, and original public/raw datasets stay unchanged.

### A first read-only walkthrough

Start in Command, read its **WHAT YOU ARE LOOKING AT** guide, and select a candidate in **Cold-chain & trip detail**. Request its road route and inspect the result that comes into view. Highlight an available alternative, focus the map, and compare the road-service estimate with the candidate's separate planning input. Then click **Show on map** on a scenario row to see its selected allocation links. This changes a display, not an approved route.

Preview **Delivery delay** for the same candidate. Read the two-hour duration change, reduced deadline margin and all four allocation outcomes without checking consent or applying. Export the comparison if useful. Use **Recompute** to confirm what the unchanged current network produces; the unapplied preview has not altered it. When you are ready to practice changes, use a verified isolated rehearsal and follow the explicit apply, fresh proposal, approval and parked-driver steps.

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

To inspect a particular candidate, start in Command's delivery outlook and choose **Compare roads for SH...** on that row. Road intelligence opens with that candidate's named origin, destination and captured network revision. Click **Compare this journey** to calculate its route comparison; opening the workspace alone does not run it. The sidebar's **Road intelligence** and the outlook's general **Check road alternatives** button open the named journey examples instead. Editing an endpoint or choosing another journey detaches candidate attribution.

**Export comparison JSON** preserves the compared candidate ID, endpoints and network revision when the comparison came from Command; a later edit does not rewrite that captured result. Read any older-input warning and reopen the candidate from Command to use current endpoints. **Compare delivery responses in Command** returns to the current operational scenario table. The outlook's **Review current response plans** reaches the same table; its extra-delay and cargo assumptions remain in the preview. These links do not approve a trip, transfer route geometry into an assignment or change Drive.

Start with **Check a journey in three steps**: **Choose the journey**, **Compare travel options**, then **Read the notices, then decide**. The first button takes you to the journey selector. **Compare this journey** runs the calculation; the last step opens a nearby notice or focuses the comparison result. When inputs change, the guide asks you to run the comparison again. No notices is a coverage-limited result, not road clearance.

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
