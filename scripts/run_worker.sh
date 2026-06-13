#!/usr/bin/env bash
set -euo pipefail
export GAME_COMPANY_SERVER="${GAME_COMPANY_SERVER:-http://127.0.0.1:8080}"
python -m app.worker_runner "$@"
