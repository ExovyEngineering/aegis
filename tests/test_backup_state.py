import json
import os
from pathlib import Path
import sqlite3

import pytest

from scripts import backup_state as backup


def state_database(root, name="data/aegis.sqlite", *, wal=False):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    if wal:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA wal_autocheckpoint=0")
    connection.executescript("""
        CREATE TABLE state (id INTEGER PRIMARY KEY, payload TEXT NOT NULL, revision INTEGER NOT NULL);
        CREATE TABLE proposals (id TEXT PRIMARY KEY,payload TEXT NOT NULL,revision INTEGER NOT NULL,status TEXT NOT NULL);
        CREATE TABLE audit (id INTEGER PRIMARY KEY,timestamp TEXT,actor TEXT,action TEXT,payload TEXT);
        CREATE TABLE assignments (id TEXT PRIMARY KEY,payload TEXT,acknowledged INTEGER DEFAULT 0);
        INSERT INTO state VALUES (1,'{"simulation":true,"held_lots":["L01"]}',7);
        INSERT INTO audit VALUES (1,'2026-10-28T12:00:00Z','local dispatcher','hold','{"lot":"L01"}');
    """)
    connection.commit()
    return path, connection


def saved_backup(tmp_path):
    source, connection = state_database(tmp_path)
    connection.close()
    result = backup.create_backup(source, "data/backups/one", root=tmp_path)
    return source, tmp_path / result["backup_directory"]


def test_online_backup_reads_committed_wal_without_copying_uncommitted_changes(tmp_path):
    source, writer = state_database(tmp_path, wal=True)
    try:
        writer.execute("INSERT INTO assignments VALUES ('SH01','{\"held\":false}',1)")
        writer.commit()
        # This committed row is still in the WAL, which an ordinary main-file copy loses.
        assert Path(str(source) + "-wal").stat().st_size > 0
        writer.execute("INSERT INTO assignments VALUES ('UNCOMMITTED','{}',0)")
        before = source.read_bytes()
        result = backup.create_backup(source, "data/backups/wal", root=tmp_path)
        assert result["status"] == "created"
        assert result["source_opened_read_only"] is True
        assert source.read_bytes() == before
        snap = tmp_path / result["backup_directory"] / backup.DATABASE_NAME
        with sqlite3.connect(snap) as reader:
            assert reader.execute("SELECT id,acknowledged FROM assignments").fetchall() == [("SH01", 1)]
            assert reader.execute("SELECT revision FROM state").fetchone()[0] == 7
            assert "L01" in reader.execute("SELECT payload FROM state").fetchone()[0]
        assert not any(Path(str(snap) + suffix).exists() for suffix in backup.SIDECARS)
        assert backup.verify_backup(snap.parent, root=tmp_path)["status"] == "verified"
        writer.rollback()
        assert writer.execute("SELECT COUNT(*) FROM assignments").fetchone()[0] == 1
    finally:
        writer.close()


def test_round_trip_preserves_exact_snapshot_and_operator_bytes(tmp_path):
    source, folder = saved_backup(tmp_path)
    original = source.read_bytes()
    target = tmp_path / "data/recovered/review.sqlite"
    result = backup.restore_backup(folder, target, root=tmp_path)
    assert result["status"] == "restored_to_new_copy"
    assert result["human_review_required"] is True
    assert result["server_started"] is False
    assert result["operator_database_overwritten"] is False
    assert source.read_bytes() == original
    assert target.read_bytes() == (folder / "state.sqlite").read_bytes()
    assert json.loads(Path(str(target) + ".restore.json").read_text()) == result
    with sqlite3.connect(target) as connection:
        assert connection.execute("SELECT action FROM audit").fetchall() == [("hold",)]


def test_manifest_reports_only_structure_counts_and_relative_context(tmp_path, monkeypatch):
    monkeypatch.setenv("PRIVATE_SECRET_FOR_TEST", "never expose me")
    source, folder = saved_backup(tmp_path)
    text = (folder / backup.MANIFEST_NAME).read_text()
    manifest = json.loads(text)
    assert str(tmp_path) not in text and "never expose me" not in text
    assert "local dispatcher" not in text and "held_lots" not in text
    assert manifest["source_database"] == "data/aegis.sqlite"
    assert manifest["sqlite_integrity"] == "ok"
    assert manifest["tables"][0]["name"] == "assignments"
    assert "not a signature" in manifest["authentication_warning"]
    verification = backup.verify_backup(folder, root=tmp_path)
    assert verification["author_authenticated"] is False
    assert verification["application_state_changed"] is False


