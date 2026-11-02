# Local startup and terminal lifetime

After README dependency setup, double-click **Start-AEGIS.cmd** on Windows or
run `.venv/Scripts/python scripts/start_local.py`. This builds the current
frontend, validates its local assets and starts the operator backend on loopback
port 8000 in the same terminal. Keep that terminal open. Ctrl+C stops the child
owned by this launcher; no other listener is terminated.

| Option | Behavior |
| --- | --- |
| Default | Build current source using the installed Node/npm runtime, validate assets, then run the server in the foreground |
| `--no-build` | Validate/serve existing prebuilt assets, useful in the reviewer ZIP without Node; source freshness remains unverified |
| `--check-only` | Inspect configuration, assets and listener without building, starting or opening SQLite |
| `--port 8123` | Choose another loopback port rather than interfering with a listener |

The Windows entry point requires the project's `.venv/Scripts/python.exe` and
keeps the console open after failure/exit so its message can be read. It does not
install Python, Node, dependencies or a model. Existing `.tools` Node/npm may be
used where present; they are not included in the shared source or reviewer ZIP.

The effective configuration includes inherited environment and `.env` defaults,
matching the backend. Accidental rehearsal/offline settings or a rehearsal
database path are refused for operator startup. Use `scripts/start_rehearsal.py`
for an intentionally isolated session; no launcher silently repurposes it.

An occupied port is checked before a frontend build. Health/runtime metadata may
identify an already responding AEGIS operator, but the launcher does not claim
its backend is fresh or belongs to this checkout. Stop its known terminal and
relaunch to load source changes. A foreign/unverified listener remains untouched.
The port can also become occupied between inspection and bind; a startup error
is reported rather than killing that process.

Startup checks never probe `/api/network`, which can initialize simulated state.
They validate only bounded metadata/assets and do not prove source/API uptime,
scientific model quality or production deployment. Foreground startup is not a
Windows service, scheduled job or guarantee that an agent-launched process will
survive an interrupted chat session. Use the visible local terminal for a
user-controlled session.

Unit evidence is in `tests/test_local_launcher.py`; actual owned-process smoke
evidence is recorded separately in `reports/local_startup_verification.json`.
Windows automated control-event delivery is a harness simulation of the
interrupt handler, not a physical keyboard demonstration.
