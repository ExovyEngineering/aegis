# AEGIS Master User Guide

Generated November 02, 2026 at 11:34 AM CT. Complete product handbook.

This master file is assembled from docs/manual_parts/ and dated reports. Edit those sources and rebuild to keep PDF, HTML and Markdown consistent.

## Start here: what AEGIS does

The November 1 five-task review adds a separate integrated Missouri research
study in **Model evaluation**, and a five-task guide plus food-volume/service
policy comparisons in **Project brief**. The shorter final PDF covers all ten
menus and a presentation idea. The owner has disclosed that **Kiro was not used**;
that challenge criterion is not met. An installed IDE or prepared specs are not
execution evidence. The full application remains independently runnable.

AEGIS means **Adaptive Early-warning & Guidance for Integrated Supply Chains**. We built it to help a regional poultry distributor examine food-safety evidence, understand disruption scenarios, compare constrained operational responses and keep a human dispatcher responsible for consequential decisions.

The core demonstration is centered on Missouri: Columbia, Kansas City, Jefferson City, Springfield and St. Louis. An optional Iowa road-evidence layer supports a cross-state planning example. National historical food-safety data support the retrospective modeling study; this is not a separately validated Missouri-only predictor.

For a quick start, open **Command center** and use **Try a 1-hour delay** in the
delivery outlook. Inspect a trip, then check road alternatives. The outlook is a
conditional planning projection over simulated inputs; the separate measured
FSIS model does not establish prospective delay or consumer-illness accuracy.
In **Evidence assistant**, type **chicken** or click a question for guided help.

The simplest way to read the product is a sequence: **inspect evidence → explore a response → check constraints → record a human decision → inform the driver → retain the record**. Some screens are planning experiments and never enter that dispatch sequence. This guide explains those boundaries as well as the controls.

### Who can use the current application?

| Person or situation | Useful workspaces | What they can learn or practice |
| --- | --- | --- |
| One farm sending refrigerated trucks | Route laboratory, saved experiments, Road intelligence | Test custom origins, available stock, truck capacity, stops, deadlines and route assumptions |
| Regional distributor or multi-location fleet | Command, Route laboratory, Dispatcher desk, Drive | Compare fixed-network responses and separate multi-origin route experiments; practice approval and driver communication |
| Driver or field operator | Dedicated AEGIS Drive | Inspect a dispatcher-approved trip and report or acknowledge while safely parked |
| Data/science teammate | Sources & evidence, Model evaluation | Inspect original fields, missingness, dated coverage and measured model results |
| Presenter or reviewer | Project brief, guided rehearsal, this handbook | Understand the product, practice an isolated sequence and find recorded evidence |

These are use cases, not production account types. Everyone on one local server shares its simulated state. Names entered into decision forms are self-declared. The application does not currently provide authenticated roles, organization isolation, subscription plans or a corporate account system. Farm/fleet presets change planning scale, not account permissions.

### Keep four kinds of information separate

| Kind | Examples in AEGIS | How to read it |
| --- | --- | --- |
| Real public evidence | Official recalls, establishment directory records, NWS warnings, DOT events, historical FSIS/CDC/USDA exports | Read the source, scope, observation or provider time, retrieval time and missingness |
| Simulated operations | Suppliers, supply contracts, lots, trucks, shipments, inventory, demand, cargo telemetry and fuel | Reproducible fictional examples used to demonstrate a workflow |
| Planning estimates and projections | Offline travel factor, solver costs, illustrative cargo-temperature curves | Outputs conditional on stated assumptions; they are not observations or certified safety findings |
| Measured software/science evidence | Executed tests, recorded holdout metrics, browser checks, saved proposal and audit records | Evidence with a specific date and scope; a pass does not guarantee future service uptime |

Real establishment coordinates do not prove that the simulated distributor buys from that facility. A real road-event record does not prove a fictional shipment encountered it. A projected temperature is not a sensor measurement. A sampling-positive result is not a consumer illness probability.

### What is already available, and what is not?

Available now: the ten connected workspaces in this guide; deterministic network/event simulation with read-only before/after previews; four allocation responses; separate candidate, proposed and approved map overlays; selectable road-route comparisons and captured exports; constrained farm/fleet route experiments; saved planning versions; explicit approval, holds and instructions; a parked-use driver mode; separate public/historical evidence; measured retrospective model evaluation; guided isolated rehearsal; and local backup/recovery tools.

Still outside the implemented product: live physical sensors or vehicle tracking, native phone-app distribution, commercial truck certification, automatic closure avoidance, production accounts, cloud hosting, evaluated language-model advice, isolate-level genomic reconstruction and a validated prospective illness forecast. These are recorded future extensions or scientific gaps. The Evidence assistant provides deterministic cited summaries; an optional, unverified Ollama connector can select a topic but cannot author facts or perform actions.

Genuine Kiro specification execution, final report/rubric author review and the timed team presentation remain separate submission tasks. An installed IDE, a generated document or a successful automated demonstration does not complete those tasks.

## Find your way around the application

The desktop control tower is **AEGIS Command**. Its navigation opens these ten workspaces. Operations appear first; driver work follows dispatcher review, and Sources & evidence is last. The mobile navigation offers the same workspaces in a horizontally scrollable bar; the dedicated Drive URL removes the Command navigation to give drivers a simpler surface.

| Navigation label | Main question it answers | Does simply reading it change dispatch? |
| --- | --- | --- |
| Command center | What does the simulated network look like, and how do four responses compare? | No; event/reset and explicit approval controls do change local state |
| Save the Load | Can a temperature-exposed lot reach a closer recipient, and how should FEFO change the picks? | Replay changes a stored experiment; separate human approval changes the simulated plan |
| Route laboratory | How could one farm or a multi-origin fleet serve these stops under assumptions? | No; even saved laboratory runs do not dispatch |
| Road intelligence | What do captured Missouri/Iowa road records say near these route alternatives? | No; comparison is read-only planning |
| Dispatcher desk | What did a driver report, and what human review, hold or instruction is recorded? | Reading does not; submitted decisions can change assignments/holds/instructions |
| AEGIS Drive | What assignment and instruction has the dispatcher approved for this truck? | Reading does not; parked acknowledgments and reports create records |
| Evidence assistant | How do captured facts explain scenario tradeoffs, a shipment, model limits or the driver workflow? | No; it only returns cited explanations and navigation |
| Model evaluation | What was actually measured in the historical FSIS study? | No; opening this view never trains a model |
| Project brief | Where are the master guide, shorter status brief, feature register and rehearsal tools? | Document downloads do not; recording an isolated rehearsal writes its practice record |
| Sources & evidence | Where did each evidence layer come from, and what coverage is missing? | No; source refresh can update caches, not dispatch |

### Common controls and labels

**Recent activity**, in the header beside the bell, opens **Activity history**
inside the current workspace. It shows actions actually present in the local
audit table. Filter by **Recorded action** and an **Explicit shipment ID**, then
click **Apply activity filters** to produce a new captured result. Draft filter
edits do not change the records or export until applied. **Load older activity**
continues the same snapshot; new actions appear after **Refresh activity**.
**Export captured activity JSON** downloads the pages already loaded. Source
details expose the actual raw payload and any unreadable-record error.

Activity is a recorded internal history, not an authenticated or complete replay
of every click. Actor names are self-declared. Map changes, unapplied previews and
computed routes do not create decision records. Shipment filtering matches only
an explicitly recorded top-level ID; an approval covering a plan is not silently
linked to every trip. A workspace or current-trip link only navigates, and the
historical entry can describe an earlier state. Close the panel to return to the
page beneath it; there is no tenth workspace or new dispatch authority.

Each Command workspace starts with **WHAT YOU ARE LOOKING AT**: a short explanation of the page, a visible description of what it can change, and two links to connected workspaces. Expand **How this connects** for the plain-language workflow. These links navigate; they do not approve a plan or apply an event. The guide closes its expanded details when you change pages. Dedicated Drive omits it to keep the driver surface simple.

**Reload application data**, the header refresh button, rereads the main app's saved network and supporting data, including recomputed allocation scenarios. It does not independently refresh every public provider, retrain a model or reset the network. Individual workspaces have their own refresh/recheck controls, described later. The header bell, labeled **Open review queue**, opens Command and focuses its review queue. The avatar is a visual status element, not a sign-in form or account-settings feature.

After **Recompute**, read the completion time, network revision and number of response plans. If totals and selected trips match the previous calculation, the system says so. An unchanged result can be the correct outcome when the inputs are unchanged; it is different from a request that failed or never completed. Route requests, event previews, applied events and approvals have separate outputs and errors beside the relevant controls.

**SIMULATED OPERATIONS** and the scenario reference date describe the exercise. They do not describe current live trucks. Source timestamps are separate. Green, amber and red status pills must be read with their text: green does not mean an agency certified a product or truck route. A success notice appears after an accepted action; an error or stale-version notice means stop and reread the current context before retrying.

**Pending**, **approved**, **acknowledged**, **verification recorded**, **held** and **resolved** mean different things. A pending proposal is not an assignment. A driver acknowledgment is not targeted verification. Resolving an incident does not release a lot. A released lot is not automatically reassigned. Read the workflow chapters before treating one label as a substitute for another.

### Understand what changes a route

| Your action | Result to look for | Effect on the current operation |
| --- | --- | --- |
| Toggle evidence layers or change the map allocation | Different visible geometry or candidate/proposed/approved links | Display changes only |
| Request a road route and highlight an alternative | A road comparison, distances and travel estimates | No replacement of Command planning inputs or driver instructions |
| Preview an event | Direct before/after values and four recalculated allocation comparisons | Read-only; existing state and assignments stay unchanged |
| Apply a previewed event after consent | An applied-event receipt and refreshed simulated plans | Changes the simulation and clears all approved assignments; does not reroute |
| Run a farm or fleet experiment in Route laboratory | Computed stop sequence, truck allocation and road or estimated geometry | Independent planning result; it does not dispatch or replace Command trips |
| Approve a reviewed Command proposal | Recorded simulated assignments and any approved proposed holds | Changes the approved work for Drive; it does not validate a commercial-truck detour |

Use **Route laboratory** when your question is how to redesign a farm or multi-stop fleet journey. Use **Command center** when your question is which fixed candidate trips and eligible lots should be included in a one-wave response. Those are related decisions, but a visible map line is not proof that one tool changed the other's plan.

### Useful reading paths

- **First-time teammate:** read this orientation, the Command chapter, the connected driver walkthrough, Sources & evidence, Model evaluation and the glossary. Return to detailed control tables when practicing.
- **Farm/fleet planner:** read Route laboratory and Road intelligence, then the planning-versus-dispatch and storage explanations. Use custom inputs without implying that the presets are actual farm businesses.
- **Dispatcher/driver pair:** read Dispatcher desk, AEGIS Drive and the guided practice chapter together. Use an isolated rehearsal for actions.
- **Presenter:** read the science boundaries, the Project brief/rehearsal chapter and the presentation checklist. Use the shorter project brief for status; use this handbook to learn the details.

## Open the site and choose a safe practice workspace

The ordinary local app is available at **http://127.0.0.1:8000** while its server is running. Dedicated Drive uses **http://127.0.0.1:8000/?mode=drive**. These are addresses on the current computer, not publicly deployed team links. A teammate normally runs a separate checkout or reviewer package on their own computer; GitHub shares code, not one automatically synchronized live database.

If the local server is stopped after setup, double-click **Start-AEGIS.cmd**, or
open PowerShell in the project folder and run:

```powershell
.venv/Scripts/python scripts/start_local.py
```

The launcher builds current frontend source, checks the operator configuration
and starts the backend in that terminal. Leave it running. Ctrl+C stops only its
owned child. If another service already occupies the port, it reports that
listener without killing or rebuilding it; an existing AEGIS backend's freshness
is unverified until you stop its known terminal and relaunch.

The documented setup in README.md and CONTRIBUTING.md covers installing
dependencies on a different computer. The included reviewer ZIP contains a
prebuilt frontend. Use **Start-AEGIS.cmd --no-build**, or add **--no-build** to
the Python command, to inspect and serve those existing assets without Node or a
React rebuild. This mode does not establish source freshness. **--check-only**
diagnoses configuration/assets/listener without starting, building or opening
SQLite. No launcher automatically downloads dependencies, resets original data
or repurposes an isolated rehearsal configuration as the operator app.

### Practice actions in an isolated rehearsal

Before injecting events, resetting a demo or walking through approvals for a presentation, start a separate practice server:

```powershell
.venv/Scripts/python scripts/start_rehearsal.py --port 8001
```

Open the URL it prints. Check the persistent **ISOLATED REHEARSAL** banner and the unique session identity. Project brief also shows **Verified isolated rehearsal** inside its practice panel. The launcher creates a fresh UUID database under data/rehearsals/ and preserves the operator's normal database. Adding `?mode=rehearsal` to the ordinary operator URL only opens a view; it does not create isolation.

