import hashlib
import json
from pathlib import Path

import openpyxl
import pandas as pd
import pytest

from backend.ingestion.usda import (FoodEnvironmentAtlasAdapter, PROCESSED_PATH,
                                    REPORT_PATH, VARIABLES,
                                    discover_food_environment_files,
                                    ingest_food_environment)
from scripts.ingest_usda import main


LABELS = {
    'LACCESS_POP19': 'Population, low access to store, 2019',
    'PCT_LACCESS_POP19': 'Population, low access to store (%), 2019',
    'LACCESS_LOWI19': 'Low income & low access to store, 2019',
    'PCT_LACCESS_LOWI19': 'Low income & low access to store (%), 2019',
    'LACCESS_HHNV19': 'Households, no car & low access to store, 2019',
    'PCT_LACCESS_HHNV19': 'Households, no car & low access to store (%), 2019',
    'GROC20': 'Grocery stores, 2020',
    'GROCPTH20': 'Grocery stores/1,000 pop, 2020',
    'SNAPS23': 'SNAP-authorized stores, 2023',
    'SNAPSPTH23': 'SNAP-authorized stores/1,000 pop, 2023',
}


def make_workbook(path, edit=None):
    workbook = openpyxl.Workbook()
    read_me = workbook.active
    read_me.title = 'Read_Me'
    for text in ('Food Environment Atlas data download',
                 'Source: USDA, Economic Research Service',
                 'Unavailable/not applicable/suppressed: N/A or -9999; county not in existence: -8888; State-level measures have an asterisk.',
                 'The original release date of this file is July 2025.'):
        read_me.append([text])
    variables = workbook.create_sheet(' Variable List')
    variables.append(['Variable List'])
    variables.append(['Category Name', 'Category Code', 'Subcategory Name', 'Variable Name', 'Variable Code', 'Units'])
    for code, (sheet, unit, *_rest) in VARIABLES.items():
        variables.append(['Category', sheet, 'Overall', LABELS[code], code, unit])
    for name in ('ACCESS', 'STORES'):
        sheet = workbook.create_sheet(name)
        codes = [code for code, values in VARIABLES.items() if values[0] == name]
        sheet.append([name])
        sheet.append(['FIPS', 'State', 'County', *codes])
        sheet.append(['29019', 'MO', 'Boone', *([10.25] * len(codes))])
        sheet.append(['29189', 'MO', 'St. Louis', *([0] * len(codes))])
        sheet.append(['29510', 'MO', 'St. Louis', *([1.75] * len(codes))])
        sheet.append(['01001', 'AL', 'Autauga', *([4] * len(codes))])
    if edit:
        edit(workbook)
    workbook.save(path)
    workbook.close()
    return path


def set_cell(workbook, sheet, fips, code, value):
    target = workbook[sheet]
    headers = [cell.value for cell in target[2]]
    column = headers.index(code) + 1
    for row in target.iter_rows(min_row=3):
        if row[0].value == fips:
            target.cell(row[0].row, column).value = value
            return
    raise AssertionError('Fixture county missing')


def test_rename_safe_metadata_recognition_and_exact_fips_join(tmp_path):
    path = make_workbook(tmp_path / 'unrelated_download.xlsx')
    before = path.read_bytes()
    assert discover_food_environment_files(tmp_path) == ([path], [])
    frame, report = FoodEnvironmentAtlasAdapter().read(path)
    assert path.read_bytes() == before
    assert frame['FIPS'].tolist() == ['29019', '29189', '29510']
    assert frame['County'].tolist() == ['Boone', 'St. Louis', 'St. Louis']
    assert frame['county_display_name'].nunique() == 3
    assert frame.iloc[0]['LACCESS_POP19'] == 10.25  # Fractional estimates are not rounded.
    assert frame.iloc[1]['LACCESS_POP19'] == 0  # An observed zero stays a zero.
    assert report['geography']['join_key'] == 'FIPS'
    assert report['coverage']['sheets']['ACCESS'] == {'national_rows': 4, 'missouri_rows': 3, 'header_row': 2}
    assert report['coverage']['coverage_complete'] is False
    assert report['coverage']['expected_missouri_counties'] == 115
    variables = {item['code']: item for item in report['variables']}
    assert variables['GROCPTH20']['unit'] == '# per 1,000 pop'
    assert variables['GROCPTH20']['year'] == 2020
    assert variables['SNAPS23']['denominator'] == 'Not a ratio; average monthly stores'
    assert 'not only low-income' in variables['PCT_LACCESS_LOWI19']['denominator']
    assert 'housing units' in variables['PCT_LACCESS_HHNV19']['denominator']


