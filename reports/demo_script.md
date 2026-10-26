# Five-minute AEGIS demonstration

Run setup, ingestion, training, endpoint probes, frontend build, and tests before presenting. Start the app at `http://127.0.0.1:8000`. Public response timestamps may differ on each run; the simulated seed and operational events are deterministic. Map tiles require network access. Do not claim cached evidence is live.

Use `scripts/freeze_demo_evidence.py` after a successful source refresh to retain dated responses in `data/fixtures/`. Use `scripts/demo_run.py` for an automated workflow rehearsal in an isolated temporary database; it writes `reports/demo_results.json` without resetting the operator's current state. The manual sequence below intentionally resets the local app's simulated operational state.

| Time | Action and point to demonstrate |
|---|---|
| 0:00–0:40 | Open Command; show the Missouri map and simulation label. Identify two DCs, fictional shipments, and separate official establishment markers. |
| 0:40–1:20 | Show source coverage, recall retrieval time, forecasts/alerts, and five-station NOAA coverage: all 2,730 date rows, nine missing precipitation values. Explain dated evidence and actual failures. |
| 1:20–2:00 | Show measured FSIS validation: logistic performance is no better than prevalence; no consumer illness probability or automatic hold. |
| 2:00–3:00 | Reset the simulation, inject a temperature excursion, compare A/B/C/D cost, demand, affected shipments, and solver status. Show that held lots are excluded. |
| 3:00–4:00 | Create a C proposal, review proposed hold lots and constraints, enter dispatcher identity/reason, and explicitly approve. Show audit history and approved assignments. |
| 4:00–5:00 | Open Drive at mobile width, select an approved trip, acknowledge it, submit an incident while parked, and return to the audit trail. Explain that real route/truck eligibility still requires review. |

## Reproducible API sequence

The same operational sequence can be exercised from a second PowerShell terminal. It changes only local simulated state and preserves audit history:

```powershell
$aegisApi = 'http://127.0.0.1:8000'
Invoke-RestMethod -Method Post -Uri "$aegisApi/api/demo/reset"
$aegisEvent = @{event='temperature_excursion'; shipment_id='SH11'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "$aegisApi/api/events" -ContentType 'application/json' -Body $aegisEvent
$aegisScenarios = Invoke-RestMethod "$aegisApi/api/scenarios"
$aegisScenarios | Select-Object scenario,solver_status,total_logistics_cost,unmet_demand_kg,affected_shipments
$aegisProposal = Invoke-RestMethod -Method Post -Uri "$aegisApi/api/proposals/C"
$aegisProposal | Select-Object id,scenario,proposed_hold_lots,solver_status
$aegisApproval = @{actor='Demo dispatcher'; reason='Reviewed simulated temperature excursion and proposed precautionary hold'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "$aegisApi/api/proposals/$($aegisProposal.id)/approve" -ContentType 'application/json' -Body $aegisApproval
$aegisAssignments = Invoke-RestMethod "$aegisApi/api/driver"
$aegisTrip = $aegisAssignments[0].id
Invoke-RestMethod -Method Post -Uri "$aegisApi/api/driver/$aegisTrip/acknowledge"
$aegisIncident = @{shipment_id=$aegisTrip; description='Parked safely; requesting dispatcher review of next-stop access'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "$aegisApi/api/driver/incident" -ContentType 'application/json' -Body $aegisIncident
Invoke-RestMethod "$aegisApi/api/audit"
```

For a route demonstration, POST `{"coordinates":[[-92.3341,38.9517],[-90.1994,38.6270]],"alternatives":true}` to `/api/route`. State the returned provenance and fallback flag. Never describe the public OSRM result as truck-safe or closure-aware.

Optional route-laboratory segment: replace part of the scenario explanation with a single farm/fleet comparison. Start with estimated mode for reproducibility. Point out held stops, unmet demand and truck loads; briefly toggle a refrigeration fault to show an explicitly uncalibrated projection. Return to Command for actual dispatcher approval. Do not add this segment on top of an already full five-minute presentation.

For an isolated live rehearsal, set `AEGIS_DB_PATH` to a separate file before starting a second server on another port. Map tiles and source refresh need internet. If offline, describe dated fixtures and estimated geometry explicitly rather than claiming live coverage. Kiro evidence is a separate required development artifact and must come from a real signed-in spec task.
