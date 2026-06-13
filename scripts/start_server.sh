#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

mkdir -p data

if [ -f data/server.pid ] && kill -0 "$(cat data/server.pid)" 2>/dev/null; then
  echo "Server already running with PID $(cat data/server.pid)"
  exit 0
fi

nohup .venv/bin/python -m uvicorn app.main:app \
  --host "${GAME_COMPANY_HOST:-0.0.0.0}" \
  --port "${GAME_COMPANY_PORT:-8080}" \
  > data/server.out.log 2> data/server.err.log &

echo "$!" > data/server.pid
echo "Started server with PID $(cat data/server.pid)"
