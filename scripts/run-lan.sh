#!/bin/zsh
# Same API as run.sh but reachable from a phone on the same Wi-Fi (the Expo app finds this computer automatically).
cd "$(dirname "$0")/../backend" && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8010
