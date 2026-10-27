# Data catalog

Canonical file-level evidence is `data/manifests/inventory.json`; the readable audit is `reports/data_audit.md`. Original files remain in their supplied location. File size, SHA-256, format, schema samples, nested JSON table counts, timestamp ranges, duplicate hashes, workbook dimensions, archive members, and exact read errors are stored where supported.

## Supplied evidence

| Source | Current use | Boundary |
|---|---|---|
| FSIS raw-poultry FY2024–FY2026 JSON | Metadata-confirmed primary tables ingested; 78,607 deduplicated primary rows in the initial run | National selected sampling; Salmonella Positive/Negative only for model study; secondary typing excluded from outcome count |
| FSIS RTE sample/full-year, raw beef/pork, egg, Siluriformes, NARMS | Inventoried and schema-inspected | No silent pooling with poultry labels; RTE example is not poultry training data |
| NORS CSV | Separate Parquet; initial run 66,713 rows | Historical outbreak evidence across modes and jurisdictions, not FSIS-linked consumer illness labels |
| NORS workbook, dictionary, PDF | Inventoried, sampled/documented | Workbook versions may overlap CSV; no automatic concatenation |
| BEAM exports | Five separate Parquet exports, 1,650 / 262,616 / 484 / 2,412 / 4,818 rows | Regional isolates, source categories and serotype summaries retain distinct denominators; inspect the source-report human/animal/food categories |
| FSIS MPI establishment directory | Initial run 175 Missouri rows with numeric coordinates | Official directory coordinates used for map context; no verified simulated supply relationships |
| Establishment demographics/categories, Missouri CIS workbook | Inventoried | No unvalidated identifier joins |
| USDA Food Environment Atlas workbook | Source-specific Missouri county extract: 115 counties/county-equivalents and ten ACCESS/STORES variables | Historical 2019/2020/2023 measures with separate denominators; no safety labels, allocation weights or route-location assignment |
| USDA tract-level Food Access/SRAM workbooks | Read-only sheet and schema inspection | Separate geographic/vintage definitions; not merged with county context or assigned to fictional destinations |
| FSIS annual outbreak reports, NORS documentation, other PDFs | Page count and bounded text extraction | Documentation, not observation tables |

Counts above describe the recorded source extracts. The October 27 comparison verifies that re-ingestion preserved the eight pre-existing tables' values/dtypes; USDA county context is a separate addition. Reruns against a different folder can change counts; machine-readable reports are authoritative.

## Public streams

The registry has 18 source/probe entries, including documentation and catalogs. `reports/api_status.json` records actual HTTP results, latency, content type, test timestamps, schema, and failures. A successful catalog probe establishes reachability only.

- FSIS recall responses are official source records captured with a retrieval timestamp. Recall matching needs genuine establishment/product/lot/date traceability; fictional lots do not provide it.
- Open-Meteo hourly temperature, precipitation, and wind are **weather forecasts** for the Columbia point, not observed cargo exposure.
- NWS active Missouri alerts are **official weather warnings**. Zero returned alerts is valid only for that request and timestamp.
- NCEI daily summaries are **observed historical weather**. The initial station/week probe remains separate from the expanded five-Missouri-station extract (January 2025–June 2026). Station identities/coordinates, daily labels, explicitly requested metric units and quality attributes are validated; all 2,730 station/day rows returned, with nine missing precipitation values. This bounded extract is not joined to FSIS and lacks publication-availability timestamps. Original bytes/checksums live in `data/external/noaa/`; `reports/noaa_coverage.json` reports row and per-variable coverage separately.
- Open-Meteo archive is **historical reanalysis**, separate from station observations.
- MoDOT lightweight probes inspect service metadata. The full refresh adapter queries incident layers as GeoJSON and retains coverage status. The dated source-action report records an eighteen-layer successful request with no reported layer errors; it is not a new connectivity test merely because local ingestion was rerun. Route review still needs current cache timestamps and must heed any coverage warning.
- OSRM provides ordinary driving geometry and estimates. It supplies neither commercial-truck validation nor automatic current MoDOT closures.

## Audit interpretation

CSV/JSONL missingness is based on bounded row samples. Nested JSON field/null counters and table paths preserve the distinction between metadata, primary tests, and secondary tests. Workbook row dimensions are declared by the file and are not guaranteed exact nonempty observation counts. ZIP central directories are inspected without extraction or full CRC validation. PDF extraction is bounded and may miss scanned pages. JSON parsing detects syntax failures; semantic validity still requires a source-specific adapter.

Exact-byte duplicates are found by SHA-256. A partial but syntactically valid download may require provider record-count comparison; absence of a parse error is not proof of completeness. Unknown sources stay in the inventory and are not silently merged.

## Recursive ingestion and snapshot identity

[The ingestion provenance guide](ingestion_provenance.md) describes the current
source selection rules. CSV/TSV discovery is recursive and header-first. Each
supported NORS, BEAM or establishment schema has a stable semantic identity;
filenames and discovery order do not decide the meaning of `beam_0` through
`beam_4`. Exact-byte duplicate downloads do not duplicate observations. Different
exports matching the same identity produce an explicit conflict and require the
operator to select a snapshot in a separate input folder. They are not pooled or
silently ranked by filename.

[The evidence manifest](../data/processed/evidence_manifest.json) records input
paths/hashes, output hashes and dataset status. [File-level results](../reports/evidence_ingestion.json)
include unsupported and failed CSV/TSV files. The FSIS adapter separately checks
embedded product metadata, primary-row counts and repeated sample identities;
[its report](../reports/fsis_ingestion.json) records accepted sources and errors.
Corrupt files do not stop other sources. A conflicting, failed or omitted latest
input can leave previous derived bytes on disk while the explorer reports that
those bytes are unavailable for the latest ingestion.

The explorer checks semantic schema and manifests, then computes the checksum
and parses values from the same bounded immutable request snapshot. A changed
derived table cannot inherit an old manifest checksum. Schema-only legacy output
without a manifest is labeled as such. [The recorded re-ingestion comparison](../reports/ingestion_verification.json)
checks the eight existing tables against their earlier values/dtypes and records
whether model artifacts changed; it is distinct from a model retraining run.

## USDA county context

[The Food Environment adapter](../backend/ingestion/usda.py) recognizes the
supplied workbook using embedded USDA metadata, Variable List definitions and
ACCESS/STORES sheets. [The audit](../scripts/audit_data.py) also records bounded
content evidence for this source family. The separate adapter validates all
supported Missouri rows before publication; audit recognition alone does not
establish complete data coverage.

[The USDA report](../reports/usda_food_environment.json) records 115 county and
county-equivalent FIPS identities, ten variables, source/output SHA-256, units,
years and denominators. `GROC20` and `GROCPTH20` each have 39 missing/suppressed
values; the other eight selected variables have no missing values in this
extract. Missing codes remain null, with exact cell codes and source locations
retained separately. FIPS distinguishes the two source rows named St. Louis.
County context is available in Sources & evidence and as a CSV export. See
[definitions, commands and interpretation limits](food_access_context.md).