@pytest.mark.parametrize("target", ["data/aegis.sqlite", "data/recovered/existing.sqlite", "data/recovered/existing.sqlite.restore.json"])
def test_restore_never_overwrites_operator_or_existing_files(tmp_path, target):
    source, folder = saved_backup(tmp_path)
    original = source.read_bytes()
    destination = tmp_path / ("data/recovered/existing.sqlite" if target != "data/aegis.sqlite" else target)
    existing = tmp_path / target
    if target != "data/aegis.sqlite":
        existing.parent.mkdir(parents=True)
        existing.write_bytes(b"preserve existing bytes")
    with pytest.raises(backup.BackupError):
        backup.restore_backup(folder, destination, root=tmp_path)
    assert source.read_bytes() == original
    if target != "data/aegis.sqlite":
        assert existing.read_bytes() == b"preserve existing bytes"


def test_restore_rejects_configured_app_database_even_when_absent(tmp_path, monkeypatch):
    _source, folder = saved_backup(tmp_path)
    monkeypatch.setenv("AEGIS_DB_PATH", "data/recovered/custom-operator.sqlite")
    with pytest.raises(backup.BackupError, match="configured application"):
        backup.restore_backup(folder, "data/recovered/custom-operator.sqlite", root=tmp_path)
    assert not (tmp_path / "data/recovered/custom-operator.sqlite").exists()


@pytest.mark.parametrize("suffix", backup.SIDECARS)
def test_restore_refuses_existing_orphan_sidecars(tmp_path, suffix):
    _source, folder = saved_backup(tmp_path)
    sidecar = tmp_path / f"data/recovered/copy.sqlite{suffix}"
    sidecar.parent.mkdir(parents=True)
    sidecar.write_bytes(b"old sidecar")
    with pytest.raises(backup.BackupError, match="sidecars"):
        backup.restore_backup(folder, "data/recovered/copy.sqlite", root=tmp_path)
    assert sidecar.read_bytes() == b"old sidecar"
    assert not (tmp_path / "data/recovered/copy.sqlite").exists()


@pytest.mark.parametrize("operation", ["create", "restore"])
@pytest.mark.parametrize("unsafe", ["../outside.sqlite", "data/raw/state.sqlite", ".git/state.sqlite", ".aws/state.sqlite", ".env/state.sqlite"])
def test_workspace_and_raw_data_boundaries(tmp_path, operation, unsafe):
    source, folder = saved_backup(tmp_path)
    original = source.read_bytes()
    with pytest.raises(backup.BackupError):
        if operation == "create":
            backup.create_backup(source, unsafe, root=tmp_path)
        else:
            backup.restore_backup(folder, unsafe, root=tmp_path)
    assert source.read_bytes() == original


def test_absolute_outside_source_is_rejected_without_opening_it(tmp_path):
    outside = tmp_path.parent / "outside-workspace.sqlite"
    with pytest.raises(backup.BackupError, match="inside this workspace"):
        backup.create_backup(outside, root=tmp_path)


def test_raw_database_cannot_be_used_as_backup_source(tmp_path):
    source, connection = state_database(tmp_path, "data/raw/not-operational.sqlite")
    connection.close()
    before = source.read_bytes()
    with pytest.raises(backup.BackupError, match="raw data"):
        backup.create_backup(source, root=tmp_path)
    assert source.read_bytes() == before


def test_existing_backup_directory_is_never_reused(tmp_path):
    source, folder = saved_backup(tmp_path)
    before = {path.name: path.read_bytes() for path in folder.iterdir()}
    with pytest.raises(backup.BackupError, match="already exists"):
        backup.create_backup(source, folder, root=tmp_path)
    assert before == {path.name: path.read_bytes() for path in folder.iterdir()}


