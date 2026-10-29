## Start here: what AEGIS does

AEGIS means **Adaptive Early-warning & Guidance for Integrated Supply Chains**. We built it to help a regional poultry distributor examine food-safety evidence, understand disruption scenarios, compare constrained operational responses and keep a human dispatcher responsible for consequential decisions.

The core demonstration is centered on Missouri: Columbia, Kansas City, Jefferson City, Springfield and St. Louis. An optional Iowa road-evidence layer supports a cross-state planning example. National historical food-safety data support the retrospective modeling study; this is not a separately validated Missouri-only predictor.

The simplest way to read the product is a sequence: **inspect evidence → explore a response → check constraints → record a human decision → inform the driver → retain the record**. Some screens are planning experiments and never enter that dispatch sequence. This guide explains those boundaries as well as the controls.

### Who can use the current application?

| Person or situation | Useful workspaces | What they can learn or practice |
| --- | --- | --- |
| One farm sending refrigerated trucks | Route laboratory, saved experiments, Road intelligence | Test custom origins, available stock, truck capacity, stops, deadlines and route assumptions |
| Regional distributor or multi-location fleet | Command, Route laboratory, Dispatcher desk, Drive | Compare fixed-network responses and separate multi-origin route experiments; practice approval and driver communication |
| Driver or field operator | Dedicated AEGIS Drive | Inspect a dispatcher-approved trip and report or acknowledge while safely parked |
| Data/science teammate | Sources & evidence, Model evaluation | Inspect original fields, missingness, dated coverage and measured model results |
| Presenter or reviewer | Project brief, guided rehearsal, this handbook | Understand the product, practice an isolated sequence and find recorded evidence |

These are use cases, not production account types. Everyone on one local server shares its simulated state. Names entered into decision forms are self-declared. The application does not currently provide authenticated roles, organization isolation, subscription plans or a corporate account system. Farm/fleet presets change planning scale, not account permissions.

### Keep four kinds of information separate

| Kind | Examples in AEGIS | How to read it |
| --- | --- | --- |
| Real public evidence | Official recalls, establishment directory records, NWS warnings, DOT events, historical FSIS/CDC/USDA exports | Read the source, scope, observation or provider time, retrieval time and missingness |
| Simulated operations | Suppliers, supply contracts, lots, trucks, shipments, inventory, demand, cargo telemetry and fuel | Reproducible fictional examples used to demonstrate a workflow |
| Planning estimates and projections | Offline travel factor, solver costs, illustrative cargo-temperature curves | Outputs conditional on stated assumptions; they are not observations or certified safety findings |
| Measured software/science evidence | Executed tests, recorded holdout metrics, browser checks, saved proposal and audit records | Evidence with a specific date and scope; a pass does not guarantee future service uptime |

Real establishment coordinates do not prove that the simulated distributor buys from that facility. A real road-event record does not prove a fictional shipment encountered it. A projected temperature is not a sensor measurement. A sampling-positive result is not a consumer illness probability.

### What is already available, and what is not?

Available now: the nine connected workspaces in this guide; deterministic network/event simulation; four allocation responses; constrained farm/fleet route experiments; saved planning versions and exports; explicit approval, holds and instructions; a parked-use driver mode; separate public/historical evidence; measured retrospective model evaluation; guided isolated rehearsal; and local backup/recovery tools.

Still outside the implemented product: live physical sensors or vehicle tracking, native phone-app distribution, commercial truck certification, automatic closure avoidance, production accounts, cloud hosting, evaluated language-model advice, isolate-level genomic reconstruction and a validated prospective illness forecast. These are recorded future extensions or scientific gaps. The Evidence assistant provides deterministic cited summaries; an optional, unverified Ollama connector can select a topic but cannot author facts or perform actions.

Genuine Kiro specification execution, final report/rubric author review and the timed team presentation remain separate submission tasks. An installed IDE, a generated document or a successful automated demonstration does not complete those tasks.

## Find your way around the application

The desktop control tower is **AEGIS Command**. Its navigation opens these nine workspaces. The mobile navigation offers the same workspaces in a horizontally scrollable bar; the dedicated Drive URL removes the Command navigation to give drivers a simpler surface.

