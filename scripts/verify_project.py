"""Execute local release checks and record exact commands, exits, logs and timestamps."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]


def main():
    stamp=datetime.now(timezone.utc).isoformat()
    node=shutil.which('node') or str(ROOT/'.tools/node.exe')
    npm_cli=ROOT/'.tools/package/bin/npm-cli.js'
    if npm_cli.exists(): npm=[node,str(npm_cli)]
    else:
        npm_path=shutil.which('npm.cmd') or shutil.which('npm')
        if not npm_path:raise RuntimeError('Install Node.js/npm to run frontend checks')
        npm=[npm_path]
    environment=dict(os.environ)
    environment['PATH']=str(Path(node).parent)+os.pathsep+environment.get('PATH','')
    session_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    # Short explicit paths avoid Windows MAX_PATH in extracted-package and
    # isolated Jupyter tests; every run still owns a unique temporary directory.
    temp_root=ROOT/'.tools'/('pt-'+uuid.uuid4().hex[:12]);temp_root.mkdir(parents=True,exist_ok=False)
    jobs=[('pytest',[sys.executable,'-m','pytest','-q','--basetemp',str(temp_root)]),('vitest',npm+['--prefix','frontend','test']),('frontend_build',npm+['--prefix','frontend','run','build'])]
    checks=[]
    folder=ROOT/'reports/checks'/session_id;folder.mkdir(parents=True,exist_ok=True)
    for name,command in jobs:
        started=time.monotonic();checked_at=datetime.now(timezone.utc).isoformat()
        result=subprocess.run(command,cwd=ROOT,env=environment,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',timeout=300)
        output=re.sub(r'\x1b\[[0-9;]*m','',result.stdout)
        log=folder/(name+'.txt');log.write_text(output,encoding='utf-8')
        pattern=r'(\d+) passed' if name=='pytest' else r'Tests\s+(\d+) passed'
        match=re.search(pattern,output)
        check={'name':name,'command':[str(x) for x in command],'checked_at':checked_at,'exit_code':result.returncode,'passed':result.returncode==0,'duration_seconds':round(time.monotonic()-started,3),'tests_passed':int(match[1]) if match and name!='frontend_build' else None,'log':log.relative_to(ROOT).as_posix(),'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()}
        checks.append(check);print(json.dumps(check),flush=True)
    report={'generated_at':stamp,'finished_at':datetime.now(timezone.utc).isoformat(),'all_passed':all(c['passed'] for c in checks),'checks':checks,'live_api_requests_included':False,'browser_checks_included':False,'note':'Local executed commands, not a claim of GitHub CI or browser completion. Previous reports remain separately dated.'}
    (ROOT/'reports/session_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    history=ROOT/'reports/verification_history';history.mkdir(exist_ok=True)
    (history/(session_id+'.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
    return 0 if report['all_passed'] else 1

if __name__=='__main__':sys.exit(main())