def test_restore_cannot_add_files_to_the_immutable_backup_directory(tmp_path):
    _source, folder = saved_backup(tmp_path)
    with pytest.raises(backup.BackupError, match="data/recovered"):
        backup.restore_backup(folder, folder / "another.sqlite", root=tmp_path)
    assert backup.verify_backup(folder, root=tmp_path)["status"] == "verified"


def test_creating_a_nested_backup_cannot_change_a_completed_backup(tmp_path):
    source, folder = saved_backup(tmp_path)
    with pytest.raises(backup.BackupError, match="direct children"):
        backup.create_backup(source, folder / "nested", root=tmp_path)
    assert backup.verify_backup(folder, root=tmp_path)["status"] == "verified"


@pytest.mark.parametrize("output", ["docs/private-backup", "scripts/private-backup", "data/backups", "data/recovered/wrong-area"])
def test_backup_outputs_stay_in_excluded_private_backup_area(tmp_path, output):
    source, connection = state_database(tmp_path)
    connection.close()
    with pytest.raises(backup.BackupError, match="data/backups"):
        backup.create_backup(source, output, root=tmp_path)
    assert not (tmp_path / output).exists()


@pytest.mark.parametrize("target", ["docs/private-copy.sqlite", "scripts/private-copy.sqlite", "data/backups/private-copy.sqlite", "data/recovered"])
def test_restore_outputs_stay_in_excluded_private_recovery_area(tmp_path, target):
    _source, folder = saved_backup(tmp_path)
    with pytest.raises(backup.BackupError):
        backup.restore_backup(folder, target, root=tmp_path)
    assert not (tmp_path / target).exists()


@pytest.mark.parametrize("change", ["truncated-database", "checksum", "table-count", "format", "database-file", "manifest-json", "missing-manifest", "unexpected-member"])
def test_corrupt_tampered_or_incomplete_backups_are_rejected_before_restore(tmp_path, change):
    _source, folder = saved_backup(tmp_path)
    manifest_path = folder / backup.MANIFEST_NAME
    value = json.loads(manifest_path.read_text())
    if change == "truncated-database":
        path = folder / "state.sqlite"
        path.write_bytes(path.read_bytes()[:-100])
    elif change == "checksum":
        value["database_sha256"] = "0" * 64
    elif change == "table-count":
        value["tables"][0]["row_count"] += 1
    elif change == "format":
        value["format"] = "unknown-future-version"
    elif change == "database-file":
        value["database_file"] = "../../data/aegis.sqlite"
    elif change == "unexpected-member":
        (folder / "state.sqlite-wal").write_bytes(b"orphan")
    if change == "manifest-json":
        manifest_path.write_text("{broken json")
    elif change == "missing-manifest":
        manifest_path.unlink()
    else:
        manifest_path.write_text(json.dumps(value))
    with pytest.raises((backup.BackupError, sqlite3.DatabaseError)):
        backup.restore_backup(folder, "data/new-copy.sqlite", root=tmp_path)
    assert not (tmp_path / "data/new-copy.sqlite").exists()


@pytest.mark.parametrize("statement", [
    "CREATE TABLE unknown_entity (id INTEGER)",
    "CREATE VIEW unsafe_view AS SELECT * FROM state",
    "CREATE TRIGGER unexpected_trigger AFTER INSERT ON audit BEGIN DELETE FROM state; END",
    "CREATE INDEX user_index ON audit(actor)",
    "ALTER TABLE state ADD COLUMN surprise TEXT",
])
def test_unsupported_schemas_fail_explicitly(tmp_path, statement):
    source, connection = state_database(tmp_path)
    connection.execute(statement)
    connection.commit()
    connection.close()
    with pytest.raises(backup.BackupError, match="Unsupported|require a reviewed"):
        backup.create_backup(source, "data/backups/unsupported", root=tmp_path)
    assert not (tmp_path / "data/backups/unsupported/manifest.json").exists()