The default rehearsal is offline at the backend: it uses dated fixtures, rejects provider refresh and returns labeled route estimates. Browser map tiles and deliberately opened external source links can still need internet. Keep the rehearsal terminal running. If its port is occupied, choose another unused port with the launcher rather than terminating an unrelated service. Port 8000 is reserved for the operator app.

Rehearsal and ordinary operator state are separate. An approval in one server will not appear in Drive on another port. Use Command and Drive from the same rehearsal URL during a practice sequence. Do not reset port 8000 to prepare a presentation.

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

## Dispatcher desk: turn reports into recorded decisions

**Use this workspace when:** a driver reports a concern; you need to review an approved trip; you want to record an explicit lot hold or release; or you need to send and track a dispatcher instruction.

Open **Dispatcher desk** in the main navigation. It shares the current application's simulated database with Command and Drive. It does not manage a second, independent fleet. The desk checks for local updates every 15 seconds. That check does not refresh weather, roads or recalls.

An **assignment** is a trip that a dispatcher has already approved in Command. A shipment appearing on the Command map is not necessarily an approved assignment. Until a response scenario is approved, the desk can show lots and an empty inbox while having no approved trips to inspect or instruct.

### Begin with the Decision record

The left panel supplies the identity and reason used by the decision controls elsewhere on the desk.

| Control | How to use it | What it changes |
|---|---|---|
| **Reviewing dispatcher** | Enter a name, at least two characters after spaces are removed from the ends. | Typing is only a draft. A submitted decision stores the name with its record. This is a self-declared name, not an authenticated account. |
| **Decision reason** | Enter the evidence and operational rationale, at least five characters. | Typing is only a draft. The reason is saved when an action succeeds. Update it for each materially different decision. |
| **Refresh desk** | Reload current assignments, incidents, lot status and network revision. | Reads local state; it does not approve a plan or contact public data providers. |

The name is limited to 100 characters and the reason to 1,000. Empty or whitespace-only identification does not enable a decision. Read the success or error message after every action: a button click alone is not evidence that a decision was saved.

The **Network revision** is a version number for the current simulated operational state. A later event, hold, release, reset or plan approval can make a decision based on an older revision stale. Refresh, inspect the changed facts and make a new decision. Do not interpret a stale-version rejection as permission to bypass the check.

### Dispatch readiness review

This panel answers: **What recorded constraints or workflow steps still need attention for an approved trip?** It is a diagnostic checklist. It does not send a truck, consume inventory, release a lot, certify food safety or clear a commercial route.

The four counts show **Approved trips**, **Constraint blocks**, **Review outstanding** and **Listed checks passed**. Use **Readiness status** to filter the approved assignments, then **Trip to inspect** to choose one. The selected trip displays its shipment, truck and lot identifiers, followed by individual results and their evidence. **Refresh readiness** repeats the local check. **Scope of these checks** expands the interpretation limits.

The three possible overall labels mean:

| Label | Meaning | Appropriate next step |
|---|---|---|
| **Blocked by a constraint** | At least one hard eligibility, resource or timing check failed. | Inspect its evidence. Resolve the underlying simulated condition and review a fresh plan; an acknowledgment cannot override it. |
| **Review outstanding** | The hard checks passed, but a required human workflow record is absent or incomplete. | Complete the applicable assignment acknowledgment, current instruction acknowledgment or targeted verification. |
| **Listed checks passed** | All checks in this limited checklist passed for the captured local state. | Continue human review. This is not departure authorization or a finding that the food or road is safe. |

Each approved trip has these sixteen checks:

| Check shown in the interface | What it checks |
|---|---|
| **Current canonical shipment** | The approved record refers to a known simulated shipment and has a consistent identifier. |
| **Current shipment assumptions** | Origin, destination, truck, quantity, planned travel and deadline still match the current shipment. Eligible lot substitution is allowed where the approved scenario supports it. |
| **Lot eligibility and disposition** | The lot exists, is eligible, and is neither held nor recalled in the simulation. |
| **Truck eligibility** | The assigned simulated truck is eligible. |
| **Refrigerated truck** | The truck is configured as refrigerated. This does not verify physical equipment. |
| **Positive cargo quantity** | Cargo quantity is a finite number greater than zero. |
| **Planned delivery deadline** | Planned travel fits the assigned delivery deadline. |
| **Planned lot shelf life** | Planned travel fits the lot's modeled shelf-life assumption. |
| **Allocated lot inventory** | All approved trips using that lot fit its available modeled stock. |
| **Allocated truck capacity** | All approved trips allocated to that truck fit its one-wave modeled capacity. |
| **Allocated origin capacity** | Aggregate allocation fits the distribution center's capacity. |
| **Allocated supplier capacity** | Aggregate allocation fits the lot supplier's capacity. |
| **Destination demand limit** | Aggregate allocation does not exceed the destination's modeled demand. |
| **Driver assignment acknowledgment** | The driver has acknowledged this approved assignment while parked. |
| **Current instruction acknowledgment** | The latest separately versioned dispatcher instruction has been acknowledged, or no separate version is outstanding. |
| **Requested targeted verification** | A matching, complete dispatcher checklist exists if this assignment requests scenario-B verification. |

The first thirteen checks are hard checks. The last three are workflow checks. Aggregate quantities are checked across the current approved allocation, not independently for each row. The model is a single dispatch wave; this panel does not establish multi-stop vehicle sequencing, physical stock movement, live road clearance or legal driving-hours compliance.

Results have their own checked time and network revision. If the desk and checklist captured different revisions, the interface suppresses the mismatched result and asks you to refresh. An empty panel means there are no approved assignments, or none match the selected filter; it does not mean all proposed shipments passed.

### Targeted verification review

**Use case:** scenario B requests a closer human review of selected simulated cargo excursions instead of automatically placing every such lot on hold.

Approve scenario **B — Targeted verification** in Command first. For approved assignments that request this review, the desk displays **Trip requiring verification**. If none currently request it, the panel explains that there are no applicable approved trips. A different scenario or a different solver allocation may legitimately leave it empty.

Select the trip, review the simulated evidence, and use these three checkboxes:

- **Reviewed simulated temperature history**
- **Reviewed packaging-condition scenario**
- **Reviewed simulated lot identity and assignment**

**Record verification review complete** requires all three boxes plus the reviewing dispatcher and decision reason. **Record further review required** records an unresolved review without requiring all boxes. Both outcomes are saved with a review version, the assignment context, actor, reason and time. Changing the trip, network revision or review version clears the checkbox draft so an old review is not silently reused.

Completion means a dispatcher recorded this simulated checklist. It is not a laboratory result, independently observed packaging inspection, official recall match or product-safety certification. **Further review required does not place a lot on hold.** If a human decides a hold is appropriate, use the explicit lot control as a separate recorded action.

The same targeted-verification status appears in Drive. A driver acknowledging an assignment does not complete the dispatcher checklist, and an instruction acknowledgment does not replace it.

### Driver incident inbox

Each submitted Drive report becomes an inbox item with the shipment ID, description, report time, status and review version. The count includes unresolved items. Reports are driver statements within the simulation; they do not verify that a road closure, equipment fault or food-safety condition exists in reality.

| Action | When it is available | Result |
|---|---|---|
| **Start review** | An open report, with an identified dispatcher and reason. | Changes its status to **in review** and stores the review decision. |
| **Resolve report** | An unresolved report, with an identified dispatcher and reason. | Changes its status to **resolved** and records the decision. The current implementation permits resolution directly from open as well as from in review. |

Resolving a report does not release a hold, alter a route, reinstate an assignment, complete targeted verification or certify product safety. Those decisions have their own controls. A resolved report cannot be reopened through these controls.

The original report retains its reporting network revision and original assignment context. Resetting the scenario or reusing a shipment ID later does not turn an old report into a report about the new trip. Older reports can therefore remain in the inbox after a reset; earlier legacy audit-only reports remain in the audit trail rather than receiving invented inbox review histories.

The current inbox card shows the description, report time, status, review version and latest review text. The full retained original-assignment snapshot is part of the dispatcher data response, not a separate expanded history viewer in this panel. Ask a teammate to inspect that stored response when historical context is needed; do not infer it from the displayed shipment ID alone.

If another reviewer changes the report first, the old review version is rejected. Refresh and inspect the latest state before deciding again.

### Lot hold controls

The table lists each lot, modeled inventory in kilograms, current disposition and the applicable human response.

| Status or control | Meaning and consequence |
|---|---|
| **Eligible** | The current simulation permits considering the lot, subject to the other constraints. It is not a guarantee of food safety. |
| **Ineligible** | The simulated eligibility flag prevents dispatch. A hold release does not make an ineligible lot eligible. |
| **Held — blocked** | A precautionary hold prevents the lot from being selected for dispatch. |
| **Recalled — blocked** | The recall flag prevents dispatch. The hold-release workflow cannot override a recall. |
| **Place hold** | After an explicit dispatcher name and reason, marks the lot held, increases the network revision and removes approved assignments using that lot. Other approved assignments are not removed by this lot-specific action. |
| **Release hold** | Records a human release of the precautionary hold and increases the revision. It does not recreate removed assignments or override a recall. Review and approve a fresh scenario before rescheduling. |

Buttons on recalled lots are disabled in this interface. Existing holds and recall exclusions are enforced regardless of the optimization weights. A predictive estimate alone does not automatically create a mandatory hold.

Take care to distinguish three different actions: a **lot-specific hold** removes affected assignments; introducing a **simulated event** or using **Reset demo** clears all approved assignments; approving a **fresh Command plan** replaces the current assignment set with the newly approved set. Reapproval also means the new assignments require their own acknowledgment and applicable reviews.

### Dispatcher-approved instructions

**Use case:** the dispatcher needs a driver to read a concise operational instruction and demonstrate that the current version was received.

1. Select **Approved trip for instruction**. Only currently approved trips are listed.
2. Read **Current instruction**, its version and whether its acknowledgment is pending.
3. Fill **New dispatcher instruction**, from three to 2,000 characters. Supply or update the decision identity and reason at left.
4. Select **Approve and send instruction**. On success, a new instruction version is stored and published inside the app. Its driver acknowledgment starts pending.
5. In Drive, the driver reads and acknowledges that exact current version while parked.

A newer instruction cannot be satisfied by acknowledging an older version. Version counters remain separate from assignment rows so replanning cannot accidentally turn an old acknowledgment into acknowledgment of a reused trip's new instruction.

This is in-app text. It is not an SMS, phone call, external notification, physical dispatch command or route edit. Writing “take another road” does not calculate or authorize a validated truck detour. A separate route comparison can support review, but does not change the approved trip by itself.

The backend rechecks network revision, instruction revision and the current assigned lot/truck's relevant eligibility and capacity before accepting the instruction. If the trip was removed or changed, refresh and review its replacement rather than continuing to send against an obsolete selection.

## AEGIS Drive: a simplified view for a parked driver

**Use this workspace when:** a driver needs to inspect an approved assignment, see simulated fuel and cargo status, read dispatcher instructions, acknowledge the current trip, or report an issue while safely parked.

Use **AEGIS Drive** in the main navigation or open `/?mode=drive` on the same running server. The dedicated view removes the normal Command sidebar. It is a mobile-responsive part of the same application, not a native phone app, separate hosted service or commercial navigation system. Keep Command in another tab on the same server if you are demonstrating both roles.

### Read the main display

| Display | What it means |
|---|---|
| **Current assigned destination** | The destination for the selected dispatcher-approved assignment. The shipment, lot and simulated cargo quantity identify which record is being displayed. |
| **Planned travel from origin** | The assignment's modeled total travel time from its origin, in hours. This is not live remaining travel time or an arrival countdown. |
| **Estimated distance** | The assignment's modeled distance. A later route request is a separate route review and does not silently rewrite this assignment estimate. |
| Origin-to-destination strip | The two assigned endpoint names. It is not a progress bar. |
| **Fuel scenario** | Deterministically simulated percentage, liters, tank size and assumed range. No physical fuel sensor is connected; these values do not decrease as a real vehicle moves. |
| **Cargo temperature** | The selected assignment's simulated cargo value in degrees Celsius. Above 4°C is a demo review level, not a universal regulatory threshold or an automatic product disposition. |
| Assignment and verification status strip | Whether there is an approved assignment, whether its acknowledgment is recorded, and whether targeted verification is requested or complete. |
| **Simulated dispatch-origin snapshot** | A fixed scenario-origin reference with coordinates and a scenario timestamp. It is not GPS, a moving truck marker or a current vehicle observation. |
| **Assigned-trip scenario advisories** | Simulated events relevant to this vehicle's currently approved assignments. Missing advisories do not prove a real road is clear. |

The vehicle reference can come from the first approved assignment for that truck, or the default simulated distribution center when it has no assignments. Do not read it as the truck's current progress on whichever trip you select. Coordinates are displayed in **longitude, latitude** order.

