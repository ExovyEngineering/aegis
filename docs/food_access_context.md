# Historical USDA county context

The Sources & evidence view compares Food Environment Atlas values for selected
Missouri counties/county-equivalents. This describes historical regional context.
It does not estimate shipment demand, food-safety risk or consumer illness, and
does not assign fictional destinations to counties or change allocation weights.

## Input, output and reproduction

The supplied `2025-food-environment-atlas-data.xlsx` identifies USDA Economic
Research Service in its embedded Read_Me and documents an original July 2025
release. Recognition uses that content, the Variable List and ACCESS/STORES
headers. Renaming the file does not change its identity. The adapter validates
units, vintage, county-level flags, numeric values and matching FIPS sets before
publishing a derived table.

From the repository root:

```powershell
.venv/Scripts/python scripts/ingest_usda.py
.venv/Scripts/python scripts/ingest_usda.py --data-dir C:/path/to/supplied-data
.venv/Scripts/python scripts/ingest_usda.py --file C:/path/to/selected-atlas.xlsx
```

The default uses `AEGIS_DATA_DIR`, then `data/raw/` when present, otherwise the
repository folder. Metadata-based discovery refuses multiple candidates; use
`--file` to select one explicitly. `--output-root` can write derived outputs to
an isolated review folder. No command rewrites the raw workbook.

Outputs are [the Parquet extract](../data/processed/usda_food_environment_missouri.parquet)
and [the ingestion report](../reports/usda_food_environment.json). The report
contains source/output SHA-256, import time, release note, variable metadata,
coverage, per-cell missing codes and interpretation limits. The implemented
extract contains 115 distinct Missouri FIPS identities and ten measures.

## Measures and denominators

| Original field | Vintage | Unit and interpretation |
|---|---|---|
| `LACCESS_POP19` | 2019 | Estimated persons with low foodstore access |
| `PCT_LACCESS_POP19` | 2019 | Percent of total county population with low access |
| `LACCESS_LOWI19` | 2019 | Estimated persons with both low income and low access |
| `PCT_LACCESS_LOWI19` | 2019 | Percent of total county population, not only low-income residents |
| `LACCESS_HHNV19` | 2019 | Estimated housing units without a vehicle and more than one mile from a store |
| `PCT_LACCESS_HHNV19` | 2019 | Percent of all county housing units meeting that definition |
| `GROC20` | 2020 | Supermarkets/grocery stores, Census County Business Patterns |
| `GROCPTH20` | 2020 | Grocery stores per 1,000 county residents |
| `SNAPS23` | 2023 | Average monthly SNAP-authorized stores |
| `SNAPSPTH23` | 2023 | Average monthly SNAP-authorized stores per 1,000 residents |

The access measures combine 2019 store locations with 2010 Census population
allocation and 2014-18 ACS income/vehicle inputs. Store measures have their own
vintages and definitions; these are not interchangeable annual measurements.
Population low access uses the provider's urban/rural distance thresholds.
The UI exposes each measure's definition and denominator. See the
[official USDA documentation](https://www.ers.usda.gov/data-products/food-environment-atlas/documentation)
and [source download page](https://www.ers.usda.gov/data-products/food-environment-atlas/data-access-and-documentation-downloads).

## Missingness and geographic identity

`GROC20` and `GROCPTH20` each contain 39 null observations in the Missouri extract;
the other eight selected measures contain none. The workbook documents `N/A`
and `-9999` as unavailable/not applicable/suppressed, and `-8888` for a county not
in existence in the indicator year. These codes become null, with the exact raw
cell value, FIPS, field, sheet and row retained in `coverage.missing_observations`.
The adapter does not infer which individual confidentiality or availability
reason applies. A missing value is not a measured zero. Fractional estimates
remain fractional; formulas and unsupported numeric formats fail explicitly.

FIPS is retained as a five-character string. The source uses the county text
St. Louis for two different FIPS identities, `29189` and `29510`; their labels
include FIPS so comparisons do not collapse them. No county or tract geometry
is supplied by this feature. The tract-level FARA and SRAM workbooks remain
separate, unmerged source material. Row-count completeness does not establish
current spatial coverage or complete values.

## API and verification

`GET /api/food-access` verifies the derived-file checksum and serves values parsed
from the same checked bytes. Missing data returns 404; failed ingestion,
inconsistent provenance or corrupt output returns an explicit 503.
`GET /api/food-access.csv` exports the checked county values, source hash and
interpretation; the JSON endpoint supplies units, years and denominators.
The UI rounds display values where needed and leaves missing values visibly
labeled. **Recheck local extract** performs no upstream weather/recall refresh.

Implementation: [adapter](../backend/ingestion/usda.py),
[CLI](../scripts/ingest_usda.py), [API](../backend/food_context.py),
[interface](../frontend/src/FoodAccessContext.tsx).
Evidence: [ingestion tests](../tests/test_usda_ingestion.py),
[bounded audit recognition tests](../tests/test_usda_audit.py),
[API integrity tests](../tests/test_food_context.py), and
[UI tests](../frontend/src/FoodAccessContext.test.tsx).
