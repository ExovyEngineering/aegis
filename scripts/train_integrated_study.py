"""Reproduce a conditional MO multi-source study without altering the core model."""
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd

from backend.integrated_study import (
    CDC_LAG_DAYS, FEATURE_SETS, FSIS_LAG_DAYS, HORIZON_DAYS,
    NOAA_LAG_DAYS, NORS_LAG_DAYS, build_analytic, chronological_split,
    fit_comparisons, load_weather, prepare_beam, prepare_nors, split_summary,
    wilson_interval,
)
from backend.paths import ROOT, write_json


def input_provenance(root):
    evidence = json.loads((root / "data/processed/evidence_manifest.json").read_text(encoding="utf-8"))
    fsis = json.loads((root / "data/processed/fsis_provenance.json").read_text(encoding="utf-8"))
    records = []
    for key, file_name in (("fsis", "fsis_poultry.parquet"), ("beam_1", "beam_1.parquet"), ("nors_0", "nors_0.parquet")):
        metadata = fsis if key == "fsis" else evidence["datasets"][key]
        path = root / "data/processed" / file_name
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        expected = metadata["output_sha256"]
        if digest != expected:
            raise ValueError(f"Processed study input checksum mismatch: {file_name}")
        records.append({"source": key, "processed_path": path.relative_to(root).as_posix(), "processed_sha256": digest, "matches_ingestion_manifest": True, "raw_source_provenance": metadata.get("sources", metadata.get("input_files", [])), "actual_retrieved_at": None, "actual_retrieval_note": "Exact original source retrieval timestamp not recorded; file names and local processing times are not publication timestamps", "local_manifest_generated_at": evidence.get("generated_at") if key != "fsis" else None, "historical_snapshot_vintage_verified": False})
    return records


