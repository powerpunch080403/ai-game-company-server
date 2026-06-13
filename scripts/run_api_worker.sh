#!/usr/bin/env bash
set -euo pipefail
export GAME_COMPANY_SERVER="${GAME_COMPANY_SERVER:-http://127.0.0.1:8080}"
python_bin="${PYTHON:-python}"
if [ -x ".venv/bin/python" ]; then
  python_bin=".venv/bin/python"
fi
"$python_bin" -m app.api_worker "$@"
