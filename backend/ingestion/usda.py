"""Bounded, county-level context from the USDA Food Environment Atlas.

This adapter deliberately supports ten inspected variables in ACCESS and STORES.
It does not read health/state-level indicators, build allocation weights, infer
tract membership, or turn missing/suppressed observations into zeros.
"""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import math
import os
from pathlib import Path
import re
import tempfile
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import openpyxl
import pandas as pd

from backend.paths import ROOT, write_json


SOURCE_ID = 'usda_food_environment'
SOURCE_URL = 'https://www.ers.usda.gov/data-products/food-environment-atlas/data-access-and-documentation-downloads'
DOCUMENTATION_URL = 'https://www.ers.usda.gov/data-products/food-environment-atlas/documentation'
PROCESSED_PATH = 'data/processed/usda_food_environment_missouri.parquet'
REPORT_PATH = 'reports/usda_food_environment.json'

# Codes, vintage and units must agree with the workbook's own Variable List.
# Denominators/brief definitions were checked against official USDA documentation.
VARIABLES = {
    'LACCESS_POP19': ('ACCESS', 'Count', 2019, 'Not a ratio; estimated persons', 'People beyond 1 urban mile or 10 rural miles from a foodstore.'),
    'PCT_LACCESS_POP19': ('ACCESS', 'Percent', 2019, 'Total county population (2010 Census allocation)', 'Share of county population with low foodstore access.'),
    'LACCESS_LOWI19': ('ACCESS', 'Count', 2019, 'Not a ratio; estimated persons', 'Low-income people with low foodstore access.'),
    'PCT_LACCESS_LOWI19': ('ACCESS', 'Percent', 2019, 'Total county population, not only low-income residents', 'Share of county population with both low income and low access.'),
    'LACCESS_HHNV19': ('ACCESS', 'Count', 2019, 'Not a ratio; estimated housing units', 'Housing units without a vehicle and more than 1 mile from a foodstore.'),
    'PCT_LACCESS_HHNV19': ('ACCESS', 'Percent', 2019, 'Total county housing units', 'Share of housing units without a vehicle and more than 1 mile from a foodstore.'),
    'GROC20': ('STORES', 'Count', 2020, 'Not a ratio; stores', 'County supermarkets and grocery stores; Census County Business Patterns.'),
    'GROCPTH20': ('STORES', '# per 1,000 pop', 2020, 'County residents / 1,000', 'Grocery stores per 1,000 county residents.'),
    'SNAPS23': ('STORES', 'Count', 2023, 'Not a ratio; average monthly stores', 'Average monthly SNAP-authorized stores, excluding meal-service providers.'),
    'SNAPSPTH23': ('STORES', '# per 1,000 pop', 2023, 'County residents / 1,000', 'Average monthly SNAP-authorized stores per 1,000 residents.'),
}
LIMITATIONS = [
    'Historical county/county-equivalent context, not current household access, shipment demand, food-safety risk or an illness estimate.',
    'ACCESS uses 2019 store access with 2010 Census population allocation and 2014-18 ACS income/vehicle data; store counts have separate 2020/2023 vintages.',
    'Access counts can be fractional estimates. Percentages use different population or housing-unit denominators; they are not interchangeable.',
    'Missing/suppressed/not-applicable cells stay null with their original missing code recorded; a missing value is not a measured zero.',
    'FIPS is the identity key. County names can repeat, including St. Louis county/city rows. No route-coordinate, tract, or simulated-destination join is performed.',
    'No geometry, allocation weighting, causal health inference, or comparison between different atlas vintages is implemented.',
]


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _sheet_names(path):
    """Inspect only ZIP workbook metadata, without loading large sheet payloads."""
    with ZipFile(path) as archive:
        info = archive.getinfo('xl/workbook.xml')
        if info.file_size > 2 * 1024 * 1024:
            raise ValueError('Workbook metadata exceeds the supported 2 MiB bound')
        root = ET.fromstring(archive.read(info))
    return {element.attrib['name'].strip() for element in root.iter()
            if element.tag.rsplit('}', 1)[-1] == 'sheet'}


def discover_food_environment_files(folder):
    """Filename-independent candidate detection; full content is validated later."""
    candidates, errors = [], []
    folder = Path(folder)
    for path in sorted(folder.rglob('*.xlsx')):
        if any(part in {'.tools', '.venv', 'node_modules', '.git'} for part in path.relative_to(folder).parts):
            continue
        try:
            if {'Read_Me', 'Variable List', 'ACCESS', 'STORES'} <= _sheet_names(path):
                candidates.append(path)
        except Exception as exc:
            errors.append({'file': str(path), 'error': f'{type(exc).__name__}: {exc}'})
    return candidates, errors


def _fips(value, location):
    if isinstance(value, bool):
        raise ValueError(f'{location}: invalid county FIPS {value!r}')
    if isinstance(value, (int, float)):
        if not math.isfinite(value) or value != int(value) or not 0 <= value <= 99999:
            raise ValueError(f'{location}: invalid county FIPS {value!r}')
        value = f'{int(value):05d}'
    if not isinstance(value, str) or not re.fullmatch(r'\d{5}', value):
        raise ValueError(f'{location}: expected five-digit county FIPS, got {value!r}')
    return value


