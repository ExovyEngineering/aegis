"""Run the local operator app in the foreground; never stop another listener.

Keep this terminal open. Closing it or pressing Ctrl+C ends this owned server.
Use --no-build for the explicitly prebuilt reviewer package, or --check-only
for a non-mutating startup diagnosis. No dependency/model download is automatic.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, HTTPRedirectHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def port_number(value):
    try: port = int(value)
    except (TypeError, ValueError) as error: raise argparse.ArgumentTypeError('Use an integer port from 1024 to 65535') from error
    if not 1024 <= port <= 65535: raise argparse.ArgumentTypeError('Use a port from 1024 to 65535')
    return port


def effective_environment(root=ROOT, env=None):
    """Mirror the app's dotenv defaults without executing or logging values."""
    environment = dict(os.environ if env is None else env)
    config = Path(root) / '.env'
    if config.exists():
        for line in config.read_text(encoding='utf-8-sig').splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                if key.strip().isidentifier(): environment.setdefault(key.strip(), value.strip().strip('\"\''))
    return environment


def operator_environment(root=ROOT, env=None):
    from backend.runtime import runtime_context
    workspace = Path(root).resolve()
    environment = effective_environment(workspace, env)
    selected = Path(environment.get('AEGIS_DB_PATH') or workspace/'data/aegis.sqlite')
    if not selected.is_absolute(): selected = workspace / selected
    selected = selected.resolve()
    runtime = runtime_context(selected, root=workspace, env=environment)
    if runtime['mode'] != 'operator' or runtime['offline']:
        raise ValueError('Operator startup refused a rehearsal/offline configuration. Use a clean operator terminal/configuration, or scripts/start_rehearsal.py for an isolated session. No database was opened.')
    environment['AEGIS_DB_PATH'] = str(selected)
    return environment, runtime


def frontend_assets(root=ROOT):
    workspace = Path(root).resolve()
    dist = (workspace/'frontend/dist').resolve()
    if not dist.is_relative_to(workspace): raise ValueError('Built frontend resolves outside this workspace')
    index = dist/'index.html'
    if not index.is_file() or not index.resolve().is_relative_to(dist):
        raise ValueError('Built frontend missing: build the frontend first, or run this launcher without --no-build.')
    body = index.read_bytes()
    if len(body) > 256*1024: raise ValueError('Frontend index exceeds the startup inspection bound')
    text = body.decode('utf-8')
    references = re.findall(r'(?:src|href)=[\"\']([^\"\']+)[\"\']', text)
    if not references or len(references) > 64: raise ValueError('Frontend assets are absent or exceed the startup inspection bound')
    has_script = False
    for reference in references:
        parsed = urlsplit(reference)
        if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment or not reference.startswith('/') or '\\' in reference or '%' in reference:
            raise ValueError('Frontend startup requires bounded local asset paths without redirects or queries')
        path = (dist/reference.lstrip('/')).resolve()
        if not path.is_relative_to(dist) or not path.is_file():
            raise ValueError('A built frontend asset is missing or outside frontend/dist; rebuild before starting')
        has_script = has_script or path.suffix == '.js'
    if not has_script: raise ValueError('Built frontend has no JavaScript entry asset')
    return {'index_sha256':hashlib.sha256(body).hexdigest(), 'local_asset_count':len(references), 'freshness':'Existing prebuilt assets; source freshness is not established by this check'}


def build_command(root=ROOT):
    workspace = Path(root)
    node = shutil.which('node')
    local_node = workspace/'.tools/node.exe'
    if not node and local_node.is_file(): node = str(local_node)
    npm_cli = workspace/'.tools/package/bin/npm-cli.js'
    if node and npm_cli.is_file(): return [node, str(npm_cli), '--prefix', 'frontend', 'run', 'build'], node
    npm = shutil.which('npm.cmd') or shutil.which('npm')
    if node and npm: return [npm, '--prefix', 'frontend', 'run', 'build'], node
    raise ValueError('Node.js/npm is unavailable. Install the documented runtime to build, or use --no-build only with a valid prebuilt frontend.')


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl): return None


def _local_json(port, path):
    opener = build_opener(ProxyHandler({}), NoRedirect())
    with opener.open(f'http://127.0.0.1:{port}{path}', timeout=1.5) as response:
        body = response.read(65537)
        if len(body)>65536: raise ValueError('Listener response exceeds the inspection bound')
        return json.loads(body)


def listener_status(port):
    """Probe a bind, then only safe local metadata; never fetch /network."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'): probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try: probe.bind(('127.0.0.1', port)); return {'occupied':False}
        except OSError: pass
    try:
        health = _local_json(port, '/api/health')
        runtime = _local_json(port, '/api/runtime-context')
        if health.get('status')=='ok' and health.get('mode')=='local simulated research demo' and runtime.get('mode') in ('operator','isolated_rehearsal'):
            return {'occupied':True, 'aegis_responding':True, 'runtime_mode':runtime['mode'],
                    'notice':'An AEGIS app already responds here. Nothing was rebuilt or restarted; its backend freshness and checkout identity are unverified.'}
    except (OSError, URLError, ValueError, TypeError, AttributeError): pass
    return {'occupied':True, 'aegis_responding':False, 'notice':'Port occupied by an unverified listener. No server was stopped. Choose --port or use the known existing terminal.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=port_number, default=8000)
    parser.add_argument('--no-build', action='store_true', help='Use validated prebuilt assets; source freshness remains unverified')
    parser.add_argument('--check-only', action='store_true', help='Inspect startup configuration/assets/listener without building, starting or opening SQLite')
    args = parser.parse_args(argv)
    try:
        environment, runtime = operator_environment()
        listener = listener_status(args.port)  # Before touching a running app's assets.
        if listener['occupied']:
            print(json.dumps(dict(listener, url=f'http://127.0.0.1:{args.port}/', server_started=False)))
            return 0 if listener.get('aegis_responding') and listener.get('runtime_mode')=='operator' else 2
        if args.check_only:
            try: assets = frontend_assets(); asset_error = None
            except (OSError, ValueError) as error: assets = None; asset_error = str(error)
            print(json.dumps({'status':'checked','server_started':False,'runtime_mode':runtime['mode'],'port_available':True,'frontend':assets,'frontend_error':asset_error,'database_opened':False}))
            return 0 if assets else 2
        if not args.no_build:
            command, node = build_command()
            build_env = dict(environment); build_env['PATH'] = str(Path(node).parent)+os.pathsep+build_env.get('PATH','')
            print('Building the frontend from current source…', flush=True)
            result = subprocess.run(command, cwd=ROOT, env=build_env)
            if result.returncode: return result.returncode
        assets = frontend_assets()
        if args.no_build: print('Using existing prebuilt frontend. Source freshness is unverified.', flush=True)
        print(f'AEGIS operator app: http://127.0.0.1:{args.port}/\nKeep this terminal open. Ctrl+C stops only the server started here. No original data is reset.', flush=True)
        command = [sys.executable,'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port',str(args.port)]
        with subprocess.Popen(command, cwd=ROOT, env=environment) as child:
            try: return child.wait()
            except KeyboardInterrupt:
                print('\nStopping the owned local server…', flush=True)
                if child.poll() is None: child.terminate()
                try: child.wait(timeout=8)
                except subprocess.TimeoutExpired: child.kill(); child.wait(timeout=5)
                return 130
    except (OSError, ValueError, ImportError, RuntimeError) as error:
        print(f'AEGIS startup failed: {type(error).__name__}: {error}\nSee README.md for setup. No unrelated process was stopped.', file=sys.stderr)
        return 2


if __name__ == '__main__': sys.exit(main())
