# Model card

retrospective feasibility only — not a validated prospective forecast

Salmonella positivity in a future selected FSIS raw-poultry primary sample; national

Assumed collection date + 90 days. Actual per-result publication timestamps unavailable; historical snapshots were downloaded later. No operational forecast claim.

Measured results: `reports/model_evaluation.json`. The logistic model is not operationally selected. No gradient boosting until availability and prospective evaluation are defensible. Hold decisions never derive automatically from these scores.

- Selected surveillance samples are not representative of all poultry
- No probability of consumer illness
- Single chronological holdout; no external validation
- No CDC or weather linkage
- Intervals quantify within-holdout weekly variation, not publication-lag uncertainty

Command's delivery outlook is a separate deterministic planning projection over
simulated trips and user assumptions. It combines allocation constraints and
uncalibrated cargo-temperature calculations; it has no measured prospective
delay/failure accuracy. See [delivery_outlook.md](delivery_outlook.md).
