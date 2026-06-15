from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    engine TEXT NOT NULL DEFAULT '',
    repo_url TEXT NOT NULL DEFAULT '',
    workspace_path TEXT NOT NULL DEFAULT '',
    base_branch TEXT NOT NULL DEFAULT 'main',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS epics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    goal TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sub_epics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    epic_id INTEGER NOT NULL REFERENCES epics(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    goal TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    key TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    tags_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type);
CREATE INDEX IF NOT EXISTS idx_memories_key ON memories(key);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sub_epic_id INTEGER REFERENCES sub_epics(id) ON DELETE SET NULL,
    role TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    goal TEXT NOT NULL,
    requirements_json TEXT NOT NULL,
    success_criteria_json TEXT NOT NULL,
    estimated_minutes INTEGER NOT NULL,
    memory_refs_json TEXT NOT NULL,
    branch TEXT NOT NULL,
    retry_count INTEGER NOT NULL DEFAULT 0,
    leased_by TEXT,
    leased_until TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_tasks_status_role ON tasks(status, role);
CREATE INDEX IF NOT EXISTS idx_tasks_sub_epic ON tasks(sub_epic_id);

CREATE TABLE IF NOT EXISTS worker_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    worker_id TEXT NOT NULL,
    status TEXT NOT NULL,
    estimated_minutes INTEGER NOT NULL,
    actual_minutes INTEGER NOT NULL,
    productive_minutes INTEGER NOT NULL,
    error_minutes INTEGER NOT NULL,
    retry_count INTEGER NOT NULL,
    files_changed_json TEXT NOT NULL,
    tests_json TEXT NOT NULL,
    summary TEXT NOT NULL,
    issues TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS task_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS owner_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT NOT NULL,
    objective TEXT NOT NULL,
    context TEXT NOT NULL,
    prompt TEXT NOT NULL,
    command TEXT NOT NULL,
    run_dir TEXT NOT NULL,
    exit_code INTEGER,
    stdout TEXT NOT NULL DEFAULT '',
    stderr TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_owner_runs_status ON owner_runs(status);

CREATE TABLE IF NOT EXISTS model_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL UNIQUE,
    provider TEXT NOT NULL DEFAULT '',
    model TEXT NOT NULL DEFAULT '',
    base_url TEXT NOT NULL DEFAULT '',
    api_key_env TEXT NOT NULL DEFAULT '',
    temperature REAL NOT NULL DEFAULT 0.2,
    max_tokens INTEGER,
    enabled INTEGER NOT NULL DEFAULT 1,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS machines (
    machine_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL DEFAULT '',
    kind TEXT NOT NULL DEFAULT '',
    host_hint TEXT NOT NULL DEFAULT '',
    os TEXT NOT NULL DEFAULT '',
    workspace_root TEXT NOT NULL DEFAULT '',
    artifact_root TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'offline',
    capabilities_json TEXT NOT NULL DEFAULT '[]',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_seen_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_machines_kind_status ON machines(kind, status);

CREATE TABLE IF NOT EXISTS workers (
    worker_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL DEFAULT '',
    role TEXT NOT NULL DEFAULT '',
    machine_id TEXT REFERENCES machines(machine_id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'offline',
    capabilities_json TEXT NOT NULL DEFAULT '[]',
    assigned_projects_json TEXT NOT NULL DEFAULT '[]',
    workspace_root TEXT NOT NULL DEFAULT '',
    trust_level TEXT NOT NULL DEFAULT 'limited',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_seen_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_workers_role_status ON workers(role, status);
CREATE INDEX IF NOT EXISTS idx_workers_machine_id ON workers(machine_id);

CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id TEXT PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
    worker_id TEXT,
    machine_id TEXT REFERENCES machines(machine_id) ON DELETE SET NULL,
    artifact_type TEXT NOT NULL,
    filename TEXT NOT NULL DEFAULT '',
    path TEXT NOT NULL DEFAULT '',
    content_type TEXT NOT NULL DEFAULT '',
    thumbnail_path TEXT NOT NULL DEFAULT '',
    summary TEXT NOT NULL DEFAULT '',
    tags_json TEXT NOT NULL DEFAULT '[]',
    retention_policy TEXT NOT NULL DEFAULT 'standard_30_days',
    important INTEGER NOT NULL DEFAULT 0,
    release_or_milestone INTEGER NOT NULL DEFAULT 0,
    size_bytes INTEGER,
    discord_message_id TEXT,
    discord_thread_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_artifacts_project_task ON artifacts(project_id, task_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_type ON artifacts(artifact_type);
"""

PROJECT_COLUMNS = {
    "engine": "TEXT NOT NULL DEFAULT ''",
    "repo_url": "TEXT NOT NULL DEFAULT ''",
    "workspace_path": "TEXT NOT NULL DEFAULT ''",
    "base_branch": "TEXT NOT NULL DEFAULT 'main'",
}


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: Path) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
        migrate_db(conn)


def migrate_db(conn: sqlite3.Connection) -> None:
    project_columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(projects)").fetchall()
    }
    for name, definition in PROJECT_COLUMNS.items():
        if name not in project_columns:
            conn.execute(f"ALTER TABLE projects ADD COLUMN {name} {definition}")
    conn.commit()


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
