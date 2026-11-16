#!/bin/zsh
# Starts the Mieux API + web app on http://localhost:8010
cd "$(dirname "$0")/backend" && .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8010
