# Model card

## Separate integrated Missouri research study

The final five-task review adds `reports/integrated_model_evaluation.json` and
`scripts/train_integrated_study.py`. It combines Missouri selected FSIS outcomes,
lagged PulseNet-derived BEAM human surveillance aggregates and a five-station
NOAA ambient index, with NORS ablation. The seven-day origin conditions on later
sample selection. Actual historical release dates remain unknown; the explicit
assumed lags and complete-source gate do not establish prospective availability.
Only 490 of 1,534 Missouri samples meet coverage; primary validation has 171 samples
and 22 positives. Core Brier is about 0.11246 versus baseline 0.11431; marginal
BEAM/NOAA evidence does not establish improvement. NORS worsens this cohort's
Brier to about 0.12449, with a constant holdout feature. No operational activation
or individual-lot risk/consumer-illness interpretation is allowed. Exact metrics,
calibration, uncertainty, false-positive/negative consequences and missing-month
gaps are in the report and Model evaluation. The national model below is retained
unchanged as a separate study; its no-CDC/weather-linkage limit refers to that study.

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

Save the Load adds a separate mechanistic quality-budget estimator: equivalent
age is integrated from recorded product-temperature intervals under declared
Q10 assumptions. Its point and conservative parameter cases are sensitivity
results, not calibrated confidence intervals or microbial spoilage estimates.
No FSIS outcome, consumer-illness probability or measured molecular freshness is
inferred. Humidity, vibration and ethylene have no invented poultry coefficients.
No physical sensors are connected and no prospective shelf-life accuracy is
reported. See [equations, domains and primary references](freshness_science.md).
Missing/gapped/out-of-domain history abstains; downstream picking/rescue excludes
unknown quality and retains independent use-by, hold and recall constraints.