def test_non_sqlite_and_size_bound_sources_do_not_create_valid_backup(tmp_path, monkeypatch):
    source = tmp_path / "partial.sqlite"
    source.write_bytes(b"partial download")
    with pytest.raises(backup.BackupError, match="header"):
        backup.create_backup(source, "data/backups/partial", root=tmp_path)
    with pytest.raises(backup.BackupError):
        backup.verify_backup("data/backups/partial", root=tmp_path)
    monkeypatch.setattr(backup, "MAX_DATABASE_BYTES", 5)
    with pytest.raises(backup.BackupError, match="size"):
        backup.create_backup(source, "data/backups/oversize", root=tmp_path)
    assert not (tmp_path / "data/backups/oversize").exists()


def test_interrupted_snapshot_is_retained_as_incomplete_and_never_restorable(tmp_path, monkeypatch):
    source, connection = state_database(tmp_path)
    connection.close()
    before = source.read_bytes()
    monkeypatch.setattr(backup, "_inspect", lambda path: (_ for _ in ()).throw(OSError("simulated interruption")))
    with pytest.raises(OSError):
        backup.create_backup(source, "data/backups/interrupted", root=tmp_path)
    assert not (tmp_path / "data/backups/interrupted/manifest.json").exists()
    assert source.read_bytes() == before
    with pytest.raises(backup.BackupError, match="missing/unexpected"):
        backup.verify_backup("data/backups/interrupted", root=tmp_path)


def test_symlinked_source_and_backup_member_are_rejected(tmp_path):
    source, folder = saved_backup(tmp_path)
    linked = tmp_path / "linked.sqlite"
    try:
        linked.symlink_to(source)
    except OSError:
        pytest.skip("Windows account cannot create symlinks")
    with pytest.raises(backup.BackupError, match="symbolic links"):
        backup.create_backup(linked, root=tmp_path)
    member = folder / "state.sqlite"
    contents = member.read_bytes()
    member.unlink()
    other = tmp_path / "untrusted.sqlite"
    other.write_bytes(contents)
    member.symlink_to(other)
    with pytest.raises(backup.BackupError, match="symbolic links"):
        backup.verify_backup(folder, root=tmp_path)


def test_hardlinked_source_and_backup_member_are_rejected(tmp_path):
    source, folder = saved_backup(tmp_path)
    linked = tmp_path / "hardlinked.sqlite"
    try:
        os.link(source, linked)
    except OSError:
        pytest.skip("Filesystem does not support hardlinks")
    with pytest.raises(backup.BackupError, match="hard-linked"):
        backup.create_backup(linked, root=tmp_path)
    os.link(folder / "state.sqlite", tmp_path / "copy-link.sqlite")
    with pytest.raises(backup.BackupError, match="hard-linked"):
        backup.verify_backup(folder, root=tmp_path)


def test_hardlinked_source_sidecars_are_rejected_before_sqlite_opens_them(tmp_path):
    source, connection = state_database(tmp_path)
    connection.close()
    sidecar = Path(str(source) + "-wal")
    sidecar.write_bytes(b"not a genuine WAL")
    linked = tmp_path / "sidecar-link"
    try:
        os.link(sidecar, linked)
    except OSError:
        pytest.skip("Filesystem does not support hardlinks")
    with pytest.raises(backup.BackupError, match="sidecars must be ordinary"):
        backup.create_backup(source, "data/backups/linked-sidecar", root=tmp_path)
    assert not (tmp_path / "data/backups/linked-sidecar").exists()


def test_cli_json_and_failure_do_not_echo_private_paths(tmp_path, monkeypatch, capsys):
    _source, folder = saved_backup(tmp_path)
    real_verify = backup.verify_backup
    monkeypatch.setattr(backup, "verify_backup", lambda path: real_verify(path, root=tmp_path))
    assert backup.main(["verify", "--backup", str(folder)]) == 0
    value = json.loads(capsys.readouterr().out)
    assert value["status"] == "verified" and value["author_authenticated"] is False
    monkeypatch.setattr(backup, "verify_backup", lambda path: (_ for _ in ()).throw(PermissionError("C:/private/secret")))
    assert backup.main(["verify", "--backup", str(folder)]) == 2
    failure = capsys.readouterr()
    assert "C:/private/secret" not in failure.err
    assert json.loads(failure.err)["operator_database_overwritten"] is False
