from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any

from app.db import transaction
from app.schemas import (
    EpicCreate,
    MemoryCreate,
    OwnerRunCreate,
    ProjectConfigUpdate,
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
            INSERT INTO projects (
                name, description, engine, repo_url, workspace_path,
                base_branch, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.name,
                payload.description,
                payload.engine,
                payload.repo_url,
                payload.workspace_path,
                payload.base_branch,
                timestamp,
                timestamp,
            ),
        )
        self.conn.commit()
        return self.get_project(cur.lastrowid)

    def get_project(self, project_id: int) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if row is None:
            raise KeyError("project not found")
        return row_to_dict(row) or {}

    def list_projects(self) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM projects ORDER BY id ASC").fetchall()
        return [row_to_dict(row) or {} for row in rows]

    def get_project_tree(self, project_id: int) -> dict[str, Any]:
        project = self.get_project(project_id)
        epics = [
            row_to_dict(row) or {}
            for row in self.conn.execute(
                "SELECT * FROM epics WHERE project_id = ? ORDER BY id ASC",
                (project_id,),
            ).fetchall()
        ]
        epic_ids = [epic["id"] for epic in epics]
        if not epic_ids:
            return {**project, "epics": []}

        placeholders = ",".join("?" for _ in epic_ids)
        sub_epics = [
            row_to_dict(row) or {}
            for row in self.conn.execute(
                f"SELECT * FROM sub_epics WHERE epic_id IN ({placeholders}) ORDER BY id ASC",
                epic_ids,
            ).fetchall()
        ]
        sub_epic_ids = [sub_epic["id"] for sub_epic in sub_epics]
        tasks_by_sub_epic: dict[int, list[dict[str, Any]]] = {sub_epic["id"]: [] for sub_epic in sub_epics}
        if sub_epic_ids:
            task_placeholders = ",".join("?" for _ in sub_epic_ids)
            for row in self.conn.execute(
                f"SELECT * FROM tasks WHERE sub_epic_id IN ({task_placeholders}) ORDER BY id ASC",
                sub_epic_ids,
            ).fetchall():
                task = row_to_dict(row) or {}
                tasks_by_sub_epic[task["sub_epic_id"]].append(task)

        sub_epics_by_epic: dict[int, list[dict[str, Any]]] = {epic["id"]: [] for epic in epics}
        for sub_epic in sub_epics:
            sub_epics_by_epic[sub_epic["epic_id"]].append(
                {**sub_epic, "tasks": tasks_by_sub_epic[sub_epic["id"]]}
            )
        return {
            **project,
            "epics": [
                {**epic, "sub_epics": sub_epics_by_epic[epic["id"]]}
                for epic in epics
            ],
        }

    def update_project_config(self, project_id: int, payload: ProjectConfigUpdate) -> dict[str, Any]:
        self.get_project(project_id)
        timestamp = now_iso()
        self.conn.execute(
            """
            UPDATE projects
            SET engine = ?,
                repo_url = ?,
                workspace_path = ?,
                base_branch = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                payload.engine,
                payload.repo_url,
                payload.workspace_path,
                payload.base_branch,
                timestamp,
                project_id,
            ),
        )
        self.conn.commit()
        return self.get_project(project_id)

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
        project = self._project_for_task(task_id)
        memories = []
        for key in task["memory_refs"]:
            memory = self.conn.execute("SELECT * FROM memories WHERE key = ?", (key,)).fetchone()
            if memory is not None:
                memories.append(row_to_dict(memory) or {})
        return {
            "task": task,
            "project": project,
            "memories": memories,
        }

    def list_task_reports(self, task_id: int) -> list[dict[str, Any]]:
        self.get_task(task_id)
        rows = self.conn.execute(
            "SELECT * FROM worker_reports WHERE task_id = ? ORDER BY id DESC",
            (task_id,),
        ).fetchall()
        return [row_to_dict(row) or {} for row in rows]

    def list_task_events(self, task_id: int) -> list[dict[str, Any]]:
        self.get_task(task_id)
        rows = self.conn.execute(
            "SELECT * FROM task_events WHERE task_id = ? ORDER BY id ASC",
            (task_id,),
        ).fetchall()
        return [row_to_dict(row) or {} for row in rows]

    def add_task_event(self, task_id: int, event_type: str, message: str) -> None:
        self.get_task(task_id)
        self._add_task_event(task_id, event_type, message)
        self.conn.commit()

    def retry_task(self, task_id: int, reason: str = "") -> dict[str, Any]:
        task = self.get_task(task_id)
        if task["status"] == "success":
            raise ValueError("successful task cannot be retried")
        if task["status"] == "pending":
            raise ValueError("pending task is already queued")
        timestamp = now_iso()
        with transaction(self.conn):
            self.conn.execute(
                """
                UPDATE tasks
                SET status = 'pending',
                    retry_count = retry_count + 1,
                    leased_by = NULL,
                    leased_until = NULL,
                    completed_at = NULL,
                    updated_at = ?
                WHERE id = ?
                """,
                (timestamp, task_id),
            )
            message = "Owner requested retry"
            if reason:
                message += f": {reason}"
            self._add_task_event(task_id, "retry_requested", message)
        return self.get_task(task_id)

    def cancel_task(self, task_id: int, reason: str = "") -> dict[str, Any]:
        task = self.get_task(task_id)
        if task["status"] == "success":
            raise ValueError("successful task cannot be canceled")
        if any(event["event_type"] == "merged" for event in self.list_task_events(task_id)):
            raise ValueError("merged task cannot be canceled")
        timestamp = now_iso()
        with transaction(self.conn):
            self.conn.execute(
                """
                UPDATE tasks
                SET status = 'canceled',
                    leased_by = NULL,
                    leased_until = NULL,
                    completed_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (timestamp, timestamp, task_id),
            )
            message = "Owner canceled task"
            if reason:
                message += f": {reason}"
            self._add_task_event(task_id, "canceled", message)
        return self.get_task(task_id)

    def release_task(self, task_id: int, reason: str = "") -> dict[str, Any]:
        task = self.get_task(task_id)
        if task["status"] != "running":
            raise ValueError("only running tasks can be released")
        timestamp = now_iso()
        with transaction(self.conn):
            self.conn.execute(
                """
                UPDATE tasks
                SET status = 'pending',
                    leased_by = NULL,
                    leased_until = NULL,
                    updated_at = ?
                WHERE id = ?
                """,
                (timestamp, task_id),
            )
            message = "Owner released task lease"
            if reason:
                message += f": {reason}"
            self._add_task_event(task_id, "released", message)
        return self.get_task(task_id)

    def _project_for_task(self, task_id: int) -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            SELECT projects.*
            FROM tasks
            JOIN sub_epics ON sub_epics.id = tasks.sub_epic_id
            JOIN epics ON epics.id = sub_epics.epic_id
            JOIN projects ON projects.id = epics.project_id
            WHERE tasks.id = ?
            """,
            (task_id,),
        ).fetchone()
        return row_to_dict(row)

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

    def lease_next_task(
        self,
        worker_id: str,
        role: str,
        lease_minutes: int,
        requires_project_config: bool = False,
    ) -> dict[str, Any] | None:
        timestamp = now_iso()
        lease_until = (datetime.now(UTC) + timedelta(minutes=lease_minutes)).isoformat(timespec="seconds")
        project_config_filter = """
                  AND EXISTS (
                    SELECT 1
                    FROM sub_epics
                    JOIN epics ON epics.id = sub_epics.epic_id
                    JOIN projects ON projects.id = epics.project_id
                    WHERE sub_epics.id = tasks.sub_epic_id
                      AND projects.repo_url != ''
                      AND projects.workspace_path != ''
                  )
        """ if requires_project_config else ""
        with transaction(self.conn):
            row = self.conn.execute(
                f"""
                SELECT * FROM tasks
                WHERE role = ?
                  AND (
                    status = 'pending'
                    OR (status = 'running' AND leased_until IS NOT NULL AND leased_until < ?)
                  )
                  {project_config_filter}
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

    def claim_task(self, task_id: int, worker_id: str, lease_minutes: int) -> dict[str, Any]:
        timestamp = now_iso()
        lease_until = (datetime.now(UTC) + timedelta(minutes=lease_minutes)).isoformat(timespec="seconds")
        with transaction(self.conn):
            row = self.conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            if row is None:
                raise KeyError("task not found")
            task = row_to_dict(row) or {}
            if task["status"] == "success":
                raise ValueError("successful task cannot be claimed")
            if task["status"] in {"failed", "blocked"}:
                raise ValueError("failed or blocked task must be retried before claim")
            if (
                task["status"] == "running"
                and task["leased_by"] != worker_id
                and task["leased_until"] is not None
                and task["leased_until"] >= timestamp
            ):
                raise ValueError("task is already leased by another worker")
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
        task = self.get_task(task_id)
        if task["status"] != "running" or task["leased_by"] != worker_id:
            raise ValueError("task must be leased by the reporting worker")
        timestamp = now_iso()
        with transaction(self.conn):
            report_cur = self.conn.execute(
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
            report_id = report_cur.lastrowid
            history_key = f"task_history_{task_id}_{report_id}"
            history_body = "\n".join(
                [
                    f"Task: {task['goal']}",
                    f"Role: {task['role']}",
                    f"Status: {payload.status}",
                    f"Estimated: {payload.estimated_minutes}m",
                    f"Actual: {payload.actual_minutes}m",
                    f"Productive: {payload.productive_minutes}m",
                    f"Error: {payload.error_minutes}m",
                    f"Retry: {payload.retry_count}",
                    f"Files: {', '.join(payload.files_changed) if payload.files_changed else 'none'}",
                    f"Tests: {', '.join(payload.tests) if payload.tests else 'none'}",
                    f"Summary: {payload.summary}",
                    f"Issues: {payload.issues or 'none'}",
                ]
            )
            self.conn.execute(
                """
                INSERT INTO memories (type, key, title, body, tags_json, created_at, updated_at)
                VALUES ('task_history', ?, ?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    title = excluded.title,
                    body = excluded.body,
                    tags_json = excluded.tags_json,
                    updated_at = excluded.updated_at
                """,
                (
                    history_key,
                    f"Task {task_id} report {report_id}: {payload.status}",
                    history_body,
                    json.dumps(["task_history", task["role"], payload.status]),
                    timestamp,
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

    def list_task_history(
        self,
        limit: int = 50,
        status: str | None = None,
        role: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if status:
            clauses.append("worker_reports.status = ?")
            params.append(status)
        if role:
            clauses.append("tasks.role = ?")
            params.append(role)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.conn.execute(
            f"""
            SELECT
                worker_reports.*,
                tasks.goal AS task_goal,
                tasks.role AS task_role,
                tasks.branch AS task_branch,
                projects.id AS project_id,
                projects.name AS project_name
            FROM worker_reports
            JOIN tasks ON tasks.id = worker_reports.task_id
            LEFT JOIN sub_epics ON sub_epics.id = tasks.sub_epic_id
            LEFT JOIN epics ON epics.id = sub_epics.epic_id
            LEFT JOIN projects ON projects.id = epics.project_id
            {where}
            ORDER BY worker_reports.created_at DESC, worker_reports.id DESC
            LIMIT ?
            """,
            [*params, limit],
        ).fetchall()
        return [row_to_dict(row) or {} for row in rows]

    def task_history_summary(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT
                tasks.role AS role,
                worker_reports.status AS status,
                COUNT(*) AS report_count,
                ROUND(AVG(worker_reports.estimated_minutes), 2) AS avg_estimated_minutes,
                ROUND(AVG(worker_reports.actual_minutes), 2) AS avg_actual_minutes,
                ROUND(AVG(worker_reports.actual_minutes - worker_reports.estimated_minutes), 2) AS avg_estimate_delta_minutes,
                ROUND(AVG(worker_reports.retry_count), 2) AS avg_retry_count,
                ROUND(AVG(worker_reports.error_minutes), 2) AS avg_error_minutes
            FROM worker_reports
            JOIN tasks ON tasks.id = worker_reports.task_id
            GROUP BY tasks.role, worker_reports.status
            ORDER BY tasks.role ASC, worker_reports.status ASC
            """
        ).fetchall()
        return [row_to_dict(row) or {} for row in rows]

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

    def create_owner_run(self, payload: OwnerRunCreate, prompt: str, command: str, run_dir: str) -> dict[str, Any]:
        timestamp = now_iso()
        cur = self.conn.execute(
            """
            INSERT INTO owner_runs (status, objective, context, prompt, command, run_dir, created_at)
            VALUES ('pending', ?, ?, ?, ?, ?, ?)
            """,
            (payload.objective, payload.context, prompt, command, run_dir, timestamp),
        )
        self.conn.commit()
        return self.get_owner_run(cur.lastrowid)

    def start_owner_run(self, run_id: int) -> None:
        timestamp = now_iso()
        self.conn.execute(
            "UPDATE owner_runs SET status = 'running', started_at = ?, completed_at = NULL WHERE id = ?",
            (timestamp, run_id),
        )
        self.conn.commit()

    def finish_owner_run(self, run_id: int, status: str, exit_code: int | None, stdout: str, stderr: str) -> dict[str, Any]:
        timestamp = now_iso()
        self.conn.execute(
            """
            UPDATE owner_runs
            SET status = ?, exit_code = ?, stdout = ?, stderr = ?, completed_at = ?
            WHERE id = ?
            """,
            (status, exit_code, stdout, stderr, timestamp, run_id),
        )
        self.conn.commit()
        return self.get_owner_run(run_id)

    def get_owner_run(self, run_id: int) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM owner_runs WHERE id = ?", (run_id,)).fetchone()
        if row is None:
            raise KeyError("owner run not found")
        return row_to_dict(row) or {}

    def list_owner_runs(self) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM owner_runs ORDER BY id DESC").fetchall()
        return [row_to_dict(row) or {} for row in rows]

    def _add_task_event(self, task_id: int, event_type: str, message: str) -> None:
        self.conn.execute(
            "INSERT INTO task_events (task_id, event_type, message, created_at) VALUES (?, ?, ?, ?)",
            (task_id, event_type, message, now_iso()),
        )
