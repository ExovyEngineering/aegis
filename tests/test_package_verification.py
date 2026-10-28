"""Reviewer archives are checked before trusted code runs, in an isolated process."""
import hashlib
import json
from pathlib import Path
import shutil
import socket
import stat
import zipfile

import pytest

from scripts.package_submission import build
from scripts.verify_package import ROOT,no_network,safe_member,validate_and_extract,verify_package


def archive(path,files=None,edit_manifest=None,extra=None):
    files=files or {'README.md':b'trusted test fixture'}
    manifest={'draft':True,'files':[{'path':name,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()} for name,body in files.items()]}
    if edit_manifest:edit_manifest(manifest)
    with zipfile.ZipFile(path,'w') as zipped:
        for name,body in files.items():zipped.writestr(name,body)
        zipped.writestr('PACKAGE_MANIFEST.json',json.dumps(manifest))
        if extra:
            for name,body in extra.items():zipped.writestr(name,body)
    return path


def empty_target(tmp_path):
    target=tmp_path/'extracted';target.mkdir();return target


@pytest.mark.parametrize('name',['../outside.txt','a/../../outside.txt','/absolute.txt','C:/outside.txt','a\\outside.txt','a//b.txt','a/./b.txt','a:b.txt','NUL.txt','a/COM1.json','a/trailing.'])
def test_nonportable_or_escaping_paths_are_rejected_before_writing(tmp_path,name):
    zipped=archive(tmp_path/'bad.zip',{name:b'escape'})
    target=empty_target(tmp_path);marker=tmp_path/'outside.txt';marker.write_text('unchanged')
    with pytest.raises(ValueError,match='archive path'):validate_and_extract(zipped,target)
    assert marker.read_text()=='unchanged' and list(target.iterdir())==[]


@pytest.mark.parametrize('name',['.env','backend/.env.production','.aws/credentials','.tools/account.json','backend/private.pem','data/operator.sqlite','data/operator.sqlite-wal','data/operator.db-journal','frontend/node_modules/pkg.js','data/backups/private/manifest.json','data/recovered/private.sqlite.restore.json'])
def test_private_credentials_runtime_and_operator_state_are_forbidden(tmp_path,name):
    zipped=archive(tmp_path/'bad.zip',{name:b'private'})
    target=empty_target(tmp_path)
    with pytest.raises(ValueError,match='Forbidden'):validate_and_extract(zipped,target)
    assert list(target.iterdir())==[]


def test_environment_example_is_allowed_and_all_hashes_are_verified(tmp_path):
    files={'.env.example':b'AEGIS_DATA_DIR=','backend/main.py':b'# trusted code','README.md':b'reviewer instructions'}
    zipped=archive(tmp_path/'valid.zip',files);target=empty_target(tmp_path)
    result=validate_and_extract(zipped,target)
    assert result['manifest_files_verified']==3 and result['archive_files']==4
    assert all((target/name).read_bytes()==body for name,body in files.items())


@pytest.mark.parametrize('change',['hash','size','missing_member','unexpected_member','duplicate_manifest_path'])
def test_manifest_tampering_cannot_extract_or_modify_existing_work(tmp_path,change):
    def edit(manifest):
        first=manifest['files'][0]
        if change=='hash':first['sha256']='0'*64
        if change=='size':first['bytes']+=1
        if change=='missing_member':first['path']='absent.txt'
        if change=='duplicate_manifest_path':manifest['files'].append(dict(first))
    zipped=archive(tmp_path/'bad.zip',edit_manifest=edit,extra={'unlisted.txt':b'unlisted'} if change=='unexpected_member' else None)
    target=empty_target(tmp_path)
    with pytest.raises(ValueError):validate_and_extract(zipped,target)
    assert list(target.iterdir())==[]


def test_symlink_member_is_rejected_before_extraction(tmp_path):
    zipped=tmp_path/'symlink.zip'
    with zipfile.ZipFile(zipped,'w') as stream:
        link=zipfile.ZipInfo('backend/link.py');link.create_system=3;link.external_attr=(stat.S_IFLNK|0o777)<<16
        stream.writestr(link,'../../outside.py')
        stream.writestr('PACKAGE_MANIFEST.json','{}')
    target=empty_target(tmp_path)
    with pytest.raises(ValueError,match='Symlink'):validate_and_extract(zipped,target)
    assert list(target.iterdir())==[]


def test_case_colliding_paths_are_rejected_on_every_platform(tmp_path):
    zipped=archive(tmp_path/'case.zip',{'README.md':b'one','readme.md':b'two'})
    target=empty_target(tmp_path)
    with pytest.raises(ValueError,match='case-colliding'):validate_and_extract(zipped,target)


