# Model timing and earlier-snapshot stress test

snapshot-consistent retrospective sensitivity study; creation is not verified public release

Earlier source snapshots created **2026-03-19** supply 57,459 training rows. Validation contains 7,754 selected samples dated 2026-03-20 through 2026-06-30, from a different, later source snapshot.

Training labels are frozen to earlier source snapshots and are not updated using held-out outcomes. Calendar month is known at the selected sample date. Metadata creation dates precede validation collection dates; first public release and row-level result availability are unverified. No availability dates were invented.

| Estimator | Brier | PR-AUC (AP) | ROC-AUC |
|---|---:|---:|---:|
| Frozen historical prevalence | 0.09297314 | 0.103559 | 0.500000 |
| Calendar-only logistic diagnostic | 0.09293427 | 0.101889 | 0.499197 |

Frozen smoothed historical prevalence remains the transparent estimator; this sensitivity study does not validate prospective deployment.

- The FY2024/FY2025 files were created March 19, 2026, but that is not proof they were publicly released or accessible on that day.
- FY2026 outcomes come from an October 9, 2026 snapshot and may contain retrospective revisions; no historical as-of archive was supplied.
- Sampling schedules and publication latency are unknown, so this evaluates selected future-dated samples conditional on being sampled.
- Single later-date holdout; no evidence of transportability to farms, shipments or consumers.
- No held-out labels enter frozen model parameters or historical prevalence.
- No CDC surveillance or weather feature is joined to this target.
- Intervals resample validation weeks and exclude publication-lag and selection uncertainty.