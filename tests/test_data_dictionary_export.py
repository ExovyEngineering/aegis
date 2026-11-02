"""Scientific export checks use existing evidence and never write an input table."""
import importlib.util
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_dictionary_preserves_missingness_and_distinct_outcomes(tmp_path):
    result = subprocess.run([sys.executable, str(ROOT / "scripts/build_data_dictionary.py"),
                             "--output-root", str(tmp_path)], capture_output=True, text=True)
    assert result.returncode == 0, f"Dictionary export failed:\n{result.stdout}\n{result.stderr}"
    dictionary = pd.read_csv(tmp_path / "reports/data_dictionary.csv")
    provenance = json.loads((tmp_path / "reports/source_provenance.json").read_text(encoding="utf-8"))
    usda_report = json.loads((ROOT / "reports/usda_food_environment.json").read_text(encoding="utf-8"))
    for variable in ["GROC20", "GROCPTH20"]:
        entry = dictionary.loc[(dictionary.dataset == "usda_food_environment_missouri") &
                               (dictionary.column == variable)].iloc[0]
        assert entry.null_count == pd.read_parquet(ROOT / "data/processed/usda_food_environment_missouri.parquet")[variable].isna().sum()
        assert "denominator:" in entry.definition
    noaa = dictionary.loc[(dictionary.dataset == "noaa_station_days") & (dictionary.column == "PRCP")].iloc[0]
    assert "missing is not zero" in noaa.definition
    assert dictionary.loc[dictionary.column == "TMAX_ATTRIBUTES", "definition"].str.contains("quality").all()
    fsis = next(d for d in provenance["datasets"] if d["dataset"] == "fsis_poultry")
    assert fsis["integrity"] == "matched"
    assert all(s["publication_date"] is None for s in fsis["raw_lineage"])
    assert usda_report["source_file"]["sha256"] == next(d for d in provenance["datasets"] if d["dataset"] == "usda_food_environment_missouri")["raw_lineage"][0]["sha256"]


def test_dictionary_rejects_changed_processed_bytes_before_publication(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("aegis_dictionary_export", ROOT / "scripts/build_data_dictionary.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original_reader = module.read_json

    def changed_manifest(path):
        data = original_reader(path)
        if path.name == "fsis_provenance.json":
            data["output_sha256"] = "0" * 64
        return data

    monkeypatch.setattr(module, "read_json", changed_manifest)
    monkeypatch.setattr(sys, "argv", ["build_data_dictionary.py", "--output-root", str(tmp_path)])
    with pytest.raises(ValueError, match="current bytes differ"):
        module.main()
    assert not (tmp_path / "reports/data_dictionary.csv").exists()


@pytest.mark.parametrize("recorded", [
    "data/external/noaa/station.response.json",
    r"data\external\noaa\station.response.json",
])
def test_recorded_snapshot_paths_are_portable_and_preserve_bytes(tmp_path, recorded):
    spec = importlib.util.spec_from_file_location("aegis_dictionary_paths", ROOT / "scripts/build_data_dictionary.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    snapshot = tmp_path / "data/external/noaa/station.response.json"
    snapshot.parent.mkdir(parents=True)
    raw = b'[{"DATE":"2026-01-01","PRCP":null}]\r\n'
    snapshot.write_bytes(raw)
    # Exercise POSIX semantics on Windows too, where the original bug was hidden.
    parts = module.recorded_relative_parts(recorded)
    assert PurePosixPath("/review").joinpath(*parts) == PurePosixPath("/review/data/external/noaa/station.response.json")
    resolved = module.recorded_input_path(tmp_path, recorded)
    assert resolved == snapshot.resolve()
    payload, digest = module.snapshot(resolved)
    assert payload == raw and digest == hashlib.sha256(raw).hexdigest()
    assert snapshot.read_bytes() == raw


@pytest.mark.parametrize("recorded", [
    "../private.json", r"..\private.json", "data/../private.json",
    "/private.json", r"C:\private.json", r"C:private.json",
    r"\\server\share\private.json", "",
])
def test_recorded_snapshot_paths_cannot_escape_the_project(tmp_path, recorded):
    spec = importlib.util.spec_from_file_location("aegis_dictionary_boundary", ROOT / "scripts/build_data_dictionary.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with pytest.raises(ValueError, match="relative"):
        module.recorded_input_path(tmp_path, recorded)
