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
    completed_at TEXT,
    base_commit TEXT,
    write_scope_json TEXT,
    read_scope_json TEXT,
    forbidden_scope_json TEXT
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
    created_at TEXT NOT NULL,
    head_commit TEXT
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

CREATE TABLE IF NOT EXISTS approval_requests (
    approval_id TEXT PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
    target_type TEXT NOT NULL,
    target_id TEXT,
    requested_by TEXT NOT NULL DEFAULT '',
    approved_by TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    request_summary TEXT NOT NULL,
    risk_summary TEXT NOT NULL DEFAULT '',
    approval_message TEXT NOT NULL DEFAULT '',
    discord_message_id TEXT,
    discord_thread_id TEXT,
    decision_memory_key TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    decided_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_approval_requests_status ON approval_requests(status);
CREATE INDEX IF NOT EXISTS idx_approval_requests_project ON approval_requests(project_id);
CREATE INDEX IF NOT EXISTS idx_approval_requests_target ON approval_requests(target_type, target_id);

CREATE TABLE IF NOT EXISTS discord_mappings (
    mapping_id TEXT PRIMARY KEY,
    discord_guild_id TEXT NOT NULL,
    discord_channel_id TEXT NOT NULL,
    discord_thread_id TEXT NOT NULL DEFAULT '',
    project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
    conversation_kind TEXT NOT NULL,
    thread_role TEXT NOT NULL,
    created_by TEXT NOT NULL DEFAULT '',
    summary_memory_key TEXT,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    archived_at TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_discord_mappings_location
ON discord_mappings(
    discord_guild_id,
    discord_channel_id,
    discord_thread_id,
    conversation_kind,
    thread_role
);
CREATE INDEX IF NOT EXISTS idx_discord_mappings_project ON discord_mappings(project_id);

CREATE TABLE IF NOT EXISTS task_locks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    worker_id TEXT,
    node_id TEXT,
    lock_type TEXT NOT NULL,
    resource_key TEXT NOT NULL,
    mode TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    released_at TEXT,
    expires_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_task_locks_project_status ON task_locks(project_id, status);
CREATE INDEX IF NOT EXISTS idx_task_locks_task ON task_locks(task_id);
CREATE INDEX IF NOT EXISTS idx_discord_mappings_kind_role ON discord_mappings(conversation_kind, thread_role);

CREATE TABLE IF NOT EXISTS merge_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    task_id INTEGER NOT NULL UNIQUE REFERENCES tasks(id) ON DELETE CASCADE,
    branch_name TEXT,
    base_commit TEXT,
    head_commit TEXT,
    status TEXT NOT NULL DEFAULT 'queued',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    merged_at TEXT,
    rejected_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_merge_candidates_project_status ON merge_candidates(project_id, status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_merge_candidates_task ON merge_candidates(task_id);

CREATE TABLE IF NOT EXISTS task_thread_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL UNIQUE,
    provider TEXT NOT NULL,
    channel_id TEXT,
    thread_id TEXT,
    thread_url TEXT,
    title TEXT,
    summary TEXT,
    created_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_message_at TEXT,
    metadata_json TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_task_thread_references_task ON task_thread_references(task_id);
"""

PROJECT_COLUMNS = {
    "engine": "TEXT NOT NULL DEFAULT ''",
    "repo_url": "TEXT NOT NULL DEFAULT ''",
    "workspace_path": "TEXT NOT NULL DEFAULT ''",
    "base_branch": "TEXT NOT NULL DEFAULT 'main'",
}

TASK_COLUMNS = {
    "base_commit": "TEXT",
    "write_scope_json": "TEXT",
    "read_scope_json": "TEXT",
    "forbidden_scope_json": "TEXT",
}

WORKER_REPORT_COLUMNS = {
    "head_commit": "TEXT",
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
    task_columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(tasks)").fetchall()
    }
    for name, definition in TASK_COLUMNS.items():
        if name not in task_columns:
            conn.execute(f"ALTER TABLE tasks ADD COLUMN {name} {definition}")
    worker_report_columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(worker_reports)").fetchall()
    }
    for name, definition in WORKER_REPORT_COLUMNS.items():
        if name not in worker_report_columns:
            conn.execute(f"ALTER TABLE worker_reports ADD COLUMN {name} {definition}")
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