If no plan has been approved for the selected truck, the destination reads **Ready for a reviewed plan**, and Drive says **No approved assignments**. It does not invent cargo or a route to fill the screen. Some simulated trucks may legitimately have no trip in a particular optimized allocation even when other trucks have assignments.

### Parked-use controls

Drive starts with interactions locked unless that truck already has a still-valid parked attestation saved in the same database. The page displays **READ-ONLY FOCUS** until parked use is active. Loading a page does not itself confirm that someone is parked.

**Confirm safely parked** explicitly records a self-declared parked confirmation for the displayed simulated truck. It enables the parked-only controls for up to **ten minutes**, checked by the backend. The display then shows **PARKED USE** and the remaining confirmation time. **Lock for driving** immediately switches back to read-only focus. Expiry also locks reporting and acknowledgments.

This feature does not measure speed, detect motion, prove safe parking, authenticate the driver, prevent device use outside AEGIS or guarantee prevention of distracted driving. Use the interface while safely parked; do not interact with it while driving.

The confirmation belongs to a truck. To demonstrate another vehicle, confirm parked use on the currently displayed demo vehicle so the **Simulated driver truck** selector is available, choose the intended truck, then read that truck's loaded focus state. A vehicle without its own valid attestation will be locked and needs a new **Confirm safely parked** action. This selector is a local demonstration control, not an authenticated driver-assignment system.

When the selected truck has multiple approved assignments, **Trip for advisories and incident reporting** selects the trip for the parked panels. Check its shipment, truck, lot and destination before submitting anything. Changing truck, changing trip or losing parked status closes detail panels and clears the typed incident draft. Copy important unsent text elsewhere before deliberately making such a change.

**Refresh driver data** reloads local approved assignments and focus status while parked. **Retry driver data** appears after a failed load. Drive also checks local state every 15 seconds; this is polling, not a live sensor stream or an automatic refresh of public weather/road providers.

### Dispatch instructions and two separate acknowledgments

While parked, open **Dispatch instructions**. The panel shows **Dispatcher-approved trip instructions** for the selected assignment.

**Acknowledge assignment** records that the current approved trip was acknowledged. If the dispatcher has issued a separately versioned instruction, **Acknowledge new instruction** records acknowledgment of that exact version. One is not a substitute for the other. The relevant button changes to an acknowledged state after the server accepts it.

The panel also shows targeted verification if required. **Pending dispatcher review**, **further review required** and **review complete** refer to the dispatcher's checklist. A driver cannot complete that checklist by acknowledging the trip.

Acknowledgments do not release a hold, override eligibility, permit an unapproved detour or certify that cargo is safe. A stale or removed assignment is rejected by the server. If the dispatcher changes the instruction before acknowledgment, read the new version before acknowledging again.

### Report an issue

While parked and viewing a current approved assignment, open **Report an issue**. The panel heading repeats the shipment, truck and destination so you can check the target.

There are two ways to submit:

| Control | What is submitted |
|---|---|
| **Refrigeration concern** | Immediately submits the preset refrigeration concern for this approved trip. |
| **Road delay** | Immediately submits the preset road or delivery-delay concern. |
| **Vehicle issue** | Immediately submits the preset vehicle concern. |
| **Cargo concern** | Immediately submits the preset cargo/packaging concern. |
| **Report a driver incident** plus **Send to dispatcher** | Submits your typed description, from five to 2,000 characters. The text field is a separate detailed-report action. |

The quick-report buttons submit immediately; they do not merely select a category for the text field. Typed text is not appended to a quick report. If you want a single detailed record, use the text field and **Send to dispatcher** instead of submitting both methods accidentally.

A successful report creates a record in **Driver incident inbox** with the reporting trip context and an audit entry. It does not introduce a simulator event, change the modeled cargo temperature, impose a hold, reroute the truck or call emergency services. The dispatcher must review it and record any separate consequential action.

Wait for the success receipt. A locked, expired, changed or removed assignment can reject the report. A typed description is cleared after successful submission; it is generally retained on a failed submit while the same parked context remains. Losing parked status or switching truck/trip clears the draft. A preset report is still a simulated driver statement, not verified physical evidence.

### Trip route and cargo projection

While parked, open **Trip route**. The **trip advisories** panel loads the selected shipment's cargo-temperature projection. **Review trip route while parked** requests a separate route comparison and displays the first returned route on a map.

The two temperature facts have different meanings:

- **Simulated current cargo** is the selected assignment's modeled cargo reading.
- **Illustrative journey maximum** is output from an uncalibrated physical projection using documented assumptions, including a simulated ambient temperature. It is not a measured future cargo value, validated failure probability or consumer-illness forecast.

**Within assumed temperature target** means the illustrative model remains inside its assumed review level. It does not prove food safety. **Dispatcher review requested** indicates a projection worth reviewing, not an automatic hold.

The route is labeled as ordinary OSRM driving geometry or an estimated fallback. An estimated fallback is a straight connection rather than a verified road path. The returned MoDOT proximity review is separate from routing. OSRM does not automatically avoid those events or validate commercial-truck restrictions. Requesting a route does not change the destination, planned assignment estimate or dispatcher instruction and does not authorize a detour.

If the trip or network changes during the request, the old response must not be treated as the current trip. Refresh the approved trip and request the comparison again while parked. Advisory failure does not make a missing projection or road review a favorable result.

## Guided practice: a driver concern through dispatcher response

**Purpose:** learn how the screens connect without changing the normal operator database. This is a practice workflow, not a record of real delivery operations or a claim of food-safety clearance.

### Prepare a separate workspace first

From the project folder, start a new rehearsal:

```powershell
.venv/Scripts/python scripts/start_rehearsal.py --port 8001
```

Use the URL actually printed by the launcher. If the port is occupied, choose another non-8000 port using the launcher. Check the persistent **Verified isolated rehearsal** / isolated-runtime banner before exercising actions. Adding `?mode=rehearsal` to the ordinary operator page does not isolate its database.

Keep every tab in this exercise on the same isolated server. For example, Command can use `http://127.0.0.1:8001/`, and the separate Drive tab can use `http://127.0.0.1:8001/?mode=drive`. Port 8000 remains the operator app and must not be reset for practice. Default rehearsal uses dated public fixtures and labeled route estimates; browser base-map tiles may still need internet.

### Walkthrough A: publish a plan, report a concern, instruct the driver

1. In the isolated **Command center**, compare the scenario results. Review and approve a feasible plan using a dispatcher name and a reason. Read the independent constraint details before approving. Approval replaces the current set of simulated assignments.
2. In **Dispatcher desk**, inspect an approved trip and note its truck ID. The same ID is needed in Drive. Do not assume that the truck initially displayed in Drive has the trip you want.
3. Open **AEGIS Drive** on the same isolated server. Follow the parked-use steps to select the intended simulated truck, then confirm parked use for that vehicle if needed. Select the intended trip when multiple are available.
4. Open **Dispatch instructions**, read the trip and choose **Acknowledge assignment**. If there is an outstanding separately versioned instruction, acknowledge that version too.
5. Open **Report an issue**. Submit one quick concern or one typed report, then wait for the saved receipt. Do not assume this changes cargo readings or the route.
6. Back in **Dispatcher desk**, use **Refresh desk** if needed. Enter an appropriate reviewing dispatcher and decision reason. Locate the new report and select **Start review**.
7. For a response that does not require a hold, select the approved trip, write a concise **New dispatcher instruction**, and choose **Approve and send instruction**. The instruction is app text, not a route edit.
8. In Drive, refresh and open **Dispatch instructions**. Read the latest version and select **Acknowledge new instruction** while parked.
9. In the desk, inspect **Dispatch readiness review**. Assignment and current-instruction acknowledgment should be evaluated separately. Other workflow requirements can remain outstanding.
10. If the report's operational review is complete, update the decision reason and select **Resolve report**. Explain why this resolves the report without certifying product safety or changing a lot disposition.

### Walkthrough B: a human chooses a precautionary hold

1. Begin from an approved isolated plan and a reported concern. Identify the affected trip's actual currently assigned lot; scenario D may have substituted a different eligible lot from the original candidate.
2. In **Dispatcher desk**, enter a name and a specific reason, then choose **Place hold** on that lot. Read the success message.
3. Confirm that affected approved assignments disappear from Drive and the readiness list. The lot remains held, and new optimization must exclude it. Unaffected assignments can remain until the dispatcher chooses a replacement plan.
4. Compare fresh Command scenarios. If appropriate for the exercise, approve a new feasible plan that honors the hold. This replaces all current assignments with the new approved set; previous acknowledgments and review records on assignment rows do not automatically carry over.
5. Refresh Drive, select the current trip/truck, and acknowledge the newly approved assignment while parked. Do not continue reporting or acknowledging against the removed trip context.
6. If the exercise later calls for a human hold release, record a new reason and choose **Release hold**. Observe that the release does not republish the removed assignments. Review and approve a fresh plan before rescheduling that lot. A recalled lot cannot be released through this precautionary-hold control.

An incident's report history can remain visible throughout these changes. It retains its original context; its shipment ID alone is not proof that it describes a newly approved assignment with the same ID.

### Walkthrough C: targeted verification without an automatic hold

1. In a fresh isolated scenario state, review **B — Targeted verification**. Confirm that the selected allocation includes an assignment requesting verification, then approve the plan.
2. In the desk's **Targeted verification review**, select that trip. Enter the reviewing dispatcher and reason, review the simulated evidence and tick the three applicable checklist statements.
3. Record either **verification review complete** or **further review required**. Notice the saved status in both the desk and Drive.
4. Inspect readiness. A driver acknowledgment by itself does not satisfy targeted verification; a completed matching review can satisfy that workflow check. A further-review result does not automatically place the lot on hold.
5. If a hold is appropriate to the practice case, record it separately through **Lot hold controls**. The application preserves that distinction between a review signal and an explicit consequential decision.

### What survives a page reload, and what does not

Approved assignments, acknowledgment records, incident reports/reviews, lot decisions, instruction versions and targeted-verification decisions are stored in the local SQLite database. Parked attestations are stored per truck and remain subject to their expiration. The shared database belongs to that specific running server instance.

Typed dispatcher identity/reason/instruction fields, unsent incident descriptions, selected panels and checkbox drafts are interface state. Do not rely on them surviving page reload, navigation or a context change. A saved decision is distinguished by its accepted server response and recorded version or audit entry.

The system does not continually subtract delivered quantities from inventory or advance a truck along its route. Readiness is a check of the current one-wave allocation; the displayed stock, fuel and travel are scenario assumptions, not an executed delivery ledger.

### Common questions and recovery steps

| What you see | Likely meaning | What to do |
|---|---|---|
| No approved assignments in Drive | No approved plan for this truck, a hold removed its trip, an event/reset invalidated assignments, or another truck owns the intended trip. | Inspect the current Command approval and desk assignment list; then select the right demo truck and current assignment. |
| Report/acknowledgment buttons disabled | Parked confirmation is absent or expired, no approved trip is selected, or a request is pending. | Stop safely, check the truck/trip and confirm parked use. Wait for a pending request to finish. |
| A parked-use rejection after a page looked enabled | Server time or a newer focus state no longer permits the action. | Refresh, confirm parked use again if genuinely parked, and inspect the current context. Do not silently resubmit an obsolete action. |
| “Network changed” or “Instruction changed” | Another action changed the state/version since the displayed decision was prepared. | Refresh and review the new facts or instruction before submitting again. |
| No approved trips available for instructions | Instructions require an already approved eligible assignment. | Review and approve a fresh Command scenario first; a route-laboratory experiment cannot publish assignments. |
| All verification boxes checked but completion unavailable | Dispatcher identity/reason is incomplete or the assignment/review changed. | Complete the decision record and inspect the currently selected verification trip/version. |
| Readiness still says Review outstanding | One of the three workflow checks remains incomplete. | Read the individual evidence rather than assuming all acknowledgments or checks are interchangeable. |
| Hold released but trip is still absent | Release does not recreate an assignment. | Generate, review and approve a fresh feasible scenario. |
| Old reports remain after Reset demo | Incident/audit history is retained separately from the reset network. | Inspect the report time and retained dispatcher data context with a teammate if necessary. Do not attribute an earlier report to a reused trip ID. |
| Route is estimated or advisory load failed | Provider geometry is unavailable, offline mode is active, or the request failed. | Read the explicit fallback/error. Do not treat missing evidence as a clear route or favorable temperature finding. |

These workflows support a demonstrator's human review. They do not establish authenticated fleet access, live telematics, legal departure authority, food-safety certification or control of physical trucks.

## Sources & evidence: understand where each claim comes from

**Use this workspace when you need to answer:** What data do we actually have? When was it obtained? Is a displayed number a real observation, a forecast, a historical summary, or a simulation? What failed or remains missing?

Open **Sources & evidence** in the main navigation. The screen contains the USDA county-context comparison, the ingested-data explorer, the NOAA coverage audit, import results, public-source cards, recall notices, connectivity results, and the supplied-file inventory. It is an evidence workspace. Selecting a county or filtering a source does not change inventory, dispatch a vehicle, impose a hold, or retrain the model.

