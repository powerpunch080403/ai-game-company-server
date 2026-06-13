#!/usr/bin/env bash
set -euo pipefail

host="${1:?Usage: scripts/check_remote.sh user@host}"

ssh "$host" 'set -e; hostname; uname -a; command -v git; command -v python3'
