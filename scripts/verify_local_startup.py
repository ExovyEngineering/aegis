"""Exercise foreground startup in an owned local database without provider calls.

Windows uses a hidden, owned console and a harness mapping CTRL_BREAK to the
KeyboardInterrupt handled by the launcher's Ctrl+C path. This is not a claim of
a physical keyboard press or that an agent-started service survives its session.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import time
import uuid
from urllib.request import ProxyHandler, HTTPRedirectHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def fingerprint(path):
    path = Path(path)
    if not path.exists(): return {'exists':False}
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for part in iter(lambda: stream.read(1024*1024), b''): digest.update(part)
    return {'exists':True, 'bytes':path.stat().st_size, 'sha256':digest.hexdigest()}


def database(path):
    return {suffix or 'sqlite':fingerprint(str(path)+suffix) for suffix in ('','-wal','-shm','-journal')}


def tree(relative):
    folder = ROOT/relative
    return {path.relative_to(ROOT).as_posix():fingerprint(path) for path in sorted(folder.rglob('*')) if path.is_file()} if folder.exists() else {}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args): return None


def get_json(port, path):
    opener = build_opener(ProxyHandler({}), NoRedirect())
    with opener.open(f'http://127.0.0.1:{port}{path}',timeout=1.5) as response:
        body=response.read(8*1024*1024+1)
        if len(body)>8*1024*1024: raise ValueError('Owned startup response exceeded bound')
        return json.loads(body)


def unused_port():
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as reservation:
        if hasattr(socket,'SO_EXCLUSIVEADDRUSE'): reservation.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        reservation.bind(('127.0.0.1',0))
        return reservation.getsockname()[1]


def port_released(port):
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as reservation:
        if hasattr(socket,'SO_EXCLUSIVEADDRUSE'): reservation.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        try: reservation.bind(('127.0.0.1',port)); return True
        except OSError: return False


def wait_until(predicate, timeout=20):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if predicate(): return True
        time.sleep(.1)
    return False


def windows_owned_handles(parent_pid):
    """Capture handles for this spawned process and its verified descendants.

    Handles retain process identity even if a numeric PID is later reused. No
    listener-to-PID lookup is used, and no unrelated process is eligible cleanup.
    """
    import ctypes
    from ctypes import wintypes
    class Entry(ctypes.Structure):
        _fields_=[('dwSize',wintypes.DWORD),('cntUsage',wintypes.DWORD),('th32ProcessID',wintypes.DWORD),
                  ('th32DefaultHeapID',ctypes.c_size_t),('th32ModuleID',wintypes.DWORD),('cntThreads',wintypes.DWORD),
                  ('th32ParentProcessID',wintypes.DWORD),('pcPriClassBase',wintypes.LONG),('dwFlags',wintypes.DWORD),
                  ('szExeFile',wintypes.WCHAR*260)]
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes=[wintypes.DWORD,wintypes.DWORD]; kernel.CreateToolhelp32Snapshot.restype=wintypes.HANDLE
    kernel.Process32FirstW.argtypes=[wintypes.HANDLE,ctypes.POINTER(Entry)]; kernel.Process32FirstW.restype=wintypes.BOOL
    kernel.Process32NextW.argtypes=[wintypes.HANDLE,ctypes.POINTER(Entry)]; kernel.Process32NextW.restype=wintypes.BOOL
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]; kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]; kernel.WaitForSingleObject.restype=wintypes.DWORD
    kernel.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]; kernel.GetExitCodeProcess.restype=wintypes.BOOL
    kernel.TerminateProcess.argtypes=[wintypes.HANDLE,wintypes.UINT]; kernel.TerminateProcess.restype=wintypes.BOOL
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]; kernel.CloseHandle.restype=wintypes.BOOL
    snapshot=kernel.CreateToolhelp32Snapshot(2,0)
    if snapshot==wintypes.HANDLE(-1).value: raise OSError(ctypes.get_last_error(),'Cannot inspect owned process descendants')
    rows=[]
    try:
        entry=Entry(); entry.dwSize=ctypes.sizeof(entry)
        present=kernel.Process32FirstW(snapshot,ctypes.byref(entry))
        while present:
            rows.append({'pid':entry.th32ProcessID,'parent_pid':entry.th32ParentProcessID,'executable':entry.szExeFile})
            present=kernel.Process32NextW(snapshot,ctypes.byref(entry))
    finally: kernel.CloseHandle(snapshot)
    selected={parent_pid}
    while True:
        expanded=selected|{row['pid'] for row in rows if row['parent_pid'] in selected}
        if expanded==selected: break
        selected=expanded
    handles=[]
    for row in rows:
        if row['pid'] not in selected: continue
        handle=kernel.OpenProcess(0x00100000|0x1000|1,False,row['pid'])
        if handle: handles.append((row,handle))
    if not handles: raise RuntimeError('No verified owned process handles were captured')
    return kernel,handles


def interrupt_owned_console(process, folder):
    if os.name!='nt': process.send_signal(signal.SIGINT); return {'method':'SIGINT sent to owned launcher process'}
    # This helper attaches only to the launcher's new hidden console. Ignoring
    # its own signals does not alter an operator shell or other process group.
    helper=folder/'interrupt_console.py'
    helper.write_text('''import ctypes,signal,sys
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
kernel.FreeConsole()
if not kernel.AttachConsole(int(sys.argv[1])): raise OSError(ctypes.get_last_error(),'Owned console attach failed')
signal.signal(signal.SIGINT,signal.SIG_IGN)
signal.signal(signal.SIGBREAK,signal.SIG_IGN)
handler_type=ctypes.WINFUNCTYPE(ctypes.c_int,ctypes.c_uint)
ignore=handler_type(lambda event:1)
if not kernel.SetConsoleCtrlHandler(ignore,True): raise OSError(ctypes.get_last_error(),'Owned helper control handler failed')
if not kernel.GenerateConsoleCtrlEvent(1,0): raise OSError(ctypes.get_last_error(),'Owned console interrupt failed')
kernel.FreeConsole()
''',encoding='utf-8')
    result=subprocess.run([sys.executable,str(helper),str(process.pid)],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=8)
    if result.returncode not in (0,0xC000013A): raise RuntimeError(f'Owned-console interrupt helper failed ({result.returncode}): '+result.stdout[-1000:])
    return {'method':'CTRL_BREAK delivered to owned hidden console; smoke harness maps it to KeyboardInterrupt',
            'physical_keyboard_tested':False,'control_helper_exit_code':result.returncode}


def python_launcher_exit(process,kernel,handles,pid,timeout=12):
    if os.name!='nt': return process.wait(timeout=timeout)
    import ctypes
    from ctypes import wintypes
    handle=next(handle for row,handle in handles if row['pid']==pid)
    if kernel.WaitForSingleObject(handle,int(timeout*1000))!=0: return None
    code=wintypes.DWORD()
    if not kernel.GetExitCodeProcess(handle,ctypes.byref(code)): raise OSError(ctypes.get_last_error(),'Cannot read owned Python launcher exit')
    return code.value


def main():
    from scripts.start_local import effective_environment, frontend_assets
    started=time.monotonic()
    result={'checked_at':datetime.now(timezone.utc).isoformat(),'passed':False,'checks':[],
            'provider_requests_requested':False,'llm_requested':False,'frontend_built':False,
            'prebuilt_freshness':'Source freshness unverified by this no-build lifecycle exercise',
            'physical_keyboard_tested':False,'fallback_cleanup_used':False}
    report=ROOT/'reports/local_startup_verification.json'
    if report.exists():
        history=ROOT/'reports/checks/local-startup-history';history.mkdir(exist_ok=True)
        (history/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')).write_bytes(report.read_bytes())
    def check(name, passed, detail=None):
        result['checks'].append({'name':name,'passed':bool(passed),'detail':detail})
        if not passed: raise RuntimeError(name)
    process=None; handles=[]; kernel=None; port=None; output_file=None
    result['operator_before']=database(ROOT/'data/aegis.sqlite')
    result['fixtures_before']=tree('data/fixtures'); result['cache_before']=tree('data/cache')
    try:
        dotenv=effective_environment(ROOT,{})
        check('actual dotenv does not configure a rehearsal profile',not any(key in dotenv for key in ('AEGIS_REHEARSAL_ID','AEGIS_OFFLINE_DEMO')))
        configured_db=Path(dotenv.get('AEGIS_DB_PATH') or ROOT/'data/aegis.sqlite')
        if not configured_db.is_absolute(): configured_db=ROOT/configured_db
        check('actual dotenv database is not an isolated rehearsal path',not configured_db.resolve().is_relative_to((ROOT/'data/rehearsals').resolve()))
        assets=frontend_assets(ROOT); result['frontend']=assets
        folder=(ROOT/'.tools'/f'launcher-smoke-{uuid.uuid4()}').resolve()
        if not folder.is_relative_to((ROOT/'.tools').resolve()): raise ValueError('Smoke path escaped owned directory')
        folder.mkdir()
        owned_db=folder/'startup.sqlite'; log=folder/'launcher.stdout.txt'
        environment=dict(os.environ)
        environment.pop('AEGIS_REHEARSAL_ID',None); environment.pop('AEGIS_OFFLINE_DEMO',None)
        environment.update(AEGIS_DB_PATH=str(owned_db),AEGIS_ASSISTANT_OLLAMA_ENABLED='0',PYTHONUNBUFFERED='1',PYTHONIOENCODING='utf-8')
        port=unused_port(); result.update(port=port,owned_database=owned_db.relative_to(ROOT).as_posix(),log=log.relative_to(ROOT).as_posix())
        # Windows control-event mapping belongs to this test harness only. The
        # real startup module and foreground Uvicorn process run unchanged.
        wrapper=folder/'run_launcher.py'
        wrapper.write_text("import os,runpy,signal,sys\nprint('AEGIS_LAUNCHER_HARNESS_PID='+str(os.getpid()),flush=True)\n"+(
            "signal.signal(signal.SIGBREAK,signal.default_int_handler)\n" if os.name=='nt' else '')+
            f"sys.path.insert(0,{str(ROOT)!r})\nsys.argv=['scripts/start_local.py','--no-build','--port',{str(port)!r}]\nrunpy.run_path({str(ROOT/'scripts/start_local.py')!r},run_name='__main__')\n",encoding='utf-8')
        options={}
        if os.name=='nt':
            startup=subprocess.STARTUPINFO(); startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW; startup.wShowWindow=0
            options.update(startupinfo=startup,creationflags=subprocess.CREATE_NEW_CONSOLE)
        else: options['start_new_session']=True
        output_file=log.open('w',encoding='utf-8')
        process=subprocess.Popen([sys.executable,str(wrapper)],cwd=ROOT,env=environment,stdout=output_file,stderr=subprocess.STDOUT,**options)
        result['launcher_pid']=process.pid
        if os.name=='nt': kernel,handles=windows_owned_handles(process.pid)
        def ready():
            if process.poll() is not None: return True
            try: return get_json(port,'/api/health').get('status')=='ok'
            except (OSError,ValueError): return False
        check('foreground launcher starts a reachable owned server',wait_until(ready) and process.poll() is None)
        runtime=get_json(port,'/api/runtime-context')
        check('owned server is operator mode on the explicitly owned database',runtime.get('mode')=='operator' and runtime.get('database_relative_path')==owned_db.relative_to(ROOT).as_posix())
        network=get_json(port,'/api/network')
        check('only the owned database initializes reproducible simulated entities',owned_db.exists() and len(network.get('shipments',[]))==24 and network.get('seed')==20261026)
        if os.name=='nt':
            for _,handle in handles: kernel.CloseHandle(handle)
            kernel,handles=windows_owned_handles(process.pid)
            result['owned_processes']=[row for row,_ in handles]
        output_file.flush()
        actual_pid=int(re.search(r'AEGIS_LAUNCHER_HARNESS_PID=(\d+)',log.read_text(encoding='utf-8',errors='replace'))[1])
        result['actual_python_launcher_pid']=actual_pid
        before_second=database(owned_db); before_assets=tree('frontend/dist')
        second=subprocess.run([sys.executable,str(ROOT/'scripts/start_local.py'),'--no-build','--port',str(port)],cwd=ROOT,env=environment,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=10)
        second_body=json.loads(second.stdout.strip())
        check('second launcher recognizes existing operator without restart or build',second.returncode==0 and second_body.get('aegis_responding') is True and second_body.get('server_started') is False and second_body.get('runtime_mode')=='operator')
        check('second launch keeps database and prebuilt assets unchanged',database(owned_db)==before_second and tree('frontend/dist')==before_assets and process.poll() is None)
        result['second_launch']=second_body
        result['interrupt']=interrupt_owned_console(process,folder)
        try: code=python_launcher_exit(process,kernel,handles,actual_pid)
        except subprocess.TimeoutExpired: code=None
        check('foreground interruption returns the launcher cleanup exit',code==130,{'actual_exit_code':code})
        check('owned listener port is released after foreground cleanup',wait_until(lambda:port_released(port),timeout=8))
        output_file.flush()
        text=log.read_text(encoding='utf-8',errors='replace')
        check('actual interrupt path reports owned-server shutdown','Stopping the owned local server' in text)
        result['launcher_exit_code']=code
        result['bootstrap_exit_code']=process.wait(timeout=5)
        if os.name=='nt': result['bootstrap_status_note']='Native venv redirectors may exit with Windows CTRL_BREAK status; the actual Python launcher cleanup handler is independently observed through its captured handle.'
        result['passed']=True
    except Exception as error:
        result['error']={'type':type(error).__name__,'message':str(error)}
    finally:
        if os.name=='nt' and process and process.poll() is None:
            try:
                current_kernel,current_handles=windows_owned_handles(process.pid)
                if kernel:
                    for _,handle in handles: kernel.CloseHandle(handle)
                kernel,handles=current_kernel,current_handles
            except Exception as error:
                result['cleanup_identity_error']={'type':type(error).__name__,'message':str(error)}
        if kernel:
            for row,handle in reversed(handles):
                if kernel.WaitForSingleObject(handle,2000)==258:
                    result['fallback_cleanup_used']=True
                    kernel.TerminateProcess(handle,130)
                    kernel.WaitForSingleObject(handle,5000)
                kernel.CloseHandle(handle)
        elif process and process.poll() is None:
            result['fallback_cleanup_used']=True
            if os.name!='nt':
                try: os.killpg(process.pid,signal.SIGTERM)
                except ProcessLookupError: pass
            else: process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill();process.wait(timeout=5)
        if output_file: output_file.close()
        if result['fallback_cleanup_used']: result['passed']=False
        result['operator_after']=database(ROOT/'data/aegis.sqlite')
        result['fixtures_after']=tree('data/fixtures'); result['cache_after']=tree('data/cache')
        preserved=result['operator_before']==result['operator_after'] and result['fixtures_before']==result['fixtures_after'] and result['cache_before']==result['cache_after']
        result['checks'].append({'name':'real operator database, sidecars, fixtures and caches unchanged','passed':preserved,'detail':None})
        if not preserved: result['passed']=False
        result['finished_at']=datetime.now(timezone.utc).isoformat();result['duration_seconds']=round(time.monotonic()-started,3)
        report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:result.get(key) for key in ('passed','launcher_exit_code','fallback_cleanup_used','error')}))
    return 0 if result['passed'] else 1


if __name__=='__main__':sys.exit(main())
