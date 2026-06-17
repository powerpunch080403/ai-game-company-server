from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, UTC
from pathlib import Path
import pytest
from app.db import SCHEMA
from scripts.cleanup_artifacts import cleanup_artifacts

@pytest.fixture()
def temp_db(tmp_path: Path) -> Path:
    db_file = tmp_path / "test_cleanup.db"
    conn = sqlite3.connect(db_file)
    conn.executescript(SCHEMA)
    
    # Insert test artifacts
    now = datetime.now(UTC)
    expired_35_days = (now - timedelta(days=35)).isoformat().replace("+00:00", "Z")
    fresh_5_days = (now - timedelta(days=5)).isoformat().replace("+00:00", "Z")
    
    # Insert parent project to satisfy foreign key constraints
    conn.execute(
        """
        INSERT INTO projects (id, name, description, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (1, "Test Project", "Description", now.isoformat(), now.isoformat())
    )
    
    # 1. Expired and non-important (Candidate)
    conn.execute(
        """
        INSERT INTO artifacts (artifact_id, project_id, artifact_type, filename, path, retention_policy, important, release_or_milestone, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("art-expired-candidate", 1, "log", "expired.log", "expired.log", "standard_30_days", 0, 0, expired_35_days, expired_35_days)
    )
    # 2. Expired but important (Should be skipped)
    conn.execute(
        """
        INSERT INTO artifacts (artifact_id, project_id, artifact_type, filename, path, retention_policy, important, release_or_milestone, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("art-expired-important", 1, "log", "important.log", "important.log", "standard_30_days", 1, 0, expired_35_days, expired_35_days)
    )
    # 3. Expired but release/milestone (Should be skipped)
    conn.execute(
        """
        INSERT INTO artifacts (artifact_id, project_id, artifact_type, filename, path, retention_policy, important, release_or_milestone, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("art-expired-release", 1, "build", "release.zip", "release.zip", "standard_30_days", 0, 1, expired_35_days, expired_35_days)
    )
    # 4. Fresh non-important (Should be skipped)
    conn.execute(
        """
        INSERT INTO artifacts (artifact_id, project_id, artifact_type, filename, path, retention_policy, important, release_or_milestone, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("art-fresh", 1, "log", "fresh.log", "fresh.log", "standard_30_days", 0, 0, fresh_5_days, fresh_5_days)
    )
    
    conn.commit()
    conn.close()
    return db_file

def test_cleanup_artifacts_dry_run(temp_db: Path, tmp_path: Path) -> None:
    # Setup dummy files on disk
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)
    
    candidate_file = artifact_root / "expired.log"
    important_file = artifact_root / "important.log"
    
    candidate_file.write_text("expired dummy")
    important_file.write_text("important dummy")
    
    # Run in dry-run mode
    candidates = cleanup_artifacts(temp_db, artifact_root, apply=False)
    
    # Assert candidate matches only the expired non-important artifact
    assert "art-expired-candidate" in candidates
    assert "art-expired-important" not in candidates
    assert "art-expired-release" not in candidates
    assert "art-fresh" not in candidates
    
    # Check that file on disk is NOT unlinked
    assert candidate_file.is_file() is True
    assert important_file.is_file() is True

def test_cleanup_artifacts_apply(temp_db: Path, tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)
    
    candidate_file = artifact_root / "expired.log"
    important_file = artifact_root / "important.log"
    
    candidate_file.write_text("expired dummy")
    important_file.write_text("important dummy")
    
    # Run in apply mode
    candidates = cleanup_artifacts(temp_db, artifact_root, apply=True)
    
    assert "art-expired-candidate" in candidates
    
    # Candidate file should be unlinked (deleted)
    assert candidate_file.is_file() is False
    # Important file should remain
    assert important_file.is_file() is True
    
    # Verify DB metadata is NOT deleted
    conn = sqlite3.connect(temp_db)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM artifacts WHERE artifact_id = ?", ("art-expired-candidate",)).fetchone()
    assert row is not None
    assert row["artifact_id"] == "art-expired-candidate"
    conn.close()
