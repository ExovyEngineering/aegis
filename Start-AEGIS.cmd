@echo off
setlocal
pushd "%~dp0"
if errorlevel 1 (
  echo The AEGIS project directory could not be opened.
  pause
  exit /b 2
)
if not exist ".venv\Scripts\python.exe" (
  echo The project Python environment is missing. Follow README.md to install the locked dependencies.
  pause
  popd
  exit /b 2
)
".venv\Scripts\python.exe" "scripts\start_local.py" %*
set "AEGIS_LAUNCH_EXIT=%ERRORLEVEL%"
echo.
echo AEGIS launcher finished. If a new server was started here, it has stopped.
pause
popd
exit /b %AEGIS_LAUNCH_EXIT%
