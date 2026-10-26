# Data catalog

Canonical file-level evidence is `data/manifests/inventory.json`; the readable audit is `reports/data_audit.md`. Original files remain in their supplied location. File size, SHA-256, format, schema samples, nested JSON table counts, timestamp ranges, duplicate hashes, workbook dimensions, archive members, and exact read errors are stored where supported.

## Supplied evidence

| Source | Current use | Boundary |
|---|---|---|
| FSIS raw-poultry FY2024–FY2026 JSON | Metadata-confirmed primary tables ingested; 78,607 deduplicated primary rows in the initial run | National selected sampling; Salmonella Positive/Negative only for model study; secondary typing excluded from outcome count |
| FSIS RTE sample/full-year, raw beef/pork, egg, Siluriformes, NARMS | Inventoried and schema-inspected | No silent pooling with poultry labels; RTE example is not poultry training data |
| NORS CSV | Separate Parquet; initial run 66,713 rows | Historical outbreak evidence across modes and jurisdictions, not FSIS-linked consumer illness labels |
| NORS workbook, dictionary, PDF | Inventoried, sampled/documented | Workbook versions may overlap CSV; no automatic concatenation |
| BEAM exports | Five separate Parquet exports, 1,650 / 262,616 / 484 / 2,412 / 4,818 rows in initial run | Human surveillance, source and serotype summaries retain distinct denominators |
| FSIS MPI establishment directory | Initial run 175 Missouri rows with numeric coordinates | Official directory coordinates used for map context; no verified simulated supply relationships |
| Establishment demographics/categories, Missouri CIS workbook | Inventoried | No unvalidated identifier joins |
| USDA Food Access/Environment/SRAM workbooks | Read-only sheet and schema inspection | No food-security allocation weighting before units, vintage, geography and denominators are verified |
| FSIS annual outbreak reports, NORS documentation, other PDFs | Page count and bounded text extraction | Documentation, not observation tables |

Counts above describe the saved initial ingestion report. Reruns against a different folder can change them; machine-readable reports are authoritative.

## Public streams

The registry has 18 source/probe entries, including documentation and catalogs. `reports/api_status.json` records actual HTTP results, latency, content type, test timestamps, schema, and failures. A successful catalog probe establishes reachability only.

- FSIS recall responses are official source records captured with a retrieval timestamp. Recall matching needs genuine establishment/product/lot/date traceability; fictional lots do not provide it.
- Open-Meteo hourly temperature, precipitation, and wind are **weather forecasts** for the Columbia point, not observed cargo exposure.
- NWS active Missouri alerts are **official weather warnings**. Zero returned alerts is valid only for that request and timestamp.
- NCEI daily summaries are **observed historical weather**. The initial station/week probe remains separate from the expanded five-Missouri-station extract (January 2025–June 2026). Station identities/coordinates, daily labels, explicitly requested metric units and quality attributes are validated; all 2,730 station/day rows returned, with nine missing precipitation values. This bounded extract is not joined to FSIS and lacks publication-availability timestamps. Original bytes/checksums live in `data/external/noaa/`; `reports/noaa_coverage.json` reports row and per-variable coverage separately.
- Open-Meteo archive is **historical reanalysis**, separate from station observations.
- MoDOT lightweight probes inspect service metadata. The full refresh adapter queries incident layers as GeoJSON and retains coverage status. Eighteen layers were successfully queried in this session with no reported layer errors; route review still needs current cache timestamps and must heed any coverage warning.
- OSRM provides ordinary driving geometry and estimates. It supplies neither commercial-truck validation nor automatic current MoDOT closures.

## Audit interpretation

CSV/JSONL missingness is based on bounded row samples. Nested JSON field/null counters and table paths preserve the distinction between metadata, primary tests, and secondary tests. Workbook row dimensions are declared by the file and are not guaranteed exact nonempty observation counts. ZIP central directories are inspected without extraction or full CRC validation. PDF extraction is bounded and may miss scanned pages. JSON parsing detects syntax failures; semantic validity still requires a source-specific adapter.

Exact-byte duplicates are found by SHA-256. A partial but syntactically valid download may require provider record-count comparison; absence of a parse error is not proof of completeness. Unknown sources stay in the inventory and are not silently merged.
