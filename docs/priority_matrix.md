# AEGIS delivery priorities

Agreed October 26, 2026. Feature freeze target: October 30. Submission deadline: November 2.

| Priority | Feature | Decision | Completion evidence |
|---|---|---|---|
| P0 | Required data integration and provenance | Must finish | Source-specific schemas, raw inventory, recorded API failures, retrieval/observation timestamps, explicit coverage and simulation labels |
| P0 | Validated risk estimator and baseline | Must finish | Reproducible chronological validation, prevalence comparison, calibration, uncertainty, leakage/availability audit; scientific limits remain visible |
| P0 | At least three intervention scenarios | Must finish | Distinct quantified results, feasibility/status, enforced constraints and dispatcher approval |
| P0 | Functional application with genuine AWS Kiro workflow | Must finish | App runs locally; actual Kiro opens this repository and executes a reviewed spec task; authentic evidence retained |
| P0 | Report, code and five-minute demo | Must finish | Reproducible commands, methods/results/limitations, tested demo and submission package |
| P1 | Interactive digital-twin map | Strong differentiator | Real map geometry and official evidence layers with clearly fictional operational entities |
| P1 | Optimization-based recommendations | Strong differentiator | Reproducible solver, hard safety constraints, measured tradeoffs and reviewable plans |
| P2 | Evidence/LLM operations assistant | Bounded read-only stretch authorized October 29 | Deterministic cited summaries work; optional model topic selection remains unverified until configured/evaluated. No decision tools or invented claims. Human P0 gates remain open. |
| P2 | Enterprise/farm account modes | Future extension | Authentication, tenancy, organization permissions and billing remain outside the submission |
| P2 | Live sensor integrations | Future extension | Physical sensor connectors remain outside the submission; telemetry is simulated |

## Scope decisions

Single-farm and multi-location route experiments are operational planning presets in the same application. They let a reviewer compare one dispatch origin with multiple origins and trucks. They do not establish separate account types, tenant isolation, real contracts, or a production fleet-management service.

AEGIS Drive remains a mobile-responsive mode of AEGIS sharing its backend. The MVP contains shipment information, verified-source advisories, cargo-temperature status, and an incident report. Assignment acknowledgment and dispatcher-approved instructions support the shared workflow. Typing and extended interaction are designed for use while parked.

Cold-chain projections are explicit simulations or sensitivity estimates, not validated forecasts of food safety. Road-event proximity is a review signal, not proof that a route is closed or truck-safe. Dispatch decisions remain subject to hard constraints and human approval.

## Release gate

Resolve a failing P0 check before starting a P2 feature. Preserve a runnable tested application after each change. Keep the latest measured results and known failures in `docs/progress.md` and machine-readable reports. A better map or assistant must not displace provenance, scientific validity, scenarios, Kiro evidence, or the report/demo.

The October 29 request authorizes continued stretch development alongside the
remaining human submission tasks. The evidence assistant is deliberately bounded
to existing captured facts and read-only navigation. It does not close genuine
Kiro, final author/rubric or timed presentation gates, and does not introduce
evaluated language-model advice or autonomous operations.

Inadequate discrimination does not justify an invented accuracy claim. The historical estimator can be the submitted scientific result if its validation and limits are documented. A prospective predictor remains unvalidated when actual feature-availability dates cannot support the claim.
