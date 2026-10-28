"""Build a local, allowlisted reviewer ZIP; never bundle credentials or live state."""
import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.paths import ROOT,write_json

ROOT_FILES=('CONTRIBUTING.md','.gitattributes','AGENTS.md','README.md','requirements.txt','requirements-lock.txt','.env.example','.gitignore')
SOURCE_DIRS=('.github','backend','scripts','tests','config','docs','.kiro','frontend')
SKIP={'node_modules','__pycache__','.venv','.tools','.git','.pytest_cache','.env'}
REPORTS=('usda_food_environment.json','fsis_ingestion.json','ingestion_verification.json','transport_check.json','source_actions.json','operational_state_preservation.json','aegis_project_brief.pdf','project_brief.md','project_brief_manifest.json','session_verification.json','aegis_report.md','data_audit.md','api_status.json','model_evaluation.json','model_timing.json','model_timing.md','noaa_coverage.json','noaa_coverage.md','demo_results.json','operations_demo.json','demo_script.md','validation.json','http_smoke.json','raw_integrity.json','evidence_ingestion.json','route_lab_osrm.json','kiro_requirement_review.md','kiro_installation.json')
REPORTS=REPORTS+('clean_install.json',)
REPORTS=REPORTS+('backup_recovery.json','road_intelligence_live.json','stretch_verification.json','ci_followup.json')
GUIDE='''# AEGIS reviewer draft

This package is a review artifact, not a final approved competition submission.
It includes source, a prebuilt frontend, processed source data, dated public
fixtures, measured results, the scientific draft report and figures.
All logistics and cargo telemetry are simulated. Read docs/priority_matrix.md.

## Run the packaged app

Install Python 3.13, then run from the extracted directory in PowerShell:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-lock.txt
.venv/Scripts/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. The included frontend/dist means Node is not needed
to view this build. Node/npm are needed to rebuild frontend source or run Vitest.
Map tiles and live API requests require internet. Source views fall back to
explicitly dated fixtures. Route laboratory estimated mode works offline;
OSRM requests can fail over to visibly labeled estimates.

## Reproduce supplied results

```powershell
.venv/Scripts/python scripts/train_model.py
.venv/Scripts/python scripts/validate_model_timing.py
.venv/Scripts/python scripts/acquire_noaa.py
.venv/Scripts/python scripts/demo_run.py
.venv/Scripts/python scripts/build_submission_report.py
.venv/Scripts/python -m pytest -q
```

The original large supplied downloads are excluded. Their audited filenames,
schemas and SHA-256 values remain in data/manifests/inventory.json. Set
AEGIS_DATA_DIR to the original data folder to repeat ingestion/audit. Do not
run the raw audit against this extracted code package expecting original files.
Packaged Parquet tables permit model reproduction; NOAA originals are included
with their provider response/checksum metadata. Absolute paths in historical
audit reports describe the source workstation, not the extracted location.

For an isolated guided rehearsal, start a second server with
`.venv/Scripts/python scripts/start_rehearsal.py --port 8001` and open the printed
URL. Check the isolated-runtime banner; a query parameter alone is not isolation.
The six stages and server timer retain immutable evidence without resetting the
operator database. Default rehearsal uses dated fixtures and route estimates.
See docs/rehearsal_guide.md and docs/core_release.md.

Credentials, .env, operational SQLite state, runtime installations, Kiro account
data and node_modules are excluded. The app creates a fresh simulated database.
Kiro must be installed separately; installation/version evidence is not genuine
spec execution. Sign-in and authentic Kiro work remain pending. Prospective
model validity, complete historical weather coverage, truck-safe routing and
the final organizer rubric are not certified by this package.

PACKAGE_MANIFEST.json records every bundled file's SHA-256 and byte length.
Nothing has been uploaded or submitted by creating this ZIP.
'''

def allowed(path):
    return not any(part in SKIP or part.startswith('.env') and part!='.env.example' for part in path.parts) and path.suffix.lower() not in {'.sqlite','.sqlite3','.db','.log','.pyc','.exe','.dll'}

def collect(root):
    files={}
    def add(path):
        rel=path.relative_to(root)
        if path.is_file() and not path.is_symlink() and allowed(rel):files[rel.as_posix()]=path
    for name in ROOT_FILES:add(root/name)
    for name in SOURCE_DIRS:
        folder=root/name
        if folder.exists():
            for path in folder.rglob('*'):add(path)
    for name in REPORTS:add(root/'reports'/name)
    for directory in ('data/processed','data/fixtures','data/manifests','reports/figures','reports/browser_qa/final','reports/browser_qa/operations','reports/browser_qa/depth','reports/browser_qa/drive','reports/browser_qa/controls','reports/browser_qa/readiness','reports/browser_qa/rehearsal','reports/browser_qa/roads','reports/checks','reports/verification_history'):
        folder=root/directory
        if folder.exists():
            for path in folder.rglob('*'):add(path)
    # Only include NOAA responses/metadata actually referenced by the coverage report.
    coverage=root/'reports/noaa_coverage.json'
    if coverage.exists():
        for station in json.loads(coverage.read_text(encoding='utf-8')).get('stations',[]):
            relative=station.get('raw_response_path')
            if relative:
                raw=root/Path(relative.replace('\\','/'))
                try:raw.resolve().relative_to((root/'data/external/noaa').resolve())
                except ValueError:raise ValueError('NOAA response path escapes expected source folder')
                add(raw);add(raw.with_name(raw.name.replace('.response.json','.metadata.json')))
    return files

def build(root,output):
    files=collect(root)
    required=('backend/main.py','frontend/dist/index.html','data/processed/fsis_poultry.parquet','data/fixtures/fsis_recalls.json','reports/aegis_report.md','requirements-lock.txt')
    missing=[p for p in required if p not in files]
    if missing:raise ValueError('Draft package missing required files: '+', '.join(missing))
    entries={name:path.read_bytes() for name,path in files.items()}
    entries['REVIEWER_START.md']=GUIDE.encode()
    manifest={'draft':True,'genuine_kiro_execution_verified':False,'original_downloads_included':False,'files':[{'path':name,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()} for name,body in sorted(entries.items())]}
    entries['PACKAGE_MANIFEST.json']=json.dumps(manifest,indent=2).encode()
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for name,body in sorted(entries.items()):
            info=zipfile.ZipInfo(name,(2026,10,26,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16;archive.writestr(info,body)
    return {'archive':str(output),'bytes':output.stat().st_size,'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'file_count':len(entries),'draft':True,'excluded':['original supplied downloads','credentials and .env','operational SQLite databases','runtime/Kiro installations and account data','node_modules','logs'],'uploaded':False}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'artifacts/aegis-review-draft.zip');args=parser.parse_args()
    result=build(ROOT,args.output);write_json(ROOT/'reports/submission_package.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':main()
