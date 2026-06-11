@echo off
REM Auto-run Pixel Pet at Windows login (per-user, no admin needed).
REM   install_autostart.bat              -> install
REM   install_autostart.bat uninstall    -> remove
cd /d "%~dp0"

set "RUNKEY=HKCU\Software\Microsoft\Windows\CurrentVersion\Run"
set "NAME=PixelPet"

if /i "%~1"=="uninstall" (
  reg delete "%RUNKEY%" /v "%NAME%" /f
  echo Removed auto-start.
  goto :eof
)

set "PYW=%~dp0.venv\Scripts\pythonw.exe"
set "SCRIPT=%~dp0pet_win.py"

if not exist "%PYW%" (
  echo .venv not found. Run run.bat once first to create it.
  goto :eof
)

reg add "%RUNKEY%" /v "%NAME%" /t REG_SZ /d "\"%PYW%\" \"%SCRIPT%\"" /f
echo Installed auto-start: Pixel Pet will launch at login.
