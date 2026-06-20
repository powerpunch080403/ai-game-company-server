#!/usr/bin/env bash
set -euo pipefail

python -m app.worker_supervisor "$@"
