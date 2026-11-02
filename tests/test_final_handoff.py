"""Check scientific fidelity and the final guide's actual printable artifacts."""
import hashlib
import json
from pathlib import Path
import socket
import sqlite3
import struct
import zlib

import httpx
from pypdf import PdfReader
import pytest

from scripts.build_final_handoff import TITLE, build, content, number, read, readiness


def write_json(root, relative, value):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, allow_nan=False), encoding="utf-8")
    return path


def small_png():
    def chunk(kind, value):
        return struct.pack(">I", len(value)) + kind + value + struct.pack(">I", zlib.crc32(kind + value) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 4, 2, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress((b"\x00" + b"\x23\x55\x88" * 4) * 2)) + chunk(b"IEND", b""))


@pytest.fixture
def evidence(tmp_path):
    model = {"status": "conditional retrospective feasibility; prospective skill unestablished",
             "operational_activation_allowed": False,
             "primary_split": {"training_rows": 17, "validation_rows": 11, "validation_positives": 3,
                               "validation_start": "2026-01-05", "validation_end": "2026-06-23"},
             "models": {name: {"metrics": {"n": 11, "brier": 0.250007,
                       "pr_auc_average_precision": 0.33333, "roc_auc": 0.61234}}
                       for name in ["baseline", "fsis", "core_integrated", "with_nors"]},
             "ablations": [{"added_domain": "NORS sentinel ablation", "brier_change": 0.03125,
                            "interpretation": "Higher Brier in this conditional holdout; added value not established."}]}
    write_json(tmp_path, "reports/integrated_model_evaluation.json", model)
    write_json(tmp_path, "reports/decision_study.json", {
        "status": "computed simulation; not operational validation", "simulation": True,
        "requires_human_approval": True,
        "scenarios": [{"name": name, "policies": [{"policy_name": policy,
            "constraint_review": {"passed": True},
            "metrics": {"distributed_kg": 1234, "unmet_demand_kg": 56, "destinations_served": 3,
                        "projected_quality_budget_exposure_kg": 17}}
            for policy in ["Feasible order", "Eligible volume", "Balanced service"]]}
            for name in ["Sentinel scarcity", "Sentinel baseline", "Sentinel delay"]]})
    write_json(tmp_path, "reports/source_provenance.json", {"datasets": [{"dataset": "sentinel", "rows": 11}]})
    write_json(tmp_path, "reports/session_verification.json", {
        "finished_at": "2026-11-01T12:34:56Z", "all_passed": False,
        "checks": [{"name": "pytest", "passed": False, "tests_passed": 7, "log": "reports/checks/sentinel-failed.txt"}]})
    team = tmp_path / "docs/team_science_statement.md"
    team.parent.mkdir()
    team.write_text("# Team science statement\n\nNamed contributors remain pending.\n\n## Stakeholder input\n\nGuided choices followed actual user feedback.\n", encoding="utf-8")
    (tmp_path / "docs/challenge_tasks_source.md").write_text("# Five required tasks\n", encoding="utf-8")
    image = tmp_path / "reports/figures/one_health_system.png"
    image.parent.mkdir()
    image.write_bytes(small_png())
    for name in ['reports/data_dictionary.csv','data/processed/integrated_mo_analytic.csv',
                 'docs/one_health_system.md','docs/analytic_alignment.md']:
        path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text('Supported unit-test artifact\n',encoding='utf-8')
    sentinels = []
    for name in ["data/raw/source.csv", "data/aegis.sqlite", "data/aegis.sqlite-wal", "data/aegis.sqlite-shm"]:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(("untouched " + name).encode())
        sentinels.append(path)
    return tmp_path, model, sentinels


