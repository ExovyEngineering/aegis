# AEGIS Drive: visual trip view and parked-use controls

Design and acceptance contract, October 27, 2026. This document describes the
implemented Drive extension. A capability is verified only when the
corresponding executed tests and browser evidence appear in the current
verification reports; this design document alone is not completion evidence.

## Product scope

AEGIS Drive is a dedicated mobile-responsive view of the existing application,
using the same FastAPI backend, approved assignments, dispatcher decisions and
audit trail as AEGIS Command. The intended direct entry is `?mode=drive`.
It is not a separately deployed native application, a live fleet-tracking
service or a commercial navigation product.

The primary screen gives a driver a small number of clear visual facts:

| Element | Meaning and source boundary |
|---|---|
| Current destination | Destination of the selected dispatcher-approved assignment; show its simulated location name and trip/truck IDs |
| Plan status | Whether an approved assignment is available, acknowledgment is pending, instructions changed or targeted verification remains pending |
| Journey estimate | The assignment's documented travel estimate; label the source and do not present it as a live arrival prediction |
| Fuel level | A deterministic simulated value with visible simulation provenance; no vehicle sensor or physical fuel reading is connected |
| Cargo temperature | Simulated cargo telemetry for the selected assignment; distinguish it from ambient weather and illustrative thermal projections |
| Position/context | The simulated dispatch-origin position when supplied; it is not live GPS and must not imply that the truck has progressed along its route |
| Disruption/instruction status | Assignment-relevant simulated events and dated source evidence, with dispatcher-approved text kept distinct from unapproved routing suggestions |

Large destination text and fuel/cargo tiles should make status easy to scan.
Detailed source text, alternative routes, reporting and review actions belong
behind parked-use controls. Color supports a text status and must not be the
only way to identify an advisory.

No assignment means an explicit empty state. The application must not create a
fictional destination, current position, arrival countdown or approved route to
fill an empty card. Changing truck or trip must update every displayed fact and
report target together; delayed responses for another trip must not overwrite
the current selection.

## Interaction states

Drive starts with interactions locked. Unknown motion status is not evidence
that a person is parked. The user may explicitly enter a driving/read-only view
or attest that the vehicle is safely parked before using parked-only actions.

| State | Visible information | Allowed interaction |
|---|---|---|
| Locked/default | Essential destination, plan, fuel and cargo status with simulation labels | No typing, assignment/instruction acknowledgment or report submission |
| Driving/read-only | The simplified visual status view | No typing, reporting, acknowledgments or interactive route exploration; do not describe this as detected motion |
| Parked attestation active | Visual status plus concise trip details and approved instructions | Relevant parked-only actions, subject to current assignment/version and server checks |
| Attestation expired or unavailable | Visual status and a clear locked explanation | Parked-only writes remain disabled until a new valid attestation is recorded |

A parked attestation lasts **ten minutes** according to server time. The UI
must return to the locked state on expiry and must handle a server rejection
without silently retrying a consequential action. Selecting read-only mode
must relock interactions. Reloading or opening another tab must not create an
unverified assumption that the driver is parked.

The attestation is self-declared. It is not a motion sensor, operating-system
driving lock, authenticated driver identity or proof that a vehicle is stationary.
A person can misstate their circumstances, use another application or device, or
bypass presentation controls. The feature reduces opportunities for interaction
inside this demonstrator; it cannot guarantee that a driver will not text or
interact while driving. Do not claim crash prevention or verified driver safety.

## Server enforcement and existing API paths

Hiding an input or disabling a button is insufficient. The server must require
a current parked attestation for driver-originated writes and verify its
association with the relevant truck/assignment context. Missing, expired,
invalid or context-mismatched attestations must be rejected without mutation.

This applies to both the new Drive interface and existing driver paths:

- Original assignment acknowledgment at `/api/driver/{sid}/acknowledge`.
- Exact-version instruction acknowledgment at `/api/driver/{sid}/instruction-ack`.
- Incident submission at `/api/driver/incident`.
- Any new driver quick-report action that reaches those workflows.

