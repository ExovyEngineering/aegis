"""Set up or start the packaged, isolated AEGIS judge demonstration.

Setup installs pinned Python dependencies only when explicitly requested. Run
uses bundled frontend assets and a fresh offline rehearsal database each time.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from urllib.error import URLError
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.start_local import _local_json, frontend_assets
from scripts.start_rehearsal import prepare_rehearsal, rehearsal_port

DEPENDENCIES = ("fastapi", "uvicorn", "pandas", "sklearn", "ortools", "pydantic",
                "pyarrow", "httpx", "yaml", "openpyxl", "pypdf", "ijson", "matplotlib")


def require_tested_python(version=None):
    version = sys.version_info if version is None else version
    if tuple(version[:2]) != (3, 13):
        raise ValueError("This package was tested with Python 3.13. Install Python 3.13 and run setup again.")


def environment_python(root=ROOT):
    root = Path(root).resolve()
    environment = (root / ".venv").resolve()
    if not environment.is_relative_to(root) or environment == root:
        raise ValueError("The project .venv resolves outside its own folder; choose a clean extracted package.")
    relative = "Scripts/python.exe" if os.name == "nt" else "bin/python"
    interpreter = environment / relative
    return environment, interpreter


def setup(root=ROOT):
    require_tested_python()
    root = Path(root).resolve()
    locked = root / "requirements-lock.txt"
    if not locked.is_file():
        raise ValueError("requirements-lock.txt is missing. Extract the complete judge package first.")
    environment, interpreter = environment_python(root)
    if environment.exists() and any(environment.iterdir()) and not (environment / "pyvenv.cfg").is_file():
        raise ValueError("The existing .venv is not a Python virtual environment. Use a clean extracted package.")
    if not interpreter.is_file():
        print("Creating this package's Python environment...", flush=True)
        result = subprocess.run([sys.executable, "-m", "venv", str(environment)], cwd=root)
        if result.returncode:
            return result.returncode
        if not interpreter.is_file():
            raise ValueError("Python could not create .venv. Check folder write access and the Python installation.")
    version = subprocess.run([str(interpreter), "-c", "import sys; print('.'.join(map(str, sys.version_info[:2])))"],
                             cwd=root, capture_output=True, text=True)
    if version.returncode or version.stdout.strip() != "3.13":
        raise ValueError("The existing .venv does not use Python 3.13. Extract a clean package and run setup with Python 3.13.")
    print("Installing pinned dependencies. This one-time step needs internet access.", flush=True)
    result = subprocess.run([str(interpreter), "-m", "pip", "install", "-r", str(locked)], cwd=root)
    if result.returncode == 0:
        print("Setup complete. Run Start-Judges-Windows.cmd, or use this environment's Python with scripts/judge_demo.py run.", flush=True)
    else:
        print("Dependency installation failed. Check the error above and your internet connection, then rerun setup.", file=sys.stderr)
    return result.returncode


def require_dependencies():
    missing = [name for name in DEPENDENCIES if importlib.util.find_spec(name) is None]
    if missing:
        raise ValueError("Python dependencies are missing: " + ", ".join(missing) +
                         ". Run Setup-Judges-Windows.cmd or scripts/judge_demo.py setup first.")


def wait_and_open(port, identity, url, stopped, timeout=20):
    """Only open a browser after the exact newly reserved offline runtime responds."""
    deadline = time.monotonic() + timeout
    while not stopped.is_set() and time.monotonic() < deadline:
        try:
            healthy = _local_json(port, "/api/health")
            runtime = _local_json(port, "/api/runtime-context")
            expected_database = f"data/rehearsals/{identity}.sqlite"
            if (isinstance(healthy, dict) and isinstance(runtime, dict)
                    and healthy.get("status") == "ok" and runtime.get("mode") == "isolated_rehearsal"
                    and runtime.get("isolated") is True and runtime.get("offline") is True
                    and runtime.get("rehearsal_id") == identity
                    and runtime.get("database_relative_path") == expected_database):
                if not stopped.is_set() and not webbrowser.open(url, new=2):
                    print("Open this address in your browser: " + url, flush=True)
                return
        except (OSError, ValueError, URLError, webbrowser.Error):
            pass
        stopped.wait(0.25)
    if not stopped.is_set():
        print("Automatic browser opening timed out. When the server is ready, open: " + url, flush=True)


def run(port=8001, open_browser=False, root=ROOT):
    require_tested_python()
    root = Path(root).resolve()
    require_dependencies()
    try:
        frontend_assets(root)
    except (OSError, ValueError) as error:
        raise ValueError("The bundled frontend cannot be opened. Re-extract the complete judge package. " + str(error)) from error
    launch = prepare_rehearsal(port=port, root=root)
    environment = dict(os.environ)
    environment.update(launch["environment"])
    print("\nAEGIS judge demonstration", flush=True)
    print("Open: " + launch["url"], flush=True)
    print("Keep this terminal open. Press Ctrl+C to stop this demonstration.", flush=True)
    print("A fresh isolated simulated session is used. Source fixtures are dated; routing estimates and telemetry are labeled.", flush=True)
    print("Map tiles need internet. No Node.js build, API key or AWS account is needed for this demo.\n", flush=True)
    stopped = threading.Event()
    if open_browser:
        threading.Thread(target=wait_and_open,
                         args=(port, launch["rehearsal_id"], launch["url"], stopped), daemon=True).start()
    try:
        result = subprocess.run(launch["command"], cwd=root, env=environment)
        return result.returncode
    except KeyboardInterrupt:
        return 130
    finally:
        stopped.set()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("setup", help="Create/reuse .venv and install pinned Python dependencies (internet required)")
    start = commands.add_parser("run", help="Start a fresh isolated demo using the included frontend")
    start.add_argument("--port", type=rehearsal_port, default=8001)
    start.add_argument("--open-browser", action="store_true")
    args = parser.parse_args(argv)
    try:
        return setup() if args.action == "setup" else run(args.port, args.open_browser)
    except (OSError, RuntimeError, ValueError, argparse.ArgumentTypeError) as error:
        print("AEGIS could not start: " + str(error), file=sys.stderr)
        if args.action == "run":
            alternate = 8003 if args.port == 8002 else 8002
            print(f"If the port is occupied, rerun scripts/judge_demo.py run --port {alternate}. No existing server is stopped.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
