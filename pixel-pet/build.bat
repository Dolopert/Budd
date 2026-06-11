@echo off
REM Build a standalone PixelPet.exe with PyInstaller (Windows).
cd /d "%~dp0"

if not exist ".venv" (
  py -3.11 -m venv .venv 2>nul || python -m venv .venv
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  ".venv\Scripts\pip.exe" install -r requirements-windows.txt
)

".venv\Scripts\pip.exe" install pyinstaller
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

".venv\Scripts\pyinstaller.exe" --noconsole --onefile ^
  --name PixelPet ^
  --add-data "sprite_sheet;sprite_sheet" ^
  pet_win.py

echo.
echo Built: dist\PixelPet.exe