Existing revision, lot-hold, recall, eligibility and instruction-version guards
remain necessary. A parked attestation does not grant dispatcher authority,
approve a detour, release held stock, override a recall or complete targeted
verification. An acknowledgment is not a departure authorization or a safety
finding. Dispatcher instructions remain human-approved app records; they do not
automatically execute physical dispatch.

The app remains a local demonstration with self-declared identities. Parked
attestation is an interaction precondition, not production authentication,
authorization or tenant isolation. Public hosting needs separate controls.

## Reporting and routing behavior

While parked, a driver can select a predefined quick-report category or submit
a concise description for the selected approved assignment. Quick reports use
the standard incident workflow and appear in the dispatcher desk with the same
immutable reporting context and audit trail. They must not bypass review,
automatically impose a hold or silently modify routing and inventory.

Use a clear success receipt only after the server accepts the report. Retain an
unsent description on failure where practical and prevent duplicate submission
while a request is pending. If the assignment was invalidated, explain the
rejection and refresh the relevant state instead of reporting against another
trip. A preset report is still a simulated driver statement, not verified
evidence that a real road, cargo or vehicle event occurred.

Route review is available while parked when supported. The displayed geometry
and duration retain their OSRM/cache/fallback provenance. Requesting or viewing
an alternative never changes the assigned destination or authorizes a detour.
Public OSRM driving routes do not establish commercial-vehicle suitability and
do not automatically incorporate current MoDOT closures. A dispatch-origin
marker is not a moving vehicle location, and a static route map is not live
turn-by-turn navigation. Do not show invented road-clearance or truck-safe labels.

Do not add a decorative "Call dispatch" button without an actual configured
contact action. An internal reporting or instruction panel should be named for
what it really does. No external phone call, text or message is sent by this
design.

## Reference handling

The supplied `pic2supplychain.html` and `Build Winning Supply Chain Project.html`
are duplicate saved planning conversations: their normalized visible text is
identical. They contain accessible local images, including a NEXUS mobile driver
concept and an illustrative dark logistics-map concept. They are visual and
planning references, not independently verified organizer rules, live data or
implementation instructions.

Useful mobile cues are a dominant destination, large journey estimate, simple
fuel/cargo tiles and a small action area. The pictured Berlin destination, fuel
percentage, temperature, waypoint and progress values are illustrative and must
not be copied into AEGIS as observations. A dense desktop control-room image is
not a requirement for the driver view. Keep AEGIS's source and simulation labels
visible even when simplifying the interface.

## Acceptance evidence to retain

- Direct `?mode=drive` entry renders the dedicated view, including empty and
  failed-backend states, at desktop and narrow mobile sizes.
- All status cards and reports follow the selected approved truck/trip; stale
  responses cannot restore a different trip's details.
- Default/read-only states suppress typing, reports and acknowledgments.
- Server tests reject missing, expired and wrong-context parked attestations
  through the existing driver endpoints as well as new controls.
- A valid attestation permits only appropriate writes; expiry and relocking
  block subsequent writes without mutating assignments or incidents.
- Quick reports reach the normal dispatcher inbox and preserve reporting
  assignment context; normal reports and exact-version acknowledgments work.
- Held/recalled or invalidated assignments cannot be revived by a driver action.
- Fuel, cargo and origin-position provenance remain explicit; no live GPS,
  motion detection, route progress or physical sensor integration is implied.
- Every visible action has an implemented result, a pending state, a useful
  failure state and appropriate double-submit protection.
- Relevant pytest, Vitest, production-build and isolated actual-browser results
  are recorded after execution; existing operator state and raw files remain
  unchanged by the test rehearsal.


## Executed evidence

The October 27 implementation is covered by `tests/test_drive.py`,
`tests/test_drive_integration.py`, frontend driver tests and
`reports/browser_qa/drive/results.json` (65 actual-Chrome checks). The current
full-suite result remains in `reports/session_verification.json`; this document
is not a substitute for those dated logs. Browser capture confirms destination,
journey and both gauges fit at 390 x 844. The dedicated entry avoids bulk recall,
inventory and model requests. Original report/assignment context is preserved.
