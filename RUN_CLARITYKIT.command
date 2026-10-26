#!/bin/bash
set -e
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required. Install Python 3 from https://www.python.org/downloads/macos/ and reopen this file."
  read -r -p "Press Return to close... " _
  exit 1
fi

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate

if ! python -m pip install -r requirements.txt; then
  echo "\nCould not install requirements. Check your internet connection and try again."
  read -r -p "Press Return to close... " _
  exit 1
fi

echo "\nStarting ClarityKit at http://127.0.0.1:5000"
python app.py &
APP_PID=$!
trap 'kill "$APP_PID" 2>/dev/null || true' EXIT
sleep 2
open "http://127.0.0.1:5000" >/dev/null 2>&1 || true
wait "$APP_PID"
