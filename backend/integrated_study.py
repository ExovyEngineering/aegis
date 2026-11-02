"""Conditional retrospective multi-source study; never an operational risk service.

The outcome is a result in a *selected FSIS sample*, not shipment contamination
or human illness. Snapshot publication timestamps are absent. Assumed availability
lags permit a sensitivity study, not a verified historical information set.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from backend.weather_coverage import CITIES, numeric_value, profile_station

SEED = 20261101
HORIZON_DAYS = 7
FSIS_LAG_DAYS = 90
CDC_LAG_DAYS = 90
NOAA_LAG_DAYS = 7
NORS_LAG_DAYS = 730
FSIS_FEATURES = ["fsis_mo_lag90_prevalence", "month_sin", "month_cos"]
CDC_FEATURES = ["beam_mo_human_log_isolates"]
NOAA_FEATURES = ["noaa_mean_tmax_c_trailing28", "noaa_mean_tmin_c_trailing28", "noaa_mean_daily_prcp_mm_trailing28"]
NORS_FEATURES = ["nors_mo_food_salmonella_log_records_trailing12months"]
FEATURE_SETS = {
    "fsis": FSIS_FEATURES,
    "fsis_cdc": FSIS_FEATURES + CDC_FEATURES,
    "core_integrated": FSIS_FEATURES + CDC_FEATURES + NOAA_FEATURES,
    "with_nors": FSIS_FEATURES + CDC_FEATURES + NOAA_FEATURES + NORS_FEATURES,
}


def numeric(series):
    return pd.to_numeric(series.astype("string").str.replace(",", "", regex=False), errors="coerce")


def load_weather(root: Path):
    """Read only the five identity/location-verified caches, preserving raw bytes."""
    rows, provenance = [], []
    for station in CITIES:
        stem = f"{station['station_id']}_2025-01-01_2026-06-30"
        raw = root / "data/external/noaa" / (stem + ".response.json")
        meta = raw.with_name(stem + ".metadata.json")
        body, metadata = raw.read_bytes(), json.loads(meta.read_text(encoding="utf-8"))
        if hashlib.sha256(body).hexdigest() != metadata["sha256"]:
            raise ValueError(f"NOAA checksum mismatch: {raw.name}")
        payload = json.loads(body)
        profile = profile_station(payload, station, "2025-01-01", "2026-06-30", metadata["retrieved_at"], metadata["source_url"])
        provenance.append({"station_id": station["station_id"], "sha256": metadata["sha256"], "retrieved_at": metadata["retrieved_at"], "source_url": metadata["source_url"], "rows": len(payload), "latitude": profile["latitude"], "longitude": profile["longitude"]})
        for row in payload:
            clean = {"date": pd.Timestamp(row["DATE"]), "station_id": station["station_id"]}
            for metric in ("TMAX", "TMIN", "PRCP"):
                flags = row.get(metric + "_ATTRIBUTES", "").split(",")
                value = numeric_value(row.get(metric))
                clean[metric] = value if value is not None and len(flags) >= 3 and not flags[1].strip() else np.nan
            rows.append(clean)
    station_days = pd.DataFrame(rows)
    # All five stations must contribute a quality-pass value for each daily index.
    # A flagged/missing precipitation measurement stays missing, never zero.
    daily = station_days.groupby("date")[["TMAX", "TMIN", "PRCP"]].mean()
    counts = station_days.groupby("date")[["TMAX", "TMIN", "PRCP"]].count()
    daily = daily.where(counts.eq(len(CITIES))).asfreq("D")
    trailing = daily.rolling(28, min_periods=28).mean()
    trailing.columns = NOAA_FEATURES
    return trailing, provenance, int(len(station_days)), daily


def prepare_beam(frame):
    selected = frame.loc[frame["State"].eq("MO") & frame["Pathogen"].eq("Salmonella") & frame["Source Type"].eq("Human")].copy()
    key = ["Year", "Month", "State", "Source Type", "Source Site", "Pathogen", "Serotype/Species"]
    if selected.duplicated(key).any():
        raise ValueError("Duplicate BEAM human state/month/site/serotype keys; refusing to pool")
    selected["period"] = pd.to_datetime({"year": numeric(selected["Year"]), "month": numeric(selected["Month"]), "day": 1}) + pd.offsets.MonthEnd(0)
    selected["count"] = numeric(selected["Number of isolates"])
    if selected["count"].isna().any() or selected["count"].lt(0).any():
        raise ValueError("BEAM isolate count missing/negative")
    monthly = selected.groupby("period")["count"].sum().sort_index().to_frame("isolates")
    monthly["available_assumed"] = monthly.index + pd.Timedelta(days=CDC_LAG_DAYS)
    return monthly, len(selected)


def prepare_nors(frame):
    # These are counts of exported outbreak records, not individual cases or FSIS labels.
    selected = frame.loc[frame["State"].eq("Missouri") & frame["Primary Mode"].eq("Food") & frame["Etiology"].str.contains("Salmonella", case=False, na=False)].copy()
    periods = pd.to_datetime({"year": numeric(frame["Year"]), "month": numeric(frame["Month"]), "day": 1}) + pd.offsets.MonthEnd(0)
    selected_periods = pd.to_datetime({"year": numeric(selected["Year"]), "month": numeric(selected["Month"]), "day": 1}) + pd.offsets.MonthEnd(0)
    index = pd.date_range(periods.min(), periods.max(), freq="ME")
    records = selected_periods.value_counts().reindex(index, fill_value=0).sort_index()
    monthly = records.rolling(12, min_periods=12).sum().to_frame("records_trailing12months")
    monthly["available_assumed"] = monthly.index + pd.Timedelta(days=NORS_LAG_DAYS)
    return monthly, len(selected), str(periods.max().date())


def build_analytic(fsis, beam, nors, weather):
    """Construct only features assumed available by origin; retain missing coverage."""
    valid = fsis.loc[fsis["salmonella_sp_analysis"].isin(["Positive", "Negative"]) & fsis["salmonella_sp_analysis_canceled"].isin(["NULL", "", None])].dropna(subset=["collection_date"]).copy()
    valid["y"] = valid["salmonella_sp_analysis"].eq("Positive").astype(int)
    mo = valid.loc[valid["establishment_state"].eq("MO")].sort_values(["collection_date", "sample_number"]).copy()
    mo["outcome_date"] = pd.to_datetime(mo["collection_date"])
    mo["forecast_origin"] = mo["outcome_date"] - pd.Timedelta(days=HORIZON_DAYS)
    mo["label_available_assumed"] = mo["outcome_date"] + pd.Timedelta(days=FSIS_LAG_DAYS)
    daily = mo.groupby("outcome_date")["y"].agg(["sum", "count"]).sort_index()
    cumulative = daily.cumsum()
    cutoff = mo["forecast_origin"] - pd.Timedelta(days=FSIS_LAG_DAYS)
    prior = cumulative.reindex(cutoff, method="ffill").fillna(0)
    mo["fsis_mo_lag90_prevalence"] = (prior["sum"].to_numpy() + 1) / (prior["count"].to_numpy() + 2)
    mo["fsis_latest_allowed_collection_date"] = cutoff.to_numpy()
    mo["month_sin"] = np.sin(mo["forecast_origin"].dt.month * 2 * np.pi / 12)
    mo["month_cos"] = np.cos(mo["forecast_origin"].dt.month * 2 * np.pi / 12)
    b, _ = prepare_beam(beam)
    n, _, _ = prepare_nors(nors)
    for source, monthly, value_column, feature in (
        ("beam", b, "isolates", CDC_FEATURES[0]),
        ("nors", n, "records_trailing12months", NORS_FEATURES[0]),
    ):
        for col in (feature, source + "_observation_period_end", source + "_available_assumed"):
            mo[col] = np.nan if col == feature else pd.NaT
        for idx, row in mo.iterrows():
            available = monthly.loc[monthly["available_assumed"].le(row.forecast_origin)]
            if available.empty:
                continue
            last = available.iloc[-1]
            mo.loc[idx, feature] = np.log1p(last[value_column])
            mo.loc[idx, source + "_observation_period_end"] = available.index[-1]
            mo.loc[idx, source + "_available_assumed"] = last.available_assumed
    mo["noaa_window_end"] = mo["forecast_origin"] - pd.Timedelta(days=NOAA_LAG_DAYS)
    mo["noaa_window_start"] = mo["noaa_window_end"] - pd.Timedelta(days=27)
    matched = weather.reindex(mo["noaa_window_end"])
    for column in NOAA_FEATURES:
        mo[column] = matched[column].to_numpy()
    mo["coverage_eligible"] = mo[FEATURE_SETS["with_nors"]].notna().all(axis=1)
    mo["coverage_exclusion_reason"] = mo.apply(lambda r: "; ".join((["NOAA: fewer than 28 complete five-station quality-pass days"] if r[NOAA_FEATURES].isna().any() else []) + (["BEAM: no assumed-available monthly record"] if pd.isna(r[CDC_FEATURES[0]]) else []) + (["NORS: no assumed-available 12-month context"] if pd.isna(r[NORS_FEATURES[0]]) else [])), axis=1)
    columns = ["form_id", "sample_number", "establishment_id", "establishment_state", "source_file", "forecast_origin", "outcome_date", "label_available_assumed", "y", "fsis_latest_allowed_collection_date", "beam_observation_period_end", "beam_available_assumed", "nors_observation_period_end", "nors_available_assumed", "noaa_window_start", "noaa_window_end"] + FEATURE_SETS["with_nors"] + ["coverage_eligible", "coverage_exclusion_reason"]
    return mo[columns].reset_index(drop=True), valid


def chronological_split(analytic, validation_start="2026-01-01", validation_end="2026-07-01"):
    eligible = analytic.loc[analytic.coverage_eligible].copy()
    start, end = pd.Timestamp(validation_start), pd.Timestamp(validation_end)
    # Fitting occurs once, at validation start. No labels becoming available inside
    # the holdout enter fitting; historical feature updates use only their own origin.
    train = eligible.loc[eligible.label_available_assumed.lt(start)]
    test = eligible.loc[eligible.forecast_origin.ge(start) & eligible.forecast_origin.lt(end)]
    return train, test


def week_bootstrap_indices(dates, repetitions=400):
    weeks = pd.Series(dates).dt.to_period("W").astype(str).to_numpy()
    groups = [np.flatnonzero(weeks == week) for week in np.unique(weeks)]
    rng = np.random.default_rng(SEED)
    return [np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))]) for _ in range(repetitions)]


def wilson_interval(positives, total):
    z = 1.959963984540054
    p = positives / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = z * np.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return [float(center - half), float(center + half)]


def metrics(y, p, dates, repetitions=400):
    y, p = np.asarray(y, dtype=int), np.asarray(p, dtype=float)
    groups = week_bootstrap_indices(dates, repetitions)
    scores = [brier_score_loss(y[idx], p[idx]) for idx in groups]
    # Fixed bins include single-valued baseline predictions without artificial jitter.
    calibration = []
    bins = np.digitize(p, [0.05, 0.10, 0.15, 0.25, 0.50])
    for value in np.unique(bins):
        mask = bins == value
        count, positive = int(mask.sum()), int(y[mask].sum())
        calibration.append({"n": count, "mean_predicted": float(p[mask].mean()), "observed": float(y[mask].mean()), "wilson_95_ci": wilson_interval(positive, count)})
    flagged = p >= 0.10
    confusion = {"tp": int(((y == 1) & flagged).sum()), "fp": int(((y == 0) & flagged).sum()), "tn": int(((y == 0) & ~flagged).sum()), "fn": int(((y == 1) & ~flagged).sum())}
    return {"n": len(y), "positives": int(y.sum()), "prevalence": float(y.mean()), "brier": float(brier_score_loss(y, p)), "brier_week_block_bootstrap_95_ci": np.quantile(scores, [.025, .975]).tolist(), "pr_auc_average_precision": float(average_precision_score(y, p)) if len(np.unique(y)) == 2 else None, "roc_auc": float(roc_auc_score(y, p)) if len(np.unique(y)) == 2 else None, "mean_predicted": float(p.mean()), "calibration": calibration, "expected_calibration_error_fixed_bins": float(sum(b["n"] / len(y) * abs(b["mean_predicted"] - b["observed"]) for b in calibration)), "confusion_at_0_1": confusion, "review_fraction_at_0_1": float(flagged.mean()), "precision_at_0_1": confusion["tp"] / max(1, int(flagged.sum())), "recall_at_0_1": confusion["tp"] / max(1, int(y.sum()))}


def fit_comparisons(train, test, repetitions=400):
    if len(train) < 150 or train.y.sum() < 10 or train.y.nunique() < 2 or len(test) < 60 or test.y.nunique() < 2:
        raise ValueError("Insufficient chronological complete-case rows/classes for conditional study")
    y = test.y.to_numpy()
    prevalence = (int(train.y.sum()) + 1) / (len(train) + 2)
    predictions = {"baseline": np.full(len(test), prevalence)}
    models = {"baseline": {"features": [], "description": "Smoothed training-cohort prevalence, fixed at validation start", "metrics": metrics(y, predictions["baseline"], test.forecast_origin, repetitions)}}
    for name, features in FEATURE_SETS.items():
        model = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000, random_state=SEED))
        model.fit(train[features], train.y)
        p = model.predict_proba(test[features])[:, 1]
        predictions[name] = p
        coefficients = dict(zip(features, model[-1].coef_[0].tolist()))
        constants = [c for c in features if train[c].nunique() <= 1]
        models[name] = {"features": features, "metrics": metrics(y, p, test.forecast_origin, repetitions), "coefficients_standardized": coefficients, "constant_training_features": constants, "constant_validation_features": [c for c in features if test[c].nunique() <= 1], "training_feature_ranges": {c: {"min": float(train[c].min()), "max": float(train[c].max()), "distinct": int(train[c].nunique())} for c in features}, "validation_feature_ranges": {c: {"min": float(test[c].min()), "max": float(test[c].max()), "distinct": int(test[c].nunique())} for c in features}}
    comparisons = [("PulseNet-derived BEAM aggregate", "fsis", "fsis_cdc"), ("NOAA ambient context", "fsis_cdc", "core_integrated"), ("NORS exported outbreak-record context", "core_integrated", "with_nors"), ("All integrated domains", "baseline", "with_nors")]
    bootstrap = week_bootstrap_indices(test.forecast_origin, repetitions)
    ablations = []
    for domain, reference, augmented in comparisons:
        losses = (y - predictions[augmented]) ** 2 - (y - predictions[reference]) ** 2
        interval = np.quantile([losses[idx].mean() for idx in bootstrap], [.025, .975]).tolist()
        if interval[1] < 0:
            interpretation = "Lower Brier in this conditional holdout; prospective value unestablished"
        elif interval[0] > 0:
            interpretation = "Higher Brier in this conditional holdout; added source did not improve calibration/error"
        else:
            interpretation = "Paired interval includes zero; added value not established"
        ablations.append({"added_domain": domain, "reference_model": reference, "augmented_model": augmented, "brier_change": float(losses.mean()), "paired_week_block_bootstrap_95_ci": interval, "interpretation": interpretation})
    return models, predictions, ablations


def split_summary(train, test):
    return {"training_rows": len(train), "training_positives": int(train.y.sum()), "validation_rows": len(test), "validation_positives": int(test.y.sum()), "training_origin_start": str(train.forecast_origin.min().date()), "training_origin_end": str(train.forecast_origin.max().date()), "training_end": str(train.outcome_date.max().date()), "validation_start": str(test.forecast_origin.min().date()), "validation_end": str(test.forecast_origin.max().date()), "last_training_label_available_assumed": str(train.label_available_assumed.max().date()), "label_embargo_days": FSIS_LAG_DAYS, "horizon_days": HORIZON_DAYS}
