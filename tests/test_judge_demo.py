"""Judge setup and foreground startup must preserve raw/operator inputs."""
from pathlib import Path
import subprocess
import threading

import pytest

from scripts import judge_demo as judge


def packaged_workspace(tmp_path):
    root = tmp_path / "AEGIS application with spaces"
    (root / "frontend/dist/assets").mkdir(parents=True)
    (root / "frontend/dist/index.html").write_text('<script src="/assets/app.js"></script>', encoding="utf-8")
    (root / "frontend/dist/assets/app.js").write_text("console.log('packaged')", encoding="utf-8")
    (root / "requirements-lock.txt").write_text("example==1.0\n", encoding="utf-8")
    (root / "data/raw").mkdir(parents=True)
    (root / "data/raw/source.csv").write_bytes(b"do not change\r\n")
    (root / "data/aegis.sqlite").write_bytes(b"operator state")
    return root


def protected(root):
    return {(root / name): (root / name).read_bytes() for name in
            ("data/raw/source.csv", "data/aegis.sqlite", "requirements-lock.txt", "frontend/dist/index.html")}


def test_setup_creates_owned_environment_and_only_installs_explicit_pinned_requirements(tmp_path, monkeypatch):
    root = packaged_workspace(tmp_path)
    before = protected(root)
    calls = []
    environment, interpreter = judge.environment_python(root)

    def execute(command, **kwargs):
        calls.append((command, kwargs))
        if command[1:3] == ["-m", "venv"]:
            interpreter.parent.mkdir(parents=True)
            interpreter.write_bytes(b"fake interpreter for this mocked test")
            (environment / "pyvenv.cfg").write_text("version = 3.13\n")
        return subprocess.CompletedProcess(command, 0, "3.13\n" if "-c" in command else "", "")

    monkeypatch.setattr(judge.subprocess, "run", execute)
    assert judge.setup(root) == 0
    assert calls[0][0] == [judge.sys.executable, "-m", "venv", str(environment)]
    assert calls[-1][0] == [str(interpreter), "-m", "pip", "install", "-r", str(root / "requirements-lock.txt")]
    assert all(kwargs["cwd"] == root for _, kwargs in calls)
    assert all(path.read_bytes() == body for path, body in before.items())
    assert not (root / "data/rehearsals").exists()


def test_existing_environment_is_not_recreated_or_retried_when_install_fails(tmp_path, monkeypatch):
    root = packaged_workspace(tmp_path)
    environment, interpreter = judge.environment_python(root)
    interpreter.parent.mkdir(parents=True)
    interpreter.write_bytes(b"existing interpreter")
    (environment / "pyvenv.cfg").write_text("version = 3.13\n")
    calls = []

    def execute(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0 if "-c" in command else 7, "3.13\n", "")

    monkeypatch.setattr(judge.subprocess, "run", execute)
    assert judge.setup(root) == 7
    assert len(calls) == 2 and all("venv" not in command for command in calls)
    assert interpreter.read_bytes() == b"existing interpreter"


@pytest.mark.parametrize("version", [(3, 12, 10), (3, 14, 0)])
def test_unsupported_python_does_not_run_setup(version, monkeypatch):
    monkeypatch.setattr(judge.sys, "version_info", version)
    monkeypatch.setattr(judge.subprocess, "run", lambda *args, **kwargs: pytest.fail("Unsupported Python installed packages"))
    with pytest.raises(ValueError, match="Python 3.13"):
        judge.setup()


def test_setup_rejects_unrelated_existing_venv_directory(tmp_path, monkeypatch):
    root = packaged_workspace(tmp_path)
    unrelated = root / ".venv/notes.txt"
    unrelated.parent.mkdir()
    unrelated.write_bytes(b"preserve unrelated content")
    monkeypatch.setattr(judge.subprocess, "run", lambda *args, **kwargs: pytest.fail("Overwrote unrelated folder"))
    with pytest.raises(ValueError, match="not a Python virtual environment"):
        judge.setup(root)
    assert unrelated.read_bytes() == b"preserve unrelated content"


