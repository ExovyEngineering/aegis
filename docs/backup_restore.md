# Local operational-state backup and recovery

October 28, 2026. This is a local recovery tool and a prerequisite for future
hosting work. No cloud service, authentication or production tenant isolation
has been implemented by this feature.

Run commands from the project directory. Create a new, uniquely named backup:

```powershell
.venv/Scripts/python scripts/backup_state.py create
```

The default source is `AEGIS_DB_PATH` when present in the process environment,
otherwise `data/aegis.sqlite`. This standalone script does not read `.env`.
The default destination is a new UUID directory under `data/backups/`. The JSON
result prints that relative directory and table counts. An explicit example is:

```powershell
.venv/Scripts/python scripts/backup_state.py create --database data/aegis.sqlite --output data/backups/before-team-review
.venv/Scripts/python scripts/backup_state.py verify --backup data/backups/before-team-review
.venv/Scripts/python scripts/backup_state.py restore --backup data/backups/before-team-review --target data/recovered/team-review.sqlite
```

The source connection is read-only. SQLite's online backup API includes
committed WAL transactions in a consistent database snapshot; copying only the
active main `.sqlite` file would not provide that guarantee. Concurrent
uncommitted transactions are excluded. A backup can reflect commits made while
the online copy is running; its retrieval time is not an exact historical
transaction timestamp. SQLite may access the source's ordinary WAL/shared-memory
sidecars while coordinating a read. Do not manually copy, delete or edit them.

Each completed directory contains a standalone `state.sqlite` and
`manifest.json`. The manifest records SHA-256, size, SQLite integrity, schema
digest, table names, column definitions and row counts. It contains a relative
source label and no table values, credentials or machine-specific absolute
paths. The actual SQLite file **does contain operational records**, including
self-declared identities, instructions and incidents. Treat it as private team
state; it is excluded from the reviewer package and Git.

Verification checks both files, hashes, structure, row counts and SQLite
integrity before a restore can create its target. The tool accepts the current
reviewed AEGIS table/column set, ordinary tables and SQLite automatic indexes.
Unknown tables/columns, views, triggers, virtual tables and user-created indexes
require a reviewed format update. Database size is bounded to 256 MiB; SQLite
copy/inspection work has a 30-second operation budget. The manifest is bounded
to 1 MiB. Verification does not interpret every stored JSON value or certify the
recorded plan's scientific or operational correctness.

Restore always creates a new file. It rejects existing targets, receipt files,
orphan SQLite sidecars, the canonical operator path and the process-configured
application database. It does not start a server or redirect the running
application. A successful restore also writes `<target>.restore.json` with its
origin checksum, relative paths and the human-review requirement. Review holds,
recalls, assignments and parked confirmations before any resumed use. Original
approval history is preserved; recovery is not a fresh approval or permission
to dispatch.

Source, backup and restore paths must stay inside this workspace. Created/verified
backup directories must be direct, nonempty children of `data/backups/`; restored files
must be under `data/recovered/`. These private directories are excluded from Git
and the reviewer package; the script cannot scatter manifests or recovery
receipts into source/documentation directories. Original
`data/raw/`, credentials/configuration directories, traversal, symbolic links,
directory junctions and hard-linked files are rejected. No existing path is
deleted or overwritten. A failed/interrupted copy is retained for investigation,
without a valid completed manifest/receipt; select a new destination when retrying.
Do not use incomplete outputs. Ordinary file collisions are guarded by exclusive
creation; this is a local tool, not protection against a malicious local process
that can rewrite files concurrently.

SHA-256 detects changes relative to a manifest. It is not a digital signature,
backup-author authentication or protection against an attacker replacing both
files. Restore only trusted local backups. This operation does not back up raw
datasets, source caches, frontend assets, dependencies or the repository itself.
Use the separate reviewer package and source repository for reproducibility.

Focused regression checks live in `tests/test_backup_state.py`. They exercise
committed/uncommitted WAL behavior, exact round-trip bytes and hold/audit
preservation, corrupted/tampered/unsupported inputs, interrupted output,
workspace/raw-data boundaries, hardlinks/symlinks, overwrite protection and
structured CLI errors. Executed outcomes belong in the dated verification
report; this document does not itself establish a test pass.