def validation_figure(root, series, ablations, path):
    cache = root / ".tools/matplotlib-integrated-study"
    cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(cache))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8), gridspec_kw={"width_ratios": [1.2, 1]})
    x = np.arange(len(series))
    intervals = np.array([wilson_interval(int(row.positives), int(row.n)) if row.n else [np.nan, np.nan] for row in series.itertuples()])
    observed = series.positive_fraction.to_numpy()
    axes[0].errorbar(x, observed, yerr=np.vstack([observed - intervals[:, 0], intervals[:, 1] - observed]), fmt="o", color="#111827", label="Selected FSIS positives (Wilson 95% CI)", capsize=3)
    for name, label, color in (("baseline", "Training prevalence", "#64748b"), ("core_integrated", "FSIS + BEAM + NOAA", "#0369a1"), ("with_nors", "Core + NORS", "#b45309")):
        axes[0].plot(x, series[name + "_mean"], "o-", color=color, label=label)
    axes[0].set_xticks(x, series.month, rotation=35, ha="right")
    axes[0].set_ylabel("Selected-sample positivity / mean probability")
    axes[0].set_xlabel("Forecast origin month (outcome seven days later)")
    axes[0].set_ylim(bottom=0)
    for i, row in enumerate(series.itertuples()):
        if not row.n:
            axes[0].text(i, .01, "No complete\nsource coverage", ha="center", fontsize=8)
    axes[0].legend(fontsize=8)
    axes[0].grid(axis="y", alpha=.2)
    labels = ["+ BEAM vs FSIS", "+ NOAA vs FSIS + BEAM", "+ NORS vs core", "All domains vs prevalence"]
    for i, item in enumerate(ablations):
        low, high = item["paired_week_block_bootstrap_95_ci"]
        change = item["brier_change"]
        axes[1].errorbar(change, i, xerr=[[change - low], [high - change]], fmt="o", color="#0369a1", capsize=4)
    axes[1].set_yticks(range(len(labels)), labels)
    axes[1].invert_yaxis()
    axes[1].axvline(0, color="#64748b", linestyle="--", linewidth=1)
    axes[1].set_xlabel("Paired Brier change (lower favors added data)\n95% week-block bootstrap intervals")
    axes[1].grid(axis="x", alpha=.2)
    fig.suptitle("Missouri conditional retrospective validation: source coverage and added value", fontsize=12)
    fig.text(.02, .015, f"Snapshot availability assumed; {int(series.n.sum())} held-out selected samples / {int(series.positives.sum())} positives. No shipment, illness, or operational risk claim.", fontsize=8)
    fig.tight_layout(rect=(0, .045, 1, .94))
    fig.savefig(root / path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main(root=ROOT):
    root = Path(root)
    provenance = input_provenance(root)
    fsis = pd.read_parquet(root / "data/processed/fsis_poultry.parquet")
    beam = pd.read_parquet(root / "data/processed/beam_1.parquet")
    nors = pd.read_parquet(root / "data/processed/nors_0.parquet")
    weather, stations, station_days, daily = load_weather(root)
    analytic, valid_fsis = build_analytic(fsis, beam, nors, weather)
    train, test = chronological_split(analytic)
    models, predictions, ablations = fit_comparisons(train, test)
    _, beam_rows = prepare_beam(beam)
    _, nors_rows, nors_end = prepare_nors(nors)
    paths = {"analytic": "data/processed/integrated_mo_analytic.csv", "predictions": "reports/integrated_model_predictions.csv", "timeseries": "reports/integrated_model_timeseries.csv", "report": "reports/integrated_model_evaluation.json", "narrative": "reports/integrated_model_study.md", "figure": "reports/figures/integrated_model_validation.png"}
    # Predictions explicitly retain coverage gaps and non-holdout nulls.
    exported = analytic.copy()
    exported["prediction_reason"] = "Outside primary chronological validation window"
    exported.loc[~exported.coverage_eligible, "prediction_reason"] = exported.loc[~exported.coverage_eligible, "coverage_exclusion_reason"]
    exported.loc[test.index, "prediction_reason"] = "Conditional retrospective held-out estimate; not an operational score"
    for name, values in predictions.items():
        exported[name + "_prediction"] = float("nan")
        exported.loc[test.index, name + "_prediction"] = values
    heldout = exported.loc[test.index].copy()
    heldout["month"] = heldout.forecast_origin.dt.to_period("M").astype(str)
    series = heldout.groupby("month").agg(n=("y", "size"), positives=("y", "sum"), positive_fraction=("y", "mean"), **{name + "_mean": (name + "_prediction", "mean") for name in predictions}).reset_index()
    months = pd.period_range("2026-01", "2026-06", freq="M").astype(str)
    series = series.set_index("month").reindex(months).rename_axis("month").reset_index()
    series[["n", "positives"]] = series[["n", "positives"]].fillna(0).astype(int)
    series["coverage_reason"] = series.n.map(lambda n: "Held-out selected samples with complete source coverage" if n else "No held-out sample meets complete source-coverage gate; no estimate")
    rolling = []
    for start, end in [("2025-10-01", "2026-01-01"), ("2026-01-01", "2026-04-01"), ("2026-04-01", "2026-07-01")]:
        tr, te = chronological_split(analytic, start, end)
        try:
            fold_models, _, _ = fit_comparisons(tr, te, repetitions=150)
            rolling.append({"validation_requested_start": start, "status": "evaluated", "split": split_summary(tr, te), "metrics": {name: model["metrics"] for name, model in fold_models.items()}})
        except ValueError as exc:
            rolling.append({"validation_requested_start": start, "status": "insufficient_coverage", "reason": str(exc), "training_rows": len(tr), "validation_rows": len(te)})
    availability = {
        "fsis": {"assumed_lag_days": FSIS_LAG_DAYS, "basis": "collection_date + lag", "actual_publication_timestamps_present": False},
        "beam": {"assumed_lag_days": CDC_LAG_DAYS, "basis": "month-end + lag", "actual_publication_timestamps_present": False},
        "noaa": {"assumed_lag_days": NOAA_LAG_DAYS, "basis": "daily reporting-period end + lag; 28 trailing complete days", "actual_publication_timestamps_present": False},
        "nors": {"assumed_lag_days": NORS_LAG_DAYS, "basis": "month-end + lag; latest available trailing12 exported-record count", "actual_publication_timestamps_present": False, "source_observation_end": nors_end},
    }
    limitations = [
        "This is a conditional retrospective feasibility study. NOAA cache retrieval and FSIS snapshot-creation metadata postdate the modeled origins. Exact original BEAM/NORS retrieval timestamps were not recorded. Assumed lags are not evidence that these exact revised snapshots were available then; no prospective forecast validation or operational activation is claimed.",
        "Target is positivity in selected FSIS raw-poultry surveillance samples in Missouri, conditional on being sampled. Backdating the forecast origin does not validate forecasting whether a future sample will be selected. It is not lot contamination, probability of illness, representative state prevalence, or a linkage from a human isolate to a food sample.",
        "BEAM human Salmonella counts are PulseNet-derived aggregate surveillance context. State, pathogen, and time alignment provide no genomic linkage, epidemiological attribution, or outbreak causation; CDC records remain separate predictors and never become FSIS outcome labels.",
        "NOAA is an equal-weight five-airport Missouri ambient index. Requiring all five quality-pass station values for each of 28 days can exclude many samples. This index is not establishment exposure, route weather, cargo telemetry, or statewide representative sampling.",
        "NORS counts exported Missouri foodborne Salmonella outbreak records, not illnesses. Absent qualifying rows mean no matching record in this snapshot, not no outbreak. Its observation window ends in 2023; the latest period is capped at this source end, never extrapolated with future zeros. NORS and the broader BEAM system are not independent surveillance systems; the BEAM predictor here uses human isolate counts only.",
        "All models and ablations use the identical complete-case cohort; coverage exclusion can bias the cohort. No station, state, or source missingness is imputed. Two additional datasets overall are NORS here and USDA county food-access context in separate UI/evidence artifacts; food-access deprivation is not treated as a contamination predictor and does not weight simulated destinations without a verified county crosswalk.",
        "Regularization, feature sets, January 2026 primary split, 90-day fitting embargo, and 0.10 diagnostic review threshold are configured without holdout hyperparameter tuning; this is not a preregistered study. Source lags lack external validation; a different plausible lag could change or eliminate the study cohort.",
        "Week-block bootstrap intervals describe sampling variation within the held-out weeks, with 400 resamples. They do not capture publication/revision uncertainty, all spatial dependence, model-selection uncertainty, or individual prediction intervals. Sparse positive results make discrimination unstable.",
        "Calibration and time-series Wilson intervals assume independent Bernoulli observations. Repeated establishments and temporal dependence violate that approximation; these descriptive bands are not cluster-adjusted inferential intervals.",
        "Diagnostic false positives mean negative selected samples prioritized for review; false negatives mean positive selected samples not prioritized. Counts are not estimates of prevented illness, regulatory violations, or avoidable waste. Any hold requires human approval; held or recalled lots cannot dispatch.",
        "Standardized coefficients describe conditional associations among correlated features, not causal mechanisms. Constant training features and uncertainty spanning zero must not be presented as demonstrated added value.",
        "The primary holdout NORS feature is constant while training spans two values. Its worse Brier score reflects this sparse, old exported-record context and temporal distribution shift; it does not establish that NORS generally lacks value.",
    ]
    coverage = {"input_fsis_rows": len(fsis), "valid_fsis_samples": len(valid_fsis), "national_states": int(valid_fsis.establishment_state.nunique()), "mo_samples": len(analytic), "mo_establishments": int(analytic.establishment_id.nunique()), "mo_positives": int(analytic.y.sum()), "eligible_samples": int(analytic.coverage_eligible.sum()), "excluded_incomplete_coverage": int((~analytic.coverage_eligible).sum()), "weather_station_count": len(stations), "weather_station_days": station_days, "weather_observation_start": str(daily.index.min().date()), "weather_observation_end": str(daily.index.max().date()), "beam_source_rows": len(beam), "beam_mo_human_salmonella_rows": beam_rows, "nors_source_rows": len(nors), "nors_mo_food_salmonella_records": nors_rows, "geography_gate": "MO only; no national weather extrapolation", "availability_gate": "Conditional retrospective pass only; prospective publication availability unverified"}
    report = {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(), "status": "conditional retrospective multi-source feasibility; prospective skill unestablished", "operational_activation_allowed": False, "target": "Salmonella positivity in a selected Missouri FSIS raw-poultry primary sample collected 7 days after forecast origin", "geography": "Missouri", "horizon_days": HORIZON_DAYS, "coverage": coverage, "availability_assumptions": availability, "primary_split": split_summary(train, test), "models": models, "ablations": ablations, "rolling_validation": rolling, "timeseries": json.loads(series.to_json(orient="records")), "input_provenance": provenance, "noaa_station_provenance": stations, "source_definitions": {"beam": "https://www.cdc.gov/beam/about/index.html", "beam_report": "https://data.cdc.gov/Foodborne-Waterborne-and-Related-Diseases/BEAM-Dashboard-Report-Data/jbhn-e8xn", "noaa": "https://www.ncei.noaa.gov/support/access-data-service-api-user-documentation"}, "artifacts": paths, "limitations": limitations}
    for key in paths:
        (root / paths[key]).parent.mkdir(parents=True, exist_ok=True)
    analytic.to_csv(root / paths["analytic"], index=False)
    exported.to_csv(root / paths["predictions"], index=False)
    series.to_csv(root / paths["timeseries"], index=False)
    validation_figure(root, series, ablations, paths["figure"])
    report["artifact_sha256"] = {key: hashlib.sha256((root / paths[key]).read_bytes()).hexdigest() for key in ("analytic", "predictions", "timeseries", "figure")}
    write_json(root / paths["report"], report)
    lines = ["# Conditional Missouri integrated modeling study", "", report["status"], "", report["target"], "", f"Complete-case coverage: {coverage['eligible_samples']} of {coverage['mo_samples']} selected MO samples. Primary training: {len(train)}; validation: {len(test)} with {int(test.y.sum())} positive results.", "", "## Performance on the identical held-out cohort", "", "| Model | Brier | PR AUC/AP | ROC AUC | Mean prediction |", "|---|---:|---:|---:|---:|"]
    for name, entry in models.items():
        m = entry["metrics"]
        lines.append(f"| {name} | {m['brier']:.5f} | {m['pr_auc_average_precision']:.4f} | {m['roc_auc']:.4f} | {m['mean_predicted']:.4f} |")
    lines += ["", "## Paired added-domain ablations", "", "Brier change = augmented − reference; negative is lower error. Intervals resample the same validation weeks for both models.", ""]
    for item in ablations:
        low, high = item["paired_week_block_bootstrap_95_ci"]
        lines.append(f"- {item['added_domain']}: ΔBrier {item['brier_change']:.5f}, 95% interval [{low:.5f}, {high:.5f}]. {item['interpretation']}.")
    lines += ["", "![Held-out time series and paired added-domain comparisons](figures/integrated_model_validation.png)", "", "## Availability and alignment", "", "Origins precede collection by 7 days. FSIS results are assumed available 90 days after collection; BEAM monthly counts 90 days after month-end; NORS monthly records 730 days after month-end; NOAA observations 7 days after their reporting-period label. The NOAA predictor is the trailing 28-calendar-day average ending origin−7 days, requiring all five stations to pass documented quality checks every day. Training labels must become assumed-available strictly before the validation start. Scalers and logistic regressions fit training data only. No contemporaneous/future outcome or CDC label is used as an FSIS feature.", "", "Raw NOAA bytes and processed analytic source files are SHA-256 verified against ingestion metadata. Data records carry outcome date, origin, each source observation period, assumed availability dates, and exclusion reasons. Actual NOAA cache retrieval dates and FSIS snapshot creation dates are recorded separately; exact original BEAM/NORS retrieval times are unknown. These assumptions cannot reconstruct unavailable historical snapshot vintages.", "", "## Scientific limits", ""]
    lines += ["- " + text for text in limitations]
    lines += ["", "## Reproduce", "", "`.venv/Scripts/python.exe scripts/train_integrated_study.py`", "", "This writes separate study artifacts and does not change `reports/model_evaluation.json`, the operational risk selection, raw downloads, or operator state.", "", "CDC source definitions: [BEAM overview](https://www.cdc.gov/beam/about/index.html), [Report Data metadata](https://data.cdc.gov/Foodborne-Waterborne-and-Related-Diseases/BEAM-Dashboard-Report-Data/jbhn-e8xn)."]
    (root / paths["narrative"]).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"coverage": coverage, "primary_split": report["primary_split"], "brier": {name: entry["metrics"]["brier"] for name, entry in models.items()}, "ablations": ablations}, indent=2))
    return report


if __name__ == "__main__":
    main()
