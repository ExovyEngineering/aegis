"""Startup checks use owned files and fake child processes, never operator state."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import uuid

import pytest

from scripts import start_local as launcher

REAL_OPERATOR_ENVIRONMENT = launcher.operator_environment


@pytest.fixture
def workspace(tmp_path):
    root = tmp_path / 'AEGIS project with spaces'
    dist = root / 'frontend/dist'
    (dist / 'assets').mkdir(parents=True)
    (dist / 'assets/app.js').write_text('console.log("fixture")', encoding='utf-8')
    (dist / 'assets/app.css').write_text('body{}', encoding='utf-8')
    (dist / 'index.html').write_text('<link href="/assets/app.css"><script src="/assets/app.js"></script>', encoding='utf-8')
    operator = root / 'data/aegis.sqlite'
    operator.parent.mkdir()
    operator.write_bytes(b'operator sentinel: startup must not open or reset me')
    return root


@pytest.fixture
def isolated_launcher(workspace, monkeypatch):
    original_env, original_assets = launcher.operator_environment, launcher.frontend_assets
    monkeypatch.setattr(launcher, 'ROOT', workspace)
    monkeypatch.setattr(launcher, 'operator_environment', lambda: original_env(workspace, env={}))
    monkeypatch.setattr(launcher, 'frontend_assets', lambda: original_assets(workspace))
    monkeypatch.setattr(launcher, 'listener_status', lambda port: {'occupied': False})
    return workspace


class Child:
    def __init__(self, code=0, interrupt=False, hang_on_stop=False):
        self.code, self.interrupt, self.hang_on_stop = code, interrupt, hang_on_stop
        self.waits = []
        self.terminated = self.killed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def wait(self, timeout=None):
        self.waits.append(timeout)
        if self.interrupt and len(self.waits) == 1:
            raise KeyboardInterrupt
        if self.hang_on_stop and timeout == 8:
            raise subprocess.TimeoutExpired('owned uvicorn', timeout)
        return self.code

    def poll(self):
        return None

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True


@pytest.mark.parametrize('value', [0, 80, 1023, 65536, -1, 'bad', '8000.5', True])
def test_bad_port_is_rejected_before_any_launch(value):
    with pytest.raises(argparse.ArgumentTypeError):
        launcher.port_number(value)


def test_dotenv_defaults_are_literal_and_do_not_change_caller_environment(workspace):
    (workspace / '.env').write_text('\ufeff# fixture\nAEGIS_DB_PATH="data/custom.sqlite"\nPRIVATE_TEST_VALUE=$(do-not-execute)\nPRIVATE_TEST_VALUE=second\nBAD-NAME=ignored\n', encoding='utf-8')
    inherited = {'AEGIS_DB_PATH': 'chosen.sqlite'}
    result = launcher.effective_environment(workspace, inherited)
    assert result['AEGIS_DB_PATH'] == 'chosen.sqlite'
    assert result['PRIVATE_TEST_VALUE'] == '$(do-not-execute)'
    assert 'BAD-NAME' not in result and inherited == {'AEGIS_DB_PATH': 'chosen.sqlite'}


@pytest.mark.parametrize('environment', [
    {'AEGIS_REHEARSAL_ID': ''},
    {'AEGIS_REHEARSAL_ID': 'inherited-id'},
    {'AEGIS_OFFLINE_DEMO': '0'},
    {'AEGIS_OFFLINE_DEMO': '1'},
    {'AEGIS_DB_PATH': 'data/rehearsals/anonymous.sqlite'},
])
def test_operator_guard_rejects_partial_or_rehearsal_environment_without_creating_state(workspace, environment):
    before = (workspace / 'data/aegis.sqlite').read_bytes()
    with pytest.raises(ValueError, match='refused'):
        launcher.operator_environment(workspace, environment)
    assert not (workspace / 'data/rehearsals').exists()
    assert (workspace / 'data/aegis.sqlite').read_bytes() == before


def test_operator_guard_rejects_a_fully_valid_isolated_rehearsal_profile(workspace):
    identity = str(uuid.uuid4())
    environment = {'AEGIS_REHEARSAL_ID': identity, 'AEGIS_OFFLINE_DEMO': '0',
                   'AEGIS_DB_PATH': str(workspace / f'data/rehearsals/{identity}.sqlite')}
    with pytest.raises(ValueError, match='refused'):
        launcher.operator_environment(workspace, environment)
    assert not (workspace / 'data/rehearsals').exists()


@pytest.mark.parametrize('value', ['0', '1'])
def test_dotenv_rehearsal_configuration_is_guarded_too(workspace, value):
    (workspace / '.env').write_text(f'AEGIS_OFFLINE_DEMO={value}\n', encoding='utf-8')
    with pytest.raises(ValueError, match='refused'):
        launcher.operator_environment(workspace, {})


def test_operator_uses_effective_relative_database_without_opening_it(workspace, monkeypatch):
    (workspace / '.env').write_text('AEGIS_DB_PATH=data/new-custom.sqlite\n', encoding='utf-8')
    monkeypatch.setattr(sqlite3, 'connect', lambda *args, **kwargs: pytest.fail('Startup opened SQLite'))
    environment, runtime = launcher.operator_environment(workspace, {})
    assert environment['AEGIS_DB_PATH'] == str((workspace / 'data/new-custom.sqlite').resolve())
    assert runtime['mode'] == 'operator'
    assert not (workspace / 'data/new-custom.sqlite').exists()


def test_assets_are_validated_with_explicit_unverified_freshness(workspace):
    result = launcher.frontend_assets(workspace)
    assert result['index_sha256'] == hashlib.sha256((workspace / 'frontend/dist/index.html').read_bytes()).hexdigest()
    assert result['local_asset_count'] == 2
    assert 'freshness is not established' in result['freshness']


@pytest.mark.parametrize('reference', [
    '/missing.js', '/../outside.js', 'https://example.invalid/app.js', '//example.invalid/app.js',
    '/assets/app.js?new=1', '/assets/app.js#entry', 'assets/app.js', '/assets\\app.js',
])
def test_missing_remote_or_escaping_asset_prevents_startup(workspace, reference):
    (workspace / 'frontend/dist/index.html').write_text(f'<script src="{reference}"></script>', encoding='utf-8')
    (workspace / 'frontend/outside.js').write_text('outside', encoding='utf-8')
    with pytest.raises(ValueError):
        launcher.frontend_assets(workspace)


def test_url_encoded_path_cannot_validate_a_different_file_than_http_would_serve(workspace):
    literal = workspace / 'frontend/dist/assets/app%20bundle.js'
    literal.write_text('literal percent file, not decoded HTTP asset', encoding='utf-8')
    (workspace / 'frontend/dist/index.html').write_text('<script src="/assets/app%20bundle.js"></script>', encoding='utf-8')
    with pytest.raises(ValueError):
        launcher.frontend_assets(workspace)


def test_asset_symlink_cannot_escape_dist(workspace):
    outside = workspace / 'outside.js'
    outside.write_text('outside', encoding='utf-8')
    link = workspace / 'frontend/dist/assets/linked.js'
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip('Creating file symlinks requires an unavailable Windows privilege')
    (workspace / 'frontend/dist/index.html').write_text('<script src="/assets/linked.js"></script>', encoding='utf-8')
    with pytest.raises(ValueError, match='outside'):
        launcher.frontend_assets(workspace)


@pytest.mark.parametrize('body', [
    '<link href="/assets/app.css">',
    '<script src="/assets/app.js"></script>' * 65,
    'x' * (256 * 1024 + 1),
], ids=['no-javascript', 'too-many-assets', 'oversized-index'])
def test_incomplete_or_oversized_frontend_is_reported(workspace, body):
    (workspace / 'frontend/dist/index.html').write_text(body, encoding='utf-8')
    with pytest.raises(ValueError):
        launcher.frontend_assets(workspace)


def test_check_only_never_builds_starts_or_opens_database(isolated_launcher, monkeypatch, capsys):
    before = (isolated_launcher / 'data/aegis.sqlite').read_bytes()
    monkeypatch.setattr(launcher, 'build_command', lambda: pytest.fail('Check built frontend'))
    monkeypatch.setattr(subprocess, 'Popen', lambda *args, **kwargs: pytest.fail('Check started a process'))
    monkeypatch.setattr(sqlite3, 'connect', lambda *args, **kwargs: pytest.fail('Check opened SQLite'))
    assert launcher.main(['--check-only']) == 0
    output = json.loads(capsys.readouterr().out)
    assert not output['server_started'] and not output['database_opened'] and output['port_available']
    assert (isolated_launcher / 'data/aegis.sqlite').read_bytes() == before


def test_check_only_reports_missing_assets_without_starting(isolated_launcher, monkeypatch, capsys):
    monkeypatch.setattr(launcher, 'frontend_assets', lambda: (_ for _ in ()).throw(ValueError('fixture asset absent')))
    monkeypatch.setattr(subprocess, 'Popen', lambda *args, **kwargs: pytest.fail('Started despite missing assets'))
    assert launcher.main(['--check-only']) == 2
    output = json.loads(capsys.readouterr().out)
    assert output['frontend'] is None and output['frontend_error'] == 'fixture asset absent'


@pytest.mark.parametrize('recognized,mode,code', [(False, None, 2), (True, 'isolated_rehearsal', 2), (True, 'operator', 0)])
def test_occupied_port_never_builds_or_restarts_any_listener(isolated_launcher, monkeypatch, capsys, recognized, mode, code):
    monkeypatch.setattr(launcher, 'listener_status', lambda port: {'occupied': True, 'aegis_responding': recognized, 'runtime_mode': mode})
    monkeypatch.setattr(launcher, 'build_command', lambda: pytest.fail('Rebuilt assets behind running listener'))
    monkeypatch.setattr(launcher, 'frontend_assets', lambda: pytest.fail('Touched running listener assets'))
    monkeypatch.setattr(subprocess, 'Popen', lambda *args, **kwargs: pytest.fail('Started/restarted listener'))
    assert launcher.main([]) == code
    assert json.loads(capsys.readouterr().out)['server_started'] is False


def test_no_build_needs_no_node_and_starts_exact_owned_foreground_child(isolated_launcher, monkeypatch, capsys):
    before = (isolated_launcher / 'data/aegis.sqlite').read_bytes()
    child, captured = Child(code=7), {}
    monkeypatch.setattr(launcher, 'build_command', lambda: pytest.fail('No-build tried to find Node'))
    def popen(command, **kwargs):
        captured.update(command=command, **kwargs)
        return child
    monkeypatch.setattr(subprocess, 'Popen', popen)
    assert launcher.main(['--no-build', '--port', '8127']) == 7
    assert captured['command'] == [launcher.sys.executable, '-m', 'uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', '8127']
    assert captured['cwd'] == isolated_launcher
    assert captured['env']['AEGIS_DB_PATH'] == str((isolated_launcher / 'data/aegis.sqlite').resolve())
    assert child.waits == [None] and not child.terminated and not child.killed
    assert (isolated_launcher / 'data/aegis.sqlite').read_bytes() == before
    output = capsys.readouterr().out
    assert 'Source freshness is unverified' in output and 'Keep this terminal open' in output


def test_default_build_failure_propagates_without_starting_or_touching_database(isolated_launcher, monkeypatch):
    captured = {}
    command = ['node fixture', 'npm fixture', '--prefix', 'frontend', 'run', 'build']
    monkeypatch.setattr(launcher, 'build_command', lambda: (command, '/owned tools/node'))
    def run(command, **kwargs):
        captured.update(command=command, **kwargs)
        return subprocess.CompletedProcess(command, 9)
    monkeypatch.setattr(subprocess, 'run', run)
    monkeypatch.setattr(subprocess, 'Popen', lambda *args, **kwargs: pytest.fail('Started after failed build'))
    before = (isolated_launcher / 'data/aegis.sqlite').read_bytes()
    assert launcher.main([]) == 9
    assert captured['command'] == command and captured['cwd'] == isolated_launcher
    assert captured['env']['PATH'].startswith(str(Path('/owned tools/node').parent))
    assert (isolated_launcher / 'data/aegis.sqlite').read_bytes() == before


def test_successful_build_precedes_asset_validation_and_server_start(isolated_launcher, monkeypatch):
    calls = []
    monkeypatch.setattr(launcher, 'build_command', lambda: (['npm', 'build'], '/tools/node'))
    monkeypatch.setattr(subprocess, 'run', lambda *args, **kwargs: (calls.append('build') or subprocess.CompletedProcess(args[0], 0)))
    monkeypatch.setattr(launcher, 'frontend_assets', lambda: (calls.append('assets') or {}))
    monkeypatch.setattr(subprocess, 'Popen', lambda *args, **kwargs: (calls.append('server') or Child()))
    assert launcher.main([]) == 0
    assert calls == ['build', 'assets', 'server']


@pytest.mark.parametrize('hang', [False, True])
def test_ctrl_c_stops_only_the_owned_child_with_bounded_escalation(isolated_launcher, monkeypatch, hang):
    child = Child(interrupt=True, hang_on_stop=hang)
    monkeypatch.setattr(subprocess, 'Popen', lambda *args, **kwargs: child)
    assert launcher.main(['--no-build']) == 130
    assert child.terminated is True and child.killed is hang
    assert child.waits == ([None, 8, 5] if hang else [None, 8])


def test_configuration_failures_do_not_echo_private_environment_values(isolated_launcher, monkeypatch, capsys):
    secret = 'private-fixture-value-that-must-not-be-printed'
    monkeypatch.setenv('UNRELATED_PRIVATE_VALUE', secret)
    monkeypatch.setattr(launcher, 'operator_environment', lambda: REAL_OPERATOR_ENVIRONMENT(isolated_launcher, {'AEGIS_OFFLINE_DEMO': '1', 'UNRELATED_PRIVATE_VALUE': secret}))
    assert launcher.main(['--no-build']) == 2
    output = capsys.readouterr()
    assert secret not in output.out + output.err and 'startup failed' in output.err


def test_missing_node_and_npm_explain_no_build_option_without_downloading(workspace, monkeypatch):
    monkeypatch.setattr(launcher.shutil, 'which', lambda name: None)
    with pytest.raises(ValueError, match='--no-build'):
        launcher.build_command(workspace)
    assert not (workspace / '.tools').exists()


def test_embedded_runtime_build_uses_argument_list_and_its_own_node(workspace, monkeypatch):
    node = workspace / '.tools/node.exe'
    cli = workspace / '.tools/package/bin/npm-cli.js'
    node.parent.mkdir()
    cli.parent.mkdir(parents=True)
    node.write_bytes(b'owned runtime fixture')
    cli.write_text('fixture', encoding='utf-8')
    monkeypatch.setattr(launcher.shutil, 'which', lambda name: None)
    command, selected = launcher.build_command(workspace)
    assert selected == str(node)
    assert command == [str(node), str(cli), '--prefix', 'frontend', 'run', 'build']


def test_listener_probe_uses_only_bounded_safe_metadata(monkeypatch):
    calls = []
    class OccupiedSocket:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def setsockopt(self, *args): pass
        def bind(self, *args): raise OSError('occupied fixture')
    monkeypatch.setattr(launcher.socket, 'socket', lambda *args: OccupiedSocket())
    def local_json(port, path):
        calls.append((port, path))
        return {'status': 'ok', 'mode': 'local simulated research demo'} if path.endswith('health') else {'mode': 'operator'}
    monkeypatch.setattr(launcher, '_local_json', local_json)
    result = launcher.listener_status(8127)
    assert result['aegis_responding'] and result['runtime_mode'] == 'operator'
    assert calls == [(8127, '/api/health'), (8127, '/api/runtime-context')]
    assert 'freshness' in result['notice'] and 'unverified' in result['notice']


def test_local_json_disables_proxies_redirects_and_caps_response(monkeypatch):
    captured = {}
    class Response(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *args): self.close()
    class Opener:
        def open(self, url, timeout):
            captured.update(url=url, timeout=timeout)
            return Response(b'x' * 65537)
    def build(*handlers):
        captured['handlers'] = handlers
        return Opener()
    monkeypatch.setattr(launcher, 'build_opener', build)
    with pytest.raises(ValueError, match='bound'):
        launcher._local_json(8127, '/api/health')
    assert captured['url'] == 'http://127.0.0.1:8127/api/health' and captured['timeout'] == 1.5
    assert captured['handlers'][0].proxies == {} and isinstance(captured['handlers'][1], launcher.NoRedirect)
    assert launcher.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://example.invalid') is None
