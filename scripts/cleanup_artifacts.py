#!/usr/bin/env python3
import argparse
import os
import sqlite3
from datetime import datetime, UTC
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def get_retention_days(policy: str) -> int:
    if policy == "standard_30_days":
        return 30
    if policy == "standard_14_days":
        return 14
    if policy == "standard_7_days":
        return 7
    return 30

def cleanup_artifacts(db_path: Path, artifact_root: Path, apply: bool = False) -> list[str]:
    if not db_path.is_file():
        print(f"Database file not found at '{db_path}'")
        return []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    query = """
        SELECT artifact_id, path, created_at, retention_policy 
        FROM artifacts 
        WHERE important = 0 AND release_or_milestone = 0
    """
    
    try:
        rows = conn.execute(query).fetchall()
    except Exception as exc:
        print(f"Error querying database: {exc}")
        conn.close()
        return []
    
    now = datetime.now(UTC)
    candidates: list[dict] = []
    
    for row in rows:
        created_str = row["created_at"].replace("Z", "+00:00")
        try:
            created_dt = datetime.fromisoformat(created_str)
        except ValueError:
            continue
            
        age_days = (now - created_dt).days
        policy = row["retention_policy"]
        limit_days = get_retention_days(policy)
        
        if age_days >= limit_days:
            candidates.append({
                "artifact_id": row["artifact_id"],
                "path": row["path"],
                "created_at": row["created_at"],
                "age_days": age_days,
                "limit_days": limit_days
            })
            
    conn.close()
    
    cleaned_ids: list[str] = []
    
    if not candidates:
        print("No expired artifacts found for cleanup.")
        return []
        
    print(f"Found {len(candidates)} artifact candidate(s) for cleanup.")
    print("-" * 60)
    for c in candidates:
        rel_path = c["path"]
        abs_path = artifact_root / rel_path
        exists_str = "[File Exists]" if abs_path.is_file() else "[File Missing]"
        print(f"ID: {c['artifact_id']} | Age: {c['age_days']} days (Limit: {c['limit_days']}) | {exists_str}")
        print(f"  Path: {abs_path}")
        
        if apply:
            if abs_path.is_file():
                try:
                    abs_path.unlink()
                    print(f"  -> DELETED disk file.")
                except Exception as exc:
                    print(f"  -> ERROR deleting file: {exc}")
            else:
                print(f"  -> Skip (file missing).")
            cleaned_ids.append(c["artifact_id"])
        else:
            print(f"  -> [DRY-RUN] Would delete this file.")
            cleaned_ids.append(c["artifact_id"])
            
    print("-" * 60)
    if not apply:
        print("Note: Running in DRY-RUN mode. No files were deleted. Use --apply to delete files.")
        
    return cleaned_ids

def main():
    parser = argparse.ArgumentParser(description="Purge expired and non-important artifacts from local disk.")
    parser.add_argument("--db-path", default=os.getenv("GAME_COMPANY_DB_PATH", "data/game_company.sqlite3"))
    parser.add_argument("--artifact-root", default=os.getenv("GAME_COMPANY_ARTIFACT_ROOT", "artifacts"))
    parser.add_argument("--apply", action="store_true", help="Actually execute file deletion on disk.")
    args = parser.parse_args()
    
    db_path = Path(args.db_path)
    artifact_root = Path(args.artifact_root)
    
    cleanup_artifacts(db_path, artifact_root, apply=args.apply)

if __name__ == "__main__":
    main()
