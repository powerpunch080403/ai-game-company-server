#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f data/server.pid ]; then
  echo "No PID file found."
  exit 0
fi

pid="$(cat data/server.pid)"
if kill -0 "$pid" 2>/dev/null; then
  kill "$pid"
  echo "Stopped server with PID $pid"
else
  echo "Server process $pid is not running."
fi

rm -f data/server.pid
