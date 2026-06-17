from __future__ import annotations

import fnmatch
import json
import sqlite3
import subprocess
import uuid
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any

from app.db import transaction
from app.schemas import (
    ApprovalCreate,
    ApprovalDecision,
    ArtifactCreate,
    DiscordMappingArchive,
    DiscordMappingUpsert,
    DiscordThreadCompactRequest,
    EpicCreate,
    MachineHeartbeat,
    MachineUpsert,
    MemoryCreate,
    ModelProfileUpsert,
    OwnerRunCreate,
    ProjectConfigUpdate,
    ProjectCreate,
    SubEpicCreate,
    TaskCreate,
    WorkerHeartbeat,
    WorkerUpsert,
    WorkerReportCreate,
)


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def stable_discord_mapping_id(payload: DiscordMappingUpsert) -> str:
    thread_id = payload.discord_thread_id or "channel"
    raw = "|".join(
        [
            payload.discord_guild_id,
            payload.discord_channel_id,
            thread_id,
            payload.conversation_kind,
            payload.thread_role,
        ]
    )
    return f"discord_{sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def compact_timestamp_slug(value: str) -> str:
    return value.replace(":", "").replace("+", "Z")


def unique_items(values: list[str]) -> list[str]:
    seen: set[str] = set()
    items: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            items.append(value)
    return items


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
        "capabilities_json",
        "assigned_projects_json",
    ):
        if key in item:
            item[key.removesuffix("_json")] = json.loads(item.pop(key))
    for key in (
        "write_scope_json",
        "read_scope_json",
        "forbidden_scope_json",
    ):
        if key in item:
            val = item.pop(key)
            item[key.removesuffix("_json")] = json.loads(val) if val is not None else None
    if "enabled" in item:
        item["enabled"] = bool(item["enabled"])
    for key in ("important", "release_or_milestone"):
        if key in item:
            item[key] = bool(item[key])
    return item


def get_current_base_commit(repo_path: str, default_branch: str = "main") -> str | None:
    """Return the current HEAD commit of `default_branch` in `repo_path`.

    Returns None if the path is missing, not a git repo, or git fails.
    Never raises — failures are silently swallowed to preserve normal task flow.
    """
    try:
        from pathlib import Path as _Path
        if not repo_path or not _Path(repo_path).exists():
            return None
        result = subprocess.run(
            ["git", "rev-parse", default_branch],
            capture_output=True,
            text=True,
            cwd=repo_path,
            timeout=5,
        )
        if result.returncode == 0:
            commit = result.stdout.strip()
            return commit if commit else None
        return None
    except Exception:
        return None


