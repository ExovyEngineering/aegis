"""Reproduction must execute isolated code and retain honest input provenance."""
import hashlib
import json
from pathlib import Path

import pytest

from scripts.notebook_support import NotebookRun


def put(root, relative, payload):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if not isinstance(payload, bytes):
        payload = json.dumps(payload).encode("utf-8")
    path.write_bytes(payload)
    return path


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


@pytest.fixture
def project(tmp_path):
    # Keep a space in the project path without exhausting Windows MAX_PATH
    # after pytest's own nested temporary root and the UUID analysis copy.
    root = tmp_path / "A B"
    root.mkdir()
    put(root, "backend/__init__.py", b"")
    put(root, "backend/paths.py", b"# immutable source snapshot\n")
    put(root, "docs/model_card.md", b"Published scientific limitations\r\n")
    put(root, "config/api_registry.yaml", b"provider: dated-fixture\n")
    put(root, "requirements-lock.txt", b"example==1.0\n")
    put(root, "requirements.txt", b"example\n")
    put(root, "data/processed/measured.csv", b"value\r\n1\r\n")
    put(root, "data/processed/fsis_poultry.parquet", b"test fixture, not parsed")
    put(root, "data/fixtures/source.json", {"provenance": "dated fixture"})
    put(root, "data/manifests/inventory.json", {"files": []})
    put(root, "reports/model_evaluation.json", {"baseline": {"brier": 0.125}, "sentinel": "published"})
    put(root, "reports/figures/evidence.svg", b"<svg xmlns='http://www.w3.org/2000/svg'/>")
    put(root, "data/external/noaa/station.response.json", b"[]\r\n")
    put(root, "data/external/noaa/station.metadata.json", {"sha256": digest(b"[]\r\n")})
    put(root, "reports/noaa_coverage.json", {"stations": [{"raw_response_path": "data/external/noaa/station.response.json", "sha256": digest(b"[]\r\n")}]})
    put(root, ".env", b"PRIVATE_TEST_TOKEN=do-not-copy\n")
    put(root, ".venv/private.txt", b"local runtime")
    put(root, ".tools/private.json", b"private tooling state")
    put(root, "data/aegis.sqlite", b"original operator bytes")
    put(root, "data/aegis.sqlite-wal", b"original uncheckpointed bytes")
    put(root, "data/processed/private.sqlite3-wal", b"private SQLite3 sidecar, never copy")
    put(root, "data/raw/unselected.csv", b"unselected original\r\n")
    put(root, "scripts/train_model.py", b'''import json, os, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
if "--fail" in sys.argv:
    print("meaningful scientific step failure", file=sys.stderr)
    raise SystemExit(9)
if "--network" in sys.argv:
    import socket
    socket.create_connection(("example.invalid", 443))
if "--direct-loopback" in sys.argv:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        connection.settimeout(0.1)
        connection.connect(("127.0.0.1", 65534))
asyncio_result = None
if "--asyncio" in sys.argv:
    import asyncio
    async def simple_work():
        await asyncio.sleep(0)
        return "completed without application networking"
    asyncio_result = asyncio.run(simple_work())
payload = {
    "script_root": str(root), "cwd": str(Path.cwd()),
    "database_path": os.environ.get("AEGIS_DB_PATH"),
    "rehearsal_id": os.environ.get("AEGIS_REHEARSAL_ID"),
    "offline": os.environ.get("AEGIS_OFFLINE_DEMO"),
    "raw_dir": os.environ.get("AEGIS_DATA_DIR"),
    "asyncio_result": asyncio_result,
}
(root / "reports/owned-result.json").write_text(json.dumps(payload), encoding="utf-8")
(root / "docs/model_card.md").write_text("recomputed in own project", encoding="utf-8")
print("recomputed scientific step")
''')
    raw = root / "original analysis inputs"
    raw.mkdir()
    sources = {"poultry.json": b"poultry raw\r\n", "atlas.xlsx": b"original workbook"}
    evidence = {}
    for name in ("beam_0", "beam_1", "beam_2", "beam_3", "beam_4", "nors_0", "establishments_0"):
        filename = name + ".csv"
        sources[filename] = (name + " original observations\r\n").encode()
        evidence[name] = {"status": "available", "input_files": [{"file": filename, "relative_path": filename,
            "path": str(raw / filename), "sha256": digest(sources[filename])}]}
    for name, payload in sources.items():
        put(raw, name, payload)
    put(raw, "unrelated-private.csv", b"not part of the published analysis")
    put(root, "data/processed/fsis_provenance.json", {"status": "complete", "sources": [
        {"source_file": "poultry.json", "path": str(raw / "poultry.json"), "sha256": digest(sources["poultry.json"])}]})
    put(root, "data/processed/evidence_manifest.json", {"datasets": evidence})
    put(root, "reports/usda_food_environment.json", {"status": "available", "source_file": {
        "filename": "atlas.xlsx", "sha256": digest(sources["atlas.xlsx"])}})
    return root, raw, sources


