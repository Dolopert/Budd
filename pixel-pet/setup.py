"""
py2app build script for Pixel Pet.

Build a standalone .app bundle (hidden from the Dock via LSUIElement):

    pip install py2app
    python setup.py py2app

The result is dist/Pixel Pet.app
"""

from setuptools import setup

APP = ["pet.py"]

DATA_FILES = [
    ("sprite_sheet", [
        "sprite_sheet/walk_sprite.png",
        "sprite_sheet/sit_sprite.png",
    ]),
]

OPTIONS = {
    "argv_emulation": False,
    "packages": ["PIL"],
    "plist": {
        "CFBundleName": "Pixel Pet",
        "CFBundleDisplayName": "Pixel Pet",
        "CFBundleIdentifier": "com.pixelpet.app",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "LSUIElement": True,  # hide from the Dock
        "NSHighResolutionCapable": True,
    },
}

setup(
    app=APP,
    name="Pixel Pet",
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
