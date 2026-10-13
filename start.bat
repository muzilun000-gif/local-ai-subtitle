@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
set PY_VER=
where py >nul 2>nul
if errorlevel 1 goto check_python
for %%V in (3.12 3.11 3.13 3.10) do if not defined PY_VER call :probe %%V
if defined PY_VER goto use_py
:check_python
python -c "import sys; sys.exit(0 if (3,10) <= sys.version_info[:2] <= (3,13) else 1)" >nul 2>nul
if errorlevel 1 (
  echo Please install Python 3.11 or 3.12: https://www.python.org/downloads/
  pause
  exit /b 1
)
python tools\launch.py %*
goto done
:use_py
py -%PY_VER% tools\launch.py %*
:done
set RESULT=%ERRORLEVEL%
if not "%RESULT%"=="0" pause
exit /b %RESULT%
:probe
py -%1 -c "import sys" >nul 2>nul
if not errorlevel 1 set PY_VER=%1
exit /b 0
