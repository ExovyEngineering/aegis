"""Reproduce, test and package AEGIS locally. Never deploy or reset operator state."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.demo_run import database_fingerprints


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'artifacts/AEGIS-Final-Build.zip')
    args=parser.parse_args()
    output=args.output.resolve()
    if not output.is_relative_to((ROOT/'artifacts').resolve()):
        parser.error('Keep final release archives inside this project artifacts directory')
    before=database_fingerprints([ROOT/'data/aegis.sqlite'])
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    logs=ROOT/'reports/checks'/('final-release-'+stamp);logs.mkdir(parents=True,exist_ok=False)
    jobs=[
        ['scripts/train_integrated_study.py'],
        ['scripts/run_decision_study.py'],
        ['scripts/build_data_dictionary.py'],
        ['scripts/render_one_health_system.py'],
        ['scripts/build_team_statement.py'],
        ['scripts/demo_run.py'],
        ['scripts/freshness_demo.py'],
        ['scripts/verify_project.py'],
        ['scripts/build_submission_report.py'],
        ['scripts/build_project_brief.py'],
        ['scripts/build_master_guide.py'],
        ['scripts/build_final_handoff.py','--preview-dir','reports/browser_qa/final_submission/print-render'],
        ['scripts/package_submission.py','--output',str(output)],
        ['scripts/verify_package.py','--archive',str(output)],
    ]
    result={'started_at':datetime.now(timezone.utc).isoformat(),'passed':False,'steps':[],
            'archive':str(output.relative_to(ROOT)),'operator_before':before,
            'deployed':False,'competition_submission_performed':False,'human_or_kiro_signoff_inferred':False,
            'note':'Application networking is not needed by these reproduction steps. Offline package checks reuse the installed dependency environment. Browser and live-provider probes are separate dated evidence.'}
    try:
        for index,args_ in enumerate(jobs,1):
            started=time.monotonic();command=[sys.executable,*args_]
            print(f'[{index}/{len(jobs)}] {args_[0]}',flush=True)
            completed=subprocess.run(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',timeout=900)
            log=logs/(f'{index:02}-'+Path(args_[0]).stem+'.txt');log.write_text(completed.stdout,encoding='utf-8')
            result['steps'].append({'command':command,'exit_code':completed.returncode,'duration_seconds':round(time.monotonic()-started,3),'log':log.relative_to(ROOT).as_posix()})
            if completed.returncode:
                raise RuntimeError(f'{args_[0]} failed with exit {completed.returncode}; inspect {log.relative_to(ROOT)}')
        result['passed']=True
    except Exception as error:
        result['error']=f'{type(error).__name__}: {error}'
    finally:
        result['operator_after']=database_fingerprints([ROOT/'data/aegis.sqlite'])
        result['operator_preserved']=result['operator_before']==result['operator_after']
        if not result['operator_preserved']:
            result['passed']=False
            result['preservation_warning']='Operator bytes changed during the run; concurrent activity is not attributed. No restore or reset was attempted.'
        result['finished_at']=datetime.now(timezone.utc).isoformat()
        (ROOT/'reports/final_release.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':result['passed'],'archive':result['archive'],'steps':len(result['steps']),'operator_preserved':result['operator_preserved'],'error':result.get('error')},indent=2))
    return 0 if result['passed'] else 1


if __name__=='__main__':sys.exit(main())