def test_runs_get_independent_copies_without_private_state_or_original_downloads(project):
    root, raw, _ = project
    first, second = NotebookRun(root, "first"), NotebookRun(root, "second")
    assert first.workspace != second.workspace
    assert first.workspace.is_relative_to(root / "reports/notebook_runs")
    assert first.workspace.name == second.workspace.name == "project"
    assert first.workspace.parts[-2].startswith("first-")
    for relative in (".env", ".venv", ".tools", "data/aegis.sqlite", "data/aegis.sqlite-wal",
                     "data/processed/private.sqlite3-wal", "data/raw", raw.name):
        assert not (first.workspace / relative).exists()
    for relative in ("data/processed/measured.csv", "data/external/noaa/station.response.json", "docs/model_card.md"):
        assert (first.workspace / relative).read_bytes() == (root / relative).read_bytes()
    (first.workspace / "data/processed/measured.csv").write_bytes(b"owned alteration")
    assert (second.workspace / "data/processed/measured.csv").read_bytes() == b"value\r\n1\r\n"
    assert (root / "data/processed/measured.csv").read_bytes() == b"value\r\n1\r\n"
    assert first.verify_preservation()["passed"] is True


def test_contained_scientific_script_really_executes_in_owned_project(project, monkeypatch):
    root, _, _ = project
    run = NotebookRun(root, "execute")
    monkeypatch.setenv("AEGIS_DB_PATH", str(root / "data/aegis.sqlite"))
    monkeypatch.setenv("AEGIS_REHEARSAL_ID", "inherited-owner-profile")
    monkeypatch.setenv("AEGIS_OFFLINE_DEMO", "0")
    monkeypatch.setenv("AEGIS_DATA_DIR", "/inherited/raw/source")
    record = run.run_script("scripts/train_model.py")
    actual = run.read_json("reports/owned-result.json")
    assert Path(actual["script_root"]) == Path(actual["cwd"]) == run.workspace
    assert actual["offline"] == "1" and actual["raw_dir"] is None
    assert actual["rehearsal_id"] != "inherited-owner-profile"
    assert Path(actual["database_path"]).is_relative_to(run.workspace)
    assert actual["rehearsal_id"] in Path(actual["database_path"]).name
    assert record["exit_code"] == 0
    assert run.baseline_json("reports/model_evaluation.json")["sentinel"] == "published"
    assert (root / "docs/model_card.md").read_bytes() == b"Published scientific limitations\r\n"
    result = run.finish()
    assert result["passed"] is True and result["commands"][0]["exit_code"] == 0
    assert result["preservation"]["operator_preserved"] is True
    assert json.loads((run.folder / "RUN_MANIFEST.json").read_text())["input_hashes"]["data/processed/measured.csv"]["sha256"] == digest(b"value\r\n1\r\n")


