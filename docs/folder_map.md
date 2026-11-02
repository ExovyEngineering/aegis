# Where to find things

| Folder or file | Purpose |
| --- | --- |
| `artifacts/AEGIS-Judges.zip` | The single organized file to share with judges. |
| `artifacts/AEGIS-Judges/00_START_HERE.html` | Open first after extracting; links and setup steps. |
| `artifacts/AEGIS-Judges/01_Guides/` | Final task/menu/presentation PDF, team statement, full handbook, quick start and walkthrough. |
| `artifacts/AEGIS-Judges/02_Application/` | Runnable application and source, prebuilt frontend, derived data and dated fixtures. |
| `artifacts/AEGIS-Judges/03_Verification/` | Measured tests, browser checks, source statuses and package evidence. |
| `artifacts/AEGIS-Judges/04_Reproducible_Analysis/` | Links to executed notebooks, HTML previews and reproduction instructions inside the application folder. |
| `backend/`, `frontend/` | Maintained application source. |
| `scripts/` | Audit, ingestion, model, simulation, testing, launch and packaging commands. |
| `config/` | API registry, policies and feature configuration. |
| `docs/` | Architecture, scientific limitations, operating instructions and progress. |
| `reports/` | Generated PDFs, measured evaluations, test histories and figures. |
| `data/processed/` | Derived source-specific tables and the integrated analytic export. |
| `data/external/` | Preserved selected NOAA responses and metadata. |
| `data/fixtures/` | Explicitly dated demo evidence. |
| `data/manifests/` | Original-file inventory and source checksums. |
| `data/rehearsals/` | Private local isolated simulation databases created on launch; excluded from handoff. |
| `tests/` | Backend and packaging tests; frontend tests live beside frontend source. |
| `notebooks/` | Four maintained analysis notebooks with checked outputs and setup/replay instructions. |
| `reports/notebooks/` | Executed notebook copies, standalone HTML previews and execution summaries. |
| `reports/notebook_runs/`, `reports/notebook_executions/` | Private copied analysis workspaces, raw staging, logs and ephemeral kernels; excluded from handoff. |
| `.kiro/` | Prepared specs and steering, with owner non-use disclosure. |
| `.venv/`, `.tools/` | Local development runtimes and dependencies; excluded from handoff. |
| Original CSV/JSON/XLSX/PDF downloads, including `Databases-and-etc/` | Preserved supplied files. Historical audit paths record their locations at audit time; the raw notebook profile locates the provenance-listed names recursively and verifies their bytes. |

Generated handoff folders and archives contain copies of allowlisted material;
they do not reorganize or overwrite original data. Rebuilding the judge folder
retains the previous version under `artifacts/judge-history/`. Use the newest
canonical `AEGIS-Judges.zip`, not a historical build, when sharing.
