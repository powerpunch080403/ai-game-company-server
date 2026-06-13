from __future__ import annotations

import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def main() -> int:
    db_path = Path(os.getenv("GAME_COMPANY_DB_PATH", "./data/game_company.sqlite3"))
    backup_dir = Path(os.getenv("GAME_COMPANY_BACKUP_DIR", "./backups"))
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return 1

    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_path = backup_dir / f"game_company_{timestamp}.sqlite3"

    source = sqlite3.connect(db_path)
    try:
        target = sqlite3.connect(backup_path)
        try:
            source.backup(target)
        finally:
            target.close()
    finally:
        source.close()

    print(f"Backup written: {backup_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
