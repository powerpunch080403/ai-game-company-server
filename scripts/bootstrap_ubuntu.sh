#!/usr/bin/env bash
set -euo pipefail

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m app.seed

cat <<'MSG'
Server is ready.
Run: source .venv/bin/activate && ./scripts/run_dev.sh
API docs: http://SERVER_IP:8080/docs
MSG
