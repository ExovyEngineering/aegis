import hashlib
import json
import sys

import openpyxl
import pytest

import scripts.audit_data as audit


def atlas(path,edit=None):
    workbook=openpyxl.Workbook()
    read_me=workbook.active;read_me.title='Read_Me'
    read_me.append(['Food Environment Atlas data download'])
    read_me.append(['Contact: example'])
    read_me.append(['Source: USDA, Economic Research Service using data from various sources.'])
    variables=workbook.create_sheet(' Variable List')
    variables.append(['Variable List'])
    variables.append(['Category Name','Category Code','Subcategory Name','Variable Name','Variable Code','Units'])
    variables.append(['Access and Proximity to Foodstore','ACCESS','Overall','Population, low access to store, 2015','LACCESS_POP15','Count'])
    variables.append(['Access and Proximity to Foodstore','ACCESS','Overall','Population, low access to store, 2019','LACCESS_POP19','Count'])
    for name,columns in [('ACCESS',['LACCESS_POP19','PCT_LACCESS_POP19','LACCESS_LOWI19']),
                         ('STORES',['GROC20','GROCPTH20','SNAPS23','SNAPSPTH23'])]:
        sheet=workbook.create_sheet(name)
        sheet.append([name]);sheet.append(['FIPS','State','County',*columns])
        sheet.append(['29019','MO','Boone',*([0]*len(columns))])
    if edit:edit(workbook)
    workbook.save(path);workbook.close()
    return path


def test_audit_identifies_renamed_atlas_by_bounded_content_and_preserves_raw(tmp_path):
    path=atlas(tmp_path/'renamed_without_source_hint.xlsx')
    original=path.read_bytes()
    result=audit.inspect_file(path)
    assert result['errors']==[]
    assert result['likely_source']=='USDA Food Environment Atlas'
    assert result['sha256']==hashlib.sha256(original).hexdigest()
    assert path.read_bytes()==original
    evidence=result['source_recognition']
    assert evidence['title']=='Food Environment Atlas data download'
    assert 'USDA, Economic Research Service' in evidence['provider_excerpt']
    assert evidence['variable_evidence']=={'code':'LACCESS_POP19','unit':'Count','label':'Population, low access to store, 2019'}
    assert 'source-family recognition only' in evidence['limitation'].lower()


@pytest.mark.parametrize('mutation',[
    lambda w:w['Read_Me'].__setitem__('A1','A generic food-store workbook'),
    lambda w:w['Read_Me'].__setitem__('A3','Source: unverified producer'),
    lambda w:w[' Variable List'].__setitem__('F4','A different unit'),
    lambda w:w[' Variable List'].__setitem__('D4','Population 2019 *'),
    lambda w:w['STORES'].__setitem__('F2','UNKNOWN_FIELD'),
    lambda w:w.remove(w['STORES']),
])
def test_misleading_filename_or_partial_metadata_does_not_establish_atlas_identity(tmp_path,mutation):
    result=audit.inspect_file(atlas(tmp_path/'2025-food-environment-atlas-data.xlsx',mutation))
    assert result['errors']==[]
    assert result['likely_source']!='USDA Food Environment Atlas'
    assert 'source_recognition' not in result


def test_source_recognition_is_bounded_and_keeps_declared_row_dimensions(tmp_path,monkeypatch):
    path=atlas(tmp_path/'large_declared.xlsx',lambda w:w['ACCESS'].__setitem__('A1000000','Outside the sample'))
    from openpyxl.worksheet._read_only import ReadOnlyWorksheet
    original=ReadOnlyWorksheet.iter_rows
    seen={}
    def bounded_rows(sheet,*args,**kwargs):
        for row in original(sheet,*args,**kwargs):
            seen[sheet.title]=seen.get(sheet.title,0)+1
            assert seen[sheet.title]<=201
            yield row
    monkeypatch.setattr(ReadOnlyWorksheet,'iter_rows',bounded_rows)
    result=audit.inspect_file(path)
    assert result['likely_source']=='USDA Food Environment Atlas'
    assert result['errors']==[]
    assert seen['ACCESS']==201
    access=next(sheet for sheet in result['sheets'] if sheet['name']=='ACCESS')
    assert access['declared_rows']==1000000
    assert 'Outside the sample' not in str(result['sheets'])


def test_corrupt_workbook_is_recorded_and_audit_continues_to_other_files(tmp_path,monkeypatch,capsys):
    supplied=tmp_path/'supplied';supplied.mkdir()
    atlas(supplied/'renamed.xlsx')
    partial=supplied/'partial.xlsx';partial.write_bytes(b'partial download')
    (supplied/'other.csv').write_text('item\n1\n',encoding='utf-8')
    output=tmp_path/'audit';output.mkdir()
    monkeypatch.setattr(audit,'ROOT',output)
    monkeypatch.setattr(sys,'argv',['audit_data.py','--data-dir',str(supplied)])
    audit.main()
    report=json.loads((output/'data/manifests/inventory.json').read_text())
    assert len(report['files'])==3
    failed=next(item for item in report['files'] if item['filename']=='partial.xlsx')
    assert failed['errors']==['BadZipFile: File is not a zip file']
    assert failed['sha256']==hashlib.sha256(b'partial download').hexdigest()
    assert next(item for item in report['files'] if item['filename']=='renamed.xlsx')['likely_source']=='USDA Food Environment Atlas'
    assert next(item for item in report['files'] if item['filename']=='other.csv')['row_count']==1
    assert 'Audit renamed.xlsx' in capsys.readouterr().out


def test_generic_workbook_stays_unrecognized_despite_usda_filename(tmp_path):
    workbook=openpyxl.Workbook()
    workbook.active.append(['id','quantity'])
    workbook.active.append(['x',2])
    path=tmp_path/'USDA_Food_Environment_Atlas.xlsx'
    workbook.save(path);workbook.close()
    result=audit.inspect_file(path)
    assert result['likely_source']=='Unrecognized / documentation; do not merge'
    assert 'source_recognition' not in result


def test_repository_audit_skips_runtime_credentials_and_editor_settings(tmp_path,monkeypatch):
    supplied=tmp_path/'supplied';supplied.mkdir()
    (supplied/'raw.csv').write_text('id\n1\n')
    for name in ('.aws','.codex','.agents','.vscode'):
        directory=supplied/name;directory.mkdir()
        (directory/'settings.json').write_text('{"local_account":"not a dataset"}')
    output=tmp_path/'audit';output.mkdir()
    monkeypatch.setattr(audit,'ROOT',output)
    monkeypatch.setattr(sys,'argv',['audit_data.py','--data-dir',str(supplied)])
    audit.main()
    report=json.loads((output/'data/manifests/inventory.json').read_text())
    assert [item['filename'] for item in report['files']]==['raw.csv']
