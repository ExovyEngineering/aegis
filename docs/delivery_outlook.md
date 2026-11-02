# Delivery outlook

Start in Command center. The outlook computes the current simulated delivery
wave automatically. **Try a 1-hour delay** reruns the calculation with 60 extra
minutes on every candidate trip. Compare unserved demand, delivery windows and
cargo checks, then use **Inspect** to open a candidate. **Compare roads for SH...**
carries that row's named endpoints and captured network revision into Road
intelligence; click **Compare this journey** there to calculate a comparison.
The general **Check road alternatives** button opens named journey examples
instead. No planning preview is an approval.

## What is calculated

`POST /api/delivery-outlook` reads one bounded operational snapshot through a
read-only SQLite connection. It computes scenario A before the chosen assumptions
and scenarios A–D after them, using the existing OR-Tools allocation and independent
constraint checks. Each result must be feasible with zero violations and a passed
independent review. Held, recalled or ineligible lots remain excluded.

Inputs are the expected integer network revision, 0–240 whole additional delay
minutes, a −20 to 45°C ambient planning assumption and an optional refrigerated
truck fault. A fault makes the shared truck ineligible; it does not immediately
raise the cargo reading. Existing simulated faults and unrefrigerated vehicles
remain distinguishable from chosen faults. No provider is contacted.

Outputs include before/after allocation, destination shortages, candidate deadline
margins and projected cargo temperatures at arrival or the six-hour check horizon.
Candidate flags include trips that the allocation may exclude. Baseline means a
newly computed A allocation, rather than the approved assignment list.

## Interpretation

This is a **deterministic planning projection**, not a fitted disruption forecast,
live ETA, pathogen-growth model or probability of illness. Added delay is uniform
and chosen by the user; it is not inferred from a road event. Ambient temperature
is a planning input, not the weather feed. Thermal coefficients are uncalibrated,
and 4°C is the demonstration review threshold. The clock is relative to one
simulated wave, not the current calendar day.

New projected temperatures do not become observations or automatic holds. Scenario
C uses existing simulated review readings and proposes any holds for separate human
approval. Scenario D can substitute eligible supply on fixed candidate trips; it
does not redesign a road route. The measured FSIS sampling baseline/evaluation on
Model evaluation remains a separate scientific result.

## Captured results and safeguards

Editing assumptions marks the old result as captured until **Estimate impact**
finishes. The result stamp and JSON export retain the actual calculated inputs.
Changed revisions, incomplete provenance and failed independent checks fail
visibly. A second semantic snapshot check rejects a calculation if operational
state changed during it. The endpoint neither initializes a missing database nor
creates a proposal, audit event, hold, route, assignment or source refresh.

The UI does not publish these what-if allocations. **Review current response
plans** focuses Command's current scenario comparison, as does **Compare delivery
responses in Command** from Road intelligence. Extra-delay and cargo assumptions
stay in the outlook preview. Road comparison exports preserve the compared
candidate's ID, endpoints and network revision; later edits do not reattribute an
older result. Reopen the candidate from Command to use updated endpoints. These
handoffs do not approve road geometry, alter assignments or publish a detour.
Review and approve a separate current plan through the existing workflow.
