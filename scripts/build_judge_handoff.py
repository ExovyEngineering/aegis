"""Organize a verified AEGIS application archive into one judge handoff.

Copies allowlisted material; never moves supplied data or opens operator state.
Prior judge folders are retained under artifacts/judge-history before replacement.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import sys
from urllib.parse import unquote, urlsplit
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_package import safe_member, validate_and_extract
from scripts.execute_notebooks import NOTEBOOKS, code_digest

NAME = "AEGIS-Judges"
GUIDES = {
    "reports/final_submission_guide.pdf": "Final_Submission_Guide.pdf",
    "reports/team_science_statement.pdf": "Team_Science_Statement.pdf",
    "reports/aegis_master_guide.pdf": "Full_User_Handbook.pdf",
    "docs/judge_quick_start.md": "judge_quick_start.md",
    "docs/judge_walkthrough.md": "judge_walkthrough.md",
}
EVIDENCE = (
    "reports/session_verification.json", "reports/final_submission_verification.json",
    "reports/browser_qa/final_submission/results.json", "reports/api_status.json",
    "reports/integrated_model_evaluation.json", "reports/decision_study.json",
    "reports/source_provenance.json", "reports/data_dictionary.csv",
)


def add_analysis(app, staging):
    """Require executed, current notebooks and expose their in-package previews."""
    report = read(app / "reports/notebook_execution.json")
    records = {row["notebook"]: row for row in report.get("notebooks", [])}
    if (report.get("passed") is not True or report.get("operator_preserved") is not True
            or set(records) != set(NOTEBOOKS)):
        raise ValueError("Re-execute all four bundled notebooks before building the judge handoff")
    links = []
    for name in NOTEBOOKS:
        entry = records[name]
        source, executed = app / "notebooks" / name, app / "reports/notebooks" / name
        parsed = read(source)
        for cell in parsed["cells"]:
            if isinstance(cell["source"], list):
                cell["source"] = "".join(cell["source"])
        preview = executed.with_suffix(".html")
        if (entry.get("status") != "passed" or entry.get("executed_code_cells", 0) != entry.get("code_cells")
                or entry.get("code_cells", 0) < 1 or code_digest(parsed) != entry.get("source_code_sha256")
                or sha256(executed) != entry.get("executed_notebook_sha256")
                or sha256(preview) != entry.get("html_sha256")):
            raise ValueError(f"Notebook execution or checksum is incomplete/stale: {name}")
        title = name.removesuffix(".ipynb").replace("_", " ")
        links.append(f'<li><a href="../02_Application/reports/notebooks/{html.escape(preview.name)}">Read {html.escape(title)}</a> '
                     f'(<a href="../02_Application/notebooks/{html.escape(name)}">Jupyter notebook</a>)</li>')
    folder = staging / "04_Reproducible_Analysis"
    folder.mkdir()
    (folder / "index.html").write_text(
        "<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>AEGIS reproducible analysis</title><style>body{font:17px/1.6 system-ui;max-width:1000px;margin:40px auto;padding:0 24px;color:#193b2e}li{margin:18px 0}a{color:#176044}code{overflow-wrap:anywhere}</style>"
        "<h1>Reproducible analysis notebooks</h1><p>Four notebooks were executed with numerical assertions against the reported results. "
        "The HTML previews contain real outputs and embedded figures and open without installing Jupyter.</p><ol>" + "".join(links) +
        "</ol><h2>Run them again</h2><p>From <code>02_Application</code>, install the optional pinned tools with "
        "<code>.venv/Scripts/python -m pip install -r requirements-notebooks.txt</code>, then run "
        "<code>.venv/Scripts/python scripts/execute_notebooks.py</code>. Use <code>.venv/bin/python</code> on macOS/Linux.</p>"
        "<p><a href='../02_Application/notebooks/README.md'>Full instructions and original-source replay</a> · "
        "<a href='../02_Application/reports/notebook_execution.json'>Actual execution record</a> · "
        "<a href='../00_START_HERE.html'>Back to Start Here</a></p>"
        "<p>Default execution uses bundled source snapshots; full raw preprocessing requires the original files separately. "
        "Notebook workspaces are isolated. Model results remain retrospective and logistics/telemetry remain simulated.</p></html>", encoding="utf-8")
    (folder / "README.md").write_text(
        "# Reproducible analysis\n\nOpen index.html for executed previews and notebook links.\n\n"
        "Files and reproduction commands are in ../02_Application/notebooks/README.md.\n"
        "The optional notebook environment is separate from the basic demo setup.\n"
        "Default replay uses bundled snapshots; original-source preprocessing needs the excluded raw files.\n", encoding="utf-8")
    return len(records)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inside(path, directory):
    resolved, boundary = Path(path).resolve(), Path(directory).resolve()
    if resolved == boundary or not resolved.is_relative_to(boundary):
        raise ValueError("Judge output must stay inside the project artifacts directory")
    return resolved


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []

    def handle_starttag(self, tag, attrs):
        self.targets.extend(value for key, value in attrs if key in {"href", "src"} and value)


def verify_links(folder):
    document = folder / "00_START_HERE.html"
    parser = Links()
    parser.feed(document.read_text(encoding="utf-8"))
    local_links = 0
    for target in parser.targets:
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        relative = unquote(parsed.path)
        path = (folder / relative).resolve()
        if not path.is_relative_to(folder.resolve()) or not path.is_file():
            raise ValueError(f"Broken or escaping Start Here link: {target}")
        local_links += 1
    return local_links


def test_summary(app, package):
    session = read(app / "reports/session_verification.json")
    browser = read(app / "reports/browser_qa/final_submission/results.json")
    lines = ["AEGIS — measured verification", "", "Each record retains its own scope and date.",
             f"Local checks: {session.get('finished_at', 'not recorded')}"]
    for check in session.get("checks", []):
        status = "PASS" if check.get("passed") is True else "FAIL / not verified"
        count = check.get("tests_passed")
        suffix = f" ({count} tests)" if type(count) is int else ""
        lines.append(f"- {check.get('name', 'unknown')}: {status}{suffix}")
    checks = browser.get("checks", [])
    passed = sum(item.get("passed") is True for item in checks)
    lines += ["", f"Separately dated Chrome evidence: {browser.get('finished_at', 'not recorded')}",
              f"- {passed}/{len(checks)} checks passed; scope: {browser.get('scope', 'see results.json')}",
              "", f"Extracted application verification: {package.get('finished_at', 'not recorded')}",
              f"- Passed: {package.get('passed') is True}; {len(package.get('checks', []))} checks",
              f"- Application archive SHA-256: {package.get('archive_sha256', 'not recorded')}",
              f"- Fresh Python environment tested by this offline check: {package.get('fresh_python_environment') is True}",
              "", "The offline verifier reuses installed dependencies. Judge setup installs them on the reviewer machine.",
              "Browser evidence is separately dated; the existing Chrome scope is not a fresh-install claim.",
              "Public API statuses are separately dated in api_status.json. No new live-source success is inferred.",
              "Simulation, uncertainty, human approval and Kiro non-use remain disclosed."]
    return "\n".join(lines) + "\n"


def verify_judge_archive(archive):
    """Check exact portable membership and all bytes, without executing/extracting."""
    with zipfile.ZipFile(archive) as zipped:
        infos = zipped.infolist()
        names = [item.filename for item in infos]
        if len(names) > 10000 or sum(item.file_size for item in infos) > 100 * 1024 * 1024:
            raise ValueError("Judge archive exceeds its size/member bound")
        if len(names) != len(set(name.casefold() for name in names)):
            raise ValueError("Duplicate judge archive path")
        for name in names:
            safe_member(name)
            if not name.startswith(NAME + "/"):
                raise ValueError("Judge archive must have one AEGIS-Judges top-level folder")
        manifest_path = NAME + "/JUDGE_HANDOFF_MANIFEST.json"
        manifest = json.loads(zipped.read(manifest_path))
        expected = {NAME + "/" + item["path"]: item for item in manifest["files"]}
        if len(expected) != len(manifest["files"]) or set(names) != set(expected) | {manifest_path}:
            raise ValueError("Judge manifest membership mismatch")
        for name, item in expected.items():
            payload = zipped.read(name)
            if len(payload) != item["bytes"] or hashlib.sha256(payload).hexdigest() != item["sha256"]:
                raise ValueError(f"Judge archive checksum mismatch: {name}")
    return {"passed": True, "files_verified": len(expected), "archive_sha256": sha256(archive)}


def build(root=ROOT, archive=None):
    root = Path(root).resolve()
    artifacts = root / "artifacts"
    if artifacts.resolve() != artifacts or not artifacts.resolve().is_relative_to(root):
        raise ValueError("Artifacts directory must be inside this project, without symlinks")
    artifacts.mkdir(exist_ok=True)
    archive = inside(archive or artifacts / "AEGIS-Final-Build.zip", artifacts)
    package = read(root / "reports/package_verification.json")
    if package.get("passed") is not True or package.get("archive_sha256") != sha256(archive):
        raise ValueError("Verify this exact application archive with scripts/verify_package.py first")
    staging = inside(artifacts / (".judge-build-" + str(uuid.uuid4())), artifacts)
    staging.mkdir()
    app = staging / "02_Application"
    app.mkdir()
    validate_and_extract(archive, app)
    required = ("Setup-Judges-Windows.cmd", "Start-Judges-Windows.cmd", "scripts/judge_demo.py",
                "docs/judge_start_here.html", "docs/judge_quick_start.md", "docs/judge_walkthrough.md")
    for name in required:
        if not (app / name).is_file():
            raise ValueError(f"Rebuild the application archive; judge file is missing: {name}")
    guides, evidence = staging / "01_Guides", staging / "03_Verification"
    guides.mkdir()
    evidence.mkdir()
    for source, destination in GUIDES.items():
        shutil.copyfile(app / source, guides / destination)
    for name in EVIDENCE:
        destination = "browser_results.json" if name.endswith("/results.json") else Path(name).name
        shutil.copyfile(app / name, evidence / destination)
    shutil.copyfile(root / "reports/package_verification.json", evidence / "package_verification.json")
    shutil.copyfile(app / "config/api_registry.csv", evidence / "api_registry.csv")
    for name in ("judge_launcher_smoke.json",):
        source = root / "reports" / name
        if source.is_file():
            shutil.copyfile(source, evidence / name)
    summary = test_summary(app, package)
    (evidence / "TEST_RESULTS.txt").write_text(summary, encoding="utf-8")
    template = (app / "docs/judge_start_here.html").read_text(encoding="utf-8")
    if template.count("{{VERIFICATION}}") != 1:
        raise ValueError("Start Here template must contain exactly one verification placeholder")
    (staging / "00_START_HERE.html").write_text(template.replace("{{VERIFICATION}}", "<pre>" + html.escape(summary) + "</pre>"), encoding="utf-8")
    shutil.copyfile(app / "docs/judge_quick_start.md", staging / "00_START_HERE.txt")
    notebook_count = add_analysis(app, staging)
    links = verify_links(staging)
    files = [{"path": path.relative_to(staging).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)}
             for path in sorted(staging.rglob("*")) if path.is_file()]
    manifest = {"schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
                "application_archive_sha256": sha256(archive), "files": files,
                "source_originals_modified": False, "operator_database_included": False,
                "genuine_kiro_use": False, "note": "Hashes establish integrity, not organizer acceptance or publisher authentication."}
    (staging / "JUDGE_HANDOFF_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    pending = inside(artifacts / (".judge-archive-" + str(uuid.uuid4()) + ".zip"), artifacts)
    with zipfile.ZipFile(pending, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zipped:
        for path in sorted(staging.rglob("*")):
            if path.is_file():
                info = zipfile.ZipInfo(NAME + "/" + path.relative_to(staging).as_posix(), (2026, 11, 2, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                zipped.writestr(info, path.read_bytes())
    verified = verify_judge_archive(pending)
    destination, output = inside(artifacts / NAME, artifacts), inside(artifacts / (NAME + ".zip"), artifacts)
    # Both endpoints of every directory move are resolved and bounded above/below.
    if destination.exists():
        history = inside(artifacts / "judge-history", artifacts)
        history.mkdir(exist_ok=True)
        backup = inside(history / (NAME + "-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")), artifacts)
        destination.rename(backup)
    staging.rename(destination)
    pending.replace(output)
    checksum = artifacts / (NAME + ".zip.sha256")
    checksum.write_text(f"{verified['archive_sha256']}  {output.name}\n", encoding="ascii")
    result = {"created_at": manifest["created_at"], "passed": True,
              "folder": str(destination.relative_to(root)), "archive": str(output.relative_to(root)),
              "bytes": output.stat().st_size, "sha256": verified["archive_sha256"],
              "application_archive_sha256": manifest["application_archive_sha256"],
              "files_verified": verified["files_verified"], "start_page_local_links_checked": links,
              "executed_notebooks_included": notebook_count,
              "raw_files_moved": False, "operator_database_opened": False,
              "uploaded_or_submitted": False}
    (root / "reports/judge_handoff.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=ROOT / "artifacts/AEGIS-Final-Build.zip")
    args = parser.parse_args()
    try:
        print(json.dumps(build(ROOT, args.archive), indent=2))
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        print(f"Judge handoff failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