### Five labels to understand before reading the screen

| Label or term | Plain-language meaning | What it does not establish |
|---|---|---|
| Observed historical weather | Weather reported for a past station/date and retained from NOAA/NCEI | Temperature inside a refrigerated truck or current weather everywhere along a route |
| Weather forecast | A provider's prediction for upcoming weather | A past observed measurement or a measured cargo temperature |
| Historical reanalysis | A provider's reconstructed historical weather product | The same data stream as NOAA station observations |
| Simulated cargo temperature | Fictional truck/cargo readings used in the digital twin | A connected physical sensor or a verified condition of real poultry |
| Dated fixture / cached response | A saved public response with a retrieval time | A request that just succeeded, complete coverage, or guaranteed current conditions |

**Provenance** means the record of where a value came from and how it was handled. It includes source identity, original filenames and hashes, import status, retrieval time, geographic scope, units, and known limits. A **SHA-256** is a file fingerprint: matching fingerprints support that the same bytes are being used. A fingerprint alone does not prove that a provider is authentic, that a file is complete, or that a scientific linkage is valid.

Read retrieval and observation times separately. A file downloaded today can contain observations from years ago. A forecast valid tomorrow can have been retrieved earlier today. Neither time is a proven FSIS laboratory-result publication date.

### Food access across Missouri

This panel describes the historical operating region using a checked USDA Food Environment Atlas extract. It currently includes **115 Missouri counties/county-equivalents** and **ten measures**. It is useful for explaining the social and retail context in which food distribution happens. It is not a farm safety rating, an outbreak detector, a current demand estimate, or an allocation rule.

| Control | How to use it | Result |
|---|---|---|
| **USDA county** | Choose a county by its displayed name and five-digit FIPS identity | Replaces the main county's values on all ten cards |
| **Compare USDA county** | Choose a second county, or **No comparison** | Adds or removes the second county's value on each card |
| **Definition and denominator** | Expand a measure's explanation | Shows its original field code, definition, and population/housing/store denominator |
| **Download county CSV** | Download the checked local extract | Exports county values and source provenance; numeric source precision is retained |
| **Recheck local extract** | Ask the backend to re-read and verify the saved extract | Checks local integrity; it does not download a new USDA release or refresh weather/recalls |
| **Source provenance and interpretation limits** | Expand the details | Shows source links, original workbook hash, import time, release note, and limitations |
| **Retry USDA context** | Available after a failed read | Retries the local checked extract; it cannot repair a corrupt source automatically |

The values displayed in the cards may be rounded to two decimal places. The CSV retains numeric source precision. The export is a table of this checked historical extract, not a current list of customers or deliveries.

The following ten variables are implemented:

| Source code | Vintage | What the value describes |
|---|---|---|
| `LACCESS_POP19` | 2019 | Estimated people with low foodstore access |
| `PCT_LACCESS_POP19` | 2019 | Percent of total county population with low access |
| `LACCESS_LOWI19` | 2019 | Estimated people with both low income and low access |
| `PCT_LACCESS_LOWI19` | 2019 | Percent of total county population with both conditions; the denominator is not only low-income residents |
| `LACCESS_HHNV19` | 2019 | Estimated housing units without a vehicle and more than one mile from a foodstore |
| `PCT_LACCESS_HHNV19` | 2019 | Percent of all county housing units meeting that definition |
| `GROC20` | 2020 | Grocery stores/supermarkets under the source definition |
| `GROCPTH20` | 2020 | Grocery stores per 1,000 county residents |
| `SNAPS23` | 2023 | Average monthly SNAP-authorized stores under the source definition |
| `SNAPSPTH23` | 2023 | Average monthly SNAP-authorized stores per 1,000 residents |

The access measures combine 2019 store locations with provider-defined historical population, income, and vehicle inputs. They are not ten measurements from one common year. Read the definition before comparing counties, especially when comparing a count with a rate.

**Missing / suppressed** is not zero. In the current extract, `GROC20` and `GROCPTH20` each have 39 missing/suppressed entries. The original missing codes and row identities are retained in the ingestion report. The application does not guess the individual reason or replace those entries with invented observations.

FIPS is the county identity. St. Louis County and St. Louis city are different units, even where original county text is similar. Their FIPS codes prevent them from being collapsed into one location. This feature does not assign simulated destinations to real counties or draw county boundaries on the logistics map.

**Use case: explain regional access without overstating it.** Select Boone County, then compare it with another county. Expand a low-access percentage's denominator, note its year, and export the CSV if the team needs a table. A defensible explanation is, "These are historical county-context measures." It would be unsupported to say that the comparison proves today's demand, the safety of a supplier, or the health risk of a particular shipment.

### Inspect the underlying evidence

This is a read-only browser of recognized, separately ingested tables. The original column names remain visible. The dataset selector identifies both the source and its import availability.

The current local tables checked for this guide are:

| Dataset shown in the selector | Rows | Examples of fields and their purpose |
|---|---:|---|
| **FSIS raw-poultry samples** | 78,607 | Sample/form identifiers, establishment identity/state, project code, collection date, primary Salmonella result, cancellation field, source file |
| **CDC NORS outbreaks** | 66,713 | Year/month/state, transmission mode, etiology, setting, illnesses, hospitalizations, deaths, food/water/animal context |
| **CDC BEAM regional isolates** | 1,650 | Year/quarter/month, HHS region, pathogen, number of isolates, past-two-year average |
| **CDC BEAM source report** | 262,616 | State, source type/site, pathogen, serotype/species, isolates and surveillance summaries |
| **CDC BEAM burden / trajectory** | 484 | Provider-defined food category, serotype, year range, burden/trajectory and illness summaries |
| **CDC BEAM illnesses / outbreaks** | 2,412 | Provider-defined serotype, food category, illness/outbreak counts and year windows |
| **CDC BEAM common serotypes** | 4,818 | Year/quarter/month, pathogen, serotype/species/subgroup and isolate counts |
| **FSIS Missouri establishments** | 175 | Official establishment identifiers, names, activities, addresses and coordinates |

These counts describe saved local extracts. They are not the number of real AEGIS suppliers, customers, trucks, or shipments. An official establishment point does not establish a supply contract. A BEAM source report includes human, animal, and food categories; inspect **Source Type** and **Source Site** before describing its content.

| Control | What it does | Important detail |
|---|---|---|
| **Dataset** | Chooses one recognized table | Unavailable/conflicting sources cannot be treated as a successful current import |
| **Filter column** | Chooses one original column | The filter applies to this column only |
| **Contains text** | Accepts a literal, case-insensitive substring | It is not SQL, a regular expression, an exact numeric comparison, or a geographic boundary query |
| **Apply source filter** | Applies the typed filter and returns to the first page | Typing alone does not change the displayed results |
| **Clear filter** | Removes the applied filter and reloads the first page | It does not erase source observations |
| **Previous rows / Next rows** | Moves through pages of 25 rows | Browser pagination stops at its 10,000-row offset cap; it is not a full-analysis tool |
| **Schema and derived-file integrity** | Shows columns and a file fingerprint | For displayed rows, the hash belongs to the same bounded file snapshot parsed for that response |
| **Source identity and import provenance** | Shows the recognized source key, import status and original-input hashes | Recognition uses supported content schemas, not the filename or order in which files were downloaded |

The heading above the table gives **matching rows** and the displayed row range. Each column reports its number of nulls **on this page only**. The symbol **∅** means a missing cell. A page with zero nulls does not prove the entire dataset is complete.

Filtering one source never joins it to another. Finding the same state, pathogen name, or serotype in two sources does not prove that a human illness, an FSIS laboratory sample, a supplier, and a simulated shipment are connected. These exports do not provide the isolate-level genomic linkage needed for molecular attribution.

There is no full-table export button in this explorer. For complete analysis, the team uses the saved processed tables and source-specific scripts. The USDA county panel has its own separate CSV export.

**Use case: inspect a positive FSIS observation.** Choose **FSIS raw-poultry samples**, choose `salmonella_sp_analysis` under **Filter column**, enter `Positive`, and click **Apply source filter**. Inspect the collection date, establishment state, cancellation field, and source identity. Expand the integrity/provenance sections. Say, "This is a selected primary laboratory result in the saved source." Do not turn that observation into a finding about a simulated lot, a current truck, or a consumer's probability of illness.

### NOAA coverage audit

The **NOAA coverage audit** shows what has actually been obtained from the required historical NOAA/NCEI stream. Its four summary facts are **Verified stations**, **Date-row coverage**, **Metric coverage**, and **Report status**. The station table shows actual station IDs/coordinates, distance from the named city, returned dates, missing variable values, quality flags, and retrieval time or error.

The recorded extract covers **January 1, 2025 through June 30, 2026**. Five verified stations represent Columbia, Kansas City, Jefferson City, Springfield, and St. Louis. There are **2,730 returned station-date rows out of 2,730 requested**, but **nine missing requested variable values**. Metric coverage is approximately **99.89%**, and the report status remains **partial**. Complete date rows do not mean complete temperature and precipitation values.

The station IDs are `USW00003945`, `USW00003947`, `USW00003963`, `USW00013995`, and `USW00013994`, respectively. The coverage report was generated at **2026-10-26 06:39:34 UTC**; individual source retrievals are also retained. See `reports/noaa_coverage.json` for the precise record. This historical report is distinct from the small station/week probe shown in the public-source cards.

The variables are daily maximum temperature (`TMAX`), minimum temperature (`TMIN`), and precipitation (`PRCP`). A flag count describes source quality information; a blank quality flag is not a promise of zero measurement error. Station reporting dates can use local observation periods, so a daily record is not automatically a UTC-midnight reading.

**Use case: answer "Is NOAA complete?"** Read both coverage percentages and the missing-metric counts, then the geographic/date limits. The accurate answer is that the bounded five-station extract has all requested date rows and some missing variable values. It does not cover every establishment or every historical training year. No validated NOAA-to-FSIS model join has been completed. Airport ambient weather is not cargo temperature or a reconstruction of a shipment's exposure.

### Source-specific ingestion

The **Source-specific ingestion** table explains what happened when supplied exports were read. It lists **Supplied export**, **Evidence layer**, **Rows ingested**, and **Validation**. This is an import report, not an upload or merge form.

Read its outcomes literally:

- **Ingested / source schema accepted:** a supported adapter parsed that source structure. This does not establish a scientific linkage to another table.
- **Duplicate:** the same bytes were already represented; no additional observations were added from that download.
- **Unrecognized:** the file is inventoried, but its structure was not accepted as a supported source. It has not been silently merged.
- **Conflict:** different exports matched the same source identity, so the importer requires explicit selection rather than pooling or guessing which is newest.
- **Failed:** inspect the exact error. A previous output may be retained, but its existence is not proof that the latest import succeeded.

For example, the small FSIS ready-to-eat sampling JSON is not a complete primary raw-poultry training set. Secondary typing tables are not additional primary sample outcomes. The UI does not offer a button that reinterprets those files to increase the sample count.

### The five public-source cards

| Card | What it supplies | How to interpret it |
|---|---|---|
| **Open-Meteo forecast** | Columbia-area forecast values | A forecast, not an observed historical NOAA stream |
| **NWS official alerts** | Official Missouri severe-weather warnings in the captured response | Read validity and retrieval context; an empty captured list is not an all-weather safety clearance |
| **NCEI historical observations** | A dated small station probe | Separate from the five-station coverage audit; neither represents cargo telemetry |
| **FSIS official recalls** | Official recall-notice evidence | Real notices remain separate from fictional lots without genuine traceability |
| **MoDOT traveler information** | Captured road-incident layers | Separate geometry evidence; OSRM does not automatically avoid these closures |

The source badge can say **Dated response available**, **Stale response - review age**, or **Coverage gap**. The source stamp identifies a dated fixture or cached response and its retrieval time. Read that stamp before interpreting the contents.

**Open official response** opens the provider endpoint in another tab. It can require internet and can fail even though an older local response remains usable for the demo. It is not a local re-import button.

**Refresh** deliberately checks that source through its adapter. Existing cache lifetimes may allow a valid cached response to be reused; clicking the button does not guarantee a new upstream observation or a new download. An unsuccessful refresh can leave a dated fallback visible with its exact failure. It does not reset the digital twin, approve a response, retrain the scientific model, or transform forecasts into observations. Refresh is disabled in verified offline rehearsal so its dated fixtures stay fixed.

### Official recall notices

The recall list gives a concise preview of saved FSIS notices. **Read official notice**, when supplied, opens the provider's notice. The app requests a bounded preview of up to 20 records and displays six notices. These are the first records in provider response order; the app does **not** establish that they are the six newest recalls.

Notice titles/dates are real source evidence where the response is recognized. Simulated lot IDs do not supply the genuine product/lot/establishment traceability needed to prove that a notice affects a demo shipment. Reading or refreshing a notice does not place a mandatory hold on a fictional lot. The human hold workflow remains separate.

