import argparse
import json
from pathlib import Path
import socket
import subprocess
import uuid

import pytest

from scripts import start_rehearsal as launcher


@pytest.mark.parametrize('port', [0, 80, 1023, 8000, 65536, 'no-port'])
def test_launcher_rejects_operator_and_unsupported_ports(port):
    with pytest.raises(argparse.ArgumentTypeError):
        launcher.rehearsal_port(port)


def test_prepare_reserves_distinct_owned_databases_without_opening_operator(tmp_path,monkeypatch):
    monkeypatch.setattr(launcher,'check_port_available',lambda port:None)
    operator=tmp_path/'data/aegis.sqlite';operator.parent.mkdir();operator.write_bytes(b'operator state unchanged')
    one=launcher.prepare_rehearsal(root=tmp_path)
    two=launcher.prepare_rehearsal(port=8123,root=tmp_path)
    assert one['status']=='prepared' and one['server_started'] is False
    assert one['rehearsal_id']!=two['rehearsal_id']
    for plan in [one,two]:
        assert str(uuid.UUID(plan['rehearsal_id']))==plan['rehearsal_id']
        path=Path(plan['database_path'])
        assert path.parent==tmp_path/'data/rehearsals' and path.read_bytes()==b''
        assert plan['environment']=={'AEGIS_REHEARSAL_ID':plan['rehearsal_id'],'AEGIS_DB_PATH':str(path),'AEGIS_OFFLINE_DEMO':'1'}
        assert plan['working_directory']==str(tmp_path)
    assert one['url']=='http://127.0.0.1:8001/?mode=rehearsal'
    assert two['command'][-1]=='8123'
    assert operator.read_bytes()==b'operator state unchanged'


def test_collision_does_not_overwrite_session_or_operator(tmp_path,monkeypatch):
    monkeypatch.setattr(launcher,'check_port_available',lambda port:None)
    identity=uuid.UUID('9e08ed3f-322c-48bc-83e4-bbf7bc8cce4b')
    monkeypatch.setattr(launcher.uuid,'uuid4',lambda:identity)
    existing=tmp_path/f'data/rehearsals/{identity}.sqlite'
    existing.parent.mkdir(parents=True);existing.write_bytes(b'existing rehearsal history')
    with pytest.raises(FileExistsError):
        launcher.prepare_rehearsal(root=tmp_path)
    assert existing.read_bytes()==b'existing rehearsal history'


def test_port_probe_rejects_occupied_loopback_without_killing_listener(tmp_path):
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as listener:
        listener.bind(('127.0.0.1',0));listener.listen()
        port=listener.getsockname()[1]
        with pytest.raises(RuntimeError,match='no server was stopped'):
            launcher.prepare_rehearsal(port=port,root=tmp_path)
        assert listener.getsockname()[1]==port
        assert not (tmp_path/'data').exists()


def test_prepare_only_prints_only_whitelisted_metadata_and_never_starts_server(tmp_path,monkeypatch,capsys):
    real_prepare=launcher.prepare_rehearsal
    monkeypatch.setattr(launcher,'prepare_rehearsal',lambda port:real_prepare(port,root=tmp_path))
    monkeypatch.setattr(launcher,'check_port_available',lambda port:None)
    monkeypatch.setenv('UNRELATED_PRIVATE_VALUE','do not print this secret')
    monkeypatch.setattr(subprocess,'run',lambda *args,**kwargs:pytest.fail('prepare-only started a process'))
    assert launcher.main(['--prepare-only'])==0
    output=capsys.readouterr()
    plan=json.loads(output.out)
    assert plan['server_started'] is False
    assert 'do not print this secret' not in output.out+output.err
    assert len(plan['powershell_commands'])==5


def test_foreground_launch_uses_owned_env_correct_cwd_and_child_exit(tmp_path,monkeypatch,capsys):
    real_prepare=launcher.prepare_rehearsal
    monkeypatch.setattr(launcher,'prepare_rehearsal',lambda port:real_prepare(port,root=tmp_path))
    monkeypatch.setattr(launcher,'check_port_available',lambda port:None)
    monkeypatch.setenv('AEGIS_DB_PATH','operator-or-inherited.sqlite')
    monkeypatch.setenv('AEGIS_REHEARSAL_ID','inherited-id')
    captured={}
    def run(command,**kwargs):
        captured.update(command=command,**kwargs)
        return subprocess.CompletedProcess(command,7)
    monkeypatch.setattr(subprocess,'run',run)
    assert launcher.main(['--port','8123'])==7
    plan=json.loads(capsys.readouterr().out)
    assert captured['cwd']==str(tmp_path)
    assert captured['command'][-4:]==['--host','127.0.0.1','--port','8123']
    assert captured['env']['AEGIS_DB_PATH']==plan['database_path']
    assert captured['env']['AEGIS_REHEARSAL_ID']==plan['rehearsal_id']
    assert captured['env']['AEGIS_OFFLINE_DEMO']=='1'


def test_unavailable_port_returns_explicit_failure_without_state_creation(tmp_path,monkeypatch,capsys):
    def unavailable(port):raise RuntimeError('port occupied')
    monkeypatch.setattr(launcher,'check_port_available',unavailable)
    assert launcher.main(['--prepare-only'])==2
    body=json.loads(capsys.readouterr().err)
    assert body['status']=='failed' and not body['server_started']
    assert body['error']=='RuntimeError: port occupied'


def test_directory_escape_is_rejected_before_database_creation(tmp_path,monkeypatch):
    monkeypatch.setattr(launcher,'check_port_available',lambda port:None)
    outside=tmp_path/'outside';outside.mkdir()
    workspace=tmp_path/'workspace';workspace.mkdir();(workspace/'data').mkdir()
    try:
        (workspace/'data/rehearsals').symlink_to(outside,target_is_directory=True)
    except OSError:
        pytest.skip('Creating a directory symlink requires an unavailable Windows privilege')
    with pytest.raises(ValueError,match='outside this workspace'):
        launcher.prepare_rehearsal(root=workspace)
    assert list(outside.iterdir())==[]
