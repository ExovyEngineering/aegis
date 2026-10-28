# AEGIS

Adaptive Early-warning & Guidance for Integrated Supply Chains: a local research prototype for a simulated Missouri poultry distributor. Built for the NAFSI SENSD Student Data Challenge, supply-chain track; submission target November 2, 2026.

AEGIS combines separately labeled official food-safety and weather evidence with deterministic simulated shipments, constrained allocation, dispatcher review, and a driver workflow. Suppliers, contracts, lots, trucks, telemetry, shipments, demand, and costs are simulated. Real establishment-directory markers do not establish supplier relationships.

## Run locally

For the finished core walkthrough and verification commands, start with
[the core software handoff](docs/core_release.md).

Teammates cloning the repository can follow [CONTRIBUTING.md](CONTRIBUTING.md)
to run with the included derived datasets and dated fixtures, create feature
branches, and verify changes. Original bulk downloads and local operator state
are intentionally excluded from Git.

Use Python 3.13 and Node.js 22/npm. From the repository root in PowerShell:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-lock.txt
.venv/Scripts/python scripts/audit_data.py
.venv/Scripts/python scripts/ingest_fsis.py
.venv/Scripts/python scripts/ingest_evidence.py
.venv/Scripts/python scripts/ingest_usda.py
.venv/Scripts/python scripts/train_model.py
.venv/Scripts/python scripts/acquire_noaa.py
.venv/Scripts/python scripts/validate_model_timing.py
.venv/Scripts/python scripts/seed_demo.py
```

`requirements-lock.txt` pins the tested Python environment; `requirements.txt` lists direct dependencies. The audit chooses `AEGIS_DATA_DIR`, then `data/raw/` if present, then this repository root. The supplied raw downloads currently live in the root. To choose another folder:

```powershell
$env:AEGIS_DATA_DIR = 'C:/path/to/raw-data'
.venv/Scripts/python scripts/audit_data.py --data-dir $env:AEGIS_DATA_DIR
```

Build the frontend, then start the combined local application:

```powershell
Set-Location frontend
npm install
npm run build
Set-Location ..
.venv/Scripts/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000>. Interactive backend documentation is at <http://127.0.0.1:8000/docs>. Build the frontend before starting the backend because static files are mounted at application startup.

For frontend development, run `npm run dev` inside `frontend/` and keep FastAPI on port 8000 in another terminal. The development interface uses port 5173. A workspace-local runtime was downloaded during development. If global Node/npm is unavailable, run these commands from the repository root instead:

```powershell
$env:PATH = "$PWD/.tools;$env:PATH"
node .tools/package/bin/npm-cli.js --prefix frontend install
node .tools/package/bin/npm-cli.js --prefix frontend run build
```

Do not commit the local runtime. A fresh checkout requires standard Node/npm installation unless `.tools/` is separately provisioned.

## AEGIS Drive

Open <http://127.0.0.1:8000/?mode=drive> for the dedicated mobile-responsive driver
surface. It shows approved trip/destination, planned travel, simulated fuel/range,
cargo and assignment status. Typing, reports and acknowledgments require an
explicit parked confirmation, which expires after ten minutes. Lock controls
before moving. The server also rejects these actions when confirmation expires.
This is a self-declared interaction safeguard, not actual motion detection.

Fuel and dispatch-origin position are deterministic scenario values, not live GPS
or sensor readings. Quick reports reach the local dispatcher inbox. No route
change or lot hold happens automatically. See [Drive design](docs/drive_design.md)
and [stretch entry criteria](docs/stretch_feature_gates.md). This is the shared
web application; no native mobile package or cloud deployment is claimed.

## Isolated presentation rehearsal

Keep the operator app on port 8000. In a separate terminal from the project folder:

```powershell
.venv/Scripts/python scripts/start_rehearsal.py --port 8001
```

Open the printed URL, normally <http://127.0.0.1:8001/?mode=rehearsal>. The launcher
reserves a fresh UUID database, and the app verifies that path before accepting
rehearsal actions. Every view displays the isolated-runtime banner. A URL
parameter alone does not isolate the operator app.

Project brief contains six guided stages, a server-based timer, notes, saved
history and immutable JSON evidence exports. Operational stages require recorded
events, approval and a coherent parked driver workflow. Default rehearsal mode
uses dated source fixtures and labeled routing estimates; provider refresh is
disabled. Map tiles may need internet. Nothing resets the operator database.

The measured timer and self-reported coverage do not prove a human presentation,
Kiro execution or final approval. See [the rehearsal guide](docs/rehearsal_guide.md).

## Team status and presentation planning

Open **Project brief** in the application to download the maintained PDF and see
recorded checks and priority gates. The same files are available directly:
[PDF](reports/aegis_project_brief.pdf), [editable brief](reports/project_brief.md),
[change history](docs/changelog.md), and [feature register](config/feature_register.yaml).

