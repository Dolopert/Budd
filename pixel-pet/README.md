# Pixel Pet 🐱

A pixel-art cat desktop companion that walks across the bottom of your screen
on top of all windows with true per-pixel transparency.

| Platform | Entry point | Stack |
|----------|-------------|-------|
| **macOS** | `pet.py` | Python 3.11 + PyObjC/Cocoa + Pillow |
| **Windows** | `pet_win.py` | Python 3.11 + PySide6 (Qt) + Pillow |

Both versions share the same behaviour and constants.

## Features
- Walks along the bottom of the screen, above all apps (window level 25)
- True per-pixel transparency — no background box
- **Left click** → sits for 3 seconds, then walks again
- Sits down on its own every 8–20 seconds while wandering
- **Drag** → move the cat anywhere on screen
- **Right click** → menu with *Quit Pixel Pet*
- Speech bubbles above the cat
  - Sitting: `~meow meow`, `purrr...`, `nya~`, `(˘ω˘)`
  - Walking (every ~8s): `where my fish nya`, `i am speed ~`, `sniff sniff`, `zoomies!!`
- Single-instance lock, clean quit on Ctrl+C and right-click quit
- Hidden from the Dock

## Setup
Drop the two sprite sheets into `sprite_sheet/`:

```
sprite_sheet/walk_sprite.png
sprite_sheet/sit_sprite.png
```

## macOS
```bash
chmod +x run.sh build.sh install_autostart.sh
./run.sh                            # auto-setup venv + run
./build.sh                          # → dist/Pixel Pet.app
./install_autostart.sh             # auto-run at login
./install_autostart.sh --uninstall
```

## Windows — easiest (any PC, one click)
Copy this whole folder to the other computer, then **double-click
`INSTALL-AND-RUN.bat`**. With no manual steps it:
1. Finds Python — or downloads & installs Python 3.11 if it's missing
2. Creates the `.venv` and downloads the libraries (PySide6, Pillow)
3. Starts the cat

Run it again any time to just launch (setup is skipped once done).

## Windows — manual
```bat
INSTALL-AND-RUN.bat                 :: one-click: installs Python if needed, then runs
run.bat                             :: auto-setup .venv + run (assumes Python already installed)
build.bat                           :: → dist\PixelPet.exe (PyInstaller)
install_autostart.bat              :: auto-run at login (per-user)
install_autostart.bat uninstall
```

> PyObjC/Cocoa is macOS-only; PySide6 is cross-platform. Use the entry point
> for your OS.
