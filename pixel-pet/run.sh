#!/bin/bash
# Run Pixel Pet now. Creates a local virtualenv and installs deps on first run.
set -e
cd "$(dirname "$0")"

PY="${PYTHON:-python3.11}"

if [ ! -d ".venv" ]; then
  echo "Setting up virtualenv (.venv)..."
  "$PY" -m venv .venv
  ./.venv/bin/pip install --upgrade pip
  ./.venv/bin/pip install -r requirements.txt
fi

exec ./.venv/bin/python pet.py
