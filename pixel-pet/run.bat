@echo off
REM Run Pixel Pet now (Windows). Creates .venv and installs deps on first run.
cd /d "%~dp0"

if not exist ".venv" (
  echo Setting up virtualenv (.venv)...
  py -3.11 -m venv .venv 2>nul || python -m venv .venv
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  ".venv\Scripts\pip.exe" install -r requirements-windows.txt
)

REM pythonw = no console window. Use python.exe instead to see logs / Ctrl+C.
start "" ".venv\Scripts\pythonw.exe" pet_win.py