def test_network_guard_blocks_dns_and_socket_attempts_without_contacting_a_host():
    with no_network() as attempts:
        with pytest.raises(RuntimeError,match='networking disabled'):socket.getaddrinfo('example.invalid',443)
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as connection:
            with pytest.raises(RuntimeError,match='networking disabled'):connection.connect(('192.0.2.1',443))
        with pytest.raises(RuntimeError,match='networking disabled'):socket.create_connection(('192.0.2.1',443))
        # Internal event-loop self-pipes remain usable, including Windows's
        # loopback fallback; arbitrary loopback application requests stay denied.
        left,right=socket.socketpair()
        try:left.send(b'x');assert right.recv(1)==b'x'
        finally:left.close();right.close()
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as connection:
            with pytest.raises(RuntimeError,match='networking disabled'):connection.connect(('127.0.0.1',9))
    assert [entry['operation'] for entry in attempts]==['DNS','socket.connect','socket.create_connection','socket.connect']


def test_failed_validation_reports_exact_failure_and_keeps_original_database(tmp_path):
    database=tmp_path/'data/aegis.sqlite';database.parent.mkdir();database.write_bytes(b'operator state must stay unchanged')
    zipped=archive(tmp_path/'invalid.zip',{'../outside.txt':b'cannot escape'})
    result=verify_package(zipped,workspace=tmp_path)
    assert result['status']=='failed' and result['passed'] is False
    assert result['archive_sha256']==hashlib.sha256(zipped.read_bytes()).hexdigest()
    assert result['operator_database_modified'] is False and result['network_requested'] is False
    assert result['check_results'][0]['status']=='failed'
    assert 'Unsafe archive path' in result['error']
    assert database.read_bytes()==b'operator state must stay unchanged'
    assert list((tmp_path/'.tools/package-verification').iterdir())==[]


def test_actual_extracted_backend_runs_offline_with_installed_dependencies(tmp_path,monkeypatch):
    # Package the current trusted backend and checked-in evidence. A tiny static
    # page replaces the build output so pytest also works before npm build in CI.
    source=tmp_path/'trusted-source';source.mkdir()
    shutil.copytree(ROOT/'backend',source/'backend',ignore=shutil.ignore_patterns('__pycache__'))
    (source/'scripts').mkdir()
    shutil.copy2(ROOT/'scripts/backup_state.py',source/'scripts/backup_state.py')
    for name in ('data/processed','data/fixtures','data/manifests'):
        shutil.copytree(ROOT/name,source/name)
    required_reports=('api_status.json','model_evaluation.json','model_timing.json','noaa_coverage.json','evidence_ingestion.json','usda_food_environment.json','fsis_ingestion.json','project_brief_manifest.json','project_brief.md','aegis_project_brief.pdf','aegis_report.md')
    (source/'reports').mkdir()
    for name in required_reports:shutil.copy2(ROOT/'reports'/name,source/'reports'/name)
    shutil.copy2(ROOT/'requirements-lock.txt',source/'requirements-lock.txt')
    frontend=source/'frontend/dist';(frontend/'assets').mkdir(parents=True)
    (frontend/'index.html').write_text('<html><title>AEGIS package test</title><script src="/assets/fixture.js"></script></html>')
    (frontend/'assets/fixture.js').write_text('// Packaged asset used only by backend integration verification')
    zipped=tmp_path/'reviewer.zip';build(source,zipped)
    workspace=tmp_path/'operator-workspace';database=workspace/'data/aegis.sqlite';database.parent.mkdir(parents=True)
    database.write_bytes(b'original operator state')
    # An inherited DB variable and checkout Python path must not escape worker isolation.
    monkeypatch.setenv('AEGIS_DB_PATH',str(database));monkeypatch.setenv('PYTHONPATH',str(ROOT))
    result=verify_package(zipped,workspace)
    assert result['passed'],result
    assert result['status']=='passed' and result['worker_exit_code']==0
    assert result['manifest_files_verified']>30
    assert result['fresh_python_environment'] is False
    assert result['isolated_extracted_directory'] is True
    assert result['network_guard_enabled'] is True and result['network_requested'] is False
    assert result['network_attempts']==[] and result['operator_database_modified'] is False
    assert all(check['status']=='passed' for check in result['check_results'])
    assert any('USDA' in check for check in result['checks']) and any('readiness' in check for check in result['checks'])
    assert any('Iowa' in check for check in result['checks']) and any('backup' in check for check in result['checks'])
    assert database.read_bytes()==b'original operator state'
    assert list((workspace/'.tools/package-verification').iterdir())==[]
