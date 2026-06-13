from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any

from app.db import transaction
from app.schemas import (
    EpicCreate,
    MemoryCreate,
    ProjectCreate,
    SubEpicCreate,
    TaskCreate,
    WorkerReportCreate,
)


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    for key in (
        "tags_json",
        "requirements_json",
        "success_criteria_json",
        "memory_refs_json",
        "files_changed_json",
        "tests_json",
    ):
        if key in item:
            item[key.removesuffix("_json")] = json.loads(item.pop(key))
    return item


class Repository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create_project(self, payload: ProjectCreate) -> dict[str, Any]:
        timestamp = now_iso()
        cur = self.conn.execute(
            """
            INSERT INTO projects (name, description, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (payload.name, payload.description, timestamp, timestamp),
        )
        self.conn.commit()
        return self.get_project(cur.lastrowid)

    def get_project(self, project_id: int) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if row is None:
            raise KeyError("project not found")
        return row_to_dict(row) or {}

    def create_epic(self, project_id: int, payload: EpicCreate) -> dict[str, Any]:
        self.get_project(project_id)
        timestamp = now_iso()
        cur = self.conn.execute(
            """
            INSERT INTO epics (project_id, name, goal, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (project_id, payload.name, payload.goal, timestamp, timestamp),
        )
        self.conn.commit()
        return row_to_dict(self.conn.execute("SELECT * FROM epics WHERE id = ?", (cur.lastrowid,)).fetchone()) or {}

    def create_sub_epic(self, epic_id: int, payload: SubEpicCreate) -> dict[str, Any]:
        if self.conn.execute("SELECT id FROM epics WHERE id = ?", (epic_id,)).fetchone() is None:
            raise KeyError("epic not found")
        timestamp = now_iso()
        cur = self.conn.execute(
            """
            INSERT INTO sub_epics (epic_id, name, goal, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (epic_id, payload.name, payload.goal, timestamp, timestamp),
        )
        self.conn.commit()
        return row_to_dict(self.conn.execute("SELECT * FROM sub_epics WHERE id = ?", (cur.lastrowid,)).fetchone()) or {}

    def upsert_memory(self, payload: MemoryCreate) -> dict[str, Any]:
        timestamp = now_iso()
        self.conn.execute(
            """
            INSERT INTO memories (type, key, title, body, tags_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                type = excluded.type,
                title = excluded.title,
                body = excluded.body,
                tags_json = excluded.tags_json,
                updated_at = excluded.updated_at
            """,
            (
                payload.type,
                payload.key,
                payload.title,
                payload.body,
                json.dumps(payload.tags),
                timestamp,
                timestamp,
            ),
        )
        self.conn.commit()
        return self.get_memory(payload.key)

    def get_memory(self, key: str) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM memories WHERE key = ?", (key,)).fetchone()
        if row is None:
            raise KeyError("memory not found")
        return row_to_dict(row) or {}

    def search_memory(self, memory_type: str | None, tag: str | None, q: str | None) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if memory_type:
            clauses.append("type = ?")
            params.append(memory_type)
        if tag:
            clauses.append("tags_json LIKE ?")
            params.append(f'%"{tag}"%')
        if q:
            clauses.append("(key LIKE ? OR title LIKE ? OR body LIKE ?)")
            params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.conn.execute(
            f"SELECT * FROM memories {where} ORDER BY updated_at DESC, id DESC",
            params,
        ).fetchall()
        return [row_to_dict(row) or {} for row in rows]

    def create_task(self, sub_epic_id: int | None, payload: TaskCreate) -> dict[str, Any]:
        if sub_epic_id is not None:
            exists = self.conn.execute("SELECT id FROM sub_epics WHERE id = ?", (sub_epic_id,)).fetchone()
            if exists is None:
                raise KeyError("sub epic not found")
        timestamp = now_iso()
        cur = self.conn.execute(
            """
            INSERT INTO tasks (
                sub_epic_id, role, goal, requirements_json, success_criteria_json,
                estimated_minutes, memory_refs_json, branch, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sub_epic_id,
                payload.role,
                payload.goal,
                json.dumps(payload.requirements),
                json.dumps(payload.success_criteria),
                payload.estimated_minutes,
                json.dumps(payload.memory_refs),
                payload.branch,
                timestamp,
                timestamp,
            ),
        )
        self._add_task_event(cur.lastrowid, "created", "Task created")
        self.conn.commit()
        return self.get_task(cur.lastrowid)

    def get_task(self, task_id: int) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            raise KeyError("task not found")
        return row_to_dict(row) or {}

    def get_task_package(self, task_id: int) -> dict[str, Any]:
        task = self.get_task(task_id)
        memories = []
        for key in task["memory_refs"]:
            memory = self.conn.execute("SELECT * FROM memories WHERE key = ?", (key,)).fetchone()
            if memory is not None:
                memories.append(row_to_dict(memory) or {})
        return {
            "task": task,
            "memories": memories,
        }

    def list_tasks(self, status: str | None = None, role: str | None = None) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if role:
            clauses.append("role = ?")
            params.append(role)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.conn.execute(f"SELECT * FROM tasks {where} ORDER BY id ASC", params).fetchall()
        return [row_to_dict(row) or {} for row in rows]

    def lease_next_task(self, worker_id: str, role: str, lease_minutes: int) -> dict[str, Any] | None:
        timestamp = now_iso()
        lease_until = (datetime.now(UTC) + timedelta(minutes=lease_minutes)).isoformat(timespec="seconds")
        with transaction(self.conn):
            row = self.conn.execute(
                """
                SELECT * FROM tasks
                WHERE role = ?
                  AND (
                    status = 'pending'
                    OR (status = 'running' AND leased_until IS NOT NULL AND leased_until < ?)
                  )
                ORDER BY id ASC
                LIMIT 1
                """,
                (role, timestamp),
            ).fetchone()
            if row is None:
                return None
            task_id = int(row["id"])
            self.conn.execute(
                """
                UPDATE tasks
                SET status = 'running',
                    leased_by = ?,
                    leased_until = ?,
                    started_at = COALESCE(started_at, ?),
                    updated_at = ?
                WHERE id = ?
                """,
                (worker_id, lease_until, timestamp, timestamp, task_id),
            )
            self._add_task_event(task_id, "leased", f"Leased by {worker_id}")
        return self.get_task(task_id)

    def complete_task(self, task_id: int, worker_id: str, payload: WorkerReportCreate) -> dict[str, Any]:
        self.get_task(task_id)
        timestamp = now_iso()
        with transaction(self.conn):
            self.conn.execute(
                """
                INSERT INTO worker_reports (
                    task_id, worker_id, status, estimated_minutes, actual_minutes,
                    productive_minutes, error_minutes, retry_count, files_changed_json,
                    tests_json, summary, issues, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    worker_id,
                    payload.status,
                    payload.estimated_minutes,
                    payload.actual_minutes,
                    payload.productive_minutes,
                    payload.error_minutes,
                    payload.retry_count,
                    json.dumps(payload.files_changed),
                    json.dumps(payload.tests),
                    payload.summary,
                    payload.issues,
                    timestamp,
                ),
            )
            self.conn.execute(
                """
                UPDATE tasks
                SET status = ?,
                    retry_count = ?,
                    leased_by = NULL,
                    leased_until = NULL,
                    completed_at = CASE WHEN ? IN ('success', 'blocked') THEN ? ELSE completed_at END,
                    updated_at = ?
                WHERE id = ?
                """,
                (payload.status, payload.retry_count, payload.status, timestamp, timestamp, task_id),
            )
            self._add_task_event(task_id, "reported", f"{worker_id} reported {payload.status}")
        return self.get_task(task_id)

    def dashboard(self, owner_recall_minutes: int) -> dict[str, Any]:
        counts = {
            row["status"]: row["count"]
            for row in self.conn.execute("SELECT status, COUNT(*) AS count FROM tasks GROUP BY status").fetchall()
        }
        last_success = self.conn.execute(
            "SELECT updated_at FROM tasks WHERE status = 'success' ORDER BY updated_at DESC LIMIT 1"
        ).fetchone()
        latest_failure = self.conn.execute(
            "SELECT id, updated_at, goal FROM tasks WHERE status = 'failed' ORDER BY updated_at DESC LIMIT 1"
        ).fetchone()
        needs_owner_attention = False
        if last_success is not None and latest_failure is not None:
            success_at = datetime.fromisoformat(last_success["updated_at"])
            failure_at = datetime.fromisoformat(latest_failure["updated_at"])
            needs_owner_attention = failure_at >= success_at + timedelta(minutes=owner_recall_minutes)
        return {
            "task_counts": counts,
            "pending": self.list_tasks(status="pending"),
            "running": self.list_tasks(status="running"),
            "latest_failure": row_to_dict(latest_failure),
            "needs_owner_attention": needs_owner_attention,
            "owner_recall_rule": f"last success + {owner_recall_minutes}m + failure",
        }

    def _add_task_event(self, task_id: int, event_type: str, message: str) -> None:
        self.conn.execute(
            "INSERT INTO task_events (task_id, event_type, message, created_at) VALUES (?, ?, ?, ?)",
            (task_id, event_type, message, now_iso()),
        )
