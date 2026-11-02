## Storage, exports and sharing

Project brief now starts with **Five tasks. One inspectable submission.** Each
task opens related operational/evidence workspaces and allowlisted source/result
exports. **Download final five-task PDF** and **Read final guide and presentation**
provide the concise handoff. Task 1 exports its diagram/dictionary/provenance and
analytic CSV; Task 5 offers a one-page team statement with last names and final
author review left for the team. Kiro non-use is explicitly disclosed.

The **Preserve food. Compare who receives it.** panel switches three captured
simulated scenarios across a feasible rule, volume/quality preservation and
balanced service. Compare distributed/unmet food, service and quality exposure,
then expand per-destination results/actions. These are fixed-seed read-only
studies; they do not change current assignments, impose holds or certify safety.
The displayed equity measure concerns destination service, not an invented
population-vulnerability score. Download JSON or CSV for all nine comparisons.

The current app is a local research demonstrator with saved SQLite operational state and separate evidence files. It does not run a continuous warehouse inventory ledger, synchronize companies through cloud accounts, or send physical truck instructions outside the application.

| Item | Where it lives or how it is shared | Important distinction |
| --- | --- | --- |
| Current network, proposals, approved assignments and audit | Local application database | Refreshing the page rereads saved state; resetting the demo changes the current exercise |
| Driver reports, focus, instructions and verification reviews | Same local backend as Command | A report/instruction on one server is not automatically shared with another teammate's server |
| Saved laboratory runs and project versions | Planning records in local database; JSON/CSV exports are downloadable | A saved experiment cannot become a dispatched trip by reopening it |
| Original supplied files | Their preserved raw locations and audit manifest | They are never overwritten to make an import succeed |
| Processed scientific tables | Source-specific derived files and ingestion reports | CDC, FSIS and county-context layers retain distinct meanings |
| Public-source caches and dated fixtures | Local evidence files with retrieval metadata | A cache read is not necessarily a new provider response; a fixture does not become current |
| Rehearsal records | The separate UUID practice database and immutable JSON exports | Automated workflow evidence is not human presentation evidence |
| Team code | Private GitHub repository and reviewed branch | GitHub shares source and allowed evidence, not credentials or an active operational database |

Unsaved form text is usually a browser draft. Navigating away, reloading, receiving a new run version or changing context can clear it. Read each workspace's save/submit receipt. Downloaded exports are independent files; later changes in the app do not update a copy you already printed or emailed.

### Which exports are actually available?

The route laboratory supports saved-run JSON and stop-sequence CSV through its planning library, plus version/project comparisons. Road intelligence exports a captured comparison JSON. County context supplies a checked county CSV. Completed/aborted rehearsals export evidence JSON. Project brief supplies this handbook and the shorter status brief in their offered formats.

The underlying source-table browser has bounded row inspection and schema/provenance; it does not currently offer a general table-export button. Model evaluation reads saved results; it does not offer an in-app training button. Do not infer an export, live refresh, account or disposition feature merely because its data are visible.

## Local backup and recovery

Backup/recovery is a command-line tool for the technical teammate, not an extra website button or a cloud service. It protects local simulated operational records when experimenting. The database itself contains recorded identities, reports, instructions and assignments, so keep backup files private.

Create a new backup from the project directory:

```powershell
.venv/Scripts/python scripts/backup_state.py create
```

