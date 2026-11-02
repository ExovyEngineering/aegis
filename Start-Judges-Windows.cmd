@echo off
setlocal
pushd "%~dp0"
if errorlevel 1 (
  echo The extracted AEGIS application folder could not be opened.
  pause
  exit /b 2
)
if not exist ".venv\Scripts\python.exe" (
  echo Run Setup-Judges-Windows.cmd first to install this package's Python dependencies.
  pause
  popd
  exit /b 2
)
".venv\Scripts\python.exe" "scripts\judge_demo.py" run --open-browser %*
set "AEGIS_JUDGE_EXIT=%ERRORLEVEL%"
echo.
echo This AEGIS demonstration has stopped. Run this file again for a fresh simulated session.
pause
popd
exit /b %AEGIS_JUDGE_EXIT%
