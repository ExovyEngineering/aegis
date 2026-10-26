import hashlib,json,zipfile
from scripts.package_submission import build,collect

def minimal(root):
    for name in ['backend/main.py','frontend/dist/index.html','data/processed/fsis_poultry.parquet','data/fixtures/fsis_recalls.json','reports/aegis_report.md','requirements-lock.txt']:
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('fixture')

def test_package_excludes_secrets_databases_and_runtime_installs(tmp_path):
    minimal(tmp_path)
    for name in ['.env','backend/.env.production','backend/private.sqlite','frontend/node_modules/pkg/index.js','.tools/kiro/account.json','original_raw.json','reports/server.log']:
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('must not be bundled')
    result=build(tmp_path,tmp_path/'draft.zip')
    with zipfile.ZipFile(result['archive']) as z:
        names=z.namelist();assert 'backend/main.py' in names
        assert not any('node_modules' in n or '.tools' in n or '.env' in n or n.endswith(('.sqlite','.log')) for n in names)
        assert 'original_raw.json' not in names
        manifest=json.loads(z.read('PACKAGE_MANIFEST.json'))
        assert manifest['draft'] and not manifest['genuine_kiro_execution_verified']
        for entry in manifest['files']:assert hashlib.sha256(z.read(entry['path'])).hexdigest()==entry['sha256']

def test_noaa_manifest_cannot_export_arbitrary_files(tmp_path):
    minimal(tmp_path)
    (tmp_path/'reports/noaa_coverage.json').write_text(json.dumps({'stations':[{'raw_response_path':'backend/main.py'}]}))
    import pytest
    with pytest.raises(ValueError,match='escapes'):collect(tmp_path)