The result prints a fresh directory under **data/backups/**. Verification checks checksum, SQLite integrity, supported schema and row counts. Restoration creates a new file under **data/recovered/**; it never overwrites the operator database or automatically points the running server at the recovered copy.

For a specific backup, follow the complete commands in **docs/backup_restore.md**. Choose a fresh destination each time. Do not manually copy or delete SQLite WAL/shared-memory sidecars. Review restored holds, recalls, assignments and parked confirmations before any resumed use. Restoring old approvals is not a new approval or permission to dispatch.

The tool records integrity relative to its manifest, not an authenticated author signature or a scientific safety finding. Raw observations, source caches, code, credentials and frontend files are outside this operational-state backup. Private backups/recovery receipts are excluded from Git and reviewer packages.

## Troubleshooting by what you see

| What you see | Likely meaning | Useful next step |
| --- | --- | --- |
| Connecting to the local backend | The local server is stopped, unavailable or not serving the expected port | Start the documented server and check its terminal; use Retry connection |
| Map tiles are blank but markers/data appear | Browser tile requests need internet or failed independently | Read the geometry/source information; do not treat missing tiles as a solver failure |
| No approved assignments in Drive | No plan is approved on this server, or an event/hold/reset/new plan invalidated earlier assignments | Check Command and Dispatcher desk on the same port; review and approve a fresh plan if appropriate |
| Driver actions are locked | No current parked attestation, expired confirmation, read-only focus or a different selected truck | Park safely and confirm for the truck now displayed; acknowledgment does not grant dispatcher authority |
| Network changed / stale version | A proposal, instruction or trip was based on an older revision | Refresh its current context and review the evidence before resubmitting; do not repeatedly click an obsolete decision |
| Source unavailable / stale / cached fallback | The provider failed, a response aged past its window, or only dated evidence exists | Read timestamps/error details; refresh deliberately when allowed, and retain the gap if it persists |
| Offline source refresh is disabled | This is the intentionally isolated offline rehearsal | Use its dated fixtures and estimates; a separate operator source check is a different action |
| Laboratory inputs changed | Current form values differ from the displayed saved/completed run | Test the plan again before interpreting the new inputs as its results |
| Unserved stops or unmet demand | Available eligible stock, capacity, timing or solver choices could not serve everything | Inspect exclusions and constraints; do not assume an unserved delivery was safe to force through or automatically wasted |
| Solver reports failure / no usable routes | The submitted assumptions did not produce the expected feasible solution, or routing evidence failed | Read its actual status and warnings; adjust plausible inputs and rerun rather than inventing feasibility |
| Hold release succeeded but no trip returned | Release does not recreate deleted assignments | Produce, review and approve a fresh eligible plan |
| Rehearsal Covered is rejected | Required audit evidence is missing, stale, invalidated or from a different trip/run | Complete the actual stage on the same isolated server, or record an honest skip reason |
| A printed guide differs from the app | The app or evidence changed after this guide's generation date | Download the current guide and consult the current labels/timestamps |

If a problem persists, retain the exact visible error and the relevant source/run identity for the technical teammate. Avoid repeating a consequential action until you know whether the previous request was accepted. The app distinguishes a rejected request from an accepted action whose subsequent refresh failed.

## Glossary for reading the site

| Term | Plain-language meaning in this project |
| --- | --- |
| Adaptive early warning | Combining evidence and scenario review to help a human notice and respond; not a guarantee of prediction |
| Digital twin | A deterministic simulated network that mirrors operational concepts; not a live replica of a real company |
| Lot | A simulated product batch with inventory, eligibility, hold and recall state |
| Candidate shipment | A possible fixed trip in the network, before scenario selection and approval |
| Proposal | A calculated response awaiting an explicit human decision |
| Approved assignment | A simulated trip published by dispatcher approval and visible to Drive |
| One-wave allocation | Choosing eligible shipments for one planning exercise; not a rolling warehouse stock ledger |
| Constraint | A limit the plan must respect, such as stock, capacity, eligibility or a hold |
| Feasible | A solver found a plan satisfying its modeled constraints; not a finding that a physical operation is safe |
| Optimal | Best under that solver's stated objective and model; not universally best or clinically safe |
| Unmet demand | Requested quantity not served by that modeled plan |
| Food waste | A model-specific reported quantity under stated assumptions; not every unserved delivery |
| Hold | A human-recorded restriction excluding a lot from dispatch in this application |
| Eligibility | Whether a simulated lot, supplier or truck meets the modeled requirements |
| Targeted verification | A recorded scenario-B review checklist; separate from driver acknowledgment and product certification |
| Revision/version | A number identifying the state a decision was based on; stale writes are rejected |
| Provenance | Where information came from, its meaning and the hashes/times/context needed to trace it |
| Retrieval time | When the app obtained a response; different from when a provider observed or edited a record |
| Cached response | Previously retrieved evidence reused locally; it may be valid within a cache window or stale |
| Dated fixture | A preserved actual source response used for a reproducible offline demonstration |
| Forecast | A provider's prediction for future weather; not an observed station measurement |
| Historical reanalysis | A reconstructed weather product; not interchangeable with required NOAA observations |
| Simulated telemetry | Generated cargo or vehicle values for the exercise; no physical sensor is connected |
| Parameter sensitivity | How a projection changes when assumed parameters change; not a statistical confidence interval |
| Positivity | The fraction of selected laboratory samples testing positive for the defined outcome; not consumer illness probability |
| Baseline | A simple comparison estimator used to judge whether a more complex model adds value |
| Chronological holdout | Later observations kept out of model fitting and used for evaluation |
| Calibration | Whether predicted sampling probabilities agree with observed frequencies in suitable groups |
| Brier score | Mean squared probability error; lower is better for the same defined evaluation task |
| PR-AUC / average precision | A ranking summary focused on positive examples; interpret relative to prevalence and the exact reported method |
| ROC-AUC | A ranking summary across thresholds; about 0.5 indicates little discriminating ability |
| FIPS | A geographic identifier; different counties with similar names remain separate |
| Geometry proximity | A spatial buffer comparison; a nearby event may be on a parallel road or other carriageway |
| OSRM driving profile | Ordinary-driving routing, without verified commercial-truck restriction checks or automatic DOT closure incorporation |
| Parked attestation | A time-limited self-declaration enabling driver interactions; not a motion sensor |
| Human approval | An explicit recorded app decision; not government authority or physical dispatch |

## Present the project accurately

Use a concrete operational story: a fictional poultry distributor has a constrained plan; evidence and a simulated disruption create a reason to review it; the team compares responses, checks exclusions and records a human decision; the driver receives the resulting assignment and can report back while parked.

Useful statements include: “These are simulated logistics on real geography”; “This source response is dated”; “The model did not outperform the simple baseline here”; “This is a review flag, not an illness probability”; and “The dispatcher must approve a consequential action.” Point to the source, result or audit record that supports each claim.

Avoid statements such as “We predict who will get sick,” “Every road is clear,” “This alternative is truck-safe,” “These are live vehicles,” “AI automatically recalled the shipment,” or “The presence of Kiro files proves Kiro execution.” The current evidence does not establish those claims.

Use the shorter presentation brief to select what fits into five minutes. Keep this handbook as the detailed reference and a place for handwritten questions. Record which claims still need an author/scientific review rather than simplifying them into unsupported certainty.

## Keep this master guide current

The editable master file is **docs/aegis_master_guide.md**. It is assembled from reviewed chapters under **docs/manual_parts/** and dated verification reports. The PDF and standalone HTML are in **reports/**. The manifest records their generation date, PDF checksum, chapter page numbers and source-file hashes.

For the technical teammate: update the relevant chapter when a visible control, workflow, data meaning or limitation changes, then run:

```powershell
.venv/Scripts/python scripts/build_master_guide.py
```

Run the project's relevant tests and frontend build for application changes. The guide compiler does not run provider checks, train models, open the operational database, create approvals or complete submission gates. Its verification appendix reads saved results and keeps their dates separate.

Useful deeper references are README.md, docs/architecture.md, docs/model_card.md, docs/simulation_assumptions.md, docs/operations_workflow.md, docs/road_intelligence.md, docs/state_dot.md, docs/backup_restore.md, docs/rehearsal_guide.md and docs/submission_checklist.md. The handbook is the main reading path; those files provide technical and submission detail.
