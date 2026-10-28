"""Start one fresh, offline, loopback-only rehearsal without touching operator state."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]


def rehearsal_port(value):
    try:
        port = int(value)
    except (TypeError, ValueError) as error:
        raise argparse.ArgumentTypeError('Use an integer TCP port from 1024 through 65535, excluding operator port 8000') from error
    if not 1024 <= port <= 65535 or port == 8000:
        raise argparse.ArgumentTypeError('Use a TCP port from 1024 through 65535; port 8000 is reserved for the operator app')
    return port


def check_port_available(port):
    """Probe a loopback bind without terminating or contacting another service."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            probe.bind(('127.0.0.1', port))
        except OSError as error:
            raise RuntimeError(f'Loopback port {port} is unavailable: {error}. Choose another port; no server was stopped.') from error


def _ps_quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def prepare_rehearsal(port=8001, root=ROOT):
    """Reserve a unique file and return only nonsecret launch metadata."""
    port = rehearsal_port(port)
    root = Path(root).resolve()
    check_port_available(port)
    session_id = str(uuid.uuid4())
    base = (root / 'data/rehearsals').resolve()
    if not base.is_relative_to(root):
        raise ValueError('Rehearsal data directory resolves outside this workspace')
    base.mkdir(parents=True, exist_ok=True)
    database = (base / f'{session_id}.sqlite').resolve()
    if database.parent != base or not database.is_relative_to(root):
        raise ValueError('Rehearsal database resolves outside the owned session directory')
    # Exclusive creation reserves this exact session identity without replacing a
    # database. SQLite initializes the empty file when the isolated app starts.
    with database.open('xb'):
        pass
    environment = {
        'AEGIS_REHEARSAL_ID': session_id,
        'AEGIS_DB_PATH': str(database),
        'AEGIS_OFFLINE_DEMO': '1',
    }
    command = [sys.executable, '-m', 'uvicorn', 'backend.main:app',
               '--host', '127.0.0.1', '--port', str(port)]
    powershell = [f'Set-Location -LiteralPath {_ps_quote(root)}']
    powershell += [f'$env:{key} = {_ps_quote(value)}' for key, value in environment.items()]
    powershell += [f'& {_ps_quote(command[0])} ' + ' '.join(command[1:])]
    return {
        'status': 'prepared',
        'server_started': False,
        'prepared_at': datetime.now(timezone.utc).isoformat(),
        'rehearsal_id': session_id,
        'database_path': str(database),
        'database_relative_path': database.relative_to(root).as_posix(),
        'url': f'http://127.0.0.1:{port}/?mode=rehearsal',
        'port': port,
        'working_directory': str(root),
        'environment': environment,
        'command': command,
        'powershell_commands': powershell,
        'notice': 'One fresh simulated session is reserved. No server has started yet. Operator state was not opened or reset. Port availability can change before Uvicorn binds.',
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=rehearsal_port, default=8001)
    parser.add_argument('--prepare-only', action='store_true',
                        help='Reserve the isolated session and print JSON/start commands without starting a server')
    args = parser.parse_args(argv)
    try:
        launch = prepare_rehearsal(args.port)
    except (OSError, ValueError, RuntimeError, argparse.ArgumentTypeError) as error:
        print(json.dumps({'status':'failed', 'server_started':False,
                          'error':f'{type(error).__name__}: {error}'}), file=sys.stderr)
        return 2
    print(json.dumps(launch, indent=2), flush=True)
    if args.prepare_only:
        return 0
    environment = dict(os.environ)
    environment.update(launch['environment'])
    try:
        # Run in the foreground. Ctrl+C ends this rehearsal server; no existing
        # operator/QA process is inspected, killed or rebound by this launcher.
        result = subprocess.run(launch['command'], cwd=launch['working_directory'], env=environment)
        return result.returncode
    except KeyboardInterrupt:
        return 130
    except OSError as error:
        print(json.dumps({'status':'failed', 'server_started':False,
                          'rehearsal_id':launch['rehearsal_id'],
                          'error':f'{type(error).__name__}: {error}'}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
