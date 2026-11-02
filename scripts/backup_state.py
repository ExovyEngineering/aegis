"""Local, bounded SQLite backup and restore to a new file; no application mutation API.

Checksums detect accidental changes. They do not authenticate a backup's author.
Only restore a trusted local AEGIS backup, and review recovered assignments before use.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
import uuid


ROOT = Path(__file__).resolve().parents[1]
FORMAT = "aegis-local-state-backup-v1"
DATABASE_NAME = "state.sqlite"
MANIFEST_NAME = "manifest.json"
MAX_DATABASE_BYTES = 256 * 1024 * 1024
MAX_MANIFEST_BYTES = 1024 * 1024
TIME_LIMIT_SECONDS = 30
SIDECARS = ("-wal", "-shm", "-journal")
PROTECTED_PARTS = {".git", ".aws", ".codex", ".agents", ".venv", "node_modules"}
# A future table or migration must be reviewed before this backup format accepts it.
SUPPORTED_COLUMNS = {
    "state": ("id", "payload", "revision"),
    "proposals": ("id", "payload", "revision", "status"),
    "audit": ("id", "timestamp", "actor", "action", "payload"),
    "assignments": ("id", "payload", "acknowledged"),
    "incidents": ("id", "shipment_id", "payload", "status", "version"),
    "dispatch_instruction_versions": ("shipment_id", "version"),
    "planning_runs": ("id", "created_at", "request_json", "result_json", "checksum"),
    "planning_projects": ("id", "name", "version", "run_id", "updated_at", "archived"),
    "planning_versions": ("project_id", "version", "run_id", "name", "created_at"),
    "driver_focus": ("truck_id", "mode", "version", "parked_until", "updated_at"),
    "rehearsal_runs": ("id", "version", "status", "payload", "snapshot_json", "snapshot_sha256"),
}
REQUIRED_TABLES = {"state", "proposals", "audit", "assignments"}


class BackupError(ValueError):
    """A bounded backup precondition or verification failure."""


def _stamp():
    return datetime.now(timezone.utc).isoformat()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _path(value, *, root=ROOT, role="path"):
    """Reject traversal, links, protected trees and paths outside the workspace."""
    root = Path(root).resolve(strict=True)
    supplied = Path(value)
    if ".." in supplied.parts:
        raise BackupError(f"{role}: parent traversal is not supported")
    candidate = supplied if supplied.is_absolute() else root / supplied
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise BackupError(f"{role}: path must stay inside this workspace") from exc
    folded = tuple(part.casefold() for part in relative.parts)
    if any(part in PROTECTED_PARTS or part.startswith(".env") for part in folded):
        raise BackupError(f"{role}: protected workspace path")
    if len(folded) >= 2 and folded[:2] == ("data", "raw"):
        raise BackupError(f"{role}: original raw data is never a backup/restore target")
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink() or (hasattr(cursor, "is_junction") and cursor.is_junction()):
            raise BackupError(f"{role}: symbolic links and directory junctions are not supported")
    try:
        resolved = candidate.resolve(strict=False)
        resolved.relative_to(root)
    except (ValueError, OSError, RuntimeError) as exc:
        raise BackupError(f"{role}: unable to verify workspace containment") from exc
    if resolved != candidate:
        raise BackupError(f"{role}: path aliases are not supported")
    return candidate


def _regular_file(path, *, maximum, role):
    if not path.is_file():
        raise BackupError(f"{role}: expected an existing regular file")
    info = path.stat()
    if info.st_nlink != 1:
        raise BackupError(f"{role}: hard-linked files are not supported")
    if not 0 < info.st_size <= maximum:
        raise BackupError(f"{role}: empty file or size exceeds the supported bound")
    return info


def _storage_area(path, *, root, directory, role):
    base = root / "data" / directory
    if path == base or not path.is_relative_to(base):
        raise BackupError(f"{role}: use a nonempty path under data/{directory}/")
    if directory == "backups" and path.parent != base:
        raise BackupError("Backup directories must be direct children of data/backups/; existing backup contents stay immutable")


def _no_sidecars(path):
    if any(Path(str(path) + suffix).exists() or Path(str(path) + suffix).is_symlink() for suffix in SIDECARS):
        raise BackupError("Snapshot/restore file has SQLite sidecars; expected a closed, standalone backup")


def _source_sidecars(path, *, root):
    for suffix in SIDECARS:
        sidecar = _path(str(path) + suffix, root=root, role="source SQLite sidecar")
        if sidecar.exists() and (not sidecar.is_file() or sidecar.stat().st_nlink != 1):
            raise BackupError("Source SQLite sidecars must be ordinary files without hardlinks")


def _digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def _reader(path, *, immutable=False):
    with path.open("rb") as stream:
        if stream.read(16) != b"SQLite format 3\x00":
            raise BackupError("Not a complete SQLite database header")
    # mode=ro cannot create a missing database. immutable is used only for closed,
    # sidecar-free copies, never for the live WAL source.
    uri = path.as_uri() + "?mode=ro" + ("&immutable=1" if immutable else "")
    connection = sqlite3.connect(uri, uri=True, timeout=5)
    try:
        connection.execute("PRAGMA query_only=ON")
        connection.execute("PRAGMA trusted_schema=OFF")
        if hasattr(connection, "setconfig"):
            connection.setconfig(sqlite3.SQLITE_DBCONFIG_DEFENSIVE, True)
        deadline = time.monotonic() + TIME_LIMIT_SECONDS
        connection.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
        return connection
    except BaseException:
        connection.close()
        raise


def _inspect(path):
    """Read one closed snapshot; no table values or arbitrary SQL in the manifest."""
    _regular_file(path, maximum=MAX_DATABASE_BYTES, role="database")
    _no_sidecars(path)
    with closing(_reader(path, immutable=True)) as connection:
        schema = list(connection.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name"))
        table_names = {row[1] for row in schema if row[0] == "table" and not row[1].startswith("sqlite_")}
        if not REQUIRED_TABLES <= table_names or not table_names <= SUPPORTED_COLUMNS.keys():
            raise BackupError("Unsupported AEGIS table set; required tables absent or unreviewed tables present")
        for kind, name, _table, sql in schema:
            if kind not in {"table", "index"} or (sql and "CREATE VIRTUAL TABLE" in sql.upper()):
                raise BackupError("Unsupported SQLite object; views, triggers and virtual tables are not accepted")
            if kind == "index" and not name.startswith("sqlite_autoindex_"):
                raise BackupError("User-defined SQLite indexes require a reviewed backup format")
        tables = []
        for name in sorted(table_names):
            # Names come from a fixed allowlist, never from user-provided SQL.
            columns = list(connection.execute(f'PRAGMA table_info("{name}")'))
            if tuple(row[1] for row in columns) != SUPPORTED_COLUMNS[name]:
                raise BackupError(f"Unsupported columns in AEGIS table {name}")
            tables.append({"name": name, "row_count": connection.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0],
                           "columns": [{"name": row[1], "type": row[2], "not_null": bool(row[3]), "primary_key_order": row[5]} for row in columns]})
        integrity = [row[0] for row in connection.execute("PRAGMA integrity_check")]
        if integrity != ["ok"]:
            raise BackupError("SQLite integrity_check did not pass")
        return {"sqlite_integrity": "ok", "schema_sha256": hashlib.sha256(_canonical(schema)).hexdigest(),
                "user_version": connection.execute("PRAGMA user_version").fetchone()[0], "tables": tables}


def _write_exclusive(path, value):
    with path.open("xb") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode("utf-8"))
        stream.write(b"\n")
        stream.flush()
        os.fsync(stream.fileno())


def create_backup(database=None, output=None, *, root=ROOT):
    root = Path(root).resolve(strict=True)
    source = _path(database or os.environ.get("AEGIS_DB_PATH") or "data/aegis.sqlite", root=root, role="source")
    _regular_file(source, maximum=MAX_DATABASE_BYTES, role="source database")
    if source.suffix.lower() not in {".sqlite", ".sqlite3", ".db"}:
        raise BackupError("Source must be an operational .sqlite, .sqlite3 or .db file")
    _source_sidecars(source, root=root)
    folder = _path(output or f"data/backups/{uuid.uuid4()}", root=root, role="backup directory")
    _storage_area(folder, root=root, directory="backups", role="backup directory")
    if folder.exists():
        raise BackupError("Backup directory already exists; nothing was overwritten")
    folder.parent.mkdir(parents=True, exist_ok=True)
    folder.mkdir()  # Exclusive directory reservation. No existing files are removed.
    target = folder / DATABASE_NAME
    # If interrupted, retain the reserved directory without a completed manifest.
    # Never remove a directory whose ownership may have changed after creation.
    with target.open("xb"):
        pass
    started = time.monotonic()
    def progress(_status, _remaining, _total):
        if time.monotonic() - started > TIME_LIMIT_SECONDS:
            raise BackupError("Online backup exceeded the 30-second limit")
    with closing(_reader(source)) as reader, closing(sqlite3.connect(target)) as writer:
        reader.backup(writer, pages=64, progress=progress, sleep=.01)
        writer.execute("PRAGMA journal_mode=DELETE")
    details = _inspect(target)
    digest = _digest(target)
    manifest = {"format": FORMAT, "created_at": _stamp(), "source_database": source.relative_to(root).as_posix(),
                    "database_file": DATABASE_NAME, "database_bytes": target.stat().st_size, "database_sha256": digest,
                    **details, "method": "SQLite online backup from a read-only connection; committed WAL content included",
                    "scope": "Local simulated AEGIS operational state only. Raw data, credentials, source caches and frontend are not included.",
                    "authentication_warning": "SHA-256 is an integrity check, not a signature or proof of author identity. Restore only trusted backups.",
                    "safety_warning": "Recovered assignments and self-declared identities require human review; this does not dispatch or certify product safety."}
    _write_exclusive(folder / MANIFEST_NAME, manifest)
    return {"status": "created", "backup_directory": folder.relative_to(root).as_posix(), "database_sha256": digest,
            "tables": [{"name": table["name"], "row_count": table["row_count"]} for table in details["tables"]],
            "source_opened_read_only": True, "source_snapshot_consistency": "SQLite online backup transaction", "cloud_deployed": False}


def _load_manifest(folder):
    path = folder / MANIFEST_NAME
    _regular_file(path, maximum=MAX_MANIFEST_BYTES, role="manifest")
    try:
        value = json.loads(path.read_bytes())
    except (ValueError, UnicodeError) as exc:
        raise BackupError("Backup manifest is not valid JSON") from exc
    if not isinstance(value, dict) or value.get("format") != FORMAT or value.get("database_file") != DATABASE_NAME:
        raise BackupError("Unsupported backup manifest format or database filename")
    if not isinstance(value.get("database_bytes"), int) or isinstance(value["database_bytes"], bool) or not 0 < value["database_bytes"] <= MAX_DATABASE_BYTES:
        raise BackupError("Unsupported manifest database size")
    digest = value.get("database_sha256")
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise BackupError("Invalid manifest database checksum")
    return value


def _verified(backup, *, root=ROOT):
    root = Path(root).resolve(strict=True)
    folder = _path(backup, root=root, role="backup directory")
    _storage_area(folder, root=root, directory="backups", role="backup directory")
    if not folder.is_dir():
        raise BackupError("Backup directory does not exist")
    expected_members = {DATABASE_NAME, MANIFEST_NAME}
    if {item.name for item in folder.iterdir()} != expected_members:
        raise BackupError("Backup has missing/unexpected files; incomplete outputs and sidecars are not accepted")
    for name in expected_members:
        _path(folder / name, root=root, role="backup member")
    manifest = _load_manifest(folder)
    source = folder / DATABASE_NAME
    info = _regular_file(source, maximum=MAX_DATABASE_BYTES, role="backup database")
    _no_sidecars(source)
    before = (info.st_size, info.st_mtime_ns, info.st_ino)
    if info.st_size != manifest["database_bytes"] or _digest(source) != manifest["database_sha256"]:
        raise BackupError("Backup database size/checksum does not match its manifest")
    actual = _inspect(source)
    if any(actual[key] != manifest.get(key) for key in actual):
        raise BackupError("Backup schema, row counts or integrity differ from the manifest")
    after = source.stat()
    if before != (after.st_size, after.st_mtime_ns, after.st_ino) or _digest(source) != manifest["database_sha256"]:
        raise BackupError("Backup changed during verification")
    return folder, source, manifest


def verify_backup(backup, *, root=ROOT):
    root = Path(root).resolve(strict=True)
    folder, _source, manifest = _verified(backup, root=root)
    return {"status": "verified", "backup_directory": folder.relative_to(root).as_posix(),
            "database_sha256": manifest["database_sha256"], "table_count": len(manifest["tables"]),
            "sqlite_integrity": "ok", "author_authenticated": False, "application_state_changed": False}


def restore_backup(backup, target, *, root=ROOT):
    root = Path(root).resolve(strict=True)
    folder, source, manifest = _verified(backup, root=root)
    destination = _path(target, root=root, role="restore target")
    if destination.suffix.lower() not in {".sqlite", ".sqlite3", ".db"}:
        raise BackupError("Restore target must use .sqlite, .sqlite3 or .db")
    if destination == root / "data/aegis.sqlite":
        raise BackupError("The canonical operator database is never a restore target")
    configured = os.environ.get("AEGIS_DB_PATH")
    if configured and destination == _path(configured, root=root, role="configured application database"):
        raise BackupError("The configured application database is never a restore target")
    _storage_area(destination, root=root, directory="recovered", role="restore target")
    receipt = Path(str(destination) + ".restore.json")
    _path(receipt, root=root, role="restore receipt")
    if destination.exists() or receipt.exists():
        raise BackupError("Restore target/receipt already exists; nothing was overwritten")
    _no_sidecars(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents an ordinary collision from overwriting state.
    # A process interruption may leave an incomplete new file; it is never reused.
    with destination.open("xb") as writer, source.open("rb") as reader:
        for chunk in iter(lambda: reader.read(1024 * 1024), b""):
            writer.write(chunk)
        writer.flush()
        os.fsync(writer.fileno())
    _path(destination, root=root, role="restored database")
    if _digest(destination) != manifest["database_sha256"] or _inspect(destination) != {key: manifest[key] for key in ("sqlite_integrity", "schema_sha256", "user_version", "tables")}:
        raise BackupError("Restored copy failed verification; file retained for investigation and must not be used")
    result = {"status": "restored_to_new_copy", "restored_at": _stamp(), "target_database": destination.relative_to(root).as_posix(),
              "backup_directory": folder.relative_to(root).as_posix(), "database_sha256": manifest["database_sha256"],
              "operator_database_overwritten": False, "server_started": False, "human_review_required": True,
              "warning": "Recovery preserves recorded state. Review assignments, holds, parked confirmations and identity assumptions before any resumed use; no dispatch or safety certification is performed."}
    _write_exclusive(receipt, result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create", help="Create a new WAL-consistent local backup directory")
    create.add_argument("--database", help="Workspace SQLite source; defaults to AEGIS_DB_PATH or data/aegis.sqlite")
    create.add_argument("--output", help="New backup directory; defaults to data/backups/<UUID>")
    verify = commands.add_parser("verify", help="Verify one closed backup without changing application state")
    verify.add_argument("--backup", required=True)
    restore = commands.add_parser("restore", help="Verify, then restore to a fresh local file; never overwrite")
    restore.add_argument("--backup", required=True)
    restore.add_argument("--target", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "create":
            result = create_backup(args.database, args.output)
        elif args.command == "verify":
            result = verify_backup(args.backup)
        else:
            result = restore_backup(args.backup, args.target)
        print(json.dumps(result, indent=2))
        return 0
    except (BackupError, OSError, sqlite3.Error, ValueError) as exc:
        # Avoid echoing arbitrary SQLite values, absolute paths or environment data.
        error = str(exc) if isinstance(exc, BackupError) else "Operation failed; check local file permissions, SQLite integrity and path availability"
        print(json.dumps({"status": "failed", "error_type": type(exc).__name__, "error": error,
                          "operator_database_overwritten": False, "server_started": False}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
