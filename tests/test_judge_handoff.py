"""Judge handoff copies verified evidence without network or operator mutation."""
import hashlib
import json
from pathlib import Path
import re
import socket
import sqlite3
import zipfile

import httpx
import pytest

from scripts import build_judge_handoff as handoff


ROOT = Path(__file__).resolve().parents[1]


def encoded(value):
    return json.dumps(value, sort_keys=True).encode("utf-8")


def write_archive(path, entries):
    """Use a valid trusted application-package contract, not an executable app."""
    manifest = {"draft": True, "files": [
        {"path": name, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
        for name, payload in sorted(entries.items())
    ]}
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, payload in entries.items():
            archive.writestr(name, payload)
        archive.writestr("PACKAGE_MANIFEST.json", encoded(manifest))


@pytest.fixture
def supplied(tmp_path):
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "reports").mkdir()
    entries = {name: ("observed source bytes: " + name + "\r\n").encode("utf-8")
               for name in handoff.GUIDES}
    entries.update({name: encoded({"sentinel": name}) for name in handoff.EVIDENCE})
    entries.update({
        "Setup-Judges-Windows.cmd": b"@echo off\r\nrem fixture, never executed\r\n",
        "Start-Judges-Windows.cmd": b"@echo off\r\nrem fixture, never executed\r\n",
        "scripts/judge_demo.py": b"raise RuntimeError('fixture must never be executed')\n",
        "docs/judge_start_here.html": (ROOT / "docs/judge_start_here.html").read_bytes(),
        "docs/judge_quick_start.md": (ROOT / "docs/judge_quick_start.md").read_bytes(),
        "docs/judge_walkthrough.md": (ROOT / "docs/judge_walkthrough.md").read_bytes(),
        "docs/folder_map.md": b"# Source folder map\r\n",
        "config/api_registry.csv": b"id,status\r\nfixture,separately dated\r\n",
        "reports/session_verification.json": encoded({
            "finished_at": "2026-11-02T10:01:02Z",
            "checks": [{"name": "pytest", "passed": True, "tests_passed": 13},
                       {"name": "frontend_build", "passed": False, "tests_passed": None}],
        }),
        "reports/browser_qa/final_submission/results.json": encoded({
            "finished_at": "2026-11-01T09:08:07Z",
            "checks": [{"passed": True}, {"passed": False}, {}],
            "scope": "sentinel <must stay text> & separate",
        }),
    })
    archive = tmp_path / "artifacts/application.zip"
    write_archive(archive, entries)
    verification = {"passed": True, "archive_sha256": handoff.sha256(archive),
                    "finished_at": "2026-11-02T11:02:03Z", "checks": ["fixture integrity"],
                    "fresh_python_environment": False}
    (tmp_path / "reports/package_verification.json").write_bytes(encoded(verification))
    for name in ("data/aegis.sqlite", "data/aegis.sqlite-wal", "supplied-original.csv"):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(("private unmodified sentinel " + name).encode("utf-8"))
    protected = {path: path.read_bytes() for path in [
        archive, tmp_path / "reports/package_verification.json", tmp_path / "data/aegis.sqlite",
        tmp_path / "data/aegis.sqlite-wal", tmp_path / "supplied-original.csv",
    ]}
    return tmp_path, archive, entries, protected