def test_missing_codes_remain_null_with_separate_reasons(tmp_path):
    def edit(workbook):
        set_cell(workbook, 'STORES', '29019', 'GROC20', -9999)
        set_cell(workbook, 'STORES', '29189', 'GROC20', 'N/A')
        set_cell(workbook, 'STORES', '29510', 'GROC20', '-8888')
        set_cell(workbook, 'ACCESS', '29019', 'LACCESS_POP19', None)
    frame, report = FoodEnvironmentAtlasAdapter().read(make_workbook(tmp_path / 'atlas.xlsx', edit))
    assert frame['GROC20'].isna().all()
    assert report['coverage']['null_counts']['GROC20'] == 3
    assert len(report['coverage']['missing_reasons']['GROC20']) == 3
    missing = {(item['FIPS'], item['field']): item for item in report['coverage']['missing_observations']}
    assert missing['29019', 'GROC20']['source_value'] == -9999
    assert missing['29189', 'GROC20']['source_value'] == 'N/A'
    assert missing['29510', 'GROC20']['source_value'] == '-8888'
    assert missing['29019', 'GROC20']['sheet'] == 'STORES'
    assert report['coverage']['missing_reasons']['LACCESS_POP19'] == {'blank': 1}
    assert report['records'][0]['GROC20'] is None
    assert report['records'][1]['LACCESS_POP19'] == 0


@pytest.mark.parametrize('value', ['unknown', '1,000', float('inf'), True, -1, 'None', '=1+2'])
def test_unknown_or_invalid_observations_are_errors_not_coerced_to_null(tmp_path, value):
    # Infinity is not representable in XLSX numeric cells: use its text token to
    # exercise the parser's unsupported non-finite input path.
    if value == float('inf'):
        value = 'inf'
    path = make_workbook(tmp_path / 'atlas.xlsx', lambda w: set_cell(w, 'STORES', '29019', 'GROC20', value))
    with pytest.raises(ValueError, match='STORES row 3 GROC20'):
        FoodEnvironmentAtlasAdapter().read(path)


def test_percent_bounds_do_not_clamp_observations(tmp_path):
    path = make_workbook(tmp_path / 'atlas.xlsx', lambda w: set_cell(w, 'ACCESS', '29019', 'PCT_LACCESS_POP19', 101))
    with pytest.raises(ValueError, match='percentage outside 0-100'):
        FoodEnvironmentAtlasAdapter().read(path)


@pytest.mark.parametrize('mutation,match', [
    (lambda w: w['Read_Me'].__setitem__('A1', 'Generic food workbook'), 'does not identify'),
    (lambda w: w['Read_Me'].__setitem__('A3', 'No documented missing values'), 'missing-value'),
    (lambda w: w[' Variable List'].__setitem__('F3', 'Fraction'), 'Unsupported metadata'),
    (lambda w: w[' Variable List'].__setitem__('D3', 'Population 2024'), 'Unsupported metadata'),
    (lambda w: w[' Variable List'].__setitem__('D3', 'Population 2019 *'), 'Unsupported metadata'),
    (lambda w: w['STORES'].__setitem__('A2', 'county_code'), 'title/header'),
    (lambda w: w['STORES'].__setitem__('B3', 'KS'), 'state/FIPS mismatch'),
    (lambda w: w['STORES'].__setitem__('A3', '29189'), 'duplicate county FIPS'),
    (lambda w: w['STORES'].__setitem__('C3', 'Other county'), 'identity differs'),
    (lambda w: w['STORES'].delete_rows(3), 'FIPS sets differ'),
])
def test_schema_units_vintage_and_geographic_identity_are_validated(tmp_path, mutation, match):
    path = make_workbook(tmp_path / '2025-food-environment-atlas-data.xlsx', mutation)
    with pytest.raises(ValueError, match=match):
        FoodEnvironmentAtlasAdapter().read(path)


