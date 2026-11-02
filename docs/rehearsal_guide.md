# Isolated presentation rehearsal

This workflow prepares a fresh simulated database and starts a second local
application. It preserves the operator's normal database and history. A scripted
workflow pass, an automated browser pass and a human five-minute presentation are
separate evidence; none should be presented as the others.

## Start a new rehearsal

Build the frontend and install the documented Python dependencies first. From
the repository root in PowerShell, run:

```powershell
.venv/Scripts/python scripts/start_rehearsal.py
```

Open the printed URL, normally <http://127.0.0.1:8001/?mode=rehearsal>. The launcher
runs the server in the foreground; leave that terminal open and use Ctrl+C to
stop it when finished. Port 8000 is reserved for the operator application and is
rejected. If 8001 is occupied, choose another port rather than stopping whatever
already owns it:

```powershell
.venv/Scripts/python scripts/start_rehearsal.py --port 8123
```

Each launch reserves one unique `data/rehearsals/<UUID>.sqlite` using exclusive
creation. It never overwrites an existing session, resets the operator database,
or deletes old rehearsal files. The application initializes the reserved SQLite
file when that isolated server receives its first request. An occupied port or
invalid path fails explicitly; the launcher does not kill another service.

To inspect the configuration before starting a process:

```powershell
.venv/Scripts/python scripts/start_rehearsal.py --prepare-only
```

The JSON output has `status: prepared` and `server_started: false`, the reserved
UUID/database path, the URL, an argument-list command and ready-to-paste
PowerShell commands. It prints only the three controlled environment variables,
not the rest of your environment or account credentials. A prepared file is not
evidence that a server is running. Port availability can change between the
probe and Uvicorn's actual bind; a failed bind leaves the reserved file intact.

The runtime contract is:

```text
AEGIS_REHEARSAL_ID=<canonical UUID>
AEGIS_DB_PATH=<absolute repository>/data/rehearsals/<same UUID>.sqlite
AEGIS_OFFLINE_DEMO=1
```

The backend verifies the exact identity/path relationship. Changing only the
URL query string does not isolate a server. Before using a manual API sequence,
read `/api/runtime-context` and require `mode: isolated_rehearsal`,
`isolated: true`, `offline: true` and the expected session UUID. A missing or
misconfigured runtime is a reason to stop the rehearsal, not permission to reset
the operator app.

## Evidence and offline behavior

The isolated profile uses the same installed backend, prebuilt frontend,
processed evidence and scientific reports as the operator application. Server
source/routing requests in the offline demo are restricted to explicit dated
fixtures, cached evidence or labeled estimates as implemented by the adapters.
Source timestamps remain unchanged; the profile does not make an old recall,
forecast or road record current. Map tiles are separate browser requests and may
still require internet. An unavailable tile is not a failed logistics solver.

Use the rehearsal workspace and the five-minute narrative in
[the demo script](../reports/demo_script.md). Confirm the isolated profile before
injecting an event or approving a plan. Record the presenter's identity, actual
wall-clock time and unresolved gaps when practicing; leave author/rubric and
genuine Kiro review pending until their real evidence exists.

In **Project brief**, open **Practice the five-minute story**, enter a presenter
and purpose, select the appropriate record type, then choose **Start rehearsal
timer**. Use **Self-reported team practice** only for actual presenter practice;
browser/script checks belong to **Automated workflow check**. The server records elapsed wall-clock time
through navigation and refresh; the planned five minutes are a target, not an
automatically awarded result.

The six ordered stages cover the actor/map (40 seconds), evidence and science
(80), disruption/tradeoffs (60), approval (60), driver workflow (40) and closing
(20). Use **Open Command**, **Open Sources & evidence**, **Open Model evaluation**
or **Open AEGIS Drive** for the relevant stage. Return through **Project brief**
to record notes and choose **Record stage covered** or **Record stage skipped**.
A skipped stage needs a reason and remains visibly skipped. The disruption,
approval and driver stages additionally require matching audit actions recorded
after this run began; older actions or a written assertion cannot substitute.

The disruption/approval stages also offer **Open Save the Load**. An actual
stored **Replay heat excursion** or **Add road-delay frame**, followed by a
coherent approved rescue from the same experiment, can supply those operational
stages. Normal/recovery frames and an unapproved proposal do not substitute.
The tracker retains the actual action names and bounded freshness provenance;
missing, stale or mismatched records fail visibly. Reassignment invalidates an
earlier driver acknowledgment: confirm parking, acknowledge the current trip and
submit its incident after the reviewed rescue. Evidence/model narration and the
closing stage still need their own coverage notes.

After all stages have a recorded outcome, add closing notes and choose **Finish
and save rehearsal**. Use **Abort and save record** if stopping early. Open a
saved record to inspect its timing, coverage and source snapshot, or choose
**Download rehearsal evidence JSON**. Completed/aborted records retain their
snapshots; a later scenario change does not rewrite those exports. Recording
coverage establishes self-reported practice and recorded simulated actions, not
presentation quality, genuine Kiro work, author signoff or final acceptance.

Start another fresh launcher session when repeating a clean narrative. Existing
session databases retain their history for review. Do not use a reset on port
8000 as a presentation shortcut.

## Accelerated software check

```powershell
.venv/Scripts/python scripts/demo_run.py
```

This separate command runs the operational sequence through an in-process test
client and an owned temporary database, then writes
`reports/demo_results.json`. It records contextual parked driver acknowledgment
and incident reporting after explicit dispatcher approval.

The script measures SHA-256, byte lengths and existence for both the configured
original SQLite database and the canonical `data/aegis.sqlite`, including their
`-wal`, `-shm` and `-journal` sidecars, before and after. A byte change makes the
check fail; an unreadable file makes preservation unknown and also fails. The
reported comparison does not attribute a concurrent change to a particular
process. The original database binding is restored even when the script fails.

Temporary-script output is explicitly accelerated. It does not establish a
five-minute human rehearsal, complete NOAA coverage, prospective model validity,
truck-safe routing, authentic Kiro execution or final competition submission.

The launcher is covered by `tests/test_rehearsal_launcher.py`; measured scripted
preservation is covered by `tests/test_demo_run.py`. Current executed counts and
browser evidence belong in the dated verification reports.