| Navigation label | Main question it answers | Does simply reading it change dispatch? |
| --- | --- | --- |
| Command center | What does the simulated network look like, and how do four responses compare? | No; event/reset and explicit approval controls do change local state |
| Route laboratory | How could one farm or a multi-origin fleet serve these stops under assumptions? | No; even saved laboratory runs do not dispatch |
| Road intelligence | What do captured Missouri/Iowa road records say near these route alternatives? | No; comparison is read-only planning |
| Dispatcher desk | What did a driver report, and what human review, hold or instruction is recorded? | Reading does not; submitted decisions can change assignments/holds/instructions |
| Sources & evidence | Where did each evidence layer come from, and what coverage is missing? | No; source refresh can update caches, not dispatch |
| Model evaluation | What was actually measured in the historical FSIS study? | No; opening this view never trains a model |
| Evidence assistant | How do captured facts explain scenario tradeoffs, a shipment, model limits or the driver workflow? | No; it only returns cited explanations and navigation |
| Project brief | Where are the master guide, shorter status brief, feature register and rehearsal tools? | Document downloads do not; recording an isolated rehearsal writes its practice record |
| AEGIS Drive | What assignment and instruction has the dispatcher approved for this truck? | Reading does not; parked acknowledgments and reports create records |

### Common controls and labels

**Reload application data**, the header refresh button, rereads the main app's saved network and supporting data. It does not independently refresh every public provider, retrain a model or reset the network. Individual workspaces have their own refresh/recheck controls, described later. The bell and avatar in the Command header are visual status elements; they are not a separate notification inbox, sign-in form or account-settings feature.

**SIMULATED OPERATIONS** and the scenario reference date describe the exercise. They do not describe current live trucks. Source timestamps are separate. Green, amber and red status pills must be read with their text: green does not mean an agency certified a product or truck route. A success notice appears after an accepted action; an error or stale-version notice means stop and reread the current context before retrying.

**Pending**, **approved**, **acknowledged**, **verification recorded**, **held** and **resolved** mean different things. A pending proposal is not an assignment. A driver acknowledgment is not targeted verification. Resolving an incident does not release a lot. A released lot is not automatically reassigned. Read the workflow chapters before treating one label as a substitute for another.

### Useful reading paths

- **First-time teammate:** read this orientation, the Command chapter, the connected driver walkthrough, Sources & evidence, Model evaluation and the glossary. Return to detailed control tables when practicing.
- **Farm/fleet planner:** read Route laboratory and Road intelligence, then the planning-versus-dispatch and storage explanations. Use custom inputs without implying that the presets are actual farm businesses.
- **Dispatcher/driver pair:** read Dispatcher desk, AEGIS Drive and the guided practice chapter together. Use an isolated rehearsal for actions.
- **Presenter:** read the science boundaries, the Project brief/rehearsal chapter and the presentation checklist. Use the shorter project brief for status; use this handbook to learn the details.

## Open the site and choose a safe practice workspace

The ordinary local app is available at **http://127.0.0.1:8000** while its server is running. Dedicated Drive uses **http://127.0.0.1:8000/?mode=drive**. These are addresses on the current computer, not publicly deployed team links. A teammate normally runs a separate checkout or reviewer package on their own computer; GitHub shares code, not one automatically synchronized live database.

If the local server is stopped, open PowerShell in the project folder and run:

```powershell
.venv/Scripts/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Leave that terminal running. The documented setup in README.md and CONTRIBUTING.md covers installing dependencies on a different computer. The included reviewer ZIP contains a prebuilt frontend; viewing it does not require rebuilding React.

### Practice actions in an isolated rehearsal

Before injecting events, resetting a demo or walking through approvals for a presentation, start a separate practice server:

```powershell
.venv/Scripts/python scripts/start_rehearsal.py --port 8001
```

Open the URL it prints. Check the persistent **ISOLATED REHEARSAL** banner and the unique session identity. Project brief also shows **Verified isolated rehearsal** inside its practice panel. The launcher creates a fresh UUID database under data/rehearsals/ and preserves the operator's normal database. Adding `?mode=rehearsal` to the ordinary operator URL only opens a view; it does not create isolation.

The default rehearsal is offline at the backend: it uses dated fixtures, rejects provider refresh and returns labeled route estimates. Browser map tiles and deliberately opened external source links can still need internet. Keep the rehearsal terminal running. If its port is occupied, choose another unused port with the launcher rather than terminating an unrelated service. Port 8000 is reserved for the operator app.

Rehearsal and ordinary operator state are separate. An approval in one server will not appear in Drive on another port. Use Command and Drive from the same rehearsal URL during a practice sequence. Do not reset port 8000 to prepare a presentation.