def test_final_pdf_preserves_measured_results_images_links_and_input_bytes(evidence, monkeypatch):
    root, _, sentinels = evidence
    protected = [*sentinels, *(root / "docs").glob("*.md"),
                 root / "reports/integrated_model_evaluation.json", root / "reports/decision_study.json",
                 root / "reports/source_provenance.json", root / "reports/session_verification.json",
                 root / "reports/figures/one_health_system.png"]
    before = {path: path.read_bytes() for path in protected}

    def forbidden(*args, **kwargs):
        raise AssertionError("Guide compilation must not access providers or an operator database")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(sqlite3, "connect", forbidden)
    compiled = {task["id"]: task["status"] for task in readiness(root)["tasks"]}
    assert compiled["Task 1"] == "Evidence compiled"
    assert "Research implemented" in compiled["Task 2"]
    assert "Policy study implemented" in compiled["Task 3"]
    result = build(root)
    assert all(path.read_bytes() == payload for path, payload in before.items())
    reader = PdfReader(root / result["pdf"])
    text = " ".join(" ".join(page.extract_text() for page in reader.pages).split())
    assert reader.metadata.title == TITLE
    assert "Final Submission Guide" in reader.pages[0].extract_text()
    assert result["pages"] == len(reader.pages)
    assert result["overflow_count"] == 0
    assert result["sha256"] == hashlib.sha256((root / result["pdf"]).read_bytes()).hexdigest()
    assert "0.250007" in text and "0.33333" in text and "0.61234" in text
    assert "0.031250" in text and "Higher Brier" in text
    assert "1,234" in text and "Sentinel scarcity" in text
    assert "pytest: failed" in text and "tests 7" in text
    assert "Kiro not used; requirement not met" in text
    assert "final team review pending" in text and "not consumer illness" in text
    assert sum(len(page.images) for page in reader.pages) >= 1
    assert len(reader.outline) == result["bookmarks"] == len(result["chapters"])
    assert not any(chapter["title"] == "Team science statement" for chapter in result["chapters"])
    for chapter, destination in zip(result["chapters"], reader.outline):
        assert reader.get_destination_page_number(destination) == chapter["page"] - 1
        # PDF extraction can insert kerning spaces ("T ask") and wrap headings.
        assert "".join(chapter["title"].split()) in "".join(reader.pages[chapter["page"] - 1].extract_text().split())
    assert sum(len(page["/Annots"]) if "/Annots" in page else 0 for page in reader.pages) == result["contents_links"]
    html = (root / result["html"]).read_text(encoding="utf-8")
    assert f"<title>{TITLE}</title>" in html
    assert 'src="data:image/png;base64,' in html and "<nav" in html
    assert "https://fonts." not in html
    assert result["human_submission_verified"] is False
    assert result["operational_database_accessed"] is False


def test_missing_and_failed_scientific_reports_do_not_claim_an_implemented_study(tmp_path):
    state = readiness(tmp_path)
    tasks = {task["id"]: task for task in state["tasks"]}
    assert tasks["Task 1"]["status"] == "Evidence incomplete"
    assert tasks["Task 2"]["status"].startswith("Model study missing")
    assert tasks["Task 3"]["status"].startswith("Policy study missing")
    assert "incomplete" in tasks["Task 5"]["status"]
    assert "not recorded training samples" in content(tmp_path, state)
    for path in ["reports/integrated_model_evaluation.json", "reports/decision_study.json"]:
        write_json(tmp_path, path, {"status": "failed", "error": "No supported scientific input"})
    write_json(tmp_path, "reports/source_provenance.json", {"datasets": [{"dataset": "sentinel"}]})
    failed = {task["id"]: task for task in readiness(tmp_path)["tasks"]}
    assert failed["Task 1"]["status"] == "Evidence incomplete"
    assert "implemented" not in failed["Task 2"]["status"].lower()
    assert "implemented" not in failed["Task 3"]["status"].lower()
    assert "incomplete" in failed["Task 5"]["status"].lower()


@pytest.mark.parametrize("payload", ["{broken", "[]", '{"brier":NaN}', '{"brier":Infinity}', '{"brier":1e309}'])
def test_corrupt_or_nonfinite_scientific_input_is_rejected(tmp_path, payload):
    path = tmp_path / "reports/integrated_model_evaluation.json"
    path.parent.mkdir()
    path.write_text(payload, encoding="utf-8")
    with pytest.raises((ValueError, json.JSONDecodeError)):
        read(tmp_path, "reports/integrated_model_evaluation.json")
    assert not (tmp_path / "reports/final_handoff_manifest.json").exists()


def test_metric_formatting_does_not_turn_missing_booleans_or_nonfinite_values_into_scores():
    assert all(number(value) == "not recorded" for value in [None, True, False, "0.9", float("nan"), float("inf")])
    assert number(0.125, 4) == "0.1250"
