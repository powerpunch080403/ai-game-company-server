#!/usr/bin/env bash
set -euo pipefail

python_bin="${PYTHON:-python}"
"$python_bin" -m app.project_template "$@"
