# AEGIS — start here

For judges, share **artifacts/AEGIS-Judges.zip**. Extract it completely, open the
**AEGIS-Judges** folder, then double-click **00_START_HERE.html**. A text version
is alongside it. The numbered folders separate guides, the runnable application,
and measured verification evidence.

The PDFs open without installation. For the interactive demo on Windows, install
Python 3.13 (64-bit), open **02_Application**, run **Setup-Judges-Windows.cmd**
once, then run **Start-Judges-Windows.cmd**. The setup downloads pinned Python
dependencies. The demo uses a fresh isolated simulated session, the prebuilt
frontend, dated evidence fixtures and labeled route estimates. Node.js and API
keys are not required for this route. Map tiles still require internet.

Detailed instructions: [judge quick start](docs/judge_quick_start.md) and
[five-minute walkthrough](docs/judge_walkthrough.md). Repository layout:
[folder map](docs/folder_map.md).

Build the organized handoff after verifying the application archive:

```powershell
.venv/Scripts/python scripts/package_submission.py --output artifacts/AEGIS-Final-Build.zip
.venv/Scripts/python scripts/verify_package.py --archive artifacts/AEGIS-Final-Build.zip
.venv/Scripts/python scripts/build_judge_handoff.py
```

Keep the original supplied data in place. Neither packaging command requires a
raw-data download or changes the operator's assignments. The source repository
contains the same instructions; `artifacts/` is generated locally and excluded
from Git. Kiro non-use and scientific limitations remain explicitly disclosed.
