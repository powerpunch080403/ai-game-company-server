#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

db_path="${GAME_COMPANY_DB_PATH:-./data/game_company.sqlite3}"
backup_dir="${GAME_COMPANY_BACKUP_DIR:-./backups}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"

mkdir -p "$backup_dir"

if [ ! -f "$db_path" ]; then
  echo "Database not found: $db_path"
  exit 1
fi

sqlite3 "$db_path" ".backup '$backup_dir/game_company_$timestamp.sqlite3'"
echo "Backup written: $backup_dir/game_company_$timestamp.sqlite3"
