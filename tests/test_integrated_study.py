"""Scientific integrity checks for the separate conditional integrated study."""
import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from backend.integrated_study import (
    CITIES, CDC_FEATURES, FEATURE_SETS, NOAA_FEATURES, build_analytic,
    chronological_split, load_weather, metrics, prepare_beam, prepare_nors,
)
from scripts.train_integrated_study import input_provenance


def inputs():
    fsis = pd.DataFrame({
        "form_id": [str(i) for i in range(6)], "sample_number": range(6),
        "establishment_id": [123] * 6, "establishment_state": ["MO"] * 5 + ["CA"],
        "source_file": ["preserved.json"] * 6,
        "collection_date": pd.to_datetime(["2024-06-01", "2024-09-01", "2024-12-01", "2025-03-01", "2025-06-01", "2025-06-01"]),
        "salmonella_sp_analysis": ["Positive", "Negative", "Negative", "Positive", "Negative", "Positive"],
        "salmonella_sp_analysis_canceled": ["NULL"] * 6,
    })
    beam = pd.DataFrame([{"Year": str(y), "Month": m, "State": "MO", "Pathogen": "Salmonella", "Source Type": "Human", "Source Site": "Stool", "Serotype/Species": "Enteritidis", "Number of isolates": 100 + m} for y in (2023, 2024, 2025) for m in range(1, 13)])
    nors = pd.DataFrame({"Year": [2021, 2023, 2023], "Month": [1, 1, 12], "State": ["Missouri", "Missouri", "California"], "Primary Mode": ["Food", "Food", "Water"], "Etiology": ["Salmonella enterica", "Salmonella enterica", "Copper"]})
    weather = pd.DataFrame({column: np.ones(1100) for column in NOAA_FEATURES}, index=pd.date_range("2023-01-01", periods=1100))
    return fsis, beam, nors, weather


def test_future_fsis_labels_and_unavailable_cdc_records_cannot_change_earlier_features():
    fsis, beam, nors, weather = inputs()
    original, _ = build_analytic(fsis, beam, nors, weather)
    assert original.establishment_state.unique().tolist() == ["MO"]
    assert len(original) == 5
    target = original.iloc[-1]
    assert target.forecast_origin == pd.Timestamp("2025-05-25")
    assert target.outcome_date - target.forecast_origin == pd.Timedelta(days=7)
    assert target.fsis_latest_allowed_collection_date == pd.Timestamp("2025-02-24")
    assert target.beam_observation_period_end == pd.Timestamp("2025-01-31")
    assert target.beam_available_assumed <= target.forecast_origin
    assert target.noaa_window_end == target.forecast_origin - pd.Timedelta(days=7)
    assert target.noaa_window_end - target.noaa_window_start == pd.Timedelta(days=27)
    # Positive/negative perturbations after the allowable FSIS date cannot enter history.
    fsis.loc[fsis.collection_date.ge("2025-03-01"), "salmonella_sp_analysis"] = "Negative"
    beam.loc[(beam.Year == "2025") & beam.Month.ge(2), "Number of isolates"] = 999999
    perturbed, _ = build_analytic(fsis, beam, nors, weather)
    pd.testing.assert_frame_equal(original[FEATURE_SETS["with_nors"]], perturbed[FEATURE_SETS["with_nors"]])
    # A genuinely assumed-available earlier record does affect the CDC feature.
    beam.loc[(beam.Year == "2025") & beam.Month.eq(1), "Number of isolates"] = 500
    changed, _ = build_analytic(fsis, beam, nors, weather)
    assert changed.iloc[-1][CDC_FEATURES[0]] != target[CDC_FEATURES[0]]


def test_snapshot_end_and_duplicate_source_keys_are_not_silently_extrapolated_or_pooled():
    _, beam, nors, _ = inputs()
    with pytest.raises(ValueError, match="Duplicate BEAM"):
        prepare_beam(pd.concat([beam, beam.iloc[[0]]], ignore_index=True))
    monthly, count, end = prepare_nors(nors)
    assert count == 2
    assert end == "2023-12-31"
    assert monthly.index.max() == pd.Timestamp("2023-12-31")
    # It does not create zero-record months in2024 merely because forecast origins go later.
    assert not (monthly.index.year > 2023).any()


def test_missing_weather_remains_excluded_and_raw_inputs_are_preserved():
    fsis, beam, nors, weather = inputs()
    originals = [frame.copy(deep=True) for frame in (fsis, beam, nors, weather)]
    weather.loc[pd.Timestamp("2025-05-18"), NOAA_FEATURES[2]] = np.nan
    originals[-1] = weather.copy(deep=True)
    analytic, _ = build_analytic(fsis, beam, nors, weather)
    assert not analytic.iloc[-1].coverage_eligible
    assert "NOAA" in analytic.iloc[-1].coverage_exclusion_reason
    assert pd.isna(analytic.iloc[-1][NOAA_FEATURES[2]])
    for observed, preserved in zip((fsis, beam, nors, weather), originals):
        pd.testing.assert_frame_equal(observed, preserved)