@pytest.mark.parametrize("relative", ["../scripts/train_model.py", "C:/outside.py", "/outside.py", "backend/paths.py"])
def test_script_paths_cannot_escape_owned_scripts(project, relative):
    root, _, _ = project
    run = NotebookRun(root, "boundary")
    with pytest.raises(ValueError):
        run.run_script(relative)
    assert run.commands == []


def test_json_readers_reject_outside_paths(project):
    root, _, _ = project
    outside = put(root.parent, "outside.json", {"secret": "must not read"})
    run = NotebookRun(root, "readers")
    with pytest.raises(ValueError):
        run.read_json(str(outside))
    with pytest.raises(ValueError):
        run.baseline_json(str(outside))


def test_failed_script_is_recorded_and_cannot_finish_as_passed(project):
    root, _, _ = project
    run = NotebookRun(root, "failure")
    with pytest.raises(RuntimeError, match="exit 9"):
        run.run_script("scripts/train_model.py", "--fail")
    assert run.commands[-1]["exit_code"] == 9
    assert "meaningful scientific step failure" in (run.folder / run.commands[-1]["log"]).read_text()
    with pytest.raises(RuntimeError):
        run.finish()
    assert json.loads((run.folder / "RUN_MANIFEST.json").read_text())["passed"] is False


def test_script_network_guard_fails_before_any_real_connection(project):
    root, _, _ = project
    run = NotebookRun(root, "network")
    with pytest.raises(RuntimeError):
        run.run_script("scripts/train_model.py", "--network")
    log = (run.folder / run.commands[-1]["log"]).read_text()
    assert "disables network access" in log
    assert run.verify_preservation()["passed"] is True


def test_asyncio_internal_wakeup_pair_still_works_without_application_networking(project):
    root, _, _ = project
    run = NotebookRun(root, "async")
    record = run.run_script("scripts/train_model.py", "--asyncio")
    assert record["exit_code"] == 0
    assert run.read_json("reports/owned-result.json")["asyncio_result"] == "completed without application networking"
    assert run.verify_preservation()["passed"] is True


def test_direct_tcp_loopback_outside_internal_socketpair_is_still_denied(project):
    root, _, _ = project
    run = NotebookRun(root, "tcp")
    with pytest.raises(RuntimeError):
        run.run_script("scripts/train_model.py", "--direct-loopback")
    record = run.commands[-1]
    assert record["exit_code"] != 0
    # A connection-refused error could mean an actual network attempt escaped;
    # require the reproduction guard's own denial instead.
    assert "disables network access" in (run.folder / record["log"]).read_text()
    assert run.verify_preservation()["passed"] is True


@pytest.mark.parametrize("changed", ["data/processed/measured.csv", "scripts/train_model.py"])
def test_changed_source_or_measured_input_is_reported_without_restore(project, changed):
    root, _, _ = project
    run = NotebookRun(root, "changed")
    (root / changed).write_bytes(b"concurrent external change")
    preserved = run.verify_preservation()
    assert preserved["passed"] is False and changed in preserved["changed_inputs"]
    assert preserved["operator_preserved"] is True
    with pytest.raises(RuntimeError):
        run.finish()
    assert (root / changed).read_bytes() == b"concurrent external change"


def test_changed_operator_wal_is_flagged_without_opening_or_restoring_it(project):
    root, _, _ = project
    run = NotebookRun(root, "operator")
    (root / "data/aegis.sqlite-wal").write_bytes(b"new external operator work")
    preserved = run.verify_preservation()
    assert preserved["passed"] is False and preserved["operator_preserved"] is False
    with pytest.raises(RuntimeError):
        run.finish()
    assert (root / "data/aegis.sqlite-wal").read_bytes() == b"new external operator work"


