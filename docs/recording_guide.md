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
