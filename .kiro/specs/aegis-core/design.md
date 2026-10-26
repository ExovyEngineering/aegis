# AEGIS core design

Status: Codex-prepared design; actual Kiro review and execution unverified.

Use the modular architecture described in `docs/architecture.md`. Treat raw files as immutable, processed evidence as source-specific, and simulated operational state as transactional SQLite data. Run a deterministic single-worker OR-Tools allocation. Present all plans as proposals before approval.

Record network revision with each proposal. On approval, verify pending status and revision, revalidate hard safety constraints, commit simulated holds/assignments, and append an actor/reason audit event. Reject repeated and stale approvals. Event injection advances revision and invalidates prior assignments.

Public adapters share timestamped caching but retain independent schemas. NCEI historical observations require station/date/quality coverage validation before joins. OSRM route geometry can be compared with official MoDOT event geometry, but proximity is a review signal rather than a definitive road closure/truck-safe route determination.

The model study uses primary FSIS Salmonella results, a lagged historical prevalence feature, chronological holdout, embargo, baseline comparison, calibration, and uncertainty estimates. Lack of publication dates prevents a validated prospective claim. A historical estimator remains the operational evidence layer when discrimination is inadequate.

The route laboratory supports a single-farm origin or multiple regional origins with a shared fleet-planning model. It is a simulation preset selector, not an account/organization system. Any cargo projection must separate thermal assumptions from measured weather, simulated telemetry and validated predictive results. Use one shared Command/Drive backend; the driver MVP remains shipment information, source advisories, temperature status and parked-use incident reporting.

The release order follows `docs/priority_matrix.md`. P0 scientific/provenance and submission evidence cannot be displaced by P1 visual/optimization additions or P2 assistants/accounts/sensors.
