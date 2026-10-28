# Five-minute AEGIS demonstration

Build and test the application before presenting. Start a fresh isolated server with `.venv/Scripts/python scripts/start_rehearsal.py` and open the printed URL, normally `http://127.0.0.1:8001/?mode=rehearsal`. Keep the normal operator app on port 8000. Source timestamps and simulated operational time are different; map tiles may need internet. Do not claim dated evidence is live.

The launcher reserves a new UUID-named SQLite file, uses the verified isolated runtime profile and requests offline-demo adapters. It never resets the operator database or kills another server. See [the rehearsal guide](../docs/rehearsal_guide.md) for port conflicts, prepare-only output and source limitations. A URL query parameter alone does not provide database isolation.

`scripts/demo_run.py` is a separate accelerated in-process software check. It writes `reports/demo_results.json`, measures original SQLite/sidecar fingerprints before/after and restores the original database binding on errors. Its scripted scenario-D narrative is not a timed human presentation and is separate from the manual scenario-C path below.

| Time | Action and point to demonstrate |
|---|---|
| 0:00–0:40 | Open Command; show the Missouri map and simulation label. Identify two DCs, fictional shipments, and separate official establishment markers. |
| 0:40–1:20 | Show source coverage, recall retrieval time, forecasts/alerts, and five-station NOAA coverage: all 2,730 date rows, nine missing precipitation values. Explain dated evidence and actual failures. |
| 1:20–2:00 | Show measured FSIS validation: logistic performance is no better than prevalence; no consumer illness probability or automatic hold. |
| 2:00–3:00 | In this fresh isolated session, inject a temperature excursion, compare A/B/C/D cost, demand, affected shipments, and solver status. Show that held lots are excluded. |
| 3:00–4:00 | Create a C proposal, review proposed hold lots and constraints, enter dispatcher identity/reason, and explicitly approve. Show audit history and approved assignments. |
| 4:00–4:40 | Open Drive at mobile width on this same isolated server. Confirm safely parked, select an approved trip, acknowledge its displayed revision, submit an incident, then return to the audit trail. Explain that real route/truck eligibility still requires review. |
| 4:40–5:00 | Close with the contribution and explicit limits: retrospective estimator, bounded NOAA coverage, simulated operations and human authority. Return to the rehearsal workspace to record closing coverage and actual elapsed time. |

## Reproducible API sequence

This manual path can be exercised from a second PowerShell terminal. Start a fresh launcher session first. It explicitly verifies the isolated runtime before any mutation; it does not reset port 8000 or overwrite an earlier rehearsal:

For a timed practice record, choose **Start rehearsal timer** in **Project brief**
before using the commands, and return there to record each stage with notes. This
API sequence does not itself create or complete a human presentation record.

```powershell
$aegisApi = 'http://127.0.0.1:8001'
$aegisRuntime = Invoke-RestMethod "$aegisApi/api/runtime-context"
if ($aegisRuntime.mode -ne 'isolated_rehearsal' -or -not $aegisRuntime.isolated -or -not $aegisRuntime.offline -or -not $aegisRuntime.rehearsal_id) { throw 'Stop: this server is not a verified isolated offline rehearsal.' }
$aegisEvent = @{event='temperature_excursion'; shipment_id='SH11'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "$aegisApi/api/events" -ContentType 'application/json' -Body $aegisEvent
$aegisScenarios = Invoke-RestMethod "$aegisApi/api/scenarios"
$aegisScenarios | Select-Object scenario,solver_status,total_logistics_cost,unmet_demand_kg,affected_shipments
$aegisProposal = Invoke-RestMethod -Method Post -Uri "$aegisApi/api/proposals/C"
$aegisProposal | Select-Object id,scenario,proposed_hold_lots,solver_status
$aegisApproval = @{actor='Demo dispatcher'; reason='Reviewed simulated temperature excursion and proposed precautionary hold'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "$aegisApi/api/proposals/$($aegisProposal.id)/approve" -ContentType 'application/json' -Body $aegisApproval
$aegisAssignments = Invoke-RestMethod "$aegisApi/api/driver"
$aegisTruck = $aegisAssignments[0].truck_id
$aegisTrip = $aegisAssignments[0].id
$aegisFocus = (Invoke-RestMethod "$aegisApi/api/drive/$aegisTruck").focus
$aegisParked = @{mode='parked'; expected_version=$aegisFocus.version; parked_confirmation=$true} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "$aegisApi/api/drive/$aegisTruck/focus" -ContentType 'application/json' -Body $aegisParked
$aegisRevision = (Invoke-RestMethod "$aegisApi/api/network").revision
$aegisContext = @{expected_network_revision=$aegisRevision} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "$aegisApi/api/driver/$aegisTrip/acknowledge" -ContentType 'application/json' -Body $aegisContext
$aegisIncident = @{shipment_id=$aegisTrip; expected_network_revision=$aegisRevision; description='Parked safely; requesting dispatcher review of next-stop access'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "$aegisApi/api/driver/incident" -ContentType 'application/json' -Body $aegisIncident
Invoke-RestMethod "$aegisApi/api/audit"
```

For a route demonstration, POST `{"coordinates":[[-92.3341,38.9517],[-90.1994,38.6270]],"alternatives":true}` to `/api/route`. State the returned provenance and fallback flag. Never describe the public OSRM result as truck-safe or closure-aware.

Optional route-laboratory segment: replace part of the scenario explanation with a single farm/fleet comparison. Start with estimated mode for reproducibility. Point out held stops, unmet demand and truck loads; briefly toggle a refrigeration fault to show an explicitly uncalibrated projection. Return to Command for actual dispatcher approval. Do not add this segment on top of an already full five-minute presentation.

Record actual presenter time separately from automated checks. Stop the rehearsal server with Ctrl+C after use; its UUID database retains that session's history. Start a new launcher session for another clean presentation. Dated fixtures and estimated geometry remain labeled in offline mode. Kiro evidence is a separate required development artifact and must come from a real signed-in spec task.