### Connectivity evidence and supplied-file inventory

**Connectivity evidence** shows the source ID, saved test status, HTTP status, latency, content type, and last probe/failure. **JSON evidence** opens the saved probe records. This is dated testing evidence. It does not perform a new request just because the screen is opened, and a reachable documentation webpage is not the same as a working data adapter.

For this guide, the saved registry contains 19 endpoints with 14 recorded HTTP successes. Five earlier FSIS/USDA ERS website probes retain DNS-resolution failures. Their locally imported tables and dated official responses can remain available. Do not replace the recorded errors with an assumed success or say that every integration is live. Later refresh actions and the road workspace have their own independent timestamps and evidence.

**Supplied data inventory** lists the 42 audited original files, their sizes, likely sources, and read status. **Full inventory** opens the complete manifest, including the supported metadata and exact errors where applicable. An **Inspected** file is not necessarily an ingested model input. Workbook dimensions may be declared dimensions rather than an exact parsed count. Unsupported files remain recorded rather than silently merged.

### A useful evidence-review routine

1. Open **Sources & evidence** and read the source time and label before quoting a value.
2. Choose a real ingested dataset and inspect a bounded row, its original column names, and the source-input hash.
3. Read the import status. Resolve an unavailable/conflicting import through the documented source-specific workflow rather than assuming an older file is current.
4. If discussing weather, compare the NOAA date-row and variable coverage. Keep forecast, reanalysis, station weather, and cargo simulation separate.
5. If discussing food access, state the county, FIPS, measure, year, and denominator.
6. If discussing a recall, inspect the official notice and admit when genuine shipment-level matching is absent.
7. Record the data's limitations in the presentation. The evidence screen supports traceable claims; it does not automatically establish a safe operational disposition.

## Model evaluation: understand the measured result

**Use this workspace when you need to answer:** What exactly was predicted? Was it evaluated on later observations? Did a fitted model improve on a simple historical baseline? What can we honestly claim?

Open **Model evaluation** in the main navigation. This is a read-only display of saved scientific evaluation artifacts. Opening it does not train a model, query a live laboratory, change a lot's eligibility, or generate a new individualized risk forecast for the selected shipment.

The target is **Salmonella positivity in a selected national FSIS raw-poultry primary sample**. The unit is a selected laboratory sample. It is not a consumer, shipment, whole farm, or all poultry sold in Missouri. Positive/negative primary results are used only with the implemented cancellation/date rules. CDC outbreaks, BEAM surveillance, NOAA weather, road events, and simulated cargo are not joined into this target.

### The baseline and the fitted model

The **Historical prevalence** baseline gives every held-out observation the same smoothed training-period estimate. Smoothing keeps an estimate from becoming an unjustified absolute zero or one when counts are small. In the saved primary study, that training estimate is approximately **9.00%** selected-sample positivity. The later holdout's observed positivity is approximately **9.81%**. Neither percentage is a consumer-illness probability.

**Logistic regression** is the fitted comparison model. It uses an assumed 90-day-lagged historical prevalence feature plus two calendar-month features that represent seasonality. It does not use live sensor data, weather, consumer symptoms, or a gene-sequence comparison. The more complicated model is useful only if the evaluation shows a defensible improvement. Here it did not establish such an improvement, so the saved **Operational selection** remains **smoothed historical prevalence; prospective skill not established**.

### Primary chronological holdout: the numbers shown

The following values were checked against `reports/model_evaluation.json` for this October 29, 2026 guide. That saved artifact does not record a model-run timestamp; the guide's check date is not an invented training date.

| Quantity | Saved result |
|---|---|
| Training samples | 48,361 |
| Last training collection date | May 30, 2025 |
| Validation samples | 23,472 |
| Validation collection dates | August 29, 2025 through June 30, 2026 |
| Time separation | A 90-day embargo before the validation start is excluded from fitting |
| Baseline Brier score | 0.08855575 |
| Logistic Brier score | 0.08859440 |
| Baseline Brier 95% week-block interval | 0.08543538 to 0.09224387 |
| Logistic Brier 95% week-block interval | 0.08547636 to 0.09229202 |
| Baseline PR-AUC / average precision | 0.09811691 |
| Logistic PR-AUC / average precision | 0.09814105 |
| Baseline ROC-AUC | 0.50000000 |
| Logistic ROC-AUC | 0.49802936 |
| Precision and recall at threshold 0.5 | Both are 0 for both estimators in this saved evaluation |

The **Training samples**, **Validation samples**, **Baseline Brier**, and **Logistic Brier** cards summarize this study. The **Chronological holdout comparison** table includes its metrics and uncertainty intervals. Dates describe collection-date ordering, not verified dates on which results became available to the public.

### What each metric means

| Displayed metric | Plain-language interpretation | Common mistake to avoid |
|---|---|---|
| **Brier** | Average squared difference between a predicted probability and the observed 0/1 outcome; lower is better | It is not an accuracy percentage. A score near 0.0886 does not mean 91.14% accurate |
| **95% week-block CI** | A resampling interval that retains groups of observations from the same validation week | It does not cover unknown publication delays, selection bias, all future periods, or individual shipment uncertainty |
| **PR-AUC (AP)** | How useful the model's ranking is when focusing on the relatively uncommon positive samples | Its reference level depends on how common positives are; a number near 0.10 must be compared with the baseline |
| **ROC-AUC** | Ability to rank positive samples above negative ones | A result near 0.5 provides little useful discrimination in this holdout; it is not a safety certification |
| **Precision @ 0.5** | Among samples predicted positive at the 50% cutoff, the positive fraction under the implementation's reporting rule | Zero here is not a statement that overall accuracy is zero |
| **Recall @ 0.5** | Fraction of actual positive samples selected by that 50% cutoff | These estimates did not produce useful positive classifications at that cutoff; a lower threshold would require its own reviewed evaluation |

The primary baseline's Brier score is slightly lower than the logistic model's. Their displayed Brier intervals overlap closely, the PR-AUC values are essentially similar, and logistic ROC-AUC is near 0.5. The defensible conclusion is that this study did not establish useful improvement over the baseline. It does not support inventing an accuracy figure or adding a more elaborate model solely for presentation.

### Calibration and coefficients

The **Calibration** chart compares the fitted model's predicted probabilities with observed selected-sample positivity in grouped predictions. The dashed reference line is the ideal agreement line. Hovering the chart reveals the plotted values. A curve close to the reference line can be encouraging about those groups, but good-looking calibration alone does not prove useful ranking or valid future deployment.

**Feature coefficients** appear under **Interpretation & limitations**. The current feature names are `lag90_prevalence`, `month_sin`, and `month_cos`. These are fitted associations on the logistic model's scale. They are not causes, degrees of temperature change, supplier rankings, regulatory findings, or instructions to hold stock. A single coefficient should not be quoted as the percentage change in a consumer's illness risk.

### Snapshot timing audit

The **Snapshot timing audit** asks whether the historical information used to fit an estimator could plausibly have existed before the later observations being evaluated. This is a separate retrospective sensitivity study, not an extra validation result to merge into the primary holdout table.

The cards show **Training snapshot cutoff**, **Training samples**, **Later samples**, and **Public release verified**. In the current saved audit:

- The training snapshot cutoff is **March 19, 2026**.
- There are **57,459** earlier training samples and **7,754** later validation samples.
- The later sample window is **March 20 through June 30, 2026**.
- **Public release verified** is **No**. A file-creation date is not proof of its first public release.
- The snapshot baseline Brier is approximately **0.09297314**; the calendar-only logistic comparison is approximately **0.09293427**. Logistic ROC-AUC is approximately **0.49920**.

The audit artifact was generated at **2026-10-26 06:42:45 UTC** (`reports/model_timing.json`). Training labels are frozen to earlier source snapshots; held-out outcomes do not update those fitted parameters or that frozen baseline. Actual row-level result availability and an authoritative historical as-of archive remain unavailable. The FY2026 evaluation file can contain later retrospective revisions. This audit improves transparency, but it does not turn the project into a validated prospective forecasting system.

Why are the two studies' sample counts and scores different? They use different time/snapshot rules and different held-out samples. A result from one study cannot be substituted into the other study's denominator, dates, or uncertainty interval.

### Where the fitted model makes errors

Expand **Inspect measured state-level error analysis** inside **Where the fitted model makes errors**. The table shows establishment state, holdout sample count, observed sample positivity, and logistic Brier loss. Only states with at least 30 held-out samples are included; 42 groups are currently recorded.

These are descriptive slices of the same national holdout. They are not independent state-level validation, farm ratings, or supplier league tables. Differences can reflect which samples were selected. A state absent from the table has not been assigned a zero risk or a perfect score. The study does not establish subgroup uncertainty or prospective state-level performance.

### A useful science-presentation routine

1. State the target and unit first: a selected FSIS primary raw-poultry sample and its Salmonella outcome.
2. Show the chronological dates and sample counts. Explain the assumed reporting lag and embargo without presenting them as verified publication history.
3. Compare the baseline and logistic Brier scores, then PR-AUC and ROC-AUC. Explain why the baseline is retained.
4. Show calibration as one diagnostic, not a substitute for the other results.
5. Expand the state error breakdown to demonstrate inspection, and identify its subgroup limitations.
6. Read **Snapshot timing audit** and **Public release verified: No**. Explain what remains unknown.
7. End with the supported contribution: measured evaluation, reproducible evidence, visible uncertainty, and human-reviewed operational choices.

A defensible presentation sentence is: "We evaluated a national retrospective sampling target chronologically, compared it with a transparent baseline, and retained the baseline because the fitted model did not establish useful improvement." Avoid "We predict which consumer will become ill," "This farm is unsafe," or "The model automatically orders a hold."

### Evidence/science troubleshooting and current boundaries

| What you see | What it usually means | Appropriate next action |
|---|---|---|
| A stale source card with an older retrieval time | The saved response has aged or a new request failed | Read its date/error; deliberately refresh in the operator app if needed, or demonstrate the dated fixture honestly |
| A failed FSIS/ERS connectivity row while local rows still display | A saved provider request failed, but valid local data remains | Keep these facts separate; a website outage does not erase a prior input, and a prior input does not prove a new request worked |
| A dataset is disabled/unreadable/conflicting | A recognized current import or integrity check is unavailable | Have the developer inspect the exact report and source-specific adapter; do not invent rows or mix snapshots |
| A filter returns zero rows | The literal substring did not match that column in the selected source | Check the selected dataset/column, copy an actual visible value, or use **Clear filter**; do not interpret it as no real-world cases |
| ∅ or Missing / suppressed | The source does not supply a usable value for that cell | Keep it missing; do not substitute zero |
| A NOAA status of partial despite 100% date-row coverage | Returned dates and complete variables are different checks | Review metric missingness, flags, station/date scope and the lack of a validated FSIS join |
| No recall notices or an unrecognized schema message | No supported saved preview is available | Inspect the dated source response; do not infer that no recall exists |
| Missing model metrics or a timing-report error | The required saved evaluation artifact cannot be read | Restore/reproduce the documented scientific artifact through the developer workflow; no values are inferred by opening the page |

The app does not currently provide isolate-level molecular attribution, a validated weather-to-FSIS prediction, live cargo sensing, or a verified real recall-to-demo-lot match. Missing per-result publication timing remains a scientific limitation. Broader NOAA historical coverage is incomplete. Genuine signed-in Kiro specification execution, author/rubric review, and the timed team presentation remain separate project gates; polished evidence screens do not complete those gates automatically.

For deeper source records, consult `docs/data_catalog.md`, `docs/ingestion_provenance.md`, `docs/food_access_context.md`, `docs/model_card.md`, `reports/model_evaluation.json`, `reports/model_timing.json`, `reports/noaa_coverage.json`, and the source-specific import manifests. These files support the screen; they should not be described as additional live integrations.

### Separate Missouri integrated study

Model evaluation now also shows **One Health model: what did integration add?**
It compares prevalence, FSIS history, added BEAM, core BEAM/NOAA and added NORS on
the same supported Missouri cohort at a seven-day lead. Only 490 of 1,534 samples
meet coverage; primary validation has 171 samples and 22 positives. Monthly gaps
remain missing, not zero. Open the assumptions/calibration/error section and
download the model JSON or aligned CSV. The original national study remains
separate and unchanged.

The core Brier score is about 0.11246 versus baseline 0.11431. Marginal BEAM/NOAA
intervals include zero; NORS worsens this cohort's result. No prospective
activation, consumer illness, genomic causation or individual-lot inference is
allowed. This is an exploratory aggregate alignment, not a validated production
weather-to-FSIS predictor. The final five-task PDF includes exact metrics,
uncertainty and the resulting limits. The owner disclosed Kiro non-use.

## Evidence assistant: explain a captured decision context

Open **Evidence assistant** when you want help understanding a delivery plan or its evidence. Start by typing **chicken** in **Your evidence question**, then click **Ask AEGIS**. The helper offers **Choose what to check** choices; click one to get a cited explanation. A broad word is a starting point, not a failed search or an illness prediction.