def test_numeric_fips_preserves_leading_zero_and_does_not_accept_ambiguous_text(tmp_path):
    def edit(workbook):
        for name in ('ACCESS', 'STORES'):
            workbook[name]['A6'] = 1001
    path = make_workbook(tmp_path / 'atlas.xlsx', edit)
    frame, report = FoodEnvironmentAtlasAdapter().read(path)
    assert len(frame) == 3 and report['coverage']['sheets']['ACCESS']['national_rows'] == 4
    workbook = openpyxl.load_workbook(path)
    workbook['ACCESS']['A3'] = '29,019'
    workbook.save(path)
    workbook.close()
    with pytest.raises(ValueError, match='five-digit county FIPS'):
        FoodEnvironmentAtlasAdapter().read(path)


def test_ingestion_outputs_hashes_records_and_source_unchanged(tmp_path):
    path = make_workbook(tmp_path / 'atlas.xlsx', lambda w: set_cell(w, 'STORES', '29019', 'GROC20', -9999))
    original = hashlib.sha256(path.read_bytes()).hexdigest()
    report = ingest_food_environment(path, tmp_path / 'derived')
    output = tmp_path / 'derived' / PROCESSED_PATH
    written = json.loads((tmp_path / 'derived' / REPORT_PATH).read_text())
    assert report == written and report['status'] == 'available'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == original == report['source_file']['sha256']
    assert report['processed_file']['sha256'] == hashlib.sha256(output.read_bytes()).hexdigest()
    assert report['processed_file']['columns'] == pd.read_parquet(output).columns.tolist()
    assert report['records'][0]['GROC20'] is None
    assert 'NaN' not in (tmp_path / 'derived' / REPORT_PATH).read_text()
    assert 'FOODINSEC_21_23' not in report['processed_file']['columns']  # State-level layer is excluded.


def test_cli_default_data_dir_env_and_duplicate_selection(tmp_path, monkeypatch, capsys):
    folder = tmp_path / 'supplied'
    folder.mkdir()
    first = make_workbook(folder / 'unexpected.xlsx')
    monkeypatch.setenv('AEGIS_DATA_DIR', str(folder))
    root = tmp_path / 'derived'
    assert main(['--output-root', str(root)]) == 0
    assert '3 Missouri' in capsys.readouterr().out
    make_workbook(folder / 'duplicate.xlsx')
    assert main(['--output-root', str(root)]) == 1
    failed = json.loads((root / REPORT_PATH).read_text())
    assert failed['status'] == 'failed' and 'Multiple candidate' in failed['error']
    assert main(['--file', str(first), '--output-root', str(root)]) == 0


def test_corrupt_workbook_discovery_records_exact_error_and_continues(tmp_path, capsys):
    make_workbook(tmp_path / 'valid.xlsx')
    (tmp_path / 'partial.xlsx').write_bytes(b'partial download')
    candidates, errors = discover_food_environment_files(tmp_path)
    assert len(candidates) == 1
    assert len(errors) == 1 and errors[0]['error'] == 'BadZipFile: File is not a zip file'
    assert main(['--data-dir', str(tmp_path), '--output-root', str(tmp_path / 'derived')]) == 0
    assert 'BadZipFile: File is not a zip file' in capsys.readouterr().err


def test_cli_read_failure_keeps_old_derived_data_and_reports_error(tmp_path, capsys):
    target = tmp_path / PROCESSED_PATH
    target.parent.mkdir(parents=True)
    target.write_bytes(b'prior data')
    partial = tmp_path / 'partial.xlsx'
    partial.write_bytes(b'partial download')
    assert main(['--file', str(partial), '--output-root', str(tmp_path)]) == 1
    assert target.read_bytes() == b'prior data'
    failed = json.loads((tmp_path / REPORT_PATH).read_text())
    assert failed['status'] == 'failed' and failed['error'].startswith('BadZipFile:')
    assert 'BadZipFile:' in capsys.readouterr().err
