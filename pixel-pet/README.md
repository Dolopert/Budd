# Pixel Pet 🐱

A pixel-art cat desktop companion for **macOS**, built with Python 3.11 +
PyObjC/Cocoa + Pillow. It walks across the bottom of your screen on top of all
windows with true per-pixel transparency.

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

## Run (auto-setup venv + run)
```bash
chmod +x run.sh
./run.sh
```

## Build a standalone .app
```bash
chmod +x build.sh
./build.sh
# → dist/Pixel Pet.app
```

## Auto-run at login
```bash
chmod +x install_autostart.sh
./install_autostart.sh             # install
./install_autostart.sh --uninstall # remove
```

> **Note:** PyObjC/Cocoa is macOS-only. These files won't run on Windows/Linux.
