#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -d .venv ]; then python3 -m venv .venv; fi
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if [ ! -f .env ]; then cp .env.example .env; echo "Edit .env with your Angel One SmartAPI credentials, then rerun ./run_dashboard.sh"; exit 0; fi
python server.py
