# Team review - October 28, 2026

Start with [the core software handoff](core_release.md). It covers Command,
Drive, the isolated rehearsal, reviewer installation and current source failures.
Use `scripts/start_rehearsal.py` for practice; the URL parameter alone never
isolates the operator app. The updated PDF records actual test evidence.

No overnight account action is required. The local draft package has not been uploaded or submitted.

1. Open dedicated Drive at <http://127.0.0.1:8000/?mode=drive>. Confirm safely parked before testing reports or acknowledgments, then use Lock for driving to verify the controls are read-only. Fuel/position are simulated. Open AEGIS Command at <http://127.0.0.1:8000>. If the computer/server restarted, run `.venv/Scripts/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000` from the NAFSI folder. Check Command, Route laboratory, Dispatcher desk, Sources and Drive. Route laboratory's **Your operation** edits custom locations/fleet; **Dispatcher desk** reviews reports, instructions and holds. Run and save experiments in the route library before leaving the editor; unsaved changes remain in-memory. The Project brief tab downloads the maintained PDF with test evidence and presentation notes.
2. Read `reports/aegis_report.md` and `docs/priority_matrix.md`. Keep the distinction between a validated retrospective baseline and an unproven prospective predictor. NOAA precipitation has nine missing values; thermal projections remain uncalibrated.
3. Open installed Kiro and sign in when ready. `docs/kiro_handoff.md` contains the bounded real spec task. Existing Codex work must not be presented as Kiro-authored work.
4. Rehearse `reports/demo_script.md` with a timer. Use a separate demo database to preserve current work; the isolated scripted version is `.venv/Scripts/python scripts/demo_run.py`.

`artifacts/aegis-review-draft.zip` is a local reviewer bundle with source, prebuilt frontend, processed evidence, dated source fixtures, report/figures and a SHA manifest. It excludes credentials, original large downloads, operational databases, runtime/Kiro installations and account data. See `reports/submission_package.json` for its checksum. The packaged `REVIEWER_START.md` explains how to run it from another folder.

Remaining P0 decisions: authentic Kiro task evidence, final organizer-rubric/author review, timed presentation, and scientifically honest treatment of unavailable publication timing. Account modes, LLM assistance and live sensing remain P2.

Latest extension: Sources & evidence now includes historical USDA county comparison and CSV export. The checked extract has 115 Missouri county/county-equivalent FIPS identities and ten measures with separate 2019/2020/2023 vintages. Grocery count and rate each have 39 missing values; none are replaced with zero. These measures do not rate food safety or alter demand/dispatch. See [the county-context guide](food_access_context.md).

In Dispatcher desk, inspect **Dispatch readiness review** after approving a scenario. The sixteen checks distinguish hard constraint failures from outstanding assignment/instruction acknowledgments or targeted verification. **Listed checks passed** requests final human review; it does not depart a truck or certify food safety. See [the workflow guide](operations_workflow.md).

Source discovery now works recursively with semantic content signatures, explicit duplicate/conflict/failure records and checksum-verified request snapshots. [The ingestion guide](ingestion_provenance.md) explains how to choose one export snapshot when two different files describe the same evidence layer. The existing source/model values were compared separately in [the re-ingestion verification](../reports/ingestion_verification.json). See `docs/changelog.md` and `reports/project_brief.md` for the maintained session evidence.

Drive design and stretch entry criteria: `docs/drive_design.md` and `docs/stretch_feature_gates.md`. Current automated/browser outcomes are in the project brief and `docs/progress.md`; pending Kiro and scientific gates remain separate.

Next three team actions remain: complete the authentic Kiro task/sign-in workflow, review the report and claims against the final submission requirements, and rehearse the five-minute presentation with a timer. These software additions do not close those gates.
