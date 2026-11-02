# Open AEGIS — judge quick start

AEGIS is a local research application for a **simulated Missouri poultry
distribution network**. The package contains the application, its prebuilt web
interface, processed evidence, dated public-data fixtures, measured research
results and printable guides. Python runs the application on your own computer.

## 1. Extract the handoff

Extract **AEGIS-Judges.zip** completely to a folder you can write to. Open the
extracted **AEGIS-Judges** folder, then open **00_START_HERE.html** in a browser
or **00_START_HERE.txt** in a text editor.

| Folder | What to open |
|---|---|
| `01_Guides` | Final submission guide, one-page team statement and full user manual. PDFs open without installing the app. |
| `02_Application` | Working application, setup/start launchers, source code, data and detailed documentation. |
| `03_Verification` | Recorded checks, source status and package-verification evidence. Read their timestamps and scope. |

The outer folder is the judge handoff. Work inside **02_Application** for the
commands below. Do not open `frontend/index.html` or `frontend/dist/index.html`
directly: the web interface needs the local Python backend.

## 2. Windows: install once, then start

1. Install **64-bit Python 3.13** if it is not already installed. A working
   `py -3.13 --version` or `python --version` reporting Python 3.13 confirms the
   interpreter is available. Reopen the terminal after installing Python.
2. In File Explorer, open **02_Application** and double-click
   **Setup-Judges-Windows.cmd**. It creates a local `.venv` and installs the
   pinned dependencies from `requirements-lock.txt`. **This first setup needs
   internet access.** Wait for a successful completion before continuing.
3. Double-click **Start-Judges-Windows.cmd**. Keep its terminal window open.
4. Open the URL printed by the launcher, normally
   **http://127.0.0.1:8001/?mode=rehearsal**. The browser may open automatically;
   if it does not, paste that address into a new tab.

The judge start command uses the included prebuilt interface, so **Node.js is
not needed to view this package**. No API key, AWS account, Kiro installation,
database server or project-owner sign-in is needed for the included demo.

If double-click launchers are unavailable, open PowerShell in `02_Application`:

```powershell
py -3.13 scripts/judge_demo.py setup
.venv/Scripts/python.exe scripts/judge_demo.py run --port 8001 --open-browser
```

Use `python` instead of `py -3.13` only when that command points to Python 3.13.
The environment's interpreter is invoked directly; no PowerShell activation
script is required.

## 3. macOS or Linux

With Python 3.13 installed, open a terminal inside `02_Application`:

```sh
python3.13 scripts/judge_demo.py setup
.venv/bin/python scripts/judge_demo.py run --port 8001 --open-browser
```

Open the printed URL and keep the terminal open. These commands use the same
Python backend and prebuilt interface. Read the verification reports for the
operating systems and checks actually exercised; instructions alone are not a
claim that every platform was independently tested.

## 4. What a successful start looks like

- The browser opens **Project brief** with the five challenge-task cards.
- A banner identifies an **isolated rehearsal** and **offline** demo.
- **Command center** shows simulated Missouri logistics entities and computed
  planning results. A browser map background needs internet access.
- **Model evaluation** shows measured results; **Sources & evidence** shows
  source/retrieval dates, gaps and dated fixtures.

The launcher creates a fresh simulated session under
`02_Application/data/rehearsals/`. Previewing, applying a simulated event and
approving a simulated plan are part of the intended walkthrough. Each new launch
starts a separate session; a browser refresh within that running server keeps
the same session. To stop it, press **Ctrl+C** in its terminal. Retain that
session's database or downloaded evidence if you want its history.

The included offline profile uses captured public evidence and labeled route
estimates. It does not make old recalls, forecasts or road incidents current.
Live refresh is intentionally disabled in this profile. OpenStreetMap background
tiles and links to official websites are separate browser requests and still
need internet; their unavailability does not imply that the allocation solver
failed.

## If something does not open

| Symptom | Action |
|---|---|
| Python is missing, wrong version, or opens an app-store prompt | Install Python 3.13, reopen the terminal, confirm its version, then rerun setup. |
| Dependency installation fails | Keep the exact error visible. Confirm internet/package-index access and rerun setup after resolving it. The Python dependencies are not bundled as installed runtimes. |
| Browser says it cannot connect | Start the judge launcher first, leave its terminal open, and use its printed `127.0.0.1` URL. Opening a PDF or HTML entry file does not start the backend. |
| Port 8001 is occupied | Use another port; do not stop an unrelated service. In PowerShell run `.venv/Scripts/python.exe scripts/judge_demo.py run --port 8002 --open-browser`, then use the printed 8002 URL. On macOS/Linux use `.venv/bin/python`. |
| The page is blank or cannot load assets | Extract the entire archive before launching. Use the local HTTP URL, not a directly opened `index.html`. Check the terminal for the exact error. |
| Map background is blank | Check internet access. Inspect the visible source warning and planning tables; route estimates and simulated entities remain separately labeled. |
| Drive has no assigned trip | In Command center, review and approve a feasible simulated scenario first. Then select a truck that appears in its approved assignment list. |
| A driver button is disabled | Confirm safely parked, select an approved assignment and complete the relevant review/acknowledgment step. The interface does not detect actual vehicle motion. |
| A proposal is stale after another change | Compare/review the current plan again. Approval checks the current network version. |

For a short visit, follow [the judge walkthrough](judge_walkthrough.md). The
final submission guide covers all five tasks and every dashboard menu. Detailed
developer installation and reproduction steps remain in `README.md`.

## Interpretation and disclosure

All lots, shipments, suppliers' commercial relationships, trucks, cargo readings,
fuel, demand and logistics costs are simulated. Official establishment markers
do not establish supplier contracts. The retrospective model predicts selected
FSIS sampling outcomes, not consumer illness or a particular lot's safety;
added-data benefit is uncertain. Save the Load uses illustrative quality-decay
assumptions, not calibrated molecular freshness or microbial safety clearance.
Routing is not certified for commercial-vehicle restrictions.

**The owner disclosed that Kiro was not used; that challenge criterion is not
met.** Prepared specifications do not establish genuine Kiro work. Team last
names/final author review remain identified in the provided guide. Consult the
dated reports for the checks actually executed; opening this package does not
establish an organizer's acceptance or a completed human presentation.
