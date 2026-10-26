# Working on AEGIS

Read [the engineering rules](AGENTS.md), [priorities](docs/priority_matrix.md),
and [scientific limitations](docs/model_card.md) before changing behavior.

## First checkout

Install Git, Python 3.13 and Node.js 22. Clone the team's repository, then run
these commands from its root in PowerShell:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-lock.txt
Copy-Item .env.example .env
npm --prefix frontend ci
npm --prefix frontend run build
.venv/Scripts/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. The app creates a fresh simulated SQLite database.
The checkout includes derived datasets, dated evidence fixtures and measured
results; the original large downloads and local operational state are excluded.
You do not need to re-ingest raw sources just to run the app. For a separate
frontend development server, run `npm --prefix frontend run dev` while FastAPI
is running. Each teammate has their own local database and scenario state.

For raw-data reproduction, obtain the original files from the project owner,
set `AEGIS_DATA_DIR` to that folder, and follow the ingestion commands in
[README.md](README.md). Do not replace the original audit with a scan of a
checkout missing those downloads. The manifest records their checksums.

## Make a change

```powershell
git switch main
git pull --ff-only
git switch -c feature/short-description
# Make and verify your changes.
.venv/Scripts/python -m pytest -q
npm --prefix frontend test
npm --prefix frontend run build
git add <specific-files>
git diff --cached
git commit -m "Describe the resulting behavior"
git push -u origin feature/short-description
```

Open a pull request into `main`; explain behavior, verification and remaining
limitations. Coordinate before editing the same large UI or API module.
Keep unrelated generated results out of a feature PR. CI repeats backend tests,
frontend tests and the production build, without live-source refreshes.

Never commit `.env`, credentials, runtime installations, local SQLite databases,
or original bulk downloads. Keep dated fixtures labeled; never invent API
success or evaluation metrics. Human approval remains mandatory for holds and
dispatch decisions. A predictive score cannot independently impose a hold.

## Owner: invite teammates

In the private repository, open **Settings > Collaborators** (or organization
access settings), invite each teammate by GitHub username, and grant the access
needed for their work. Teammates must accept the invitation before cloning.
Share the repository URL; do not share account passwords or access tokens.

Branch protection and required reviews depend on the repository's GitHub plan.
An Actions workflow in the repository does not itself enforce merge protection.