def test_run_uses_fresh_offline_uuid_prebuilt_assets_and_never_builds_or_installs(tmp_path, monkeypatch, capsys):
    root = packaged_workspace(tmp_path)
    before = protected(root)
    monkeypatch.setattr(judge, "require_dependencies", lambda: None)
    monkeypatch.setattr("scripts.start_rehearsal.check_port_available", lambda port: None)
    monkeypatch.setenv("AEGIS_DB_PATH", "inherited-operator.sqlite")
    monkeypatch.setenv("AEGIS_REHEARSAL_ID", "inherited")
    monkeypatch.setenv("PRIVATE_JUDGE_TOKEN", "never print this")
    calls = []

    def execute(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(judge.subprocess, "run", execute)
    assert judge.run(port=8123, root=root) == 0
    assert judge.run(port=8123, root=root) == 0
    assert len(calls) == 2
    identities = []
    for command, kwargs in calls:
        assert command[1:4] == ["-m", "uvicorn", "backend.main:app"]
        assert command[-4:] == ["--host", "127.0.0.1", "--port", "8123"]
        assert kwargs["cwd"] == root and kwargs["env"]["AEGIS_OFFLINE_DEMO"] == "1"
        identity = kwargs["env"]["AEGIS_REHEARSAL_ID"]
        identities.append(identity)
        assert kwargs["env"]["AEGIS_DB_PATH"] == str(root / f"data/rehearsals/{identity}.sqlite")
        assert Path(kwargs["env"]["AEGIS_DB_PATH"]).read_bytes() == b""
    assert identities[0] != identities[1]
    assert all(path.read_bytes() == body for path, body in before.items())
    output = capsys.readouterr().out
    assert "http://127.0.0.1:8123/?mode=rehearsal" in output
    assert "never print this" not in output


def test_port_conflict_does_not_start_process_or_create_a_database(tmp_path, monkeypatch):
    root = packaged_workspace(tmp_path)
    monkeypatch.setattr(judge, "require_dependencies", lambda: None)
    def occupied(port):
        raise RuntimeError("Loopback port occupied; no server was stopped")
    monkeypatch.setattr("scripts.start_rehearsal.check_port_available", occupied)
    monkeypatch.setattr(judge.subprocess, "run", lambda *args, **kwargs: pytest.fail("Started a server on occupied port"))
    before = protected(root)
    with pytest.raises(RuntimeError, match="occupied"):
        judge.run(root=root)
    assert not (root / "data/rehearsals").exists()
    assert all(path.read_bytes() == body for path, body in before.items())


def test_missing_frontend_aborts_before_reserving_a_session(tmp_path, monkeypatch):
    root = packaged_workspace(tmp_path)
    (root / "frontend/dist/assets/app.js").unlink()
    monkeypatch.setattr(judge, "require_dependencies", lambda: None)
    monkeypatch.setattr(judge, "prepare_rehearsal", lambda **kwargs: pytest.fail("Reserved session with incomplete frontend"))
    with pytest.raises(ValueError, match="Re-extract"):
        judge.run(root=root)


def test_browser_waits_for_exact_isolated_offline_runtime(monkeypatch):
    identity = "9e08ed3f-322c-48bc-83e4-bbf7bc8cce4b"
    stopped = threading.Event()
    opened = []
    states = iter([
        {"mode": "operator"},
        {"mode": "isolated_rehearsal", "isolated": True, "offline": True,
         "rehearsal_id": identity, "database_relative_path": f"data/rehearsals/{identity}.sqlite"},
    ])
    calls = []
    def read(port, path):
        calls.append((port, path))
        return {"status": "ok"} if path == "/api/health" else next(states)
    monkeypatch.setattr(judge, "_local_json", read)
    monkeypatch.setattr(judge.webbrowser, "open", lambda url, new: opened.append(url) or True)
    judge.wait_and_open(8001, identity, "http://127.0.0.1:8001/?mode=rehearsal", stopped, timeout=2)
    assert len(calls) == 4 and opened == ["http://127.0.0.1:8001/?mode=rehearsal"]


def test_browser_never_opens_when_startup_is_cancelled_or_times_out(monkeypatch, capsys):
    stopped = threading.Event()
    monkeypatch.setattr(judge, "_local_json", lambda *args: pytest.fail("Read after cancellation/deadline"))
    monkeypatch.setattr(judge.webbrowser, "open", lambda *args, **kwargs: pytest.fail("Opened an unverified browser target"))
    judge.wait_and_open(8001, "unused", "http://127.0.0.1:8001/", stopped, timeout=0)
    assert "timed out" in capsys.readouterr().out
    stopped.set()
    judge.wait_and_open(8001, "unused", "http://127.0.0.1:8001/", stopped, timeout=5)
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("healthy, runtime", [
    ([], {}),
    ({"status": "ok"}, []),
    ({"status": "ok"}, {"mode": "isolated_rehearsal", "isolated": True, "offline": True,
                          "rehearsal_id": "different-session", "database_relative_path": "data/rehearsals/different-session.sqlite"}),
])
def test_browser_rejects_malformed_or_another_sessions_runtime(monkeypatch, healthy, runtime):
    stopped = threading.Event()
    monkeypatch.setattr(stopped, "wait", lambda duration: stopped.set())
    monkeypatch.setattr(judge, "_local_json", lambda port, path: healthy if path == "/api/health" else runtime)
    monkeypatch.setattr(judge.webbrowser, "open", lambda *args, **kwargs: pytest.fail("Opened another or malformed runtime"))
    judge.wait_and_open(8001, "expected-session", "http://127.0.0.1:8001/", stopped, timeout=5)


def test_windows_launchers_use_local_environment_foreground_and_quoted_paths():
    root = Path(__file__).resolve().parents[1]
    start = (root / "Start-Judges-Windows.cmd").read_text()
    setup = (root / "Setup-Judges-Windows.cmd").read_text()
    assert 'pushd "%~dp0"' in start and 'pushd "%~dp0"' in setup
    assert '".venv\\Scripts\\python.exe" "scripts\\judge_demo.py" run --open-browser %*' in start
    assert 'py -3.13 "scripts\\judge_demo.py" setup\ngoto finished' in setup
    assert "pip" not in start and "taskkill" not in start.lower()