After code changes, refresh the measured checks and presentation artifact:

```powershell
.venv/Scripts/python scripts/verify_project.py
.venv/Scripts/python scripts/build_project_brief.py
```

The verifier executes pytest, Vitest and the production build, preserving dated
logs and JSON history. It does not refresh public sources or imply browser/CI
success. Update the feature register and changelog as capabilities change.

To rebuild and independently check the local reviewer archive:

```powershell
.venv/Scripts/python scripts/package_submission.py
.venv/Scripts/python scripts/verify_package.py
```

The package verifier checks file membership, sizes and hashes before extraction,
then runs an isolated copy with a fresh demo database and blocked external network
access. It checks USDA, source browsing, readiness, planning, approval and Drive.
It reuses the installed Python dependencies; it does not claim a fresh dependency
installation, cloud deployment or competition submission.

Route laboratory now saves completed experiments as versioned local projects,
compares two saved projects, reopens historical versions, and exports inputs and
results. Saving never dispatches. Unsaved editor changes still remain temporary.
Command's decision details expose independent constraint checks and exclusions.
Dispatcher desk records scenario-B verification reviews; completing a simulated
checklist does not certify product safety or automatically impose a hold.
Sources includes a bounded read-only browser of separately ingested tables.

Sources also compares historical USDA Food Environment Atlas measures for all
115 Missouri counties/county-equivalents. Each measure retains its year, unit and
denominator; missing/suppressed values stay null. This context does not change
shipment eligibility or allocation. See [the county-context guide](docs/food_access_context.md).

Evidence imports now discover supported schemas recursively and assign stable
source identities. Exact duplicate downloads do not inflate observations;
different exports for the same semantic table require explicit snapshot selection.
The browser checks the same bytes it displays against the import manifest. See
[ingestion provenance](docs/ingestion_provenance.md).

Dispatcher desk includes a read-only readiness checklist for approved trips.
It separates hard constraints from outstanding acknowledgments and scenario-B
verification. Passing these checks is not a departure authorization or safety
certification. Review the source evidence and explicit human decisions.

## Refresh evidence and run checks

```powershell
.venv/Scripts/python scripts/test_apis.py
.venv/Scripts/python scripts/refresh_sources.py
.venv/Scripts/python scripts/freeze_demo_evidence.py
.venv/Scripts/python scripts/demo_run.py
.venv/Scripts/python -m pytest -q
Set-Location frontend
npm test -- --run
npm run build
```

The endpoint probe uses short timeouts and sequential requests. It writes `reports/api_status.json`, dated JSON responses under `data/cache/`, and the registry's tested status. HTTP success for a documentation or download page does not establish a data feed. An unavailable source must stay visibly unavailable; cached results retain their retrieval timestamps.

Copy `.env.example` to `.env` for local configuration. The loader reads literal `KEY=value` lines without shell evaluation; existing process environment variables take precedence. No API key is hardcoded. NCEI Access Data Service public requests used here do not require the separate CDO token. `NCEI_TOKEN` is reserved and unused by the present Access Data Service adapter.

`scripts/refresh_sources.py` fetches full adapter responses, including MoDOT incident layers and OSRM alternatives with road-event proximity review. Use `--source modot` or another supported source to restrict requests. The lightweight `test_apis.py` probe checks only the registry URLs; its MoDOT result is service discovery. Connectivity probes preserve richer incident/route caches when present.

`scripts/freeze_demo_evidence.py` preserves dated official responses as demo fixtures under `data/fixtures/`. The API falls back to these fixtures when a generated cache is absent, with fixture status and retrieval time exposed. Frozen evidence is not live source coverage. `scripts/demo_run.py` exercises the deterministic proposal/approval/driver workflow in an isolated temporary SQLite database and writes `reports/demo_results.json`; it does not reset the application's existing operational database.

## What is implemented

