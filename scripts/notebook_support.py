"""Isolated, auditable execution support shared by the analysis notebooks.

Original data, published reports and the operator database are read-only inputs.
Every notebook gets its own copied project and writes only there. Full raw mode
requires exact provenance-matched original files and stages independent copies.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import shutil
import subprocess
import sys
import time
import uuid

SKIP = {"__pycache__", ".git", ".tools", ".venv", "node_modules", ".pytest_cache"}
INPUT_DIRS = ("backend", "scripts", "config", "docs", "data/processed", "data/fixtures", "data/manifests", "data/external/noaa", "reports/figures")
PRIVATE_SUFFIXES = {".sqlite", ".sqlite3", ".db", ".pyc", ".pem", ".key", ".log"}


def file_fingerprint(path):
    path = Path(path)
    if not path.exists():
        return {"exists": False}
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
    return {"exists": True, "bytes": size, "sha256": digest.hexdigest()}


def operator_fingerprints(root):
    return {suffix or "sqlite": file_fingerprint(Path(root) / ("data/aegis.sqlite" + suffix))
            for suffix in ("", "-wal", "-shm", "-journal")}


def local_path(root, relative):
    value = PureWindowsPath(str(relative))
    if value.anchor or ".." in value.parts or not value.parts:
        raise ValueError("Notebook path must be relative and stay inside its workspace")
    root = Path(root).resolve()
    path = root.joinpath(*value.parts).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Notebook path resolves outside its workspace")
    return path


def safe_input(path, root):
    relative = path.relative_to(root)
    return (not path.is_symlink() and not any(part in SKIP for part in relative.parts)
            and not any(part.startswith(".env") for part in relative.parts)
            and path.suffix.lower() not in PRIVATE_SUFFIXES
            and not any(token in path.name.lower() for token in (".sqlite-", ".sqlite3-", ".db-")))


class NotebookRun:
    def __init__(self, root, label):
        if not re.fullmatch(r"[a-z0-9_-]{1,64}", label):
            raise ValueError("Use a short alphanumeric notebook run label")
        self.root = Path(root).resolve()
        self.label = label
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.id = label + "-" + str(uuid.uuid4())
        base = local_path(self.root, "reports/notebook_runs")
        self.folder = local_path(base, self.id)
        self.workspace = self.folder / "project"
        self.workspace.mkdir(parents=True, exist_ok=False)
        self._operator_before = operator_fingerprints(self.root)
        self._raw_before = {}
        self.commands = []
        self._protected = {}
        paths = set()
        for name in INPUT_DIRS:
            directory = local_path(self.root, name)
            if directory.exists():
                paths.update(path for path in directory.rglob("*") if path.is_file() and safe_input(path, self.root))
        report_dir = self.root / "reports"
        if report_dir.exists():
            paths.update(path for path in report_dir.iterdir() if path.is_file() and safe_input(path, self.root))
        for name in ("requirements-lock.txt", "requirements.txt"):
            path = self.root / name
            if path.is_file():
                paths.add(path)
        for source in sorted(paths):
            relative = source.relative_to(self.root)
            target = self.workspace / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            before = file_fingerprint(source)
            shutil.copyfile(source, target)
            if file_fingerprint(target) != before:
                raise ValueError(f"Notebook input changed during copy: {relative}")
            self._protected[relative.as_posix()] = before
        # Runtime data live only in this owned copy, even if the caller's shell
        # points at an active dispatcher database.
        self.runtime_id = str(uuid.uuid4())
        self._guard = self.workspace / ".notebook_guard"
        self._guard.mkdir()
        (self._guard / "sitecustomize.py").write_text(
            "import socket\nfrom threading import local\n"
            "_context = local()\n"
            "_connect = socket.socket.connect\n_pair = socket.socketpair\n"
            "_connect_ex = socket.socket.connect_ex\n_sendto = socket.socket.sendto\n"
            "def _deny(*args, **kwargs):\n"
            "    raise RuntimeError('Notebook script reproduction disables network access; use bundled snapshots')\n"
            "def _guarded_connect(connection, address):\n"
            "    internal = getattr(_context, 'pair', False) and isinstance(address, tuple) and address[0] in ('127.0.0.1', '::1')\n"
            "    if connection.family in (socket.AF_INET, socket.AF_INET6) and not internal: return _deny()\n"
            "    return _connect(connection, address)\n"
            "def _guarded_pair(*args, **kwargs):\n"
            "    previous = getattr(_context, 'pair', False)\n"
            "    _context.pair = True\n"
            "    try: return _pair(*args, **kwargs)\n"
            "    finally: _context.pair = previous\n"
            "def _guarded_connect_ex(connection, address):\n"
            "    if connection.family in (socket.AF_INET, socket.AF_INET6): return _deny()\n"
            "    return _connect_ex(connection, address)\n"
            "def _guarded_sendto(connection, *args):\n"
            "    if connection.family in (socket.AF_INET, socket.AF_INET6): return _deny()\n"
            "    return _sendto(connection, *args)\n"
            "socket.create_connection = _deny\n"
            "socket.getaddrinfo = _deny\n"
            "socket.socket.connect = _guarded_connect\n"
            "socket.socket.connect_ex = _guarded_connect_ex\n"
            "socket.socket.sendto = _guarded_sendto\n"
            "socket.socketpair = _guarded_pair\n", encoding="utf-8")

    def read_json(self, relative):
        return json.loads(local_path(self.workspace, relative).read_text(encoding="utf-8"))

    def baseline_json(self, relative):
        return json.loads(local_path(self.root, relative).read_text(encoding="utf-8"))

    def run_script(self, relative, *args, timeout=900):
        script = local_path(self.workspace, relative)
        scripts = (self.workspace / "scripts").resolve()
        if not script.is_relative_to(scripts) or not script.is_file() or script.suffix != ".py":
            raise ValueError("Execute only an included Python script inside workspace/scripts")
        environment = dict(os.environ)
        for key in ("AEGIS_DB_PATH", "AEGIS_REHEARSAL_ID", "AEGIS_OFFLINE_DEMO", "AEGIS_DATA_DIR", "PYTHONPATH"):
            environment.pop(key, None)
        environment.update(AEGIS_DB_PATH=str(self.workspace / "data/rehearsals" / (self.runtime_id + ".sqlite")),
                           AEGIS_REHEARSAL_ID=self.runtime_id, AEGIS_OFFLINE_DEMO="1",
                           PYTHONPATH=str(self._guard) + os.pathsep + str(self.workspace),
                           PYTHONHASHSEED="0", PYTHONDONTWRITEBYTECODE="1",
                           MPLCONFIGDIR=str(self.workspace / ".tools/matplotlib"))
        command = [sys.executable, str(script), *map(str, args)]
        started = time.monotonic()
        result = subprocess.run(command, cwd=self.workspace, env=environment,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace", timeout=timeout)
        log = self.folder / (f"{len(self.commands) + 1:02}-" + script.stem + ".txt")
        log.write_text(result.stdout, encoding="utf-8")
        record = {"script": script.relative_to(self.workspace).as_posix(), "arguments": list(map(str, args)),
                  "exit_code": result.returncode, "duration_seconds": round(time.monotonic() - started, 3),
                  "log": log.relative_to(self.folder).as_posix(), "log_sha256": file_fingerprint(log)["sha256"]}
        self.commands.append(record)
        print(result.stdout.rstrip())
        if result.returncode:
            raise RuntimeError(f"{relative} failed with exit {result.returncode}; inspect {log}")
        return record

    def _raw_requirements(self):
        fsis = self.baseline_json("data/processed/fsis_provenance.json")
        evidence = self.baseline_json("data/processed/evidence_manifest.json")
        usda = self.baseline_json("reports/usda_food_environment.json")
        rows = [{"filename": item["source_file"], "sha256": item["sha256"]} for item in fsis["sources"]]
        for dataset in evidence["datasets"].values():
            rows.extend({"filename": item["file"], "sha256": item["sha256"]} for item in dataset["input_files"])
        rows.append({"filename": usda["source_file"]["filename"], "sha256": usda["source_file"]["sha256"]})
        unique = {}
        for row in rows:
            name = row["filename"]
            if PureWindowsPath(name).name != name or not re.fullmatch(r"[a-f0-9]{64}", row["sha256"]):
                raise ValueError("Raw lineage must contain safe filenames and SHA-256 values")
            if name in unique and unique[name] != row["sha256"]:
                raise ValueError(f"Conflicting raw lineage hashes: {name}")
            unique[name] = row["sha256"]
        return unique

    def ingest_raw(self, raw_dir):
        """Run original adapters on independently copied, provenance-verified inputs."""
        raw_dir = Path(raw_dir).resolve()
        if not raw_dir.is_dir():
            raise FileNotFoundError(f"Raw-data folder unavailable: {raw_dir}")
        requirements = self._raw_requirements()
        found = {}
        excluded = SKIP | {"artifacts", "reports", "frontend", "backend", "scripts", "tests", "docs", "config", "notebooks", "processed", "fixtures", "cache", "rehearsals", "external", "manifests"}
        for directory, dirs, names in os.walk(raw_dir, followlinks=False):
            dirs[:] = sorted(name for name in dirs if name not in excluded and not (Path(directory) / name).is_symlink())
            for name in names:
                if name not in requirements:
                    continue
                path = Path(directory) / name
                if path.is_symlink() or not path.resolve().is_relative_to(raw_dir):
                    continue
                fingerprint = file_fingerprint(path)
                if fingerprint["sha256"] != requirements[name]:
                    raise ValueError(f"Raw source checksum differs from published lineage: {name}")
                found.setdefault(name, path)
                self._raw_before[str(path)] = fingerprint
        missing = sorted(set(requirements) - set(found))
        if missing:
            raise FileNotFoundError("Original analysis inputs missing; raw ingestion not run: " + "; ".join(missing))
        staging = self.workspace / "raw_inputs"
        staging.mkdir(exist_ok=False)
        for name, source in sorted(found.items()):
            target = staging / name
            shutil.copyfile(source, target)
            if file_fingerprint(target)["sha256"] != requirements[name]:
                raise ValueError(f"Raw bytes changed while staging: {name}")
        # Staging avoids discovering generated files in the author's original
        # repository. The untouched original directory is never an adapter output.
        commands = [self.run_script("scripts/audit_data.py", "--data-dir", staging),
                    self.run_script("scripts/ingest_fsis.py", "--data-dir", staging),
                    self.run_script("scripts/ingest_evidence.py", "--data-dir", staging),
                    self.run_script("scripts/ingest_usda.py", "--data-dir", staging)]
        fsis = self.read_json("data/processed/fsis_provenance.json")
        evidence = self.read_json("data/processed/evidence_manifest.json")
        usda = self.read_json("reports/usda_food_environment.json")
        if fsis.get("status") != "complete" or usda.get("status") != "available":
            raise ValueError("Raw ingestion did not rebuild all required FSIS/USDA inputs; retained outputs are not fresh evidence")
        if not evidence.get("datasets") or any(row.get("status") != "available" for row in evidence["datasets"].values()):
            raise ValueError("Raw CDC/directory ingestion is incomplete; retained outputs are not fresh evidence")
        return {"status": "recomputed_from_verified_raw_copies", "originals_staged": len(found),
                "source_hashes": requirements, "commands": commands}

    def verify_preservation(self):
        changed = [name for name, expected in self._protected.items() if file_fingerprint(self.root / name) != expected]
        raw_changed = [name for name, expected in self._raw_before.items() if file_fingerprint(name) != expected]
        operator_ok = operator_fingerprints(self.root) == self._operator_before
        return {"passed": not changed and not raw_changed and operator_ok, "changed_inputs": changed,
                "operator_preserved": operator_ok, "raw_preserved": not raw_changed, "changed_raw_inputs": raw_changed}

    def finish(self):
        preservation = self.verify_preservation()
        result = {"id": self.id, "started_at": self.started_at, "finished_at": datetime.now(timezone.utc).isoformat(),
                  "commands": self.commands, "copied_input_count": len(self._protected),
                  "input_hashes": self._protected, "raw_input_hashes": self._raw_before,
                  "preservation": preservation, "passed": preservation["passed"] and all(row["exit_code"] == 0 for row in self.commands),
                  "network_policy": "Source scripts run with socket/DNS networking disabled; Jupyter kernel transport is separate."}
        (self.folder / "RUN_MANIFEST.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        if not result["passed"]:
            raise RuntimeError("Notebook inputs changed during execution; inspect its RUN_MANIFEST.json. No restore was attempted.")
        return result
