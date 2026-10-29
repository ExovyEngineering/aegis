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
