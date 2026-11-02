@echo off
setlocal
pushd "%~dp0"
if errorlevel 1 (
  echo The extracted AEGIS application folder could not be opened.
  pause
  exit /b 2
)
echo AEGIS judge setup - run once after extracting the complete package.
py -3.13 --version >nul 2>&1
if not errorlevel 1 goto use_py
python --version >nul 2>&1
if errorlevel 1 goto missing_python
python "scripts\judge_demo.py" setup
goto finished
:use_py
py -3.13 "scripts\judge_demo.py" setup
goto finished
:missing_python
echo Python was not found. Install Python 3.13, reopen this folder and run setup again.
echo You can still open the PDFs in 01_Guides without installing Python.
set "AEGIS_JUDGE_EXIT=2"
goto exit_setup
:finished
set "AEGIS_JUDGE_EXIT=%ERRORLEVEL%"
echo.
echo Read the setup result above. After successful setup, open Start-Judges-Windows.cmd.
:exit_setup
pause
popd
exit /b %AEGIS_JUDGE_EXIT%
