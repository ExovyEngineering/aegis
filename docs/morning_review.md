# Tomorrow's short review

No overnight account action is required. The local draft package has not been uploaded or submitted.

1. Open AEGIS at <http://127.0.0.1:8000>. If the computer/server restarted, run `.venv/Scripts/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000` from the NAFSI folder. Check Command, Route laboratory, Dispatcher desk, Sources and Drive. Route laboratory's **Your operation** edits custom locations/fleet; **Dispatcher desk** reviews reports, instructions and holds. Custom drafts are in-memory; copy needed inputs before leaving the editor.
2. Read `reports/aegis_report.md` and `docs/priority_matrix.md`. Keep the distinction between a validated retrospective baseline and an unproven prospective predictor. NOAA precipitation has nine missing values; thermal projections remain uncalibrated.
3. Open installed Kiro and sign in when ready. `docs/kiro_handoff.md` contains the bounded real spec task. Existing Codex work must not be presented as Kiro-authored work.
4. Rehearse `reports/demo_script.md` with a timer. Use a separate demo database to preserve current work; the isolated scripted version is `.venv/Scripts/python scripts/demo_run.py`.

`artifacts/aegis-review-draft.zip` is a local reviewer bundle with source, prebuilt frontend, processed evidence, dated source fixtures, report/figures and a SHA manifest. It excludes credentials, original large downloads, operational databases, runtime/Kiro installations and account data. See `reports/submission_package.json` for its checksum. The packaged `REVIEWER_START.md` explains how to run it from another folder.

Remaining P0 decisions: authentic Kiro task evidence, final organizer-rubric/author review, timed presentation, and scientifically honest treatment of unavailable publication timing. Account modes, LLM assistance and live sensing remain P2.
