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

## Windows
```bat
run.bat                             :: auto-setup .venv + run
build.bat                           :: → dist\PixelPet.exe (PyInstaller)
install_autostart.bat              :: auto-run at login (per-user)
install_autostart.bat uninstall
```

> PyObjC/Cocoa is macOS-only; PySide6 is cross-platform. Use the entry point
> for your OS.