- Read-only recursive data audit, streaming JSON/CSV validation, file hashes, duplicate detection, workbook and archive inspection, errors, and source metadata.
- Registry with a Google Sheets CSV export, public connectivity probes, timestamped caches, independent weather/routing adapters, and MoDOT route-proximity review.
- Metadata-confirmed FSIS raw-poultry ingestion; separate NORS, BEAM, and establishment adapters.
- Deterministic network: three suppliers, two DCs, 15 destinations, eight refrigerated trucks, 24 shipment candidates, 12 lots, and temperature excursions.
- Four OR-Tools allocation scenarios; hard eligibility, hold/recall, stock, capacity, demand, deadline, and shelf-life checks.
- SQLite proposals, revision checks, explicit dispatcher approval, driver assignments and acknowledgments, incident reporting, and audit records.
- A chronological retrospective model feasibility evaluation with a historical-prevalence baseline, logistic regression, calibration, Brier score, PR-AUC, ROC-AUC, and weekly-block bootstrap intervals.
- Farm and multi-depot route laboratory: configurable trucks, capacity and shift duration; multi-stop routes return to origin and respect stock, holds, eligibility, service times and deadlines. Route tests never publish driver assignments.
- Explicit cargo-temperature scenario projections with ambient/delay/refrigeration-fault controls and parameter-sensitivity ranges; no failure probabilities or food-safety validation claims.
- Five-station NOAA extract: 2,730 date rows from January 2025 through June 2026; nine precipitation values missing. An earlier-snapshot model sensitivity study keeps all held-out outcomes out of frozen parameters.
- Custom farm/fleet planning: editable origins, delivery stops and trucks with explicit stock, deadline, shelf-life and safety assumptions.
- Dispatcher desk: incident inbox, audited human holds/releases, versioned approved-trip instructions and separate driver acknowledgment. See `docs/operations_workflow.md`.

The Command/Drive interface is implemented in `frontend/`. Latest verification is recorded in `reports/validation.json` and `reports/session_verification.json`. Separate dated Chrome rehearsals and screenshots live under `reports/browser_qa/`; they do not imply present provider freshness. A timed team presentation remains pending. See [the five-minute demo](reports/demo_script.md), [priorities](docs/priority_matrix.md), and [acceptance matrix](docs/progress.md).

## Scientific and operational limits

The current logistic model has no demonstrated predictive advantage over prevalence and is not a validated prospective forecast. Actual result-publication dates are missing; a 90-day reporting lag is an explicit assumption. No score measures consumer illness probability or automatically imposes a hold.

NOAA coverage now includes a bounded five-station 2025–June 2026 extract, with variable-level gaps and quality attributes reported in `reports/noaa_coverage.json`. It is not complete historical training-year coverage or a validated FSIS/weather join. Forecasts, historical reanalysis, observed station weather, and simulated cargo temperatures remain separate evidence types.

OSRM's public demonstration service supplies driving routes without commercial-truck restrictions. Its routes do not automatically include current MoDOT closures. A separate 250-meter proximity/intersection review compares returned alternatives with queried MoDOT geometry; nearby parallel roads and duplicated event geometries can produce review alerts. Offline travel estimates use haversine distance × 1.25 at 65 km/h; straight lines are not road geometry. The A–D scenario allocation remains a single dispatch wave. The separate farm/fleet laboratory computes returning multi-stop routes with timing constraints, but does not dispatch them. No route is certified truck-safe.

This is a loopback-only demonstration with self-declared dispatcher identity; production authentication and authorization are not implemented. Approval changes simulated assignments, not real shipments. Official Kiro IDE 1.4.26 is installed in `.tools/kiro/` and its version/signature verified. Account sign-in and authentic spec execution remain pending; `.kiro/` files alone do not prove Kiro usage. Follow [the concrete Kiro handoff](docs/kiro_handoff.md).

Reproduce operational route experiments and the draft submission report:

```powershell
.venv/Scripts/python scripts/route_lab_demo.py
.venv/Scripts/python scripts/route_lab_demo.py --routing osrm
.venv/Scripts/python scripts/demo_run.py
.venv/Scripts/python scripts/build_submission_report.py
```

The live routing command makes bounded public OSRM requests and falls back explicitly when unavailable. Route lab costs, inventory and thermal parameters are simulation assumptions. Enterprise/farm account tenancy, LLM assistance and live sensors remain P2 and are not implemented.

## Repository guide

For a short next-session handoff, read `docs/morning_review.md`. Build a local draft reviewer package with `.venv/Scripts/python scripts/package_submission.py`. The ZIP includes source, the prebuilt UI, derived data, dated fixtures and report evidence; it excludes credentials, runtime installations, operational SQLite databases and the large original downloads. It is not uploaded or certified ready for submission.

| Location | Purpose |
|---|---|
| `backend/` | FastAPI, source adapters, simulation, constrained optimization, SQLite workflow |
| `frontend/` | React/TypeScript local control tower and driver interface |
| `scripts/` | Auditing, connectivity, ingestion, model evaluation, deterministic demo seed |
| `data/manifests/inventory.json` | File-level audit with schemas, counts, samples, hashes, and exact errors |
| `data/processed/` | Derived source-specific Parquet and deterministic seed |
| `data/cache/` | Dated public responses; generated and ignored by Git |
| `data/fixtures/` | Frozen dated public evidence for the reproducible demo; not live data |
| `reports/` | Audit, endpoint tests, measured model results, and demo instructions |
| `config/api_registry.csv` | Google Sheets import |
| `docs/` | Architecture, data catalog, model card, assumptions, progress |
| `.kiro/` | Preparatory specification and steering files; genuine Kiro usage outstanding |