The factual engine is **Deterministic evidence summary**. Its sentences are authored by the application and populated with values from a captured network and dated reports. It is not an illness model, an autonomous dispatcher or an unrestricted chatbot. It has no tool for approving, holding, releasing, dispatching, refreshing a provider or rewriting scientific metrics.

### Capture context and choose an explanation

| Control | What to do | What happens |
| --- | --- | --- |
| Reload evidence context | Capture the current network and saved evidence again | Clears obsolete answer context and records a new content-addressed snapshot |
| Guided question cards | Click one of the six supported questions | Immediately requests its explanation; no second click is needed |
| Simulated shipment to review | Choose the candidate trip when reviewing a shipment | Used only for shipment-specific explanations; candidate and approved assignment can differ |
| Get answer | Ask again for the selected question and shipment | Returns facts from the captured context with source labels and limits |
| Your evidence question / Ask AEGIS | Enter 1–400 characters, such as **chicken**, **late truck** or a full question | Matches a supported topic or offers useful choices when the wording is broad or unfamiliar |
| Example questions | Click **Chicken** or another example | Fills in the wording and immediately asks it |
| Export captured answer JSON | Save the displayed answer and citations | Downloads a captured explanation; it does not create an assignment or future live update |
| Suggested workspace links | Open the relevant existing screen | Navigates for review; consequential decisions still require their ordinary explicit forms |

Expand **What this helper can do** for the captured snapshot and technical explanation. Within an answer, expand **Sources & provenance** to inspect source paths, retrieval times, checksums and limitations. The snapshot ties facts to captured content and a network revision; saved source reports retain their own dates.

If the network, assignments or report files change, a question using an old snapshot is rejected. Reload the context and inspect it before asking again. Changed topic, shipment or wording marks an already displayed briefing as belonging to the previous request. Do not treat an earlier answer as an explanation of newly edited inputs.

An action request such as “approve this plan” shows an explanation and **Open Dispatcher desk**. It keeps the evidence context available so you can choose another question. The link opens the decision workspace; it does not approve anything. A stale snapshot or an inconsistent answer instead requires **Reload evidence context**.

### Six useful topics

- **Compare response scenarios:** inspect cost, unmet demand, selected shipments, solver status and modeled constraints together. Scenario D can substitute eligible lots on fixed trips; this is not automatic rerouting. Scenario C's described holds remain proposals until a separate human approval.
- **Review a simulated shipment:** read candidate lot/truck/temperature and direct modeled exclusions. The current approved assignment may use a different lot. Passing a single-candidate check does not establish aggregate plan feasibility or product safety.
- **Explain model performance:** see the actual historical baseline/model metrics, sampling target and availability limitations. Positivity is not consumer illness probability; no new model is trained.
- **Explain source coverage:** distinguish saved HTTP probes, dated source evidence and numeric observation coverage. Reading a report does not refresh the provider or turn a stale success into a current success.
- **Explain the driver handoff:** distinguish approval, targeted verification, parked attestation, acknowledgment and incident reporting. A report or acknowledgment does not impose a hold or complete every readiness check.
- **Find the next review steps:** follow read-only navigation to the appropriate workspace. A suggestion is not an executed recommendation or an approval.

Expand a fact's evidence details to inspect its source path, available retrieval timestamp, checksum and uncertainty. A missing or unusable report produces an explicit unavailable fact rather than a fabricated metric. CDC evidence stays separate from FSIS outcomes. Historical observations, forecasts, cargo simulation and illustrative thermal projections retain their different meanings.

### Optional Ollama topic selection

The default requires no language model. **Advanced matching options** is collapsed when none is configured. A technical teammate can explicitly configure an Ollama service at a permitted loopback address. If configured, the interface offers an opt-in checkbox for that request. Only the question text and fixed topic descriptions are sent; operational records, source payloads, actor names and decision tools are not supplied to the model.

The model can return only a supported topic identifier. The server then selects the same authored, cited facts used by the guided questions. Invalid output, tool calls, extra claims, model-identity mismatch, excessive response size or service failure falls back visibly to rules where the question is supported. Offline rehearsal disables the optional model request entirely.

A loopback endpoint does not independently certify how the service runs its model. Configuration is not a successful request, a measured quality evaluation or validated advice. No actual configured model inference has been established by the mocked connector tests. The screen distinguishes **LLM topic selection only** from the deterministic factual engine. No new scientific probability or decision authority comes from enabling it.

### Practice use case

Type **chicken**, click **Ask AEGIS**, then choose **Compare response scenarios** from the suggested choices. Inspect a fact's sources. Open Command to examine the proposed trips, then return, select a shipment and click **Review a simulated shipment**. Export the captured answer for discussion. Make consequential decisions separately in the human-review workflow.

If a question is ambiguous or matched to the wrong topic, choose the appropriate guided card instead. Topic matching is not proof that the system understood every intention. Requests such as “approve this plan” do not execute anything; the assistant explains the read-only boundary. For credentials, installation and connector protocol details, a technical teammate can consult docs/evidence_assistant.md and .env.example without putting secrets into chat or Git.

## Project brief: the learning and presentation hub

Open **Project brief** to find this master handbook, the shorter project/status brief, the team's code repository, dated local-check summaries and the capability register. These documents answer different questions:

| Document | Use it for | What it does not establish |
| --- | --- | --- |
| Master user guide | Learn every workspace, control, use case and practical boundary; print and annotate it | A guarantee that all providers are currently online or every submission requirement is complete |
| Project and presentation brief | Scan implemented features, saved test evidence, limitations and a five-minute narrative | A replacement for the detailed handbook or scientific methods report |
| Scientific report | Review study methods, measured results, assumptions and limitations | Regulatory authority or a validated illness forecast |
| Submission checklist | Track required evidence and the remaining human review gates | Automatic organizer approval |

**Download master guide PDF** supplies the print-ready US Letter handbook, including contents page numbers and PDF bookmarks. **Read or print guide** opens a standalone HTML version; choose **Print this guide** or your browser's print command. **Download master guide Markdown** supplies a text version suitable for notes and future editing. The PDF shows the date it was generated; a printed copy does not update itself when the app changes.

The shorter **Download project brief PDF** and **Download editable Markdown** remain available. **Team GitHub repository** opens the private repository when your GitHub account has access. It is not a button that adds collaborators, deploys the app, signs into Kiro or uploads a submission.

The **Latest recorded local checks** table shows saved pass/fail outcomes, counts, duration and log paths. Opening the page does not run these tests again. The feature register separates P0 required work, P1 operational differentiators, and P2 stretches/deferred work. Read each row's actual status: Iowa road evidence and local recovery are implemented stretches, while cloud accounts and physical sensors remain deferred; language-model topic selection is optional and its quality remains unevaluated.

## Guided rehearsal: practice a complete story

For filming and the complete hands-on review, use **Project brief → Recording
checklist & video runbook** or the **Record the final video** chapter below. A
completed practice record does not establish that a human video was recorded or
reviewed. The operator app stays separate from fresh rehearsal sessions.

The **Practice the five-minute story** panel is part of Project brief. On the operator server it explains how to open a separate practice workspace. **Copy rehearsal launch command** copies the actual command; clipboard access can fail, in which case copy the displayed text manually. This button does not start a server.

On a verified isolated server the panel exposes a timer, ordered stages, notes, history and export. The timer measures elapsed wall-clock time on the server and continues through navigation or reload. It does not prove who was present, whether a presenter showed each screen, or whether the presentation was effective.

### Begin a practice record

1. Confirm the isolated-runtime banner before doing anything that changes a scenario.
2. Enter **Rehearsal presenter** and **Rehearsal purpose**. They are self-declared practice records, not authenticated attendance.
3. Choose **Self-reported team practice** for actual presenter practice. Use **Automated workflow check** for scripts or browser automation; do not relabel automation as a human presentation.
4. Choose **Start rehearsal timer**. This creates a record but does not reset the simulation. If a fresh initial state is needed, prefer a fresh launcher session.
5. Work through each stage, return to Project brief and record what was actually covered or skipped.

| Stage | Planned time | What to demonstrate | Additional evidence required for Covered |
| --- | --- | --- | --- |
| Actor, map and simulation | 40 seconds | Explain the distributor, geography and fictional operations | Self-reported coverage |
| Sources, coverage and measured science | 80 seconds | Show provenance, coverage gaps and actual baseline/model results | Self-reported coverage |
| Simulated disruption and tradeoffs | 60 seconds | Introduce an event and compare responses | A simulated event recorded during this run |
| Explicit dispatcher decision | 60 seconds | Review a proposal and record an approval | An approval recorded during this run |
| Parked driver workflow | 40 seconds | Confirm parking, acknowledge an assignment and report an incident | A coherent recorded sequence for the same current trip |
| Contribution and honest limitations | 20 seconds | Explain value, remaining science/implementation limits and next steps | Self-reported coverage |

The plan totals 300 seconds. Finishing the app sequence in a few seconds is an automated or accelerated check, not a five-minute human demonstration. Running over the target is recorded rather than silently changing the target.

### Record stages and finish

The stage navigation buttons, such as **Open Command**, **Open Sources & evidence**, **Open Model evaluation** and **Open AEGIS Drive**, move to the relevant workspace. Return through **Project brief**. Add **Current stage notes**, then choose **Record stage covered** or **Record stage skipped**. A skip needs a meaningful reason and remains visibly skipped. Notes alone cannot replace the operational evidence required for a Covered disruption, approval or driver stage.

For the driver stage, do not mix an old acknowledgment from one trip with a new report from another. A later event, hold, reset or fresh approval can invalidate the assignment context. Complete the coherent parked confirmation, acknowledgment and report after the latest relevant assignment change. If another client advances the run, reload its current version and write notes for the stage now displayed.

After all stages have an outcome, enter **Rehearsal closing notes** and choose **Finish and save rehearsal**. If stopping early, use **Abort and save record** with a reason. Aborting preserves the existing record; it is not deletion. A rejected request is not an optimistic success: read the error and current run before trying again.

**Download rehearsal evidence JSON** downloads the saved completed/aborted snapshot. **Saved rehearsal** and **Open saved rehearsal** reopen a retained record; **Return to current rehearsal** returns to the current view. The snapshot retains timing, outcomes, source/report hashes and bounded operational evidence. Later resets or refreshed reports do not rewrite that existing export.

### A presentation route through the product

Start with the problem and actor, then show real evidence and scientific limitations. Introduce a simulated disruption, compare the four responses, inspect constraints and approve a plan with an identity and reason. Switch to Drive on the same practice server, confirm safe parking, acknowledge a trip and report a concern. Close on reproducibility, human review and the limits that remain open.

Route laboratory and Road intelligence make useful optional demonstrations of scale and independent evidence. Avoid trying to show every optional control inside five minutes. This handbook is the detailed reference; a presentation should tell one coherent operational story.

### What rehearsal does not complete

A saved practice record does not prove authentic Kiro development, final author review, a reviewed organizer rubric, completed NOAA coverage, prospective predictive validity, truck-route safety or final submission acceptance. Keep these gates explicit even after a technically successful practice run.

## Record the final video

Use the five-minute path for the presentation and the longer checklist for the
weekend hands-on review. The sidebar puts operational work first and **Sources &
evidence** last; the presentation can open evidence earlier to support its claims.
This guide prepares a recording. It does not establish that a human has recorded,
reviewed or submitted the final video.

### Prepare clean sessions

From the NAFSI folder in PowerShell, with dependencies installed and the frontend
built using the README commands, run:

```powershell
.venv/Scripts/python scripts/start_rehearsal.py
```

Leave the terminal open and open its printed URL, normally
`http://127.0.0.1:8001/?mode=rehearsal`. Check the isolated-runtime banner. Before
any event, hold or approval, open `/api/runtime-context` on that same server and
require `mode: isolated_rehearsal`, `isolated: true`, `offline: true` and the UUID
printed by the launcher. A URL parameter alone does not isolate the database.

If the port is occupied, use `--port 8123`; do not stop its owner. For a second
clean Save the Load session, run the same command with `--port 8124` in another
terminal and verify its separate UUID. Each launch reserves a fresh private file
under `data/rehearsals/`. Never reset the operator app on port 8000, reuse an old
reviewed lot as a clean start, overwrite a rehearsal file or alter raw data.
Stop only your rehearsal server with Ctrl+C; retain its database and exports.

Before recording, check microphone, readable browser zoom, desktop and mobile
layouts, notifications and download location. Pre-open the two verified sessions
and the evidence/model sections. Preserve a dated screenshot/export for a failed
source or blank map. Offline mode uses dated fixtures, caches and labeled route
estimates; it does not make them current. Browser OpenStreetMap tiles still need
internet. If tiles fail, explain the missing background and show the route
geometry/results. Do not hide failures or describe QA placeholder tiles as live.

### Five-minute presentation path