@pytest.fixture
def no_external_access(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Packaging must not access providers, DNS or SQLite")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(sqlite3, "connect", forbidden)


def test_handoff_has_working_numbered_layout_and_exact_evidence_bytes(supplied, no_external_access):
    root, archive, entries, protected = supplied
    result = handoff.build(root, archive)
    folder = root / result["folder"]
    assert {path.name for path in folder.iterdir()} == {
        "00_START_HERE.html", "00_START_HERE.txt", "01_Guides", "02_Application",
        "03_Verification", "JUDGE_HANDOFF_MANIFEST.json",
    }
    for source, destination in handoff.GUIDES.items():
        assert (folder / "01_Guides" / destination).read_bytes() == entries[source]
    for source in ("docs/judge_quick_start.md", "docs/judge_walkthrough.md"):
        copied = folder / "01_Guides" / handoff.GUIDES[source]
        for target in re.findall(r"\]\(([^)]+)\)", copied.read_text(encoding="utf-8")):
            if not target.startswith(("http:", "https:", "#")):
                assert (copied.parent / target).is_file(), target
    for source in handoff.EVIDENCE:
        name = "browser_results.json" if source.endswith("/results.json") else Path(source).name
        assert (folder / "03_Verification" / name).read_bytes() == entries[source]
    assert (folder / "03_Verification/package_verification.json").read_bytes() == protected[root / "reports/package_verification.json"]
    assert (folder / "03_Verification/api_registry.csv").read_bytes() == entries["config/api_registry.csv"]
    assert (folder / "00_START_HERE.txt").read_bytes() == entries["docs/judge_quick_start.md"]
    assert all((folder / "02_Application" / name).read_bytes() == payload for name, payload in entries.items())
    document = (folder / "00_START_HERE.html").read_text(encoding="utf-8")
    assert "{{VERIFICATION}}" not in document
    assert "&lt;must stay text&gt; &amp; separate" in document
    assert handoff.verify_links(folder) == result["start_page_local_links_checked"] > 0
    summary = (folder / "03_Verification/TEST_RESULTS.txt").read_text(encoding="utf-8")
    assert "pytest: PASS (13 tests)" in summary
    assert "frontend_build: FAIL / not verified" in summary
    assert "1/3 checks passed" in summary
    assert "Fresh Python environment tested by this offline check: False" in summary
    assert "2026-11-02T10:01:02Z" in summary and "2026-11-01T09:08:07Z" in summary
    assert "Kiro non-use" in summary
    verified = handoff.verify_judge_archive(root / result["archive"])
    assert verified["passed"] and verified["archive_sha256"] == result["sha256"]
    checksum = root / "artifacts/AEGIS-Judges.zip.sha256"
    assert checksum.read_text().split()[0] == result["sha256"]
    assert result["raw_files_moved"] is False and result["operator_database_opened"] is False
    assert all(path.read_bytes() == payload for path, payload in protected.items())


def test_repeat_build_preserves_the_previous_judge_folder(supplied, no_external_access):
    root, archive, _, protected = supplied
    first = handoff.build(root, archive)
    folder = root / first["folder"]
    manifest = (folder / "JUDGE_HANDOFF_MANIFEST.json").read_bytes()
    (folder / "judge-notes.txt").write_bytes(b"reviewer notes must survive replacement\r\n")
    second = handoff.build(root, archive)
    history = list((root / "artifacts/judge-history").iterdir())
    assert len(history) == 1
    assert (history[0] / "JUDGE_HANDOFF_MANIFEST.json").read_bytes() == manifest
    assert (history[0] / "judge-notes.txt").read_bytes() == b"reviewer notes must survive replacement\r\n"
    assert not (root / second["folder"] / "judge-notes.txt").exists()
    assert handoff.verify_judge_archive(root / second["archive"])["passed"]
    assert all(path.read_bytes() == payload for path, payload in protected.items())


@pytest.mark.parametrize("tamper", ["payload", "missing_member", "unlisted_member"])
def test_judge_archive_rejects_changed_bytes_or_membership(supplied, tamper):
    root, archive, _, _ = supplied
    result = handoff.build(root, archive)
    with zipfile.ZipFile(root / result["archive"]) as original:
        members = {name: original.read(name) for name in original.namelist()}
    target = "AEGIS-Judges/01_Guides/Final_Submission_Guide.pdf"
    if tamper == "payload":
        body = members[target]
        members[target] = bytes([body[0] ^ 1]) + body[1:]
    elif tamper == "missing_member":
        del members[target]
    else:
        members["AEGIS-Judges/unlisted.txt"] = b"not in the manifest"
    damaged = root / "artifacts/tampered.zip"
    with zipfile.ZipFile(damaged, "w") as changed:
        for name, payload in members.items():
            changed.writestr(name, payload)
    with pytest.raises(ValueError, match="checksum mismatch|membership mismatch"):
        handoff.verify_judge_archive(damaged)


@pytest.mark.parametrize("verification", [
    {"passed": False}, {"passed": True, "archive_sha256": "0" * 64},
    {"passed": "true"}, {"passed": True},
])
def test_failed_or_mismatched_application_verification_cannot_publish(supplied, verification):
    root, archive, _, _ = supplied
    (root / "reports/package_verification.json").write_bytes(encoded(verification))
    before = {path.name for path in (root / "artifacts").iterdir()}
    with pytest.raises(ValueError, match="Verify this exact application archive"):
        handoff.build(root, archive)
    assert {path.name for path in (root / "artifacts").iterdir()} == before
    assert not (root / "reports/judge_handoff.json").exists()


def test_source_archive_must_be_inside_the_project_artifacts_directory(supplied):
    root, _, _, protected = supplied
    outside = root / "outside-application.zip"
    outside.write_bytes(b"private source must not be read")
    with pytest.raises(ValueError, match="inside the project artifacts"):
        handoff.build(root, outside)
    assert outside.read_bytes() == b"private source must not be read"
    assert not (root / "artifacts/AEGIS-Judges").exists()
    assert all(path.read_bytes() == payload for path, payload in protected.items())


def test_symlinked_artifacts_directory_cannot_publish_outside_the_project(tmp_path):
    root, external = tmp_path / "project", tmp_path / "external"
    root.mkdir()
    external.mkdir()
    sentinel = external / "private.txt"
    sentinel.write_bytes(b"outside project")
    try:
        (root / "artifacts").symlink_to(external, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"This platform cannot create the directory symlink: {error}")
    with pytest.raises(ValueError, match="Artifacts directory must be inside"):
        handoff.build(root, external / "archive.zip")
    assert list(external.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == b"outside project"


def test_traversal_in_application_archive_cannot_escape_the_staging_folder(supplied):
    root, archive, entries, protected = supplied
    write_archive(archive, entries | {"../escape.txt": b"must not escape"})
    verification = {"passed": True, "archive_sha256": handoff.sha256(archive)}
    (root / "reports/package_verification.json").write_bytes(encoded(verification))
    with pytest.raises(ValueError, match="Unsafe archive path"):
        handoff.build(root, archive)
    assert not list(root.rglob("escape.txt"))
    assert not (root / "artifacts/AEGIS-Judges.zip").exists()
    for path in (root / "data/aegis.sqlite", root / "data/aegis.sqlite-wal", root / "supplied-original.csv"):
        assert path.read_bytes() == protected[path]


@pytest.mark.parametrize("target", ["missing.pdf", "../outside.txt"])
def test_start_page_rejects_broken_or_escaping_local_links(tmp_path, target):
    folder = tmp_path / "judge-folder"
    folder.mkdir()
    (tmp_path / "outside.txt").write_bytes(b"exists but outside the handoff")
    (folder / "00_START_HERE.html").write_text(f'<a href="{target}">Review</a>', encoding="utf-8")
    with pytest.raises(ValueError, match="Broken or escaping Start Here link"):
        handoff.verify_links(folder)
