# AEGIS core software handoff

October 28, 2026. This is the runnable local research demonstrator. The software
checks and submission/team approval gates are recorded separately.

## Open the application

The developer workspace serves Command at <http://127.0.0.1:8000> and dedicated
Drive at <http://127.0.0.1:8000/?mode=drive>. If the server has stopped, run from
the project folder:

```powershell
.venv/Scripts/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

A teammate using the reviewer ZIP installs Python 3.13 and the locked
dependencies, then runs the same server command. The ZIP contains a prebuilt
frontend; Node is needed to rebuild source or run frontend tests. See
[README](../README.md), [CONTRIBUTING](../CONTRIBUTING.md) and the packaged
`REVIEWER_START.md` for the complete setup.

## Walk through the core workflow

1. In Command, inspect the Missouri map, selected trip, simulated cargo and real
   source layers. Compare all four response scenarios and open their decision
   details to inspect resource constraints and exclusions.
2. Review a scenario, enter a dispatcher identity/reason, and approve it. Only
   approved simulated assignments appear in Drive. Held/recalled stock remains
   excluded; a score cannot create a mandatory hold.
3. In Drive, confirm that you are safely parked before acknowledging a trip or
   submitting an incident. The confirmation is self-declared and expires; it
   does not detect actual motion. Fuel, position and cargo values are simulated.
4. In Dispatcher desk, review the incident, record an explicit hold/release or
   versioned instruction, and inspect readiness. A checklist does not dispatch
   or certify product safety. Releasing a hold does not restore assignments.
5. In Route laboratory, test a farm, multi-origin fleet or custom operation;
   save/reopen/compare experiments and export their results. Planning experiments
   do not become dispatch assignments.
6. In Sources & evidence, inspect timestamps, failures, missing cells, source
   hashes and USDA county comparisons. In Model evaluation, show the actual
   historical baseline/model results and their scientific limits.

## Practice without changing operator state

```powershell
.venv/Scripts/python scripts/start_rehearsal.py --port 8001
```

Open the printed URL and check the isolated-runtime banner. The six guided
stages retain a server-clock duration, notes, recorded operational evidence and
an immutable export. The default profile uses dated source fixtures and labeled
route estimates. See [the rehearsal guide](rehearsal_guide.md).

## Verify or rebuild the handoff

```powershell
.venv/Scripts/python scripts/verify_project.py
.venv/Scripts/python scripts/build_project_brief.py
.venv/Scripts/python scripts/package_submission.py
.venv/Scripts/python scripts/verify_package.py
```

Current executed results are in `reports/session_verification.json`,
`reports/validation.json`, browser reports, `reports/package_verification.json`
and `reports/clean_install.json` when available. A recorded pass is tied to its
timestamp and tested source; it is not a guarantee of future provider uptime.
The maintained PDF is downloadable from **Project brief**.

The clean installation check created a separate Python virtual environment with
system site packages disabled, installed all 51 pinned packages, passed `pip
check`, verified the extracted package offline, and completed 31 real loopback
HTTP checks including the full automated rehearsal. It used the prebuilt
frontend; no fresh local Node installation is claimed. The tested application
source checksum is retained in `reports/clean_install.json`.

To repeat the dependency/package portion in another isolated environment:

```powershell
python -m venv .tools/reviewer-env
.tools/reviewer-env/Scripts/python -m pip install -r requirements-lock.txt
.tools/reviewer-env/Scripts/python -m pip check
.tools/reviewer-env/Scripts/python scripts/verify_package.py
```

## External coverage and remaining gates

The October 28 source check recorded DNS failures on the FSIS and USDA ERS web
hosts. Dated official recall responses and imported USDA/establishment tables
remain usable; live failures stay visible. NOAA station coverage remains bounded
and includes nine missing precipitation values. No missing values are invented.

The retrospective prevalence estimator is retained because logistic regression
did not establish useful improvement. Public result-availability dates remain
unverified. There is no validated prospective illness forecast, genomic linkage,
commercial-truck certification, physical sensing or production account isolation.

The remaining team submission actions are genuine Kiro spec execution, final
report/rubric and author review, and a timed human presentation rehearsal. The
application and automated checks do not falsely mark these complete. No merge,
cloud deployment or competition submission is performed by this handoff.