Keep the operational story on one isolated server. Use the second, clearly
identified session only for the short freshness highlight. Practice the sequence
before recording; the full checklist below is longer than five minutes.

| Time | Click and explain |
|---|---|
| 0:00–0:30 | **Command center**: identify the dispatcher, Missouri map, two simulated DCs and fictional shipments. Show **SIMULATED OPERATIONS** and distinguish official establishment markers from the simulated network. |
| 0:30–1:10 | **Sources & evidence**: show retrieval/source dates, an actual failure or stale warning, official recall notices and NOAA coverage: five stations, 2,730 date rows, nine missing precipitation values. Keep CDC surveillance/outbreak evidence separate from FSIS sample outcomes. |
| 1:10–1:45 | **Model evaluation**: show the chronological holdout, prevalence baseline, logistic metrics and calibration. Read measured values from the screen. Explain selected-sample positivity, the baseline comparison and unavailable historical publication timing; no consumer illness probability or prospective-validation claim. |
| 1:45–2:45 | Back in **Command center**, select **SH11**, choose **Cargo temperature excursion**, then **Preview event impact**. Compare A/B/C/D cost, unmet demand, changed trips and solver/constraint outcomes. Check the intention box and **Apply previewed event**; it clears approved assignments and does not impose a hold automatically. |
| 2:45–3:35 | **Compare refreshed response plans**, then **Review** on scenario C. Inspect proposed assignments, lots and precautionary holds. Enter **Dispatcher name** and **Reason for approval**, then **Approve simulated plan**. Show that held/recalled stock is excluded and the approval is recorded in **Recent activity**. |
| 3:35–4:10 | **AEGIS Drive**, on the same server at mobile width: select a truck with an approved assignment, **Confirm safely parked**, open **Dispatch instructions**, **Acknowledge assignment**, then **Report an issue** and **Send to dispatcher** with a short simulated incident. Show its receipt; route, fuel and position are simulated. |
| 4:10–4:45 | Switch to the separate fresh session and say so. **Save the Load** → **Start rescue experiment** → **Replay heat excursion**. Show the point and conservative quality windows, nearer recipient and **Show FEFO pick order** / **Show FIFO pick order**. This short highlight previews a separately reviewed rescue; use the longer path below for its approval and driver handoff. |
| 4:45–5:00 | Close with the contribution: inspectable evidence, constrained tradeoffs and human authority. State the remaining scientific and human gates. Record the actual elapsed presentation time. |

In **Project brief** → **Practice the five-minute story**, enter the real
presenter/purpose, choose **Self-reported team practice** and **Start rehearsal
timer** before the practice actions. Return to record stages in the displayed
order with notes; the main scenario-C path supplies the disruption and approval
actions. **Record stage skipped** needs a reason. Finish with closing notes and
**Finish and save rehearsal**, or **Abort and save record** if stopping early;
download the rehearsal evidence JSON. Stage records are separate from the video.
Freshness alone does not cover the evidence/model narrative or the required
parked confirmation, assignment acknowledgment and incident. Do not treat a
timer, a saved record or five planned minutes as proof of presentation quality.

### Full hands-on click-through

Use this as a coverage sheet before the final take. Record pass/failure, session
UUID and export/screenshot names separately. Use fresh sessions for independent
mutation stories; scenario approvals and rescue approvals replace assignment
sets, while events and holds can invalidate decisions already under review.

- [ ] **Command center**: **Try a 1-hour delay**, inspect unserved demand,
  deadline pressure and cargo checks; open **Cargo assumptions** and compare the
  four preview responses. **Inspect SH…** opens that candidate;
  **Compare roads for SH…** carries its actual endpoints into Road intelligence.
  Change an assumption, observe that the captured result needs recomputation,
  then **Estimate impact**. Export the outlook. These previews publish nothing.
- [ ] **Command center**: inspect map presets/layer counts, candidate versus
  approved/scenario allocations, **Cold-chain & trip detail**, weather provenance
  and **Request road route**. Read route/fallback provenance. Run the complete
  SH11 event → A/B/C/D comparison → scenario-C review/approval → Drive sequence
  above. Open **Recent activity**, inspect the actual event/approval/report
  payloads and export the relevant history. Test stale-proposal rejection in a
  separate practice session; refresh and review again instead of bypassing it.
- [ ] **Save the Load**, in its own fresh session: keep the default demonstration
  candidate; **Start rescue experiment**, inspect **Sensor gateway connection**,
  then **Replay heat excursion**. Read observation and receipt times, the product
  temperature and reference-budget charts, **Point quality-window estimate**,
  **Conservative sensitivity window** and **How the quality clock is estimated**.
  Ambient, humidity, vibration and ethylene remain contextual channels.
- [ ] Inspect eligible and excluded rescue destinations, original-trip duration
  plus receiving buffer, quality margin and fallback route label. Use **Check
  road route** if needed; use **Prepare selected rescue** when shown, then
  **Review [destination]**. Open all proposed assignments and compare whole-plan
  cost, unmet demand, solver status and violations. Toggle both FEFO/FIFO pick
  orders and read actual lot, quantity and arrival-quality differences; do not
  assume FEFO always improves every measure.
- [ ] In the rescue review, fill **Reviewing dispatcher** and **Reason for rescue
  approval**. Confirm the three separate reviews: quality/food-safety disposition,
  receiving capacity/recipient acceptance, and route/vehicle limitations. Choose
  **Approve simulated rescue plan**, inspect the receipt, then **Open approved
  driver assignments**. Verify the exact truck, trip, lot and destination.
  While parked, acknowledge the assignment and submit an incident if this is a
  full rehearsal. Return to the same experiment and **Replay cooling recovery**
  or add a later frame: show renewed-review advice and the unchanged route.
  **Refresh plan for new review** retains accumulated exposure; **Continue lot’s
  exposure history** reopens it. Export the captured experiment. Repeat a clean
  story through another launcher session, never by resetting consumed quality age.
- [ ] **Route laboratory**: run **Single farm dispatch** and **Multi-location
  fleet** with estimated routing and **Test dispatch plan**. Inspect truck loads,
  unserved stops, constraints and the illustrative cold-chain projection. Try a
  delay/fault and rerun. Explore **Your operation**, then name and **Save as new
  project**; change and rerun before **Save next version**. Reopen a saved version,
  compare two experiments and export snapshot/stop sequence. Save before leaving
  an editor; route experiments do not publish Command assignments.
- [ ] **Road intelligence**: choose a named journey, **Compare planning routes**,
  inspect geometry, source/retrieval ages and a nearby notice; inspect Missouri
  and Iowa events separately, including provider time fields and coverage limits.
  **Export comparison JSON**. Zero nearby matches is not road clearance; ordinary
  driving/estimated routes do not certify truck restrictions or closure avoidance.
- [ ] **Dispatcher desk** and **AEGIS Drive**: review the submitted incident,
  fill the decision record, **Start review**, send a concise versioned instruction
  with **Approve and send instruction**, then acknowledge that exact instruction
  in parked Drive. **Resolve report** records an operational review. Inspect
  **Dispatch readiness review** and refresh it. In a separate session, place a
  human hold, show affected assignments removed and recalled lots blocked, then
  release the hold and show that a fresh plan still needs approval. **Listed
  checks passed** requests final human review; it neither dispatches nor certifies
  food safety. In Drive, **Lock for driving** must disable reports/acknowledgments.
- [ ] **Evidence assistant**: type **chicken**, **Ask AEGIS**, choose a suggested
  question, inspect its citations and expandable provenance, then try a common
  question card. Answers explain a captured network; they do not approve actions.
- [ ] **Model evaluation**: inspect timing/sensitivity and error analysis,
  **Chronological holdout comparison**, calibration and limitations. Confirm the
  sampling target/units, temporal split and displayed baseline comparison. Keep
  the FSIS estimator distinct from illustrative cargo and freshness calculations.
- [ ] **Project brief**: open the recording guide, maintained master guide and
  project brief downloads; inspect check timestamps and pending capability gates.
  Record actual presenter practice with the timer and notes as described above.
  Browser/script verification belongs to **Automated workflow check**.
- [ ] **Sources & evidence**, last in the workspace tour: inspect **Food access
  across Missouri**, county measure vintages/units/missingness and CSV export;
  these values do not rate safety or change dispatch. Inspect underlying evidence,
  filters, pagination, schema/import provenance, NOAA variable gaps, source-specific
  ingestion, official recall notices, connectivity and raw inventory. HTTP success
  is distinct from validated coverage. Offline **Refresh** is disabled; retain
  dated failures and never claim a verified recall match to a fictional lot.

### Claims and final human gates

Call Save the Load an illustrative Q10 quality-planning experiment. Its
coefficient sensitivity range is not a confidence interval. No connected physical
hardware, calibrated poultry spoilage/molecular measurement or microbiological
safety clearance has been demonstrated. Keep label/use-by limits, food-safety
review and receiving approval independent. Document coverage abstention,
unavailable FSIS publication timing and other unresolved limits in the report.

Pytest, frontend tests/build, Chrome workflow checks and the accelerated
`scripts/demo_run.py` / `scripts/freshness_demo.py` are software evidence from
their recorded timestamps. They do not establish a timed human video, current
source coverage, genuine Kiro work or final submission. Consult
[progress](progress.md) and the dated reports for executed results; do not invent
new counts or source successes for the recording.

Before delivery, a person must complete authentic signed-in Kiro spec/task work
and preserve its evidence, review authorship and the final methods/results/limits,
confirm organizer rubric, duration and delivery requirements from official
materials, and watch/listen to a real timed final take. Check the saved video and
backup evidence, then record the actual submission separately. The maintained
[demo script](../reports/demo_script.md), [rehearsal guide](rehearsal_guide.md),
[morning review](morning_review.md) and [submission checklist](submission_checklist.md)
provide the supporting handoff.

## Storage, exports and sharing

Project brief now starts with **Five tasks. One inspectable submission.** Each
task opens related operational/evidence workspaces and allowlisted source/result
exports. **Download final five-task PDF** and **Read final guide and presentation**
provide the concise handoff. Task 1 exports its diagram/dictionary/provenance and
analytic CSV; Task 5 offers a one-page team statement with last names and final
author review left for the team. Kiro non-use is explicitly disclosed.

The **Preserve food. Compare who receives it.** panel switches three captured
simulated scenarios across a feasible rule, volume/quality preservation and
balanced service. Compare distributed/unmet food, service and quality exposure,
then expand per-destination results/actions. These are fixed-seed read-only
studies; they do not change current assignments, impose holds or certify safety.
The displayed equity measure concerns destination service, not an invented
population-vulnerability score. Download JSON or CSV for all nine comparisons.

The current app is a local research demonstrator with saved SQLite operational state and separate evidence files. It does not run a continuous warehouse inventory ledger, synchronize companies through cloud accounts, or send physical truck instructions outside the application.

| Item | Where it lives or how it is shared | Important distinction |
| --- | --- | --- |
| Current network, proposals, approved assignments and audit | Local application database | Refreshing the page rereads saved state; resetting the demo changes the current exercise |
| Driver reports, focus, instructions and verification reviews | Same local backend as Command | A report/instruction on one server is not automatically shared with another teammate's server |
| Saved laboratory runs and project versions | Planning records in local database; JSON/CSV exports are downloadable | A saved experiment cannot become a dispatched trip by reopening it |
| Original supplied files | Their preserved raw locations and audit manifest | They are never overwritten to make an import succeed |
| Processed scientific tables | Source-specific derived files and ingestion reports | CDC, FSIS and county-context layers retain distinct meanings |
| Public-source caches and dated fixtures | Local evidence files with retrieval metadata | A cache read is not necessarily a new provider response; a fixture does not become current |
| Rehearsal records | The separate UUID practice database and immutable JSON exports | Automated workflow evidence is not human presentation evidence |
| Team code | Private GitHub repository and reviewed branch | GitHub shares source and allowed evidence, not credentials or an active operational database |

Unsaved form text is usually a browser draft. Navigating away, reloading, receiving a new run version or changing context can clear it. Read each workspace's save/submit receipt. Downloaded exports are independent files; later changes in the app do not update a copy you already printed or emailed.

### Which exports are actually available?

The route laboratory supports saved-run JSON and stop-sequence CSV through its planning library, plus version/project comparisons. Road intelligence exports a captured comparison JSON. County context supplies a checked county CSV. Completed/aborted rehearsals export evidence JSON. Project brief supplies this handbook and the shorter status brief in their offered formats.

The underlying source-table browser has bounded row inspection and schema/provenance; it does not currently offer a general table-export button. Model evaluation reads saved results; it does not offer an in-app training button. Do not infer an export, live refresh, account or disposition feature merely because its data are visible.

## Local backup and recovery

Backup/recovery is a command-line tool for the technical teammate, not an extra website button or a cloud service. It protects local simulated operational records when experimenting. The database itself contains recorded identities, reports, instructions and assignments, so keep backup files private.

Create a new backup from the project directory:

```powershell
.venv/Scripts/python scripts/backup_state.py create
```

