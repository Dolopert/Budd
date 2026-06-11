#!/bin/bash
# Build a standalone "Pixel Pet.app" bundle with py2app.
set -e
cd "$(dirname "$0")"

PY="${PYTHON:-python3.11}"

if [ ! -d ".venv" ]; then
  "$PY" -m venv .venv
  ./.venv/bin/pip install --upgrade pip
  ./.venv/bin/pip install -r requirements.txt
fi

./.venv/bin/pip install py2app
rm -rf build dist
./.venv/bin/python setup.py py2app

echo
echo "Built: dist/Pixel Pet.app"
echo "Run it with:  open 'dist/Pixel Pet.app'"
