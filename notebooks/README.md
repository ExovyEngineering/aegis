# Reproducible AEGIS analysis

These four Jupyter notebooks execute the maintained Python implementation. They
rebuild analytic features, fit models, evaluate held-out outcomes and solve the
simulated scenarios, then compare the numerical results with the published
snapshots. Saved outputs and HTML previews come from actual kernel execution.

| Notebook | Analysis |
| --- | --- |
| `00_Start_Here_and_Coverage.ipynb` | Input provenance, schemas, null counts, dictionary regeneration, NOAA coverage and dated API status. |
| `01_Preprocessing_and_Integration.ipynb` | Source-specific preprocessing, optional original-file replay, ecological alignment, lagged features, exclusions and chronological split. |
| `02_Modeling_and_Evaluation.ipynb` | Refit national baseline/logistic model, snapshot-timing stress test and integrated FSIS/BEAM/NOAA study; calibration, uncertainty and NORS ablation. |
| `03_Scenario_Analysis.ipynb` | Recompute three policies across three scenarios and replay quality decay, rescue approval and warehouse FEFO/FIFO allocation. |

## Read without installing Jupyter

Open `reports/notebooks/index.html` from the project/application root. Each
standalone HTML preview contains the executed code, tables and embedded figures.
The `.ipynb` files also retain their checked outputs. The judge handoff's
`04_Reproducible_Analysis/index.html` links to both formats inside `02_Application`.

## Run all notebooks

Use Python 3.13. From the project/application root after the usual application
setup, install the optional pinned notebook tools and execute the notebooks:

```powershell
.venv/Scripts/python -m pip install -r requirements-notebooks.txt
.venv/Scripts/python scripts/execute_notebooks.py
```

On macOS/Linux, use `.venv/bin/python` instead. Node.js is not required for these
analysis notebooks. Installing the optional tools needs internet; analysis uses
bundled input snapshots and disables networking in its scientific script
subprocesses. The Jupyter kernel itself uses local transport.

To open an interactive JupyterLab interface:

```powershell
.venv/Scripts/python -m jupyterlab notebooks
```

Or open a notebook in VS Code and select this project's Python 3.13 `.venv`
kernel. Choose **Run All**. The command-line runner explicitly uses the same
Python interpreter that invoked it, rather than an unrelated global kernel.

Successful command-line results are written under `reports/notebooks/`; execution
status, dependency versions, input/source checksums and cell counts are recorded
in `reports/notebook_execution.json`. `--update-notebooks` also saves successful
bundled outputs into the source notebooks. Each notebook creates a unique copied
project under `reports/notebook_runs/`; per-step logs and its `RUN_MANIFEST.json`
remain there for inspection. These private workspaces are excluded from Git and
judge packages. Published scientific inputs and the operator database are checked
for changes, not reset or restored.

## Rebuild from original source downloads

Default execution uses the included processed FSIS/CDC/USDA snapshots and the
preserved NOAA responses. It recomputes features, models and scenarios; it does
not falsely claim that the excluded bulk originals were re-ingested.

For full source-specific preprocessing, obtain the exact original analysis files
listed in the provenance manifests and run:

```powershell
.venv/Scripts/python scripts/execute_notebooks.py --notebook 01_Preprocessing_and_Integration.ipynb --raw-data-dir "C:/path/to/original/downloads"
```

The raw profile checks every required original filename/hash against recorded
lineage, copies only those analysis inputs into its private workspace, audits the
copies and runs the existing FSIS, CDC/directory and USDA adapters. Missing,
changed or incomplete sources fail explicitly. Unknown files are not merged.
Originals remain unchanged. This is an audit of the selected analytic inputs;
the original full-folder inventory remains in `data/manifests/inventory.json`.
The separate full-folder audit command is `python scripts/audit_data.py --data-dir PATH`.

Raw-profile results are saved under `reports/notebooks/raw/`, with separate status
in `reports/notebook_raw_execution.json`. In an interactive kernel, setting
`AEGIS_NOTEBOOK_RAW_DIR` explicitly enables the same path in notebook 01. Without
originals, that notebook visibly records raw ingestion as **not run** and continues
with the bundled-snapshot integration. This limitation is not hidden.

The raw-source profile also runs the maintained model, evaluation and scenario
scripts against those same regenerated workspace inputs and checks their
metrics against the published snapshots. The original bulk files are still not
included in the judge ZIP.

## Interpreting reproducibility

Assertions compare scientific metrics and allocations with numerical tolerance.
Execution dates, UUIDs, paths, audit receipts and notebook metadata naturally
change. Uncertainty intervals are conditional on the supplied snapshots and
assumed availability lags. CDC evidence remains separate from FSIS outcomes;
sample positivity is not consumer-illness or individual-lot risk. Scenario
logistics and sensor data are simulated, and quality kinetics are illustrative.
Reproducing the results does not establish prospective predictive validity,
current provider availability or genuine Kiro use.

Execution uses the official [NBClient API](https://nbclient.readthedocs.io/en/latest/client.html)
and produces static previews through [NBConvert](https://nbconvert.readthedocs.io/en/latest/api/exporters.html).
