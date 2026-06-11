@echo off
REM ===========================================================================
REM  Pixel Pet - ONE-CLICK installer + launcher (Windows)
REM
REM  Copy this whole folder to any Windows PC and double-click this file.
REM  It will, with no manual steps:
REM    1. Find Python - or download & install Python 3.11 if it's missing
REM    2. Create a private virtual environment (.venv)
REM    3. Download the libraries it needs (PySide6, Pillow)
REM    4. Start the cat
REM  Run it again any time to just launch the cat (setup is skipped once done).
REM ===========================================================================
setlocal enableextensions
title Pixel Pet - Setup and Run
cd /d "%~dp0"

echo(
echo  ===========================================
echo    Pixel Pet - one-click setup
echo  ===========================================
echo(

REM ---------------------------------------------------------------------------
REM 1. Locate a usable Python (3.9+). If none, install it.
REM ---------------------------------------------------------------------------
call :find_python
if defined PYEXE goto have_python

echo  Python was not found on this PC.
echo  Downloading and installing Python 3.11 (one-time, no admin needed)...
echo(
call :install_python
call :find_python
if defined PYEXE goto have_python

echo(
echo  [X] Could not install Python automatically.
echo      Please install it manually from:
echo          https://www.python.org/downloads/
echo      During setup tick "Add python.exe to PATH", then run this file again.
echo(
pause
exit /b 1

:have_python
echo  Using Python: %PYEXE%
echo(

REM ---------------------------------------------------------------------------
REM 2. Create the virtual environment if it isn't there yet.
REM ---------------------------------------------------------------------------
if not exist ".venv\Scripts\python.exe" (
    echo  Creating virtual environment .venv ...
    "%PYEXE%" -m venv .venv
    if errorlevel 1 (
        echo  [X] Failed to create the virtual environment.
        pause
        exit /b 1
    )
)

REM ---------------------------------------------------------------------------
REM 3. Install the libraries only if they aren't already present.
REM ---------------------------------------------------------------------------
".venv\Scripts\python.exe" -c "import PySide6, PIL" >nul 2>nul
if errorlevel 1 (
    echo  Downloading libraries PySide6 and Pillow... this may take a minute.
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements-windows.txt
    if errorlevel 1 (
        echo  [X] Failed to install the libraries. Check your internet connection.
        pause
        exit /b 1
    )
)

REM ---------------------------------------------------------------------------
REM 4. Launch. pythonw = no console window.
REM ---------------------------------------------------------------------------
echo(
echo  All set! Starting Pixel Pet...
echo  (Left-click = sit, drag = move, right-click = Quit)
echo(
start "" ".venv\Scripts\pythonw.exe" pet_win.py
exit /b 0


REM ===========================================================================
REM Subroutines
REM ===========================================================================

:find_python
REM Sets PYEXE to a working Python (3.9+) path, or leaves it undefined.
set "PYEXE="
for /f "delims=" %%V in ('py -3.11 -c "import sys;print(sys.executable)" 2^>nul') do set "PYEXE=%%V"
if defined PYEXE exit /b
for /f "delims=" %%V in ('py -3 -c "import sys;print(sys.executable)" 2^>nul') do set "PYEXE=%%V"
if defined PYEXE exit /b
for /f "delims=" %%V in ('python -c "import sys;print(sys.executable)" 2^>nul') do set "PYEXE=%%V"
if defined PYEXE exit /b
REM Fall back to the usual per-user install locations.
for %%D in (
    "%LocalAppData%\Programs\Python\Python311\python.exe"
    "%LocalAppData%\Programs\Python\Python312\python.exe"
    "%LocalAppData%\Programs\Python\Python310\python.exe"
    "%ProgramFiles%\Python311\python.exe"
) do if exist %%~D set "PYEXE=%%~D"
exit /b

:install_python
REM Prefer winget (built into modern Windows); fall back to a direct download.
where winget >nul 2>nul
if %errorlevel%==0 (
    echo  Installing via winget...
    winget install -e --id Python.Python.3.11 --scope user --accept-package-agreements --accept-source-agreements
    exit /b
)
set "PYURL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
set "PYTMP=%TEMP%\pixelpet-python-3.11.9.exe"
echo  Downloading Python installer...
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri '%PYURL%' -OutFile '%PYTMP%' } catch { exit 1 }"
if not exist "%PYTMP%" (
    echo  [X] Download failed.
    exit /b
)
echo  Running Python installer (silent)...
"%PYTMP%" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_test=0
del "%PYTMP%" >nul 2>nul
exit /b
