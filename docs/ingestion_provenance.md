# Source ingestion and verifiable snapshots

Original downloads remain unchanged. Source-family recognition, successful
parsing, provider authenticity, geographic coverage and scientific linkage are
separate claims. A readable or correctly named file does not prove all of them.

## Commands and selection

From the repository root:

```powershell
.venv/Scripts/python scripts/audit_data.py --data-dir C:/path/to/supplied-data
.venv/Scripts/python scripts/ingest_evidence.py --data-dir C:/path/to/supplied-data
.venv/Scripts/python scripts/ingest_fsis.py --data-dir C:/path/to/supplied-data
.venv/Scripts/python scripts/ingest_usda.py --data-dir C:/path/to/supplied-data
```

Each command also has a no-argument default using `AEGIS_DATA_DIR`, then
`data/raw/` when present, otherwise the repository folder. The audit inventories
supported formats recursively and reports unrecognized sources and exact read
errors. It streams nested JSON, samples workbooks/large tabular data, and checks
ZIP central-directory metadata without indiscriminate extraction. Audit workbook
dimensions remain declared, not exact parsed observation counts.

The evidence importer separately discovers CSV/TSV inputs recursively, reads
headers before observations and chooses a source-specific adapter. Runtime and
generated repository trees are excluded. Filenames and file order cannot turn
one BEAM schema into another.

| Derived identity | Semantic source |
|---|---|
| `nors_0` | CDC NORS historical outbreaks |
| `beam_0` | BEAM regional isolates |
| `beam_1` | BEAM source report; inspect human/animal/food source categories |
| `beam_2` | BEAM burden/trajectory summaries |
| `beam_3` | BEAM illnesses/outbreaks summaries |
| `beam_4` | BEAM common-serotype summary |
| `establishments_0` | FSIS Missouri establishment directory |

The identity suffixes are stable schema mappings, not indexes assigned by a
directory scan. Evidence remains separate; none of the CDC layers becomes an
FSIS training label or a genomic linkage. Directory coordinate parsing excludes
invalid/out-of-range rows and records its counts; official coordinates do not
establish real contracts for fictional logistics entities.

## Duplicates, conflicting exports and failures

Exact-byte duplicates share an input hash and are represented once in the
derived table. Different byte snapshots matching the same semantic CSV/TSV
identity produce `conflict`: no pooling, automatic date choice or overwrite is
performed. Select the intended export in a dedicated input folder and rerun.
Keep the original full folder for the audit. The importer records each source
path, hash, status and exact failure while continuing with independent files.
Unsupported workbook/archive/JSON formats are not silently read as CSV exports;
their audit records remain separate.

The FSIS importer instead requires embedded raw-poultry product metadata and
the primary observation schema. It checks a declared primary-row count where
provided, excludes a failed file as a whole, and continues valid independent
sources. Repeated sample identities are deduplicated only when all retained
observation fields agree. Conflicting establishment, date, cancellation, result
or other retained values block publication rather than silently discard a
revision. An unrelated RTE sample or secondary typing table cannot become the
primary poultry outcome.

Derived tables are published as complete files. A failed writer preserves the
previous output bytes. The latest manifest/report still records the failure or
conflict, so existence of an older Parquet file is not evidence of a successful
latest import. The explorer blocks latest failed/conflicting/missing input
identities; legacy tables without manifests expose a specific warning.

## Manifests and request integrity

[The evidence manifest](../data/processed/evidence_manifest.json) includes stable
semantic keys, all selected input paths/hashes, output hashes and dataset status.
[Per-file evidence results](../reports/evidence_ingestion.json) include
unrecognized and failed inputs. FSIS has [a separate provenance file](../data/processed/fsis_provenance.json)
and [ingestion report](../reports/fsis_ingestion.json). The USDA adapter has its
own [county report](../reports/usda_food_environment.json) and
[interpretation guide](food_access_context.md).

The data explorer validates stored source identity and checks the derived hash
against its manifest. It computes the hash and parses observations from one
immutable request snapshot, bounded to 64 MiB. Atomic replacement between reads
cannot pair a previous file's hash with a new file's values. Returned pages remain
bounded to 1-100 rows, maximum offset 10,000, with literal case-insensitive column
filters. Null counts describe the returned page, not the whole dataset.

These checks establish consistency with local recorded inputs and metadata;
they do not authenticate a provider cryptographically or invent missing result
availability dates. The FSIS snapshot creation date is not a proven public
release date. Historical model results remain retrospective, with the existing
scientific limitations visible.

## Verification evidence

The October 27 [re-ingestion verification](../reports/ingestion_verification.json)
compares values and dtypes of the eight pre-existing tables and records model
artifact preservation. It is not a new model evaluation or a new API
connectivity probe. Full session checks and their dates belong in
[session verification](../reports/session_verification.json) and the project
brief; do not infer an unexecuted result from this guide.

Implementation: [shared discovery/publication helpers](../backend/ingestion/common.py),
[CSV/TSV importer](../scripts/ingest_evidence.py),
[FSIS adapter](../backend/ingestion/fsis.py), and
[explorer](../backend/data_explorer.py).
Regression coverage: [semantic identity/conflict tests](../tests/test_ingestion_identity.py),
[explorer tests](../tests/test_data_explorer.py), and
[audit/adapter tests](../tests/test_adapters_audit.py).
