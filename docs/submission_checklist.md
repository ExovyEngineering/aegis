# AEGIS submission checklist

October 26, 2026. This checklist records required evidence, not a claim that every gate has passed. Updated experiment outputs and `docs/progress.md` take precedence over stale counts here.

## P0 release gates

| Gate | Current evidence | Remaining evidence |
|---|---|---|
| Raw data and required integrations | 42-file inventory; separate FSIS/CDC; five NOAA stations, 2,730 dates and nine missing precipitation values; public recall/routing | Expand historical years only as scientifically justified; preserve variable-level gaps |
| Provenance and source failures | Manifest, schemas, dated fixtures, exact errors and coverage API | Rehearse stale/offline coverage in the final UI; distinguish observations, forecast, reanalysis and cargo simulation |
| Risk estimator and baseline | Retrospective prevalence/logistic, calibration/uncertainty and frozen earlier-snapshot sensitivity | Actual publication timing remains unknown; no prospective-validation claim |
| Three or more interventions | Four solver scenarios with hold/recall, stock, eligibility and capacity checks | Rehearse changed-event tradeoffs and capture final reproducible results |
| Functional application | Built React/FastAPI app; documented startup, backend/UI tests, HTTP smoke and 26 passing real-browser checks (`reports/browser_qa/final/results.json`) | Fresh-environment reproduction and final timed presentation rehearsal |
| Genuine AWS Kiro workflow | Signature-verified official IDE 1.4.26 installed and version checked | User sign-in, actual spec execution and authentic evidence. Gate remains open; see `docs/kiro_handoff.md` |
| Report and code | Architecture, model card, assumptions, audit and demo script | Assemble final methods/results/limitations report and verify any additional official rubric requirements |
| Five-minute demo | Deterministic seed, accelerated isolated workflow and desktop/mobile screenshots with browser workflow verification | Timed five-minute rehearsal and backup fixture demonstration |

## Final reviewer checks

- Run the audit against the supplied folder without modifying originals.
- Run the locked Python installation, pytest, frontend tests and build using README commands.
- Show the selected national sampling target and units; do not label positivity as consumer illness probability.
- Show measured model results even if the historical baseline wins.
- Show three distinct response scenarios, solver feasibility and quantified cost/demand/waste assumptions.
- Show that held, recalled, ineligible or capacity-violating assignments cannot dispatch.
- Show human approval, stale-proposal rejection, driver assignment and acknowledgment.
- Show official recall evidence separately when real lot-level traceability is absent.
- Show NOAA observations with coverage limits, weather forecasts separately, and simulated cargo temperatures separately.
- Show MoDOT source time, route proximity limitations, OSRM restrictions and any estimated fallback.
- Demonstrate farm and multi-location planning presets with consistent simulation labels; avoid account/tenancy claims.
- Keep Drive use parked, with short advisories and explicit dispatcher authority.
- Confirm the final official submission rubric, delivery format and evidence requirements from organizer materials; the public announcement is not a full rulebook.

## Genuine Kiro handoff

The application uses React/FastAPI and continues to run independently. Kiro is the development environment used to carry out the requested specification workflow. No migration to a different application runtime is necessary.

1. Open installed Kiro 1.4.26 from Start or `.tools/kiro/Kiro.exe` and sign in interactively. Keep credentials private. The verified installation and concrete task are in `docs/kiro_handoff.md`.
2. Open `C:/Users/ericp/Downloads/NAFSI` with **File > Open Folder**. Review existing steering and this priority matrix.
3. Start a Spec workflow for a bounded, unfinished P0 task, for example validating NOAA station coverage or adding a provenance acceptance check. Supply the existing requirements and design as context.
4. Review Kiro's requirements, design and tasks against the actual implementation. Preserve working behavior and the immutable raw-data rule.
5. Execute a real task through Kiro. Review its changes and run the relevant pytest/frontend checks in Kiro's terminal. Do not mark an already completed Codex task as Kiro-authored work.
6. Record task identity, date, reviewed changes, command output and appropriate screenshots or exported history from that actual session. Keep this evidence separate from Codex-prepared documents.

Official workflow references: [Kiro installation](https://kiro.dev/docs/getting-started/installation/), [opening an existing project](https://kiro.dev/docs/getting-started/first-project/), [specifications](https://kiro.dev/docs/specs/). Kiro's documented spec phases cover requirements, design and implementation tasks; the presence of similarly named files alone does not establish execution.
