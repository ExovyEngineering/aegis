# Judge walkthrough — evidence to a reviewed decision

Start the application using [the judge quick start](judge_quick_start.md).
Use the printed local URL, normally
**http://127.0.0.1:8001/?mode=rehearsal**, and confirm the isolated/offline banner.
The following tour uses a fresh simulated session. No physical shipment or
regulatory decision is created.

## A five-minute inspection

| Time | Where to click | What to look for |
|---|---|---|
| 0:00–0:40 | **Project brief** → the five challenge-task cards | The implemented evidence, remaining limits, final-guide downloads and explicit Kiro non-use disclosure. Scroll to the food-security comparison and switch among its three scenarios; the three policies produce different captured allocations. |
| 0:40–1:20 | **Model evaluation** → integrated Missouri model study | Measured baseline and added-data results, held-out sample counts, uncertainty, calibration and the monthly coverage gap. This seven-day retrospective study is separate from the original national model. Read the values on screen; no invented accuracy is needed. |
| 1:20–2:10 | **Command center** → select **SH11** → choose **Cargo temperature excursion** → **Preview event impact** | The app computes a before/after comparison across four response plans. Inspect cost, unmet demand, affected shipments, holds proposed for review, solver status and constraint checks. A preview changes no assignment or hold. |
| 2:10–3:10 | Confirm the preview's intention checkbox → **Apply previewed event** → **Compare refreshed response plans** → **Review** for scenario **C** | The event changes this simulated network. In the proposal, inspect assignments and lots; enter a **Dispatcher name** and **Reason for approval**, then **Approve simulated plan**. Approval records a human decision and publishes simulated assignments. Held/recalled lots stay excluded. **Recent activity** shows the receipt. |
| 3:10–4:00 | **AEGIS Drive** → **Confirm safely parked** → select a truck from the approved plan → confirm parking again if prompted → **Dispatch instructions** → **Acknowledge assignment** | A previously empty driver view now shows its approved destination, trip, cargo temperature and fuel scenario. Open **Report an issue**, type a short simulated incident and choose **Send to dispatcher**. The report is recorded for dispatcher review. |
| 4:00–5:00 | **Sources & evidence** | Inspect official recall notices, source/retrieval timestamps, NOAA coverage and missing values, underlying CDC/FSIS tables and recorded connectivity. Finish by distinguishing real public evidence from fictional operations and explaining the model's research limits. |

If a step produces an explicit error, keep it visible and read its reason. A
stale proposal requires a new review; an infeasible scenario cannot be approved.
Changing the selected trip or applying another event can change the plan and
invalidate older driver acknowledgments. Reopen the intended step against the
current network rather than assuming an earlier approval still applies.

## Optional highlight: Save the Load

For a clean freshness demonstration, start another judge session on a different
available port, such as 8002. Keep that server's URL separate from the first
session. On Windows, from `02_Application`:

```powershell
.venv/Scripts/python.exe scripts/judge_demo.py run --port 8002 --open-browser
```

1. Open **Save the Load** and select **Start rescue experiment**.
2. Choose **Replay heat excursion**. Stored simulated readings feed the decay
   calculation; inspect the changed remaining-quality windows and the proposed
   closer recipient. **Add road-delay frame** tests another exposure assumption.
3. Compare **Show FEFO pick order** and **Show FIFO pick order**. These are
   computed warehouse allocations constrained by eligible stock, capacity and
   the experiment's modeled quality windows.
4. To publish a rescue, review the selected option, assignments, receiving
   conditions and route limitations; complete the named dispatcher/reason fields
   and all three review confirmations before **Approve simulated rescue plan**.
   Inspect its receipt, then check **AEGIS Drive** on this same server.

The conservative quality window is a sensitivity-based planning bound, not a
measured confidence interval. Temperature, humidity, vibration and ethylene
channels do not establish connected hardware or a calibrated poultry spoilage
model. A shorter modeled shelf-life may propose a closer recipient; it cannot
by itself impose a mandatory safety hold or clear the food for dispatch.

## The other workspaces

| Workspace | Use case and expected result |
|---|---|
| **Command center** | View the Missouri network, test delivery pressure, preview/apply a simulated disruption, compare A/B/C/D plans and review a proposal. Map layers change the evidence displayed; displaying a plan does not approve it. |
| **Save the Load** | Replay stored simulated exposure, inspect quality-decay/rescue estimates and compare FEFO/FIFO allocation. Human review publishes an eligible rescue plan. |
| **Route laboratory** | Test a single-farm journey or a multi-location fleet, change planning assumptions, calculate routes/allocations and save an inspectable planning run. Route-lab planning does not automatically publish driver assignments. |
| **Road intelligence** | Inspect separately sourced Missouri/Iowa road evidence and compare route alternatives. Offline estimates and dated incidents retain their labels; OSRM is not a truck-restriction service. |
| **Dispatcher desk** | Review submitted driver reports, holds and versioned instructions. Consequential changes require the provided human-review controls. |
| **AEGIS Drive** | Inspect an approved trip and simulated fuel/temperature, acknowledge instructions and report an issue while parked. Empty assignments before approval are expected. |
| **Evidence assistant** | Ask a guided question such as `chicken`, or choose a suggested question, to inspect cited facts from the captured network and evidence. Its explanations do not change the operational plan. |
| **Model evaluation** | Compare measured chronological validation, baseline, calibration, uncertainty, ablations and coverage. A statistical association is not consumer-illness probability or lot clearance. |
| **Project brief** | Review the five tasks, policy comparison, reports, printable handbook, dated software checks and isolated rehearsal tools. Human practice and automated checks remain different evidence. |
| **Sources & evidence** | Inspect official notices, underlying tables, original-file inventory, missingness, provenance and dated connectivity. USDA county indicators are historical context, not invented recipient need. |

The full menu-by-menu guide is provided as a PDF in `01_Guides`. The application
also exposes report downloads in **Project brief**. For technical review, the
bundled source, test suite, API registry and reproduction scripts are inside
`02_Application`; recorded evidence is available in `03_Verification` and the
application's `reports` directory.