def mocked_raw_steps(monkeypatch, run):
    calls = []
    def execute(script, *args, **kwargs):
        calls.append((script, args))
        if script.endswith("ingest_fsis.py"):
            put(run.workspace, "data/processed/fsis_provenance.json", {"status": "complete", "fresh_test_output": True})
        elif script.endswith("ingest_evidence.py"):
            put(run.workspace, "data/processed/evidence_manifest.json", {"datasets": {"beam_1": {"status": "available"}}, "fresh_test_output": True})
        elif script.endswith("ingest_usda.py"):
            put(run.workspace, "reports/usda_food_environment.json", {"status": "available", "fresh_test_output": True})
        return {"script": script, "exit_code": 0}
    monkeypatch.setattr(run, "run_script", execute)
    return calls


def test_raw_mode_stages_only_exact_verified_sources_and_preserves_originals(project, monkeypatch):
    root, raw, sources = project
    run = NotebookRun(root, "raw")
    calls = mocked_raw_steps(monkeypatch, run)
    before = {path: path.read_bytes() for path in raw.rglob("*") if path.is_file()}
    result = run.ingest_raw(raw)
    assert result["status"] == "recomputed_from_verified_raw_copies"
    assert result["originals_staged"] == len(sources)
    staging = run.workspace / "raw_inputs"
    assert {path.name for path in staging.iterdir()} == set(sources)
    assert all((staging / name).read_bytes() == payload for name, payload in sources.items())
    assert all(path.read_bytes() == payload for path, payload in before.items())
    assert [script for script, _ in calls] == ["scripts/audit_data.py", "scripts/ingest_fsis.py", "scripts/ingest_evidence.py", "scripts/ingest_usda.py"]
    assert all(Path(args[-1]) == staging for _, args in calls)
    assert run.read_json("data/processed/evidence_manifest.json")["fresh_test_output"] is True
    assert run.verify_preservation()["raw_preserved"] is True


@pytest.mark.parametrize("damage", ["missing", "changed", "different_duplicate"])
def test_raw_source_missing_changed_or_ambiguous_bytes_stop_before_execution(project, monkeypatch, damage):
    root, raw, sources = project
    run = NotebookRun(root, "bad_raw")
    calls = mocked_raw_steps(monkeypatch, run)
    path = raw / "beam_1.csv"
    if damage == "missing":
        path.unlink()
    elif damage == "changed":
        path.write_bytes(b"a different surveillance snapshot")
    else:
        put(raw, "another/beam_1.csv", b"a different surveillance snapshot")
    before = {path: path.read_bytes() for path in raw.rglob("*") if path.is_file()}
    with pytest.raises((ValueError, FileNotFoundError)):
        run.ingest_raw(raw)
    assert calls == [] and not (run.workspace / "raw_inputs").exists()
    assert all(path.read_bytes() == payload for path, payload in before.items())


def test_post_ingestion_failure_cannot_be_promoted_from_retained_available_inputs(project, monkeypatch):
    root, raw, _ = project
    run = NotebookRun(root, "raw_status")
    calls = mocked_raw_steps(monkeypatch, run)
    previous = run.run_script
    def fail_evidence(script, *args, **kwargs):
        record = previous(script, *args, **kwargs)
        if script.endswith("ingest_evidence.py"):
            put(run.workspace, "data/processed/evidence_manifest.json", {"datasets": {"beam_1": {"status": "failed"}}})
        return record
    monkeypatch.setattr(run, "run_script", fail_evidence)
    with pytest.raises(ValueError, match="incomplete"):
        run.ingest_raw(raw)
    assert len(calls) == 4


def test_original_raw_change_after_staging_is_reported_and_not_restored(project, monkeypatch):
    root, raw, _ = project
    run = NotebookRun(root, "raw_change")
    mocked_raw_steps(monkeypatch, run)
    run.ingest_raw(raw)
    source = raw / "beam_1.csv"
    source.write_bytes(b"external revision after staging")
    preserved = run.verify_preservation()
    assert preserved["passed"] is False and preserved["raw_preserved"] is False
    assert str(source) in preserved["changed_raw_inputs"]
    with pytest.raises(RuntimeError):
        run.finish()
    assert source.read_bytes() == b"external revision after staging"
