"""Export an observed-schema dictionary and provenance without rewriting inputs.

All input tables are read and hashed from the same byte snapshot. Recorded raw
hashes are lineage claims from the ingestion reports, not fresh authentication.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
from pathlib import Path, PureWindowsPath

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

SPECS = {
    "fsis_poultry": ("USDA FSIS", "selected primary raw-poultry sample", "national; retained establishment state", "food/animal outcome; retrospective model target", "collection date; no result-availability date"),
    "beam_0": ("CDC BEAM", "pathogen x HHS region x month", "HHS region", "human surveillance context; no isolate/genomic linkage", "calendar year/month; export snapshot"),
    "beam_1": ("CDC BEAM", "state x month x source type/site x pathogen x serotype", "provider state codes; select MO explicitly", "PulseNet-derived aggregate human surveillance; source categories stay separate", "calendar year/month; no row publication date"),
    "beam_2": ("CDC BEAM", "food category x serotype x provider summary period", "provider national summary", "historical burden/trajectory context", "Year and Year_range have distinct meanings"),
    "beam_3": ("CDC BEAM", "food category x serotype x first-illness year x summary period", "provider national summary", "historical illnesses/outbreaks context", "Year_first_ill differs from report Year and Year_range"),
    "beam_4": ("CDC BEAM", "pathogen x serotype/species/subgroup x month", "provider national summary", "aggregate serotype context; not genomic clusters", "calendar year/month; export snapshot"),
    "nors_0": ("CDC NORS", "reported historical outbreak record", "provider jurisdiction; includes multi-state/territory categories", "human outbreak context; not FSIS-linked illness labels", "Year/Month; historical export through 2023"),
    "establishments_0": ("USDA FSIS MPI directory", "establishment directory record", "Missouri; official point coordinates", "additional directory context; no simulated supplier contract", "directory snapshot; grant_date is not a sampling date"),
    "usda_food_environment_missouri": ("USDA ERS Food Environment Atlas", "county/county-equivalent", "115 Missouri FIPS identities", "additional historical food-security context; not shipment need", "measure-specific 2019/2020/2023; July 2025 workbook release"),
    "noaa_station_days": ("NOAA NCEI", "station x provider daily reporting-period label", "five Missouri airport stations", "ambient historical weather; not cargo exposure", "2025-01-01 through 2026-06-30; local observation periods retained"),
    "integrated_mo_analytic": ("AEGIS derived retrospective study", "selected Missouri FSIS sample; origin seven days before collection", "Missouri aggregate; no establishment/station exposure assignment", "ecological historical feature alignment; not causal or prospective validation", "explicit origins and assumed feature lags; see integrated study"),
}

FIELDS = {
    "form_id": ("identifier", "FSIS primary-sample form identifier; retained as text."),
    "sample_number": ("identifier", "Provider sample identifier; not a lot identifier."),
    "establishment_id": ("identifier", "Provider establishment identity; no automatic contract/lot join."),
    "establishment_state": ("two-character provider state code", "State attached to the sampled establishment; not consumer illness geography."),
    "project_code": ("category", "FSIS sampling-project code; different projects can have different selection mechanisms."),
    "collection_date": ("calendar date", "Sample collection date; neither result publication nor public availability."),
    "salmonella_sp_analysis": ("category", "Primary Salmonella result; only Positive/Negative qualify as model outcomes."),
    "salmonella_sp_analysis_canceled": ("provider cancellation code", "Canceled/other outcomes are excluded; raw code remains preserved."),
    "source_file": ("filename", "Supplied source snapshot filename retained by the adapter."),
    "establishment_number": ("provider grant/establishment label", "Directory label can combine activity prefixes; not interchangeable with numeric establishment_id."),
    "establishment_name": ("directory organization label", "Provider listed establishment name; not a simulated supplier identity."),
    "duns_number": ("provider business identifier", "Directory business identifier where supplied; null is not a valid match."),
    "street": ("directory address text", "Provider street-address field; historical directory snapshot."),
    "city": ("directory place label", "Provider city field; no geocoding inferred."),
    "state": ("two-character directory state code", "Directory extract is restricted to Missouri by its original adapter."),
    "zip": ("postal code text", "Provider postal label retained as text; not a county cross-walk."),
    "phone": ("directory contact text", "Provider contact field; no outreach performed."),
    "activities": ("provider activity list", "Listed inspection/processing activities; not sample positivity or a real supply relationship."),
    "dbas": ("directory trade-name text", "Provider doing-business-as names where supplied."),
    "district": ("provider administrative code", "Directory administrative district; not geographic exposure area."),
    "circuit": ("provider administrative code", "Directory administrative circuit; not a delivery corridor."),
    "size": ("provider size category", "Directory size classification; not production volume or inventory capacity."),
    "county": ("provider county text", "Directory county label; validate FIPS before a geographic join."),
    "Year": ("calendar year/provider year label", "Provider Year field; commas remain in BEAM source strings. Summary-table Year can differ from illness year."),
    "Month": ("calendar month 1-12", "Provider month; no invented day or publication timestamp."),
    "Quarter": ("calendar quarter 1-4", "Provider quarter; retain separately from month."),
    "HHS_Region": ("provider HHS region label", "Regional aggregate; never treated as an establishment location."),
    "State": ("provider state/jurisdiction label", "Provider-specific code or name; source units are not silently cross-walked."),
    "Pathogen": ("category", "Provider pathogen category; Salmonella is selected explicitly for the added study."),
    "Source Type": ("category", "Human, Animal, Food and Environment remain different denominators."),
    "Source Site": ("provider category", "Source-site category; no inference of a physical shipment location."),
    "Serotype/Species": ("provider category", "Aggregate serotype/species label; not sequence similarity or a verified cluster."),
    "Serotype/Species/Subgroup": ("provider category", "Aggregate label; not an isolate sequence or genomic linkage."),
    "Number of isolates": ("reported isolate count", "Count in this source/stratum; isolate count is not a person or FSIS-test count."),
    "Number_of_isolates": ("reported isolate count", "Provider regional isolate count; formatting commas retained in source table."),
    "Outbreak associated isolates": ("reported isolate count", "Provider association field; not evidence linking any AEGIS simulated lot."),
    "New multistate outbreaks": ("reported outbreak count", "Provider stratum-specific count; repeated summary dimensions must not be blindly summed."),
    "New multistate outbreaks - US": ("reported national outbreak count", "National summary may repeat across source dimensions; not an additive row outcome."),
    "% Isolates with clinically important antimicrobial resistance": ("percent of provider-defined tested isolates", "Provider resistance summary; denominator is not all supplied rows."),
    "Number of sequenced isolates analyzed by NARMS": ("reported sequenced isolate count", "Provider NARMS analyzed-isolate denominator; individual sequences absent."),
    "Past_two_years_average": ("mean reported isolate count", "Provider comparator with its original denominator and formatting."),
    "Past two years average": ("mean reported isolate count", "Provider comparator, not an independent observation."),
    "% Change": ("percent", "Provider change relative to its comparator; missing/undefined stays missing."),
    "table_id": ("provider summary identifier", "Retains provider summary grouping; not an outbreak or sequence identifier."),
    "Food_category": ("provider food category", "Summary category, not a verified source of a sampled shipment."),
    "Serotype": ("provider category", "Serotype label alone cannot establish outbreak causation."),
    "Burden": ("provider ordinal category", "Provider burden classification, not an AEGIS-estimated probability."),
    "Trajectory": ("provider ordinal category", "Provider trajectory classification for its summary period."),
    "Year_range": ("provider period label", "Summary observation window; not a per-result availability date."),
    "No_of_illnesses": ("reported illnesses", "Historical provider illness summary; never an FSIS selected-sample label."),
    "Hospitalization(s)": ("reported hospitalizations", "Provider summary; null is not zero."),
    "Year_first_ill": ("calendar year label", "First-illness year for this summary; distinct from report Year."),
    "No_of_outbreaks": ("reported outbreaks", "Historical provider summary count; not a predicted outcome."),
    "Running_total_by_year_range": ("cumulative reported illnesses", "Provider cumulative value; not additive over constituent years."),
    "Primary Mode": ("provider category", "NORS transmission mode; the exploratory study explicitly selects Food."),
    "Etiology": ("provider category", "Reported etiology; string matching and exclusion policy belong in the study."),
    "Serotype or Genotype": ("provider category", "NORS label; no isolate-level relationship to FSIS inferred."),
    "Etiology Status": ("provider category", "Reported confirmation status; does not authenticate a shipment match."),
    "Setting": ("provider category", "Reported outbreak setting, not shipment destination."),
    "Illnesses": ("reported illnesses", "Original text preserved; may require validated numeric parsing for analysis."),
    "Hospitalizations": ("reported hospitalizations", "Reported count; null does not mean no hospitalization."),
    "Deaths": ("reported deaths", "Reported count; null does not mean zero deaths."),
    "Info On Hospitalizations": ("provider category", "Provider availability/context for hospitalizations."),
    "Info On Deaths": ("provider category", "Provider availability/context for deaths."),
    "Food Vehicle": ("provider category/text", "Reported food vehicle; no traceability match inferred."),
    "Food Contaminated Ingredient": ("provider category/text", "Reported ingredient; no establishment/lot match inferred."),
    "IFSAC Category": ("provider category", "Provider food attribution category; no silent pooling with FSIS projects."),
    "Water Exposure": ("provider category", "Historical water exposure context; not in selected Food-mode study."),
    "Water Type": ("provider category", "Historical water context; not a poultry exposure feature."),
    "Animal Type": ("provider category", "Historical animal context; not a verified source herd/flock."),
    "FIPS": ("five-character county FIPS", "County/county-equivalent key, retained as text including leading zeros."),
    "County": ("provider county label", "Names alone are not unique; FIPS distinguishes St. Louis county/city."),
    "county_display_name": ("derived display label", "County plus FIPS for unambiguous display; no location assignment."),
    "latitude": ("decimal degrees latitude", "Provider directory coordinate; no simulated-supplier relationship."),
    "longitude": ("decimal degrees longitude", "Provider directory coordinate; no simulated-supplier relationship."),
    "fips_code": ("provider county FIPS string", "Directory county identifier; cross-walk requires validation before any join."),
    "grant_date": ("provider date text", "Directory grant date; not source observation/publication time."),
    "DATE": ("provider daily reporting-period label", "NOAA day label; not normalized to local midnight or cargo time."),
    "STATION": ("NOAA station identifier", "Airport/weather station; not an establishment or truck sensor."),
    "TMAX": ("degrees C", "Daily maximum ambient temperature from explicit metric-unit request; inspect attributes."),
    "TMIN": ("degrees C", "Daily minimum ambient temperature from explicit metric-unit request; inspect attributes."),
    "PRCP": ("mm", "Daily precipitation from explicit metric-unit request; missing is not zero; trace attributes remain available."),
    "ELEVATION": ("metres", "Provider station elevation."),
    "LATITUDE": ("decimal degrees latitude", "Provider station coordinate."),
    "LONGITUDE": ("decimal degrees longitude", "Provider station coordinate."),
    "NAME": ("station label", "Provider station name."),
    "forecast_origin": ("calendar date", "Analytic origin = selected sample collection date minus seven days; not a real-time deployment."),
    "outcome_date": ("calendar date", "Selected Missouri primary sample collection date; the seven-day-ahead retrospective outcome time."),
    "label_available_assumed": ("assumed calendar date", "Outcome collection date + 90 days; label-availability assumption for chronological fitting, not measured publication time."),
    "y": ("binary 0/1", "1 = Positive, 0 = Negative in a noncanceled selected FSIS primary poultry sample; not consumer illness."),
    "fsis_latest_allowed_collection_date": ("calendar date", "Latest historical collection eligible for lagged feature = origin minus 90 days."),
    "beam_observation_period_end": ("calendar month-end", "Latest observed BEAM month whose assumed month-end + 90 days is at/before origin."),
    "beam_available_assumed": ("assumed calendar date", "BEAM selected month-end + 90 days; no actual publication date is supplied."),
    "nors_observation_period_end": ("calendar month-end", "Latest NORS period whose assumed month-end + 730 days is at/before origin; capped at source end 2023."),
    "nors_available_assumed": ("assumed calendar date", "NORS selected month-end + 730 days; no actual historical publication date is supplied."),
    "noaa_window_start": ("provider calendar date", "First of 28 inclusive daily reporting-period labels; window end minus 27 days."),
    "noaa_window_end": ("provider calendar date", "NOAA index window ends seven days before origin under an assumed availability buffer."),
    "fsis_mo_lag90_prevalence": ("smoothed selected-sample proportion", "(Earlier MO positive results + 1)/(earlier MO primary samples + 2), using only dates allowed at origin."),
    "month_sin": ("unitless [-1,1]", "sin(origin calendar month * 2*pi/12); known calendar covariate."),
    "month_cos": ("unitless [-1,1]", "cos(origin calendar month * 2*pi/12); known calendar covariate."),
    "beam_mo_human_log_isolates": ("natural log(1 + reported isolate count)", "MO Human Salmonella isolates in the latest assumed-available month, summed over unique source-site/serotype keys."),
    "noaa_mean_tmax_c_trailing28": ("degrees C", "28-day mean of the equal-weight five-airport daily maximum ambient-temperature index; all station-days must be numeric/quality-pass."),
    "noaa_mean_tmin_c_trailing28": ("degrees C", "28-day mean of the equal-weight five-airport daily minimum ambient-temperature index; all station-days must be numeric/quality-pass."),
    "noaa_mean_daily_prcp_mm_trailing28": ("mm/day", "28-day mean of the equal-weight five-airport daily precipitation index; no missing/flagged value is imputed."),
    "nors_mo_food_salmonella_log_records_trailing12months": ("natural log(1 + exported outbreak-record count)", "Trailing 12-month count of MO Food-mode NORS rows with Salmonella etiology; not illness count or proof of no outbreak in absent rows."),
    "coverage_eligible": ("boolean", "True only if all integrated study features are nonmissing; complete coverage is not scientific validity."),
    "coverage_exclusion_reason": ("reason text; empty when eligible", "Explicit missing-source/window reason; no excluded sample is silently dropped from this export."),
}


def snapshot(path: Path) -> tuple[bytes, str]:
    payload = path.read_bytes()
    return payload, hashlib.sha256(payload).hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def recorded_relative_parts(value: str) -> tuple[str, ...]:
    """Interpret saved relative paths independently of the producing OS."""
    if not isinstance(value, str) or not value:
        raise ValueError("Recorded input path must be a nonempty relative path")
    # Windows-written reports use backslashes; PureWindowsPath accepts both
    # separators without treating a backslash as a literal POSIX filename.
    relative = PureWindowsPath(value)
    if relative.anchor or ".." in relative.parts or not relative.parts:
        raise ValueError("Recorded input path must stay relative to the project")
    return relative.parts


def recorded_input_path(root: Path, value: str) -> Path:
    root = Path(root).resolve()
    path = root.joinpath(*recorded_relative_parts(value)).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Recorded input path resolves outside the project")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=ROOT)
    args = parser.parse_args()
    report_dir = args.output_root.resolve() / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    evidence = read_json(ROOT / "data/processed/evidence_manifest.json")
    fsis = read_json(ROOT / "data/processed/fsis_provenance.json")
    usda = read_json(ROOT / "reports/usda_food_environment.json")
    noaa = read_json(ROOT / "reports/noaa_coverage.json")
    usda_vars = {v["code"]: v for v in usda["variables"]}
    lineage, dictionary = [], []

    def register(name: str, frame: pd.DataFrame, path: str, actual_hash: str | None,
                 expected_hash: str | None, inputs: list[dict], status: str,
                 note: str = "") -> None:
        provider, grain, geography, role, timing = SPECS[name]
        integrity = "matched" if actual_hash and actual_hash == expected_hash else "not recorded"
        if expected_hash and actual_hash != expected_hash:
            raise ValueError(f"{name}: current bytes differ from recorded checksum")
        entry = {"dataset": name, "provider": provider, "grain": grain,
                 "geography": geography, "role": role, "time_semantics": timing,
                 "rows": len(frame), "columns": len(frame.columns), "path": path,
                 "sha256": actual_hash, "recorded_sha256": expected_hash,
                 "integrity": integrity, "recorded_ingestion_status": status,
                 "raw_lineage": inputs, "notes": note}
        lineage.append(entry)
        for column in frame:
            series = frame[column]
            units, definition = FIELDS.get(column, ("provider field (see source dictionary)",
                "Provider field preserved; no additional scientific interpretation assigned."))
            if column.endswith("_ATTRIBUTES"):
                units = "provider comma-delimited attribute string"
                definition = "Original NOAA measurement, quality, source and observation-time attributes; not dropped or imputed."
            elif column.endswith("sort_order"):
                units, definition = "display order", "Provider display order; not a quantitative risk measurement."
            elif name == "usda_food_environment_missouri" and column in usda_vars:
                v = usda_vars[column]
                units, definition = v["unit"], f"{v['definition']} Vintage {v['year']}; denominator: {v['denominator']}."
            dictionary.append({"dataset": name, "column": column, "dtype": str(series.dtype),
                "rows": len(frame), "null_count": int(series.isna().sum()),
                "non_null_count": int(series.notna().sum()), "units": units,
                "definition": definition, "grain": grain, "role": role})

    for name in SPECS:
        if name == "noaa_station_days":
            continue
        suffix = ".csv" if name == "integrated_mo_analytic" else ".parquet"
        path = ROOT / "data/processed" / (name + suffix)
        if not path.exists():
            if name == "integrated_mo_analytic":
                continue
            raise FileNotFoundError(path)
        payload, digest = snapshot(path)
        frame = pd.read_csv(BytesIO(payload), dtype={"form_id": "string", "sample_number": "string", "establishment_id": "string"}) if suffix == ".csv" else pd.read_parquet(BytesIO(payload))
        if name == "fsis_poultry":
            inputs = [{"filename": s["source_file"], "sha256": s["sha256"],
                       "metadata_creation_date": s.get("metadata_creation_date"),
                       "publication_date": None} for s in fsis["sources"]]
            expected, status = fsis["output_sha256"], fsis["status"]
        elif name == "usda_food_environment_missouri":
            inputs = [usda["source_file"]]
            expected = usda["processed_file"]["sha256"]
            status = usda["status"]
        elif name == "integrated_mo_analytic":
            study_bytes, _ = snapshot(ROOT / "reports/integrated_model_evaluation.json")
            study = json.loads(study_bytes)
            inputs = []
            for parent in study["input_provenance"]:
                for raw_source in parent["raw_source_provenance"]:
                    inputs.append({"source": parent["source"],
                        "filename": raw_source.get("source_file", raw_source.get("file")),
                        "sha256": raw_source["sha256"],
                        "metadata_creation_date": raw_source.get("metadata_creation_date"),
                        "actual_retrieved_at": parent.get("actual_retrieved_at"), "publication_date": None})
            for station in study["noaa_station_provenance"]:
                inputs.append({"source": "NOAA NCEI", "station_id": station["station_id"],
                    "sha256": station["sha256"], "actual_retrieved_at": station["retrieved_at"],
                    "source_url": station["source_url"], "publication_date": None})
            expected = study["artifact_sha256"]["analytic"]
            status = "derived exploratory study; not an ingestion status"
        else:
            recorded = evidence["datasets"][name]
            inputs = [{"filename": s["file"], "sha256": s["sha256"]} for s in recorded["input_files"]]
            expected, status = recorded["output_sha256"], recorded["status"]
        if status not in {"complete", "available", "derived exploratory study; not an ingestion status"}:
            raise ValueError(f"{name}: latest recorded source status {status!r} is unavailable")
        register(name, frame, path.relative_to(ROOT).as_posix(), digest, expected, inputs, status)

    station_frames, station_inputs = [], []
    for station in noaa["stations"]:
        path = recorded_input_path(ROOT, station["raw_response_path"])
        payload, digest = snapshot(path)
        if digest != station["sha256"]:
            raise ValueError(f"NOAA {station['station_id']}: raw bytes differ from coverage report")
        station_frames.append(pd.DataFrame(json.loads(payload)))
        station_inputs.append({"filename": path.relative_to(ROOT).as_posix(), "sha256": digest,
            "station_id": station["station_id"], "source_url": station["source_url"],
            "retrieved_at": station["retrieved_at"], "publication_date": None})
    register("noaa_station_days", pd.concat(station_frames, ignore_index=True),
             "data/external/noaa/ (five report-selected response snapshots)",
             None, None, station_inputs, noaa["status"],
             "Logical schema only: no replacement NOAA table is written. Returned station-days differ from per-metric coverage. Raw provider attributes remain strings.")

    pd.DataFrame(dictionary).to_csv(report_dir / "data_dictionary.csv", index=False, lineterminator="\n")
    flat = [{k: v for k, v in row.items() if k != "raw_lineage"} |
            {"raw_source_count": len(row["raw_lineage"]),
             "raw_source_hashes": " | ".join(str(s.get("sha256", "not recorded")) for s in row["raw_lineage"])}
            for row in lineage]
    pd.DataFrame(flat).to_csv(report_dir / "source_provenance.csv", index=False, lineterminator="\n")
    result = {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
        "command": "python scripts/build_data_dictionary.py", "datasets": lineage,
        "dictionary_rows": len(dictionary),
        "artifact_sha256": {"dictionary_csv": snapshot(report_dir / "data_dictionary.csv")[1],
                            "provenance_csv": snapshot(report_dir / "source_provenance.csv")[1],
                            "generator_script": snapshot(Path(__file__))[1]},
        "scope": "Observed-schema inventory of derived evidence plus five report-selected original NOAA responses. No operator database, original supplied table, or model is changed.",
        "interpretation": ["Current input hashes are measured; raw lineage hashes for supplied files are copied from ingestion reports and are not a new provider-authentication or completeness check.",
            "Null counts are exact for the local loaded columns, including provider strings that can encode unavailable data; a non-null text value is not necessarily a valid analytic value.",
            "PulseNet-derived BEAM aggregates, NORS outbreaks and FSIS selected samples retain different units and labels; ecological alignment is not outbreak attribution.",
            "Directory coordinates do not identify fictional supply contracts. USDA county context does not identify actual recipient demand or map fictional destinations to counties.",
            "Publication timing, establishment exposure linkage, genomic linkage and prospective model validity remain unresolved."]}
    (report_dir / "source_provenance.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"datasets": len(lineage), "dictionary_rows": len(dictionary),
                      "output_root": str(report_dir)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