def test_label_embargo_uses_result_availability_and_origin_not_outcome_date():
    frame = pd.DataFrame({"coverage_eligible": [True] * 4, "forecast_origin": pd.to_datetime(["2025-08-01", "2025-10-01", "2025-12-28", "2026-01-01"]), "label_available_assumed": pd.to_datetime(["2025-11-06", "2026-01-06", "2026-04-04", "2026-04-08"])})
    train, test = chronological_split(frame)
    assert train.index.tolist() == [0]
    assert test.index.tolist() == [3]
    assert (train.label_available_assumed < test.forecast_origin.min()).all()


def test_noaa_quality_failures_are_missing_not_zero_and_checksums_enforced(tmp_path):
    folder = tmp_path / "data/external/noaa"
    folder.mkdir(parents=True)
    paths = []
    for i, station in enumerate(CITIES):
        rows = []
        for day in pd.date_range("2025-01-01", periods=35):
            row = {"DATE": str(day.date()), "STATION": station["station_id"], "LATITUDE": station["coordinates"][1], "LONGITUDE": station["coordinates"][0], "TMAX": 20, "TMIN": 10, "PRCP": 0, "TMAX_ATTRIBUTES": ",,S,", "TMIN_ATTRIBUTES": ",,S,", "PRCP_ATTRIBUTES": ",,S,"}
            if i == 0 and day == pd.Timestamp("2025-01-30"):
                row["PRCP_ATTRIBUTES"] = ",X,S,"
            rows.append(row)
        body = json.dumps(rows).encode()
        stem = f"{station['station_id']}_2025-01-01_2026-06-30"
        raw = folder / (stem + ".response.json")
        raw.write_bytes(body)
        (folder / (stem + ".metadata.json")).write_text(json.dumps({"sha256": hashlib.sha256(body).hexdigest(), "retrieved_at": "2026-10-26T00:00:00Z", "source_url": "https://www.ncei.noaa.gov/test"}))
        paths.append(raw)
    trailing, _, days, daily = load_weather(tmp_path)
    assert days == 175
    assert daily.loc["2025-01-29", "PRCP"] == 0
    assert pd.isna(daily.loc["2025-01-30", "PRCP"])
    assert pd.isna(trailing.loc["2025-02-04", NOAA_FEATURES[2]])
    assert trailing.loc["2025-01-28", NOAA_FEATURES[2]] == 0
    paths[0].write_bytes(b"[]")
    with pytest.raises(ValueError, match="checksum mismatch"):
        load_weather(tmp_path)


def test_metrics_include_calibration_and_interpretable_review_errors_for_single_class():
    result = metrics(np.zeros(14), np.full(14, .2), pd.date_range("2026-01-01", periods=14), repetitions=20)
    assert result["roc_auc"] is None
    assert result["pr_auc_average_precision"] is None
    assert result["brier"] == pytest.approx(.04)
    assert result["confusion_at_0_1"] == {"tp": 0, "fp": 14, "tn": 0, "fn": 0}
    assert result["calibration"][0]["observed"] == 0
    assert result["calibration"][0]["wilson_95_ci"][1] > 0


def test_processed_source_changes_require_reingestion_and_never_invent_retrieval_time(tmp_path):
    folder = tmp_path / "data/processed"
    folder.mkdir(parents=True)
    digest = hashlib.sha256(b"test input bytes").hexdigest()
    for name in ("fsis_poultry.parquet", "beam_1.parquet", "nors_0.parquet"):
        (folder / name).write_bytes(b"test input bytes")
    (folder / "fsis_provenance.json").write_text(json.dumps({"output_sha256": digest, "sources": [{"metadata_creation_date": "October 09, 2026"}]}))
    (folder / "evidence_manifest.json").write_text(json.dumps({"generated_at": "2026-10-27T00:00:00Z", "datasets": {key: {"output_sha256": digest, "input_files": []} for key in ("beam_1", "nors_0")}}))
    provenance = input_provenance(tmp_path)
    assert all(item["actual_retrieved_at"] is None for item in provenance)
    assert all(item["historical_snapshot_vintage_verified"] is False for item in provenance)
    assert provenance[0]["raw_source_provenance"][0]["metadata_creation_date"] == "October 09, 2026"
    (folder / "beam_1.parquet").write_bytes(b"changed without reingestion")
    with pytest.raises(ValueError, match="Processed study input checksum mismatch"):
        input_provenance(tmp_path)