def _number(value, code, location):
    # Sentinel meaning is taken from Read_Me, never guessed from numeric range.
    if value is None or value == '':
        return None, 'blank'
    if isinstance(value, str):
        value = value.strip()
        if value == '':
            return None, 'blank'
        if value == 'N/A':
            return None, 'N/A: unavailable/not applicable/suppressed'
    if value in (-9999, '-9999'):
        return None, '-9999: unavailable/not applicable/suppressed'
    if value in (-8888, '-8888'):
        return None, '-8888: county did not exist in indicator year'
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError(f'{location}: unsupported numeric value {value!r}')
    if isinstance(value, str) and not re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?', value):
        raise ValueError(f'{location}: unsupported numeric value {value!r}')
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f'{location}: invalid nonnegative observation {value!r}')
    if VARIABLES[code][1] == 'Percent' and number > 100:
        raise ValueError(f'{location}: percentage outside 0-100: {value!r}')
    return number, None


class FoodEnvironmentAtlasAdapter:
    """Read supported Missouri rows and metadata without changing the workbook."""

    def read(self, path):
        path = Path(path)
        original_hash = sha256(path)
        # Do not silently treat an unevaluated formula as a blank observation.
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=False)
        try:
            sheet_names = {name.strip(): name for name in workbook.sheetnames}
            if len(sheet_names) != len(workbook.sheetnames):
                raise ValueError('Ambiguous workbook sheet names after whitespace normalization')
            missing = {'Read_Me', 'Variable List', 'ACCESS', 'STORES'} - set(sheet_names)
            if missing:
                raise ValueError(f'Food Environment Atlas schema missing sheets: {sorted(missing)}')
            read_me = [str(row[0]) for row in workbook[sheet_names['Read_Me']].iter_rows(values_only=True)
                       if row and row[0] is not None]
            combined = '\n'.join(read_me)
            if not read_me or read_me[0] != 'Food Environment Atlas data download' or 'USDA, Economic Research Service' not in combined:
                raise ValueError('Workbook content does not identify the USDA Food Environment Atlas')
            if not all(text in combined for text in ('N/A', '-9999', '-8888', 'State-level')):
                raise ValueError('Workbook missing-value and geographic-level documentation is unsupported')
            release_notes = [line for line in read_me if 'original release date' in line.lower()]
            if len(release_notes) != 1:
                raise ValueError('Workbook must document one original release date')
            metadata = self._variables(workbook[sheet_names['Variable List']])
            rows_by_sheet, coverage = {}, {}
            missing_reasons = {code: Counter() for code in VARIABLES}
            missing_observations = []
            for sheet in ('ACCESS', 'STORES'):
                rows_by_sheet[sheet], coverage[sheet] = self._rows(
                    workbook[sheet_names[sheet]], sheet, missing_reasons, missing_observations)
            if set(rows_by_sheet['ACCESS']) != set(rows_by_sheet['STORES']):
                raise ValueError('ACCESS and STORES Missouri county FIPS sets differ; no partial join is allowed')
            if not rows_by_sheet['ACCESS']:
                raise ValueError('No Missouri county rows found in supported atlas sheets')
            records = []
            for fips in sorted(rows_by_sheet['ACCESS']):
                access, stores = rows_by_sheet['ACCESS'][fips], rows_by_sheet['STORES'][fips]
                if (access['State'], access['County']) != (stores['State'], stores['County']):
                    raise ValueError(f'County identity differs across sheets for FIPS {fips}')
                # The source uses the same St. Louis text for two identities; retain
                # that text and always include FIPS rather than infer a new label.
                records.append({**access, **stores,
                                'county_display_name': f"{access['County']} (FIPS {fips})"})
            frame = pd.DataFrame(records, columns=['FIPS', 'State', 'County', 'county_display_name', *VARIABLES])
            for code in VARIABLES:
                frame[code] = frame[code].astype('float64')
            report = {
                'status': 'validated', 'source_id': SOURCE_ID,
                'provider': 'USDA Economic Research Service', 'source_url': SOURCE_URL,
                'documentation_url': DOCUMENTATION_URL,
                'documentation_checked_at': '2026-10-27',
                'documentation_note': 'Definitions checked against the official documentation; supplied workbook metadata and original missing codes remain authoritative for this extract.',
                'source_file': {'filename': path.name, 'sha256': original_hash, 'size_bytes': path.stat().st_size},
                'ingested_at': datetime.now(timezone.utc).isoformat(),
                'release_note': release_notes[0],
                'geography': {'state': 'MO', 'level': 'county/county-equivalent',
                              'county_count': len(records), 'join_key': 'FIPS'},
                'variables': metadata,
                'coverage': {'sheets': coverage,
                             'null_counts': {code: sum(missing_reasons[code].values()) for code in VARIABLES},
                             'missing_reasons': {code: dict(reasons) for code, reasons in missing_reasons.items()},
                             'missing_observations': missing_observations,
                             'expected_missouri_counties': 115,
                             'coverage_complete': len(records) == 115,
                             'coverage_note': 'Completeness checks matching ACCESS/STORES FIPS sets and the expected 115 distinct Missouri county/county-equivalent rows; it does not establish current geography, complete values, or spatial coverage of routes.'},
                'records': records, 'limitations': list(LIMITATIONS),
                'provenance': 'Observed historical county context from a supplied official-source workbook; not simulated logistics, food-safety labels, or current operational measurements.',
            }
        finally:
            workbook.close()
        if sha256(path) != original_hash:
            raise RuntimeError('Source workbook changed during ingestion; no output is valid')
        return frame, report

    @staticmethod
    def _variables(sheet):
        rows = sheet.iter_rows(values_only=True)
        next(rows, None)
        header = next(rows, None)
        expected = ('Category Name', 'Category Code', 'Subcategory Name', 'Variable Name', 'Variable Code', 'Units')
        if tuple(header or ()) != expected:
            raise ValueError('Food Environment Atlas Variable List header mismatch')
        found = {}
        for row in rows:
            if len(row) < 6 or row[4] not in VARIABLES:
                continue
            code = row[4]
            if code in found:
                raise ValueError(f'Duplicate variable metadata for {code}')
            expected_sheet, unit, year, denominator, definition = VARIABLES[code]
            label = row[3]
            if row[1] != expected_sheet or row[5] != unit or not isinstance(label, str) or str(year) not in label or '*' in label:
                raise ValueError(f'Unsupported metadata, units, vintage or state-level flag for {code}')
            found[code] = {'code': code, 'label': label, 'unit': unit, 'year': year,
                           'sheet': expected_sheet, 'denominator': denominator,
                           'definition': definition, 'documentation_url': DOCUMENTATION_URL,
                           'metadata_sheet': sheet.title, 'geographic_level': 'county/county-equivalent'}
        missing = set(VARIABLES) - set(found)
        if missing:
            raise ValueError(f'Missing supported variable metadata: {sorted(missing)}')
        return [found[code] for code in VARIABLES]

    @staticmethod
    def _rows(sheet, category, missing_reasons, missing_observations):
        rows = sheet.iter_rows(values_only=True)
        title = next(rows, None)
        header = next(rows, None)
        codes = [code for code, data in VARIABLES.items() if data[0] == category]
        if not title or title[0] != category or not header or not {'FIPS', 'State', 'County', *codes} <= set(header):
            raise ValueError(f'{category}: unsupported sheet title/header')
        if len([column for column in header if column is not None]) != len({column for column in header if column is not None}):
            raise ValueError(f'{category}: duplicate column names')
        positions = {column: index for index, column in enumerate(header)}
        selected, seen, count = {}, set(), 0
        for row_number, row in enumerate(rows, start=3):
            if not any(value is not None and value != '' for value in row):
                continue
            get = lambda key: row[positions[key]] if positions[key] < len(row) else None
            location = f'{category} row {row_number}'
            fips = _fips(get('FIPS'), location)
            state, county = get('State'), get('County')
            if not isinstance(state, str) or not re.fullmatch(r'[A-Z]{2}', state) or not isinstance(county, str) or not county.strip():
                raise ValueError(f'{location}: invalid state/county identity')
            if fips in seen:
                raise ValueError(f'{location}: duplicate county FIPS {fips}')
            seen.add(fips)
            count += 1
            if (state == 'MO') != fips.startswith('29'):
                raise ValueError(f'{location}: Missouri state/FIPS mismatch {state}/{fips}')
            if state != 'MO':
                continue
            record = {'FIPS': fips, 'State': state, 'County': county}
            for code in codes:
                record[code], reason = _number(get(code), code, f'{location} {code}')
                if reason:
                    missing_reasons[code][reason] += 1
                    missing_observations.append({'FIPS': fips, 'field': code, 'source_value': get(code),
                                                 'reason': reason, 'sheet': sheet.title,
                                                 'row_number': row_number})
            selected[fips] = record
        return selected, {'national_rows': count, 'missouri_rows': len(selected), 'header_row': 2}


def ingest_food_environment(path, output_root=ROOT):
    """Write only derived output, preserving original bytes and a verifiable hash."""
    root = Path(output_root)
    frame, report = FoodEnvironmentAtlasAdapter().read(path)
    target = root / PROCESSED_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, suffix='.parquet', delete=False) as stream:
            temporary = Path(stream.name)
        frame.to_parquet(temporary, index=False)
        output_hash = sha256(temporary)
        os.replace(temporary, target)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    report['processed_file'] = {'path': PROCESSED_PATH, 'sha256': output_hash,
                                'rows': len(frame), 'columns': list(frame)}
    report['status'] = 'available'
    write_json(root / REPORT_PATH, report)
    return report