The result prints a fresh directory under **data/backups/**. Verification checks checksum, SQLite integrity, supported schema and row counts. Restoration creates a new file under **data/recovered/**; it never overwrites the operator database or automatically points the running server at the recovered copy.

For a specific backup, follow the complete commands in **docs/backup_restore.md**. Choose a fresh destination each time. Do not manually copy or delete SQLite WAL/shared-memory sidecars. Review restored holds, recalls, assignments and parked confirmations before any resumed use. Restoring old approvals is not a new approval or permission to dispatch.

The tool records integrity relative to its manifest, not an authenticated author signature or a scientific safety finding. Raw observations, source caches, code, credentials and frontend files are outside this operational-state backup. Private backups/recovery receipts are excluded from Git and reviewer packages.

## Troubleshooting by what you see

| What you see | Likely meaning | Useful next step |
| --- | --- | --- |
| Connecting to the local backend | The local server is stopped, unavailable or not serving the expected port | Start the documented server and check its terminal; use Retry connection |
| Map tiles are blank but markers/data appear | Browser tile requests need internet or failed independently | Read the geometry/source information; do not treat missing tiles as a solver failure |
| No approved assignments in Drive | No plan is approved on this server, or an event/hold/reset/new plan invalidated earlier assignments | Check Command and Dispatcher desk on the same port; review and approve a fresh plan if appropriate |
| Driver actions are locked | No current parked attestation, expired confirmation, read-only focus or a different selected truck | Park safely and confirm for the truck now displayed; acknowledgment does not grant dispatcher authority |
| Network changed / stale version | A proposal, instruction or trip was based on an older revision | Refresh its current context and review the evidence before resubmitting; do not repeatedly click an obsolete decision |
| Source unavailable / stale / cached fallback | The provider failed, a response aged past its window, or only dated evidence exists | Read timestamps/error details; refresh deliberately when allowed, and retain the gap if it persists |
| Offline source refresh is disabled | This is the intentionally isolated offline rehearsal | Use its dated fixtures and estimates; a separate operator source check is a different action |
| Laboratory inputs changed | Current form values differ from the displayed saved/completed run | Test the plan again before interpreting the new inputs as its results |
| Unserved stops or unmet demand | Available eligible stock, capacity, timing or solver choices could not serve everything | Inspect exclusions and constraints; do not assume an unserved delivery was safe to force through or automatically wasted |
| Solver reports failure / no usable routes | The submitted assumptions did not produce the expected feasible solution, or routing evidence failed | Read its actual status and warnings; adjust plausible inputs and rerun rather than inventing feasibility |
| Hold release succeeded but no trip returned | Release does not recreate deleted assignments | Produce, review and approve a fresh eligible plan |
| Rehearsal Covered is rejected | Required audit evidence is missing, stale, invalidated or from a different trip/run | Complete the actual stage on the same isolated server, or record an honest skip reason |
| A printed guide differs from the app | The app or evidence changed after this guide's generation date | Download the current guide and consult the current labels/timestamps |

If a problem persists, retain the exact visible error and the relevant source/run identity for the technical teammate. Avoid repeating a consequential action until you know whether the previous request was accepted. The app distinguishes a rejected request from an accepted action whose subsequent refresh failed.

## Glossary for reading the site

| Term | Plain-language meaning in this project |
| --- | --- |
| Adaptive early warning | Combining evidence and scenario review to help a human notice and respond; not a guarantee of prediction |
| Digital twin | A deterministic simulated network that mirrors operational concepts; not a live replica of a real company |
| Lot | A simulated product batch with inventory, eligibility, hold and recall state |
| Candidate shipment | A possible fixed trip in the network, before scenario selection and approval |
| Proposal | A calculated response awaiting an explicit human decision |
| Approved assignment | A simulated trip published by dispatcher approval and visible to Drive |
| One-wave allocation | Choosing eligible shipments for one planning exercise; not a rolling warehouse stock ledger |
| Constraint | A limit the plan must respect, such as stock, capacity, eligibility or a hold |
| Feasible | A solver found a plan satisfying its modeled constraints; not a finding that a physical operation is safe |
| Optimal | Best under that solver's stated objective and model; not universally best or clinically safe |
| Unmet demand | Requested quantity not served by that modeled plan |
| Food waste | A model-specific reported quantity under stated assumptions; not every unserved delivery |
| Hold | A human-recorded restriction excluding a lot from dispatch in this application |
| Eligibility | Whether a simulated lot, supplier or truck meets the modeled requirements |
| Targeted verification | A recorded scenario-B review checklist; separate from driver acknowledgment and product certification |
| Revision/version | A number identifying the state a decision was based on; stale writes are rejected |
| Provenance | Where information came from, its meaning and the hashes/times/context needed to trace it |
| Retrieval time | When the app obtained a response; different from when a provider observed or edited a record |
| Cached response | Previously retrieved evidence reused locally; it may be valid within a cache window or stale |
| Dated fixture | A preserved actual source response used for a reproducible offline demonstration |
| Forecast | A provider's prediction for future weather; not an observed station measurement |
| Historical reanalysis | A reconstructed weather product; not interchangeable with required NOAA observations |
| Simulated telemetry | Generated cargo or vehicle values for the exercise; no physical sensor is connected |
| Parameter sensitivity | How a projection changes when assumed parameters change; not a statistical confidence interval |
| Positivity | The fraction of selected laboratory samples testing positive for the defined outcome; not consumer illness probability |
| Baseline | A simple comparison estimator used to judge whether a more complex model adds value |
| Chronological holdout | Later observations kept out of model fitting and used for evaluation |
| Calibration | Whether predicted sampling probabilities agree with observed frequencies in suitable groups |
| Brier score | Mean squared probability error; lower is better for the same defined evaluation task |
| PR-AUC / average precision | A ranking summary focused on positive examples; interpret relative to prevalence and the exact reported method |
| ROC-AUC | A ranking summary across thresholds; about 0.5 indicates little discriminating ability |
| FIPS | A geographic identifier; different counties with similar names remain separate |
| Geometry proximity | A spatial buffer comparison; a nearby event may be on a parallel road or other carriageway |
| OSRM driving profile | Ordinary-driving routing, without verified commercial-truck restriction checks or automatic DOT closure incorporation |
| Parked attestation | A time-limited self-declaration enabling driver interactions; not a motion sensor |
| Human approval | An explicit recorded app decision; not government authority or physical dispatch |

## Present the project accurately

Use a concrete operational story: a fictional poultry distributor has a constrained plan; evidence and a simulated disruption create a reason to review it; the team compares responses, checks exclusions and records a human decision; the driver receives the resulting assignment and can report back while parked.

Useful statements include: “These are simulated logistics on real geography”; “This source response is dated”; “The model did not outperform the simple baseline here”; “This is a review flag, not an illness probability”; and “The dispatcher must approve a consequential action.” Point to the source, result or audit record that supports each claim.

Avoid statements such as “We predict who will get sick,” “Every road is clear,” “This alternative is truck-safe,” “These are live vehicles,” “AI automatically recalled the shipment,” or “The presence of Kiro files proves Kiro execution.” The current evidence does not establish those claims.

Use the shorter presentation brief to select what fits into five minutes. Keep this handbook as the detailed reference and a place for handwritten questions. Record which claims still need an author/scientific review rather than simplifying them into unsupported certainty.

## Keep this master guide current

The editable master file is **docs/aegis_master_guide.md**. It is assembled from reviewed chapters under **docs/manual_parts/** and dated verification reports. The PDF and standalone HTML are in **reports/**. The manifest records their generation date, PDF checksum, chapter page numbers and source-file hashes.

For the technical teammate: update the relevant chapter when a visible control, workflow, data meaning or limitation changes, then run:

```powershell
.venv/Scripts/python scripts/build_master_guide.py
```

Run the project's relevant tests and frontend build for application changes. The guide compiler does not run provider checks, train models, open the operational database, create approvals or complete submission gates. Its verification appendix reads saved results and keeps their dates separate.

Useful deeper references are README.md, docs/architecture.md, docs/model_card.md, docs/simulation_assumptions.md, docs/operations_workflow.md, docs/road_intelligence.md, docs/state_dot.md, docs/backup_restore.md, docs/rehearsal_guide.md and docs/submission_checklist.md. The handbook is the main reading path; those files provide technical and submission detail.

## Recorded verification and what remains open

A saved pass describes an executed check at its recorded time. It is not a promise that every provider is online now, that a vehicle is safe, or that the submission has been approved.

Latest saved local check finished: 2026-11-02T17:34:09.500779+00:00. Read the following results literally; missing evidence is not counted as a pass.

| Check | Saved result | Meaning |
| --- | --- | --- |
| pytest | PASS; 1283 tests | Executed local command; see reports/checks/20261102T173101620197Z/pytest.txt |
| vitest | PASS; 406 tests | Executed local command; see reports/checks/20261102T173101620197Z/vitest.txt |
| frontend_build | PASS | Executed local command; see reports/checks/20261102T173101620197Z/frontend_build.txt |

Backend tests exercise data handling, holds, recalls, capacities, eligibility, approvals, stale versions, driver safeguards and isolated rehearsal. Frontend tests exercise user interactions and error states. A production build checks that the app compiles. These cover different questions.

- Recording preparation: Chrome workflows and automated tracker record: 116/116 saved browser checks, recorded 2026-10-31T07:15:22.941Z. Evidence: reports/browser_qa/recording/results.json. Runs have separate dates and are not all repeated for every change.
- Save the Load, FEFO and driver handoff: 94/94 saved browser checks, recorded 2026-10-31T06:30:41.552Z. Evidence: reports/browser_qa/freshness/results.json. Runs have separate dates and are not all repeated for every change.
- Road intelligence: 58/58 saved browser checks, recorded 2026-10-28T19:15:52.092Z. Evidence: reports/browser_qa/roads/results.json. Runs have separate dates and are not all repeated for every change.
- Guided rehearsal: 76/76 saved browser checks, recorded 2026-10-28T06:07:06.190Z. Evidence: reports/browser_qa/rehearsal/results.json. Runs have separate dates and are not all repeated for every change.
- County context/readiness: 61/61 saved browser checks, recorded 2026-10-28T06:27:38.973Z. Evidence: reports/browser_qa/readiness/results.json. Runs have separate dates and are not all repeated for every change.
- Drive: 65/65 saved browser checks, recorded 2026-10-28T06:28:06.730Z. Evidence: reports/browser_qa/drive/results.json. Runs have separate dates and are not all repeated for every change.
- Dispatcher/custom operations: 50/50 saved browser checks, recorded 2026-10-28T06:27:54.619Z. Evidence: reports/browser_qa/operations/results.json. Runs have separate dates and are not all repeated for every change.
- Planning/evidence depth: 36/36 saved browser checks, recorded 2026-10-28T06:19:01.253Z. Evidence: reports/browser_qa/depth/results.json. Runs have separate dates and are not all repeated for every change.
- Command controls: 65/65 saved browser checks, recorded 2026-10-28T06:19:25.790Z. Evidence: reports/browser_qa/controls/results.json. Runs have separate dates and are not all repeated for every change.

The guided delivery-outlook, chicken-question, map-layer, road and dispatcher walkthrough recorded 76/76 actual-Chrome checks at 2026-10-30T19:40:42.320Z. External map tiles used browser-only QA placeholders; no public providers or language model were queried. This verifies application behavior, not prospective prediction accuracy. Evidence: reports/friendliness_workflow_evaluation.json.

The accelerated deterministic freshness replay recorded 15/15 checks. Evidence: reports/freshness_demo.json. It uses a fresh isolated database and simulated sensor packets; no physical hardware, calibrated spoilage prediction or timed human presentation is inferred.

The reviewer-package check verifies paths and checksums, extracts trusted project code into a separate directory, blocks application networking, and exercises offline workflows. It does not establish a new dependency installation unless a separate installation report explicitly records one.

A deliberately injected browser failure is a test case, not a provider outage. A test failure and its correction remain part of the evidence history. The earlier duplicate CI timing failure and synchronized follow-up are described in reports/ci_followup.json. For the current remote commit, inspect GitHub checks directly rather than assuming an older run applies.

### Submission and scientific gates still requiring real evidence

- Genuine Kiro sign-in, specification execution and reviewed task/test evidence remain separate from Codex-generated files or an installed IDE.
- Final organizer-rubric review, author review and a timed human team presentation remain pending unless the team records their actual completion.
- Actual per-result public availability dates are missing. Retrospective sampling results are not a validated prospective forecast.
- NOAA coverage is bounded and retains precipitation gaps; no validated FSIS-weather join is claimed.
- Isolate-level genomic linkage, production accounts, physical sensors, cloud hosting and evaluated language-model advice are not implemented. The evidence assistant uses server-authored facts; optional topic selection is not a validated advisory model.

Use the application to explain a transparent decision-support workflow and measured limitations. Do not replace an open requirement with a feature count or an invented accuracy figure.