def validate_changed_files_scope(
    changed_files: list[str],
    write_scope: list[str] | None,
    forbidden_scope: list[str] | None,
) -> tuple[bool, list[str]]:
    if not changed_files:
        return True, []

    norm_files = [f.replace("\\", "/") for f in changed_files]
    norm_write = [w.replace("\\", "/") for w in write_scope] if write_scope is not None else None
    norm_forbidden = [f.replace("\\", "/") for f in forbidden_scope] if forbidden_scope is not None else None

    # 1. Check forbidden scope
    if norm_forbidden:
        violated_forbidden = []
        for f in norm_files:
            for pat in norm_forbidden:
                if fnmatch.fnmatch(f, pat):
                    violated_forbidden.append(f)
                    break
        if violated_forbidden:
            return False, violated_forbidden

    # 2. Check write scope
    if norm_write:
        violated_write = []
        for f in norm_files:
            matched = False
            for pat in norm_write:
                if fnmatch.fnmatch(f, pat):
                    matched = True
                    break
            if not matched:
                violated_write.append(f)
        if violated_write:
            return False, violated_write

    return True, []


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

    def upsert_model_profile(self, payload: ModelProfileUpsert) -> dict[str, Any]:
        timestamp = now_iso()
        self.conn.execute(
            """
            INSERT INTO model_profiles (
                role, provider, model, base_url, api_key_env, temperature,
                max_tokens, enabled, notes, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(role) DO UPDATE SET
                provider = excluded.provider,
                model = excluded.model,
                base_url = excluded.base_url,
                api_key_env = excluded.api_key_env,
                temperature = excluded.temperature,
                max_tokens = excluded.max_tokens,
                enabled = excluded.enabled,
                notes = excluded.notes,
                updated_at = excluded.updated_at
            """,
            (
                payload.role,
                payload.provider,
                payload.model,
                payload.base_url,
                payload.api_key_env,
                payload.temperature,
                payload.max_tokens,
                1 if payload.enabled else 0,
                payload.notes,
                timestamp,
                timestamp,
            ),
        )
        self.conn.commit()
        return self.get_model_profile(payload.role)

    def get_model_profile(self, role: str) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM model_profiles WHERE role = ?", (role,)).fetchone()
        if row is None:
            raise KeyError("model profile not found")
        return row_to_dict(row) or {}

    def list_model_profiles(self, enabled: bool | None = None) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if enabled is not None:
            clauses.append("enabled = ?")
            params.append(1 if enabled else 0)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.conn.execute(
            f"SELECT * FROM model_profiles {where} ORDER BY role ASC",
            params,
        ).fetchall()
        return [row_to_dict(row) or {} for row in rows]

    def upsert_machine(self, payload: MachineUpsert) -> dict[str, Any]:
        timestamp = now_iso()
        self.conn.execute(
            """
            INSERT INTO machines (
                machine_id, display_name, kind, host_hint, os, workspace_root,
                artifact_root, status, capabilities_json, notes, created_at,
                updated_at, last_seen_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
            ON CONFLICT(machine_id) DO UPDATE SET
                display_name = excluded.display_name,
                kind = excluded.kind,
                host_hint = excluded.host_hint,
                os = excluded.os,
                workspace_root = excluded.workspace_root,
                artifact_root = excluded.artifact_root,
                status = excluded.status,
                capabilities_json = excluded.capabilities_json,
                notes = excluded.notes,
                updated_at = excluded.updated_at
            """,
            (
                payload.machine_id,
                payload.display_name,
                payload.kind,
                payload.host_hint,
                payload.os,
                payload.workspace_root,
                payload.artifact_root,
                payload.status,
                json.dumps(payload.capabilities),
                payload.notes,
                timestamp,
                timestamp,
            ),
        )
        self.conn.commit()
        return self.get_machine(payload.machine_id)

    def get_machine(self, machine_id: str) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM machines WHERE machine_id = ?", (machine_id,)).fetchone()
        if row is None:
            raise KeyError("machine not found")
        return row_to_dict(row) or {}

    def list_machines(self, kind: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if kind:
            clauses.append("kind = ?")
            params.append(kind)
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.conn.execute(
            f"SELECT * FROM machines {where} ORDER BY machine_id ASC",
            params,
        ).fetchall()
        return [row_to_dict(row) or {} for row in rows]

    def heartbeat_machine(self, machine_id: str, payload: MachineHeartbeat) -> dict[str, Any]:
        machine = self.get_machine(machine_id)
        timestamp = now_iso()
        capabilities = payload.capabilities if payload.capabilities is not None else machine["capabilities"]
        notes = payload.notes if payload.notes is not None else machine["notes"]
        self.conn.execute(
            """
            UPDATE machines
            SET status = ?,
                capabilities_json = ?,
                notes = ?,
                updated_at = ?,
                last_seen_at = ?
            WHERE machine_id = ?
            """,
            (
                payload.status,
                json.dumps(capabilities),
                notes,
                timestamp,
                timestamp,
                machine_id,
            ),
        )
        self.conn.commit()
        return self.get_machine(machine_id)

    def upsert_worker(self, payload: WorkerUpsert) -> dict[str, Any]:
        timestamp = now_iso()
        self.conn.execute(
            """
            INSERT INTO workers (
                worker_id, display_name, role, machine_id, status,
                capabilities_json, assigned_projects_json, workspace_root,
                trust_level, notes, created_at, updated_at, last_seen_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
            ON CONFLICT(worker_id) DO UPDATE SET
                display_name = excluded.display_name,
                role = excluded.role,
                machine_id = excluded.machine_id,
                status = excluded.status,
                capabilities_json = excluded.capabilities_json,
                assigned_projects_json = excluded.assigned_projects_json,
                workspace_root = excluded.workspace_root,
                trust_level = excluded.trust_level,
                notes = excluded.notes,
                updated_at = excluded.updated_at
            """,
            (
                payload.worker_id,
                payload.display_name,
                payload.role,
                payload.machine_id,
                payload.status,
                json.dumps(payload.capabilities),
                json.dumps(payload.assigned_projects),
                payload.workspace_root,
                payload.trust_level,
                payload.notes,
                timestamp,
                timestamp,
            ),
        )
        self.conn.commit()
        return self.get_worker(payload.worker_id)

    def get_worker(self, worker_id: str) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM workers WHERE worker_id = ?", (worker_id,)).fetchone()
        if row is None:
            raise KeyError("worker not found")
        return row_to_dict(row) or {}

    def list_workers(
        self,
        role: str | None = None,
        status: str | None = None,
        machine_id: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if role:
            clauses.append("role = ?")
            params.append(role)
        if status:
            clauses.append("status = ?")
            params.append(status)
        if machine_id:
            clauses.append("machine_id = ?")
            params.append(machine_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.conn.execute(
            f"SELECT * FROM workers {where} ORDER BY worker_id ASC",
            params,
        ).fetchall()
        return [row_to_dict(row) or {} for row in rows]

    def heartbeat_worker(self, worker_id: str, payload: WorkerHeartbeat) -> dict[str, Any]:
        worker = self._ensure_worker(worker_id, role=payload.role or "", machine_id=payload.machine_id)
        timestamp = now_iso()
        role = payload.role if payload.role is not None else worker["role"]
        machine_id = payload.machine_id if payload.machine_id is not None else worker["machine_id"]
        capabilities = payload.capabilities if payload.capabilities is not None else worker["capabilities"]
        workspace_root = payload.workspace_root if payload.workspace_root is not None else worker["workspace_root"]
        notes = payload.notes if payload.notes is not None else worker["notes"]
        self.conn.execute(
            """
            UPDATE workers
            SET role = ?,
                machine_id = ?,
                status = ?,
                capabilities_json = ?,
                workspace_root = ?,
                notes = ?,
                updated_at = ?,
                last_seen_at = ?
            WHERE worker_id = ?
            """,
            (
                role,
                machine_id,
                payload.status,
                json.dumps(capabilities),
                workspace_root,
                notes,
                timestamp,
                timestamp,
                worker_id,
            ),
        )
        self.conn.commit()
        return self.get_worker(worker_id)

    def create_artifact(self, payload: ArtifactCreate) -> dict[str, Any]:
        self.get_project(payload.project_id)
        if payload.task_id is not None:
            self.get_task(payload.task_id)
        if payload.machine_id is not None:
            self.get_machine(payload.machine_id)
        artifact_id = payload.artifact_id or str(uuid.uuid4())
        timestamp = now_iso()
        self.conn.execute(
            """
            INSERT INTO artifacts (
                artifact_id, project_id, task_id, worker_id, machine_id,
                artifact_type, filename, path, content_type, thumbnail_path,
                summary, tags_json, retention_policy, important,
                release_or_milestone, size_bytes, discord_message_id,
                discord_thread_id, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, '', ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?)
            """,
            (
                artifact_id,
                payload.project_id,
                payload.task_id,
                payload.worker_id,
                payload.machine_id,
                payload.artifact_type,
                payload.filename,
                payload.content_type,
                payload.thumbnail_path,
                payload.summary,
                json.dumps(payload.tags),
                payload.retention_policy,
                1 if payload.important else 0,
                1 if payload.release_or_milestone else 0,
                payload.discord_message_id,
                payload.discord_thread_id,
                timestamp,
                timestamp,
            ),
        )
        self.conn.commit()
        return self.get_artifact(artifact_id)

    def get_artifact(self, artifact_id: str) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM artifacts WHERE artifact_id = ?", (artifact_id,)).fetchone()
        if row is None:
            raise KeyError("artifact not found")
        return row_to_dict(row) or {}

    def list_artifacts(
        self,
        project_id: int | None = None,
        task_id: int | None = None,
        artifact_type: str | None = None,
        important: bool | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if project_id is not None:
            clauses.append("project_id = ?")
            params.append(project_id)
        if task_id is not None:
            clauses.append("task_id = ?")
            params.append(task_id)
        if artifact_type:
            clauses.append("artifact_type = ?")
            params.append(artifact_type)
        if important is not None:
            clauses.append("important = ?")
            params.append(1 if important else 0)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.conn.execute(
            f"SELECT * FROM artifacts {where} ORDER BY created_at DESC, artifact_id ASC",
            params,
        ).fetchall()
        return [row_to_dict(row) or {} for row in rows]

    def attach_artifact_file(
        self,
        artifact_id: str,
        relative_path: str,
        filename: str,
        content_type: str,
        size_bytes: int,
    ) -> dict[str, Any]:
        self.get_artifact(artifact_id)
        timestamp = now_iso()
        self.conn.execute(
            """
            UPDATE artifacts
            SET path = ?,
                filename = ?,
                content_type = ?,
                size_bytes = ?,
                updated_at = ?
            WHERE artifact_id = ?
            """,
            (relative_path, filename, content_type, size_bytes, timestamp, artifact_id),
        )
        self.conn.commit()
        return self.get_artifact(artifact_id)

    def create_approval(self, payload: ApprovalCreate) -> dict[str, Any]:
        if payload.project_id is not None:
            self.get_project(payload.project_id)
        approval_id = payload.approval_id or str(uuid.uuid4())
        timestamp = now_iso()
        self.conn.execute(
            """
            INSERT INTO approval_requests (
                approval_id, project_id, target_type, target_id, requested_by,
                approved_by, status, request_summary, risk_summary,
                approval_message, discord_message_id, discord_thread_id,
                decision_memory_key, created_at, updated_at, decided_at
            )
            VALUES (?, ?, ?, ?, ?, NULL, 'pending', ?, ?, ?, ?, ?, ?, ?, ?, NULL)
            """,
            (
                approval_id,
                payload.project_id,
                payload.target_type,
                payload.target_id,
                payload.requested_by,
                payload.request_summary,
                payload.risk_summary,
                payload.approval_message,
                payload.discord_message_id,
                payload.discord_thread_id,
                payload.decision_memory_key,
                timestamp,
                timestamp,
            ),
        )
        self.conn.commit()
        return self.get_approval(approval_id)

    def get_approval(self, approval_id: str) -> dict[str, Any]:
        row = self.conn.execute(
            "SELECT * FROM approval_requests WHERE approval_id = ?",
            (approval_id,),
        ).fetchone()
        if row is None:
            raise KeyError("approval request not found")
        return row_to_dict(row) or {}

    def list_approvals(
        self,
        status: str | None = None,
        project_id: int | None = None,
        target_type: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if project_id is not None:
            clauses.append("project_id = ?")
            params.append(project_id)
        if target_type:
            clauses.append("target_type = ?")
            params.append(target_type)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.conn.execute(
            f"SELECT * FROM approval_requests {where} ORDER BY created_at DESC, approval_id ASC",
            params,
        ).fetchall()
        return [row_to_dict(row) or {} for row in rows]

    def decide_approval(self, approval_id: str, payload: ApprovalDecision) -> dict[str, Any]:
        approval = self.get_approval(approval_id)
        if approval["status"] != "pending":
            raise ValueError("only pending approval requests can be decided")
        timestamp = now_iso()
        approved_by = payload.approved_by if payload.approved_by else approval["approved_by"]
        approval_message = payload.approval_message if payload.approval_message else approval["approval_message"]
        decision_memory_key = (
            payload.decision_memory_key
            if payload.decision_memory_key is not None
            else approval["decision_memory_key"]
        )
        self.conn.execute(
            """
            UPDATE approval_requests
            SET status = ?,
                approved_by = ?,
                approval_message = ?,
                decision_memory_key = ?,
                updated_at = ?,
                decided_at = ?
            WHERE approval_id = ?
            """,
            (
                payload.status,
                approved_by,
                approval_message,
                decision_memory_key,
                timestamp,
                timestamp,
                approval_id,
            ),
        )
        self.conn.commit()
        return self.get_approval(approval_id)

    def upsert_discord_mapping(
        self,
        payload: DiscordMappingUpsert,
        mapping_id: str | None = None,
    ) -> dict[str, Any]:
        if payload.project_id is not None:
            self.get_project(payload.project_id)
        resolved_mapping_id = mapping_id or payload.mapping_id or stable_discord_mapping_id(payload)
        timestamp = now_iso()
        try:
            self.conn.execute(
                """
                INSERT INTO discord_mappings (
                    mapping_id, discord_guild_id, discord_channel_id,
                    discord_thread_id, project_id, conversation_kind, thread_role,
                    created_by, summary_memory_key, notes, created_at, updated_at,
                    archived_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                ON CONFLICT(mapping_id) DO UPDATE SET
                    discord_guild_id = excluded.discord_guild_id,
                    discord_channel_id = excluded.discord_channel_id,
                    discord_thread_id = excluded.discord_thread_id,
                    project_id = excluded.project_id,
                    conversation_kind = excluded.conversation_kind,
                    thread_role = excluded.thread_role,
                    created_by = excluded.created_by,
                    summary_memory_key = excluded.summary_memory_key,
                    notes = excluded.notes,
                    updated_at = excluded.updated_at
                """,
                (
                    resolved_mapping_id,
                    payload.discord_guild_id,
                    payload.discord_channel_id,
                    payload.discord_thread_id,
                    payload.project_id,
                    payload.conversation_kind,
                    payload.thread_role,
                    payload.created_by,
                    payload.summary_memory_key,
                    payload.notes,
                    timestamp,
                    timestamp,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("discord mapping location already exists") from exc
        self.conn.commit()
        return self.get_discord_mapping(resolved_mapping_id)

    def get_discord_mapping(self, mapping_id: str) -> dict[str, Any]:
        row = self.conn.execute(
            "SELECT * FROM discord_mappings WHERE mapping_id = ?",
            (mapping_id,),
        ).fetchone()
        if row is None:
            raise KeyError("discord mapping not found")
        return row_to_dict(row) or {}

    def list_discord_mappings(
        self,
        project_id: int | None = None,
        conversation_kind: str | None = None,
        thread_role: str | None = None,
        discord_guild_id: str | None = None,
        discord_channel_id: str | None = None,
        discord_thread_id: str | None = None,
        active: bool | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if project_id is not None:
            clauses.append("project_id = ?")
            params.append(project_id)
        if conversation_kind:
            clauses.append("conversation_kind = ?")
            params.append(conversation_kind)
        if thread_role:
            clauses.append("thread_role = ?")
            params.append(thread_role)
        if discord_guild_id:
            clauses.append("discord_guild_id = ?")
            params.append(discord_guild_id)
        if discord_channel_id:
            clauses.append("discord_channel_id = ?")
            params.append(discord_channel_id)
        if discord_thread_id is not None:
            clauses.append("discord_thread_id = ?")
            params.append(discord_thread_id)
        if active is True:
            clauses.append("archived_at IS NULL")
        elif active is False:
            clauses.append("archived_at IS NOT NULL")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.conn.execute(
            f"SELECT * FROM discord_mappings {where} ORDER BY created_at DESC, mapping_id ASC",
            params,
        ).fetchall()
        return [row_to_dict(row) or {} for row in rows]

    def archive_discord_mapping(self, mapping_id: str, payload: DiscordMappingArchive) -> dict[str, Any]:
        self.get_discord_mapping(mapping_id)
        timestamp = now_iso()
        note_suffix = f"\nArchive reason: {payload.reason}" if payload.reason else ""
        self.conn.execute(
            """
            UPDATE discord_mappings
            SET archived_at = COALESCE(archived_at, ?),
                notes = notes || ?,
                updated_at = ?
            WHERE mapping_id = ?
            """,
            (timestamp, note_suffix, timestamp, mapping_id),
        )
        self.conn.commit()
        return self.get_discord_mapping(mapping_id)

    def compact_discord_thread(self, mapping_id: str, payload: DiscordThreadCompactRequest) -> dict[str, Any]:
        mapping = self.get_discord_mapping(mapping_id)
        timestamp = now_iso()
        thread_id = mapping["discord_thread_id"] or "channel"
        project_tag = f"project:{mapping['project_id']}" if mapping.get("project_id") is not None else "global"
        thread_tag = f"thread:{thread_id}"
        summary_key = (
            mapping.get("summary_memory_key")
            or f"{project_tag}:thread:{thread_id}:summary:current"
        )
        title = payload.title or f"{mapping['thread_role']} summary for {thread_id}"
        tags = unique_items(
            [
                "thread_summary",
                project_tag,
                thread_tag,
                f"conversation:{mapping['conversation_kind']}",
                f"role:{mapping['thread_role']}",
                *payload.tags,
            ]
        )

        archived_memory: dict[str, Any] | None = None
        existing = self.conn.execute("SELECT * FROM memories WHERE key = ?", (summary_key,)).fetchone()
        if existing is not None:
            existing_memory = row_to_dict(existing) or {}
            archive_key = f"{summary_key}:archive:{compact_timestamp_slug(timestamp)}:{uuid.uuid4().hex[:8]}"
            archive_tags = unique_items([*existing_memory.get("tags", []), "summary_archive"])
            self.conn.execute(
                """
                INSERT INTO memories (type, key, title, body, tags_json, created_at, updated_at)
                VALUES ('thread_summary', ?, ?, ?, ?, ?, ?)
                """,
                (
                    archive_key,
                    f"Archived {existing_memory['title']}",
                    existing_memory["body"],
                    json.dumps(archive_tags),
                    timestamp,
                    timestamp,
                ),
            )
            archived_memory = self.get_memory(archive_key)

        self.conn.execute(
            """
            INSERT INTO memories (type, key, title, body, tags_json, created_at, updated_at)
            VALUES ('thread_summary', ?, ?, ?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                type = excluded.type,
                title = excluded.title,
                body = excluded.body,
                tags_json = excluded.tags_json,
                updated_at = excluded.updated_at
            """,
            (
                summary_key,
                title,
                payload.summary,
                json.dumps(tags),
                timestamp,
                timestamp,
            ),
        )
        self.conn.execute(
            """
            UPDATE discord_mappings
            SET summary_memory_key = ?,
                updated_at = ?
            WHERE mapping_id = ?
            """,
            (summary_key, timestamp, mapping_id),
        )

        archived_mapping: dict[str, Any] | None = None
        if payload.archive_mapping:
            archive_reason = payload.archive_reason or "Thread compacted after context summary."
            note_suffix = f"\nArchive reason: {archive_reason}"
            self.conn.execute(
                """
                UPDATE discord_mappings
                SET archived_at = COALESCE(archived_at, ?),
                    notes = notes || ?,
                    updated_at = ?
                WHERE mapping_id = ?
                """,
                (timestamp, note_suffix, timestamp, mapping_id),
            )

        continuation_mapping: dict[str, Any] | None = None
        if payload.continuation_discord_thread_id:
            continuation_thread_id = payload.continuation_discord_thread_id
            continuation_summary_key = f"{project_tag}:thread:{continuation_thread_id}:summary:current"
            continuation_payload = DiscordMappingUpsert(
                discord_guild_id=mapping["discord_guild_id"],
                discord_channel_id=mapping["discord_channel_id"],
                discord_thread_id=continuation_thread_id,
                project_id=mapping.get("project_id"),
                conversation_kind=mapping["conversation_kind"],
                thread_role=mapping["thread_role"],
                created_by=payload.created_by,
                summary_memory_key=continuation_summary_key,
                notes=(
                    payload.continuation_notes
                    or f"Continuation of {mapping_id}. Previous summary memory: {summary_key}."
                ),
            )
            continuation_mapping = self.upsert_discord_mapping(continuation_payload)

        self.conn.commit()
        current_memory = self.get_memory(summary_key)
        current_mapping = self.get_discord_mapping(mapping_id)
        if payload.archive_mapping:
            archived_mapping = current_mapping
        return {
            "mapping": current_mapping,
            "memory": current_memory,
            "archived_memory": archived_memory,
            "archived_mapping": archived_mapping,
            "continuation_mapping": continuation_mapping,
        }

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
                estimated_minutes, memory_refs_json, branch, created_at, updated_at,
                write_scope_json, read_scope_json, forbidden_scope_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                json.dumps(payload.write_scope) if payload.write_scope is not None else None,
                json.dumps(payload.read_scope) if payload.read_scope is not None else None,
                json.dumps(payload.forbidden_scope) if payload.forbidden_scope is not None else None,
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

    def assign_task_to_sub_epic(self, task_id: int, sub_epic_id: int, reason: str = "") -> dict[str, Any]:
        self.get_task(task_id)
        if self.conn.execute("SELECT id FROM sub_epics WHERE id = ?", (sub_epic_id,)).fetchone() is None:
            raise KeyError("sub epic not found")
        timestamp = now_iso()
        with transaction(self.conn):
            self.conn.execute(
                "UPDATE tasks SET sub_epic_id = ?, updated_at = ? WHERE id = ?",
                (sub_epic_id, timestamp, task_id),
            )
            message = f"Owner assigned task to sub epic {sub_epic_id}"
            if reason:
                message += f": {reason}"
            self._add_task_event(task_id, "assigned", message)
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
            original_branch = row["branch"]
            from app.config import load_settings
            cfg = load_settings()
            updated_branch = original_branch
            if cfg.node_id:
                parts = original_branch.split("/")
                last_part = parts[-1]
                prefix = f"{task_id}-"
                if last_part.startswith(prefix):
                    slug = last_part.removeprefix(prefix)
                else:
                    slug = last_part
                updated_branch = f"worker/{cfg.node_id}/{task_id}-{slug}"

            # Record base_commit from project workspace (if available and not already set)
            project = self._project_for_task(task_id)
            new_base_commit = None
            if project:
                workspace_path = project.get("workspace_path") or ""
                default_branch = project.get("base_branch") or "main"
                if workspace_path:
                    new_base_commit = get_current_base_commit(workspace_path, default_branch)

            self.conn.execute(
                """
                UPDATE tasks
                SET status = 'running',
                    leased_by = ?,
                    leased_until = ?,
                    started_at = COALESCE(started_at, ?),
                    updated_at = ?,
                    branch = ?,
                    base_commit = COALESCE(base_commit, ?)
                WHERE id = ?
                """,
                (worker_id, lease_until, timestamp, timestamp, updated_branch, new_base_commit, task_id),
            )
            self._add_task_event(task_id, "leased", f"Leased by {worker_id}")
            self._touch_worker(worker_id, role=role, status="busy")
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
            if task["status"] in {"failed", "blocked", "needs_rebase", "scope_violation"}:
                raise ValueError("failed, blocked, needs_rebase, or scope_violation task must be retried before claim")
            if (
                task["status"] == "running"
                and task["leased_by"] != worker_id
                and task["leased_until"] is not None
                and task["leased_until"] >= timestamp
            ):
                raise ValueError("task is already leased by another worker")
            original_branch = task["branch"]
            from app.config import load_settings
            cfg = load_settings()
            updated_branch = original_branch
            if cfg.node_id:
                parts = original_branch.split("/")
                last_part = parts[-1]
                prefix = f"{task_id}-"
                if last_part.startswith(prefix):
                    slug = last_part.removeprefix(prefix)
                else:
                    slug = last_part
                updated_branch = f"worker/{cfg.node_id}/{task_id}-{slug}"

            # Record base_commit from project workspace (if available and not already set)
            project_for_bc = self._project_for_task(task_id)
            new_base_commit = None
            if project_for_bc:
                workspace_path = project_for_bc.get("workspace_path") or ""
                default_branch = project_for_bc.get("base_branch") or "main"
                if workspace_path:
                    new_base_commit = get_current_base_commit(workspace_path, default_branch)

            self.conn.execute(
                """
                UPDATE tasks
                SET status = 'running',
                    leased_by = ?,
                    leased_until = ?,
                    started_at = COALESCE(started_at, ?),
                    updated_at = ?,
                    branch = ?,
                    base_commit = COALESCE(base_commit, ?)
                WHERE id = ?
                """,
                (worker_id, lease_until, timestamp, timestamp, updated_branch, new_base_commit, task_id),
            )
            self._add_task_event(task_id, "leased", f"Leased by {worker_id}")
            self._touch_worker(worker_id, role=task["role"], status="busy")
        return self.get_task(task_id)

    def complete_task(self, task_id: int, worker_id: str, payload: WorkerReportCreate) -> dict[str, Any]:
        task = self.get_task(task_id)
        if task["status"] != "running" or task["leased_by"] != worker_id:
            raise ValueError("task must be leased by the reporting worker")
        timestamp = now_iso()

        # Stale-base detection: if worker reports success but main has moved, mark needs_rebase
        final_status = payload.status
        stale_msg = ""
        scope_violation_msg = ""
        if payload.status == "success":
            task_base_commit = task.get("base_commit")
            if task_base_commit:
                stale_project = self._project_for_task(task_id)
                if stale_project:
                    ws = stale_project.get("workspace_path") or ""
                    db = stale_project.get("base_branch") or "main"
                    if ws:
                        current_commit = get_current_base_commit(ws, db)
                        if current_commit and current_commit != task_base_commit:
                            final_status = "needs_rebase"
                            stale_msg = (
                                f"base moved from {task_base_commit[:12]} to "
                                f"{current_commit[:12]}; rebase required before merge"
                            )

            if payload.changed_files is not None:
                write_scope = task.get("write_scope")
                forbidden_scope = task.get("forbidden_scope")
                is_valid, violated = validate_changed_files_scope(
                    payload.changed_files, write_scope, forbidden_scope
                )
                if not is_valid:
                    final_status = "scope_violation"
                    scope_violation_msg = f"Scope violation: modified files {violated} outside allowed policy"

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
                    json.dumps(payload.changed_files if payload.changed_files is not None else payload.files_changed),
                    json.dumps(payload.tests),
                    payload.summary,
                    payload.issues,
                    timestamp,
                ),
            )
            report_id = report_cur.lastrowid
            history_key = f"task_history_{task_id}_{report_id}"
            reported_files = payload.changed_files if payload.changed_files is not None else payload.files_changed
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
                    f"Files: {', '.join(reported_files) if reported_files else 'none'}",
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
                    f"Task {task_id} report {report_id}: {final_status}",
                    history_body,
                    json.dumps(["task_history", task["role"], final_status]),
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
                    completed_at = CASE WHEN ? IN ('success', 'blocked', 'needs_rebase', 'scope_violation') THEN ? ELSE completed_at END,
                    updated_at = ?
                WHERE id = ?
                """,
                (final_status, payload.retry_count, final_status, timestamp, timestamp, task_id),
            )
            self._add_task_event(task_id, "reported", f"{worker_id} reported {final_status}")
            if stale_msg and final_status == "needs_rebase":
                self._add_task_event(task_id, "needs_rebase", stale_msg)
            if scope_violation_msg:
                self._add_task_event(task_id, "scope_violation", scope_violation_msg)
            self._touch_worker(worker_id, role=task["role"], status="online")
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

    def _ensure_worker(self, worker_id: str, role: str = "", machine_id: str | None = None) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM workers WHERE worker_id = ?", (worker_id,)).fetchone()
        if row is None:
            timestamp = now_iso()
            self.conn.execute(
                """
                INSERT INTO workers (
                    worker_id, display_name, role, machine_id, status,
                    capabilities_json, assigned_projects_json, workspace_root,
                    trust_level, notes, created_at, updated_at, last_seen_at
                )
                VALUES (?, '', ?, ?, 'offline', '[]', '[]', '', 'limited', '', ?, ?, NULL)
                """,
                (worker_id, role, machine_id, timestamp, timestamp),
            )
            row = self.conn.execute("SELECT * FROM workers WHERE worker_id = ?", (worker_id,)).fetchone()
        return row_to_dict(row) or {}

    def _touch_worker(
        self,
        worker_id: str,
        role: str = "",
        status: str = "online",
        machine_id: str | None = None,
    ) -> None:
        worker = self._ensure_worker(worker_id, role=role, machine_id=machine_id)
        timestamp = now_iso()
        self.conn.execute(
            """
            UPDATE workers
            SET role = CASE WHEN role = '' THEN ? ELSE role END,
                machine_id = COALESCE(machine_id, ?),
                status = ?,
                updated_at = ?,
                last_seen_at = ?
            WHERE worker_id = ?
            """,
            (role or worker["role"], machine_id, status, timestamp, timestamp, worker_id),
        )
