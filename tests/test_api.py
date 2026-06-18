from __future__ import annotations

import sqlite3
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import auth as auth_module
from app.config import Settings
from app.db import SCHEMA
from app.git_workspace import git_executable, prepare_branch, run_git
from app.main import app, get_repo, get_settings
from app.repository import Repository
from app.workspace_worker import commit_changes, push_branch


@pytest.fixture()
def client(tmp_path: Path) -> Iterator[TestClient]:
    db_path = Path(":memory:")
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)

    def repo_override() -> Repository:
        return Repository(conn)

    def settings_override() -> Settings:
        return Settings(
            db_path=db_path,
            host="127.0.0.1",
            port=8080,
            default_task_minutes=15,
            owner_recall_minutes=30,
            api_token="",
            owner_token="",
            worker_token="",
            readonly_token="",
            artifact_token="",
            owner_command="",
            owner_timeout_seconds=900,
            owner_runs_dir=Path("./owner-runs-test"),
            artifact_root=tmp_path / "artifacts",
            max_artifact_upload_bytes=1024,
            context_compact_threshold_tokens=260000,
            context_warning_tokens=220000,
            context_chars_per_token=3.5,
        )

    app.dependency_overrides[get_repo] = repo_override
    app.dependency_overrides[get_settings] = settings_override
    with TestClient(app) as test_client:
        yield test_client
    conn.close()
    app.dependency_overrides.clear()


def test_task_lifecycle(client: TestClient) -> None:
    task_payload = {
        "role": "code_worker",
        "goal": "Implement Boss FSM",
        "requirements": ["State machine", "Three attack states"],
        "success_criteria": ["Compiles", "FSM transitions run"],
        "estimated_minutes": 15,
        "memory_refs": ["boss_system"],
        "branch": "worker/boss-fsm",
    }
    created = client.post("/tasks", json=task_payload)
    assert created.status_code == 200
    assert created.json()["status"] == "pending"

    leased = client.post("/workers/code-1/lease", json={"role": "code_worker", "lease_minutes": 30})
    assert leased.status_code == 200
    leased_task = leased.json()
    assert leased_task["goal"] == "Implement Boss FSM"
    assert leased_task["status"] == "running"

    report = {
        "status": "success",
        "estimated_minutes": 15,
        "actual_minutes": 18,
        "productive_minutes": 16,
        "error_minutes": 2,
        "retry_count": 1,
        "files_changed": ["Assets/Scripts/Boss/BossFsm.cs"],
        "tests": ["Unity compile"],
        "summary": "Boss FSM implemented.",
        "issues": "",
    }
    completed = client.post(f"/workers/code-1/tasks/{leased_task['id']}/report", json=report)
    assert completed.status_code == 200
    assert completed.json()["status"] == "success"

    reports = client.get(f"/tasks/{leased_task['id']}/reports")
    assert reports.status_code == 200
    assert reports.json()[0]["summary"] == "Boss FSM implemented."
    assert reports.json()[0]["files_changed"] == ["Assets/Scripts/Boss/BossFsm.cs"]

    history_memory = client.get("/memory", params={"type": "task_history", "q": "Boss FSM"})
    assert history_memory.status_code == 200
    assert history_memory.json()[0]["type"] == "task_history"

    history = client.get("/owner/task-history")
    assert history.status_code == 200
    assert history.json()[0]["task_goal"] == "Implement Boss FSM"
    assert history.json()[0]["files_changed"] == ["Assets/Scripts/Boss/BossFsm.cs"]

    summary = client.get("/owner/task-history/summary")
    assert summary.status_code == 200
    assert summary.json()[0]["role"] == "code_worker"
    assert summary.json()[0]["status"] == "success"
    assert summary.json()[0]["report_count"] == 1

    events = client.get(f"/tasks/{leased_task['id']}/events")
    assert events.status_code == 200
    assert [event["event_type"] for event in events.json()] == ["created", "leased", "reported"]


def test_report_requires_worker_lease(client: TestClient) -> None:
    task = client.post(
        "/tasks",
        json={
            "role": "code_worker",
            "goal": "Reject unleased report",
            "requirements": ["Report without lease"],
            "success_criteria": ["Rejected"],
            "estimated_minutes": 15,
            "memory_refs": [],
            "branch": "worker/reject-unleased-report",
        },
    ).json()
    report = {
        "status": "success",
        "estimated_minutes": 15,
        "actual_minutes": 1,
        "productive_minutes": 1,
        "error_minutes": 0,
        "retry_count": 0,
        "files_changed": [],
        "tests": [],
        "summary": "Should not be accepted.",
        "issues": "",
    }
    rejected = client.post(f"/workers/code-1/tasks/{task['id']}/report", json=report)
    assert rejected.status_code == 409

    claimed = client.post(f"/workers/code-1/tasks/{task['id']}/claim", json={"lease_minutes": 30})
    assert claimed.status_code == 200
    accepted = client.post(f"/workers/code-1/tasks/{task['id']}/report", json=report)
    assert accepted.status_code == 200


def test_memory_search_by_tag(client: TestClient) -> None:
    payload = {
        "type": "project_rules",
        "key": "project_rules_v1",
        "title": "Rules",
        "body": "Task size <= 15 minutes",
        "tags": ["rules", "tasks"],
    }
    assert client.post("/memory", json=payload).status_code == 200
    result = client.get("/memory", params={"tag": "rules"})
    assert result.status_code == 200
    assert result.json()[0]["key"] == "project_rules_v1"


def test_owner_retry_failed_task_requeues_it(client: TestClient) -> None:
    task_payload = {
        "role": "code_worker",
        "goal": "Fix compile error",
        "requirements": ["Inspect logs"],
        "success_criteria": ["Compile succeeds"],
        "estimated_minutes": 15,
        "memory_refs": [],
        "branch": "worker/fix-compile-error",
    }
    created = client.post("/tasks", json=task_payload).json()
    leased = client.post("/workers/code-1/lease", json={"role": "code_worker", "lease_minutes": 30}).json()
    assert leased["id"] == created["id"]
    failed_report = {
        "status": "failed",
        "estimated_minutes": 15,
        "actual_minutes": 10,
        "productive_minutes": 6,
        "error_minutes": 4,
        "retry_count": 0,
        "files_changed": [],
        "tests": ["compile"],
        "summary": "Compile still fails.",
        "issues": "Missing symbol.",
    }
    failed = client.post(f"/workers/code-1/tasks/{created['id']}/report", json=failed_report)
    assert failed.status_code == 200
    assert failed.json()["status"] == "failed"

    retried = client.post(f"/owner/tasks/{created['id']}/retry", json={"reason": "Try a smaller fix."})
    assert retried.status_code == 200
    assert retried.json()["status"] == "pending"
    assert retried.json()["retry_count"] == 1

    leased_again = client.post("/workers/code-2/lease", json={"role": "code_worker", "lease_minutes": 30})
    assert leased_again.status_code == 200
    assert leased_again.json()["id"] == created["id"]
    assert leased_again.json()["leased_by"] == "code-2"

    events = client.get(f"/tasks/{created['id']}/events").json()
    assert [event["event_type"] for event in events] == ["created", "leased", "reported", "retry_requested", "leased"]


def test_owner_cancel_task_removes_it_from_queue(client: TestClient) -> None:
    task = client.post(
        "/tasks",
        json={
            "role": "code_worker",
            "goal": "Cancel obsolete task",
            "requirements": ["No longer needed"],
            "success_criteria": ["Not leased"],
            "estimated_minutes": 15,
            "memory_refs": [],
            "branch": "worker/cancel-obsolete-task",
        },
    ).json()

    canceled = client.post(f"/owner/tasks/{task['id']}/cancel", json={"reason": "Obsolete."})
    assert canceled.status_code == 200
    assert canceled.json()["status"] == "canceled"
    assert canceled.json()["leased_by"] is None

    lease = client.post("/workers/code-1/lease", json={"role": "code_worker", "lease_minutes": 30})
    assert lease.status_code == 204

    events = client.get(f"/tasks/{task['id']}/events").json()
    assert events[-1]["event_type"] == "canceled"


def test_owner_release_running_task_returns_it_to_queue(client: TestClient) -> None:
    task = client.post(
        "/tasks",
        json={
            "role": "code_worker",
            "goal": "Release stuck task",
            "requirements": ["Lease then release"],
            "success_criteria": ["Can be leased again"],
            "estimated_minutes": 15,
            "memory_refs": [],
            "branch": "worker/release-stuck-task",
        },
    ).json()
    leased = client.post("/workers/code-1/lease", json={"role": "code_worker", "lease_minutes": 30})
    assert leased.status_code == 200
    assert leased.json()["id"] == task["id"]

    released = client.post(f"/owner/tasks/{task['id']}/release", json={"reason": "Worker session died."})
    assert released.status_code == 200
    assert released.json()["status"] == "pending"
    assert released.json()["leased_by"] is None
    assert released.json()["retry_count"] == 0

    leased_again = client.post("/workers/code-2/lease", json={"role": "code_worker", "lease_minutes": 30})
    assert leased_again.status_code == 200
    assert leased_again.json()["id"] == task["id"]
    assert leased_again.json()["leased_by"] == "code-2"

    events = client.get(f"/tasks/{task['id']}/events").json()
    assert [event["event_type"] for event in events] == ["created", "leased", "released", "leased"]


def test_task_package_includes_memory_refs(client: TestClient) -> None:
    memory_payload = {
        "type": "project_knowledge",
        "key": "boss_system",
        "title": "Boss System",
        "body": "BossController already exists.",
        "tags": ["boss", "combat"],
    }
    assert client.post("/memory", json=memory_payload).status_code == 200
    task_payload = {
        "role": "code_worker",
        "goal": "Implement Boss Attack",
        "requirements": ["Use existing BossController"],
        "success_criteria": ["Attack can be triggered"],
        "estimated_minutes": 15,
        "memory_refs": ["boss_system", "missing_ref"],
        "branch": "worker/boss-attack",
    }
    created = client.post("/tasks", json=task_payload)
    assert created.status_code == 200

    package = client.get(f"/tasks/{created.json()['id']}/package")
    assert package.status_code == 200
    body = package.json()
    assert body["task"]["goal"] == "Implement Boss Attack"
    assert [memory["key"] for memory in body["memories"]] == ["boss_system"]
    assert body["project"] is None


def test_project_config_flows_into_task_package(client: TestClient) -> None:
    project = client.post(
        "/projects",
        json={
            "name": "Action RPG",
            "description": "First game project",
            "engine": "undecided",
            "repo_url": "https://example.test/game.git",
            "workspace_path": "/tmp/game-workspace",
            "base_branch": "main",
        },
    )
    assert project.status_code == 200
    project_id = project.json()["id"]

    updated = client.patch(
        f"/projects/{project_id}/config",
        json={
            "engine": "unity",
            "repo_url": "https://example.test/updated-game.git",
            "workspace_path": "/tmp/updated-game-workspace",
            "base_branch": "develop",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["engine"] == "unity"

    epic = client.post(f"/projects/{project_id}/epics", json={"name": "Combat", "goal": "Combat foundation"})
    assert epic.status_code == 200
    sub_epic = client.post(
        f"/epics/{epic.json()['id']}/sub-epics",
        json={"name": "Player Combat", "goal": "Player attacks"},
    )
    assert sub_epic.status_code == 200
    task = client.post(
        f"/sub-epics/{sub_epic.json()['id']}/tasks",
        json={
            "role": "code_worker",
            "goal": "Create attack input stub",
            "requirements": ["Input stub"],
            "success_criteria": ["Compiles"],
            "estimated_minutes": 15,
            "memory_refs": [],
            "branch": "worker/player-attack-input",
        },
    )
    assert task.status_code == 200

    package = client.get(f"/tasks/{task.json()['id']}/package")
    assert package.status_code == 200
    assert package.json()["project"]["repo_url"] == "https://example.test/updated-game.git"
    assert package.json()["project"]["base_branch"] == "develop"

    listed = client.get("/projects")
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == project_id

    fetched = client.get(f"/projects/{project_id}")
    assert fetched.status_code == 200
    assert fetched.json()["workspace_path"] == "/tmp/updated-game-workspace"

    tree = client.get(f"/projects/{project_id}/tree")
    assert tree.status_code == 200
    body = tree.json()
    assert body["epics"][0]["name"] == "Combat"
    assert body["epics"][0]["sub_epics"][0]["name"] == "Player Combat"
    assert body["epics"][0]["sub_epics"][0]["tasks"][0]["goal"] == "Create attack input stub"


def test_workspace_lease_requires_project_repo_config(client: TestClient) -> None:
    orphan = client.post(
        "/tasks",
        json={
            "role": "code_worker",
            "goal": "Orphan task",
            "requirements": ["No project"],
            "success_criteria": ["Skipped by workspace worker"],
            "estimated_minutes": 15,
            "memory_refs": [],
            "branch": "worker/orphan-task",
        },
    ).json()
    project = client.post(
        "/projects",
        json={
            "name": "Workspace Ready Game",
            "description": "",
            "engine": "undecided",
            "repo_url": "/tmp/game.git",
            "workspace_path": "/tmp/game-workspace",
            "base_branch": "main",
        },
    ).json()
    epic = client.post(f"/projects/{project['id']}/epics", json={"name": "Setup", "goal": ""}).json()
    sub_epic = client.post(f"/epics/{epic['id']}/sub-epics", json={"name": "Repo", "goal": ""}).json()
    project_task = client.post(
        f"/sub-epics/{sub_epic['id']}/tasks",
        json={
            "role": "code_worker",
            "goal": "Workspace task",
            "requirements": ["Has project repo"],
            "success_criteria": ["Leased by workspace worker"],
            "estimated_minutes": 15,
            "memory_refs": [],
            "branch": "worker/workspace-task",
        },
    ).json()

    leased = client.post(
        "/workers/workspace-1/lease",
        json={"role": "code_worker", "lease_minutes": 30, "requires_project_config": True},
    )
    assert leased.status_code == 200
    assert leased.json()["id"] == project_task["id"]
    assert client.get(f"/tasks/{orphan['id']}").json()["status"] == "pending"

    queue = client.get("/owner/task-queue", params={"status": "pending", "role": "code_worker"})
    assert queue.status_code == 200
    orphan_review = next(item for item in queue.json() if item["task"]["id"] == orphan["id"])["review"]
    assert orphan_review["workspace_ready"] is False
    assert "task is not attached to a project" in orphan_review["reasons"]

    running_queue = client.get("/owner/task-queue", params={"status": "running", "role": "code_worker"})
    assert running_queue.status_code == 200
    project_review = next(item for item in running_queue.json() if item["task"]["id"] == project_task["id"])["review"]
    assert project_review["workspace_ready"] is True

    assigned = client.post(
        f"/owner/tasks/{orphan['id']}/assign-sub-epic",
        json={"sub_epic_id": sub_epic["id"], "reason": "Attach orphan task to configured project."},
    )
    assert assigned.status_code == 200
    assert assigned.json()["sub_epic_id"] == sub_epic["id"]

    queue_after_assign = client.get("/owner/task-queue", params={"status": "pending", "role": "code_worker"})
    assigned_review = next(item for item in queue_after_assign.json() if item["task"]["id"] == orphan["id"])["review"]
    assert assigned_review["workspace_ready"] is True


def test_api_token_required_when_configured(client: TestClient) -> None:
    original_settings = auth_module.settings
    auth_module.settings = Settings(
        db_path=Path(":memory:"),
        host="127.0.0.1",
        port=8080,
        default_task_minutes=15,
        owner_recall_minutes=30,
        api_token="admin-token",
        owner_token="owner-token",
        worker_token="worker-token",
        readonly_token="readonly-token",
        artifact_token="artifact-token",
        owner_command="",
        owner_timeout_seconds=900,
        owner_runs_dir=Path("./owner-runs-test"),
        artifact_root=Path("./artifacts-test"),
        max_artifact_upload_bytes=1024,
        context_compact_threshold_tokens=260000,
        context_warning_tokens=220000,
        context_chars_per_token=3.5,
    )
    try:
        assert client.get("/health").status_code == 200
        unauthorized = client.get("/tasks")
        assert unauthorized.status_code == 401
        admin = client.get("/tasks", headers={"Authorization": "Bearer admin-token"})
        assert admin.status_code == 200
        readonly = client.get("/tasks", headers={"Authorization": "Bearer readonly-token"})
        assert readonly.status_code == 200
        token_header_fallback = client.get(
            "/tasks",
            headers={"Authorization": "Bearer wrong-token", "x-api-token": "readonly-token"},
        )
        assert token_header_fallback.status_code == 200
        readonly_write = client.post(
            "/tasks",
            headers={"Authorization": "Bearer readonly-token"},
            json={
                "role": "code_worker",
                "goal": "Should be forbidden",
                "requirements": ["No writes"],
                "success_criteria": ["Rejected"],
                "estimated_minutes": 15,
                "memory_refs": [],
                "branch": "worker/forbidden-readonly-write",
            },
        )
        assert readonly_write.status_code == 403

        owner_task = client.post(
            "/tasks",
            headers={"Authorization": "Bearer owner-token"},
            json={
                "role": "code_worker",
                "goal": "Token-scoped worker task",
                "requirements": ["Worker can lease"],
                "success_criteria": ["Worker can read package"],
                "estimated_minutes": 15,
                "memory_refs": [],
                "branch": "worker/token-scoped-task",
            },
        )
        assert owner_task.status_code == 200

        worker_list = client.get("/tasks", headers={"Authorization": "Bearer worker-token"})
        assert worker_list.status_code == 403
        worker_lease = client.post(
            "/workers/code-auth/lease",
            headers={"Authorization": "Bearer worker-token"},
            json={"role": "code_worker", "lease_minutes": 30},
        )
        assert worker_lease.status_code == 200
        worker_package = client.get(
            f"/tasks/{worker_lease.json()['id']}/package",
            headers={"Authorization": "Bearer worker-token"},
        )
        assert worker_package.status_code == 200
        worker_dashboard = client.get("/owner/dashboard", headers={"Authorization": "Bearer worker-token"})
        assert worker_dashboard.status_code == 403

        owner_project = client.post(
            "/projects",
            headers={"Authorization": "Bearer owner-token"},
            json={
                "name": "Artifact Token Project",
                "description": "",
                "engine": "undecided",
                "repo_url": "",
                "workspace_path": "",
                "base_branch": "main",
            },
        )
        assert owner_project.status_code == 200
        artifact_create = client.post(
            "/artifacts",
            headers={"Authorization": "Bearer artifact-token"},
            json={
                "artifact_id": "auth-artifact-1",
                "project_id": owner_project.json()["id"],
                "artifact_type": "log",
                "filename": "auth.log",
            },
        )
        assert artifact_create.status_code == 200
        artifact_blocked = client.get("/tasks", headers={"Authorization": "Bearer artifact-token"})
        assert artifact_blocked.status_code == 403
    finally:
        auth_module.settings = original_settings


def test_owner_model_profiles_can_be_upserted_and_listed(client: TestClient) -> None:
    initial = client.get("/owner/readiness")
    assert initial.status_code == 200
    assert "owner model profile is not configured" in initial.json()["blockers"]

    owner_payload = {
        "role": "owner",
        "provider": "codex-cli",
        "model": "configured-by-command",
        "base_url": "",
        "api_key_env": "",
        "temperature": 0.2,
        "max_tokens": None,
        "enabled": True,
        "notes": "Owner command profile.",
    }
    assert client.put("/owner/model-profiles/owner", json=owner_payload).status_code == 200
    payload = {
        "role": "code_worker",
        "provider": "openai-compatible",
        "model": "gpt-low-cost-worker",
        "base_url": "https://api.example.test/v1",
        "api_key_env": "GAME_COMPANY_WORKER_API_KEY",
        "temperature": 0.1,
        "max_tokens": 4096,
        "enabled": True,
        "notes": "Cheap execution model.",
    }
    created = client.put("/owner/model-profiles/code_worker", json=payload)
    assert created.status_code == 200
    body = created.json()
    assert body["role"] == "code_worker"
    assert body["enabled"] is True
    assert body["api_key_env"] == "GAME_COMPANY_WORKER_API_KEY"

    fetched = client.get("/owner/model-profiles/code_worker")
    assert fetched.status_code == 200
    assert fetched.json()["model"] == "gpt-low-cost-worker"

    listed = client.get("/owner/model-profiles", params={"enabled": True})
    assert listed.status_code == 200
    assert listed.json()[0]["role"] == "code_worker"

    mismatch = client.put("/owner/model-profiles/owner", json=payload)
    assert mismatch.status_code == 400

    readiness = client.get("/owner/readiness")
    assert readiness.status_code == 200
    assert readiness.json()["ready"] is True
    assert readiness.json()["model_profiles"] == ["code_worker", "owner"]


def test_machine_and_worker_registry(client: TestClient) -> None:
    main_machine = {
        "machine_id": "main_server",
        "display_name": "Main server",
        "kind": "main_server",
        "host_hint": "user@remote-host",
        "os": "linux",
        "workspace_root": "/home/user",
        "artifact_root": "/home/user/ai-game-company-server/artifacts",
        "status": "offline",
        "capabilities": ["control_plane", "gpu", "local_llm_future"],
        "notes": "Intel Core i5-14600KF / RTX 4070 / 32 GB DDR5.",
    }
    created_machine = client.put("/registry/machines/main_server", json=main_machine)
    assert created_machine.status_code == 200
    assert created_machine.json()["capabilities"] == ["control_plane", "gpu", "local_llm_future"]
    assert created_machine.json()["last_seen_at"] is None

    heartbeat = client.post(
        "/registry/machines/main_server/heartbeat",
        json={"status": "online", "capabilities": ["control_plane", "gpu"], "notes": "Booted."},
    )
    assert heartbeat.status_code == 200
    assert heartbeat.json()["status"] == "online"
    assert heartbeat.json()["last_seen_at"] is not None

    listed_machines = client.get("/registry/machines", params={"kind": "main_server", "status": "online"})
    assert listed_machines.status_code == 200
    assert [machine["machine_id"] for machine in listed_machines.json()] == ["main_server"]

    worker = {
        "worker_id": "workspace-code-1",
        "display_name": "Workspace Code Worker 1",
        "role": "workspace_worker",
        "machine_id": "main_server",
        "status": "offline",
        "capabilities": ["code_edit", "git_commit", "git_push"],
        "assigned_projects": [1, 2],
        "workspace_root": "/home/user/game-workspaces",
        "trust_level": "trusted",
        "notes": "v1 manual worker.",
    }
    created_worker = client.put("/registry/workers/workspace-code-1", json=worker)
    assert created_worker.status_code == 200
    assert created_worker.json()["assigned_projects"] == [1, 2]

    worker_heartbeat = client.post(
        "/registry/workers/workspace-code-1/heartbeat",
        json={"status": "online", "capabilities": ["code_edit"], "notes": "Ready."},
    )
    assert worker_heartbeat.status_code == 200
    assert worker_heartbeat.json()["status"] == "online"
    assert worker_heartbeat.json()["capabilities"] == ["code_edit"]

    listed_workers = client.get("/registry/workers", params={"machine_id": "main_server", "status": "online"})
    assert listed_workers.status_code == 200
    assert [item["worker_id"] for item in listed_workers.json()] == ["workspace-code-1"]

    mismatch = client.put("/registry/workers/other-worker", json=worker)
    assert mismatch.status_code == 400


def test_worker_registry_last_seen_updates_from_task_activity(client: TestClient) -> None:
    task = client.post(
        "/tasks",
        json={
            "role": "code_worker",
            "goal": "Touch worker registry",
            "requirements": ["Lease updates registry"],
            "success_criteria": ["Worker last_seen_at is set"],
            "estimated_minutes": 15,
            "memory_refs": [],
            "branch": "worker/touch-worker-registry",
        },
    ).json()

    leased = client.post("/workers/code-activity-1/lease", json={"role": "code_worker", "lease_minutes": 30})
    assert leased.status_code == 200
    assert leased.json()["id"] == task["id"]

    busy_worker = client.get("/registry/workers/code-activity-1")
    assert busy_worker.status_code == 200
    assert busy_worker.json()["role"] == "code_worker"
    assert busy_worker.json()["status"] == "busy"
    assert busy_worker.json()["last_seen_at"] is not None

    report = {
        "status": "success",
        "estimated_minutes": 15,
        "actual_minutes": 1,
        "productive_minutes": 1,
        "error_minutes": 0,
        "retry_count": 0,
        "files_changed": [],
        "tests": ["registry smoke"],
        "summary": "Registry touched.",
        "issues": "",
    }
    completed = client.post(f"/workers/code-activity-1/tasks/{task['id']}/report", json=report)
    assert completed.status_code == 200

    online_worker = client.get("/registry/workers/code-activity-1")
    assert online_worker.status_code == 200
    assert online_worker.json()["status"] == "online"


def test_artifact_metadata_upload_and_download(client: TestClient) -> None:
    project = client.post(
        "/projects",
        json={
            "name": "Artifact Project",
            "description": "",
            "engine": "undecided",
            "repo_url": "https://example.test/artifact.git",
            "workspace_path": "/tmp/artifact-workspace",
            "base_branch": "main",
        },
    ).json()
    task = client.post(
        "/tasks",
        json={
            "role": "test_runner",
            "goal": "Capture screenshot",
            "requirements": ["Upload screenshot"],
            "success_criteria": ["Artifact is downloadable"],
            "estimated_minutes": 15,
            "memory_refs": [],
            "branch": "worker/capture-screenshot",
        },
    ).json()
    machine = {
        "machine_id": "test_runner_12400_3060",
        "display_name": "Test Runner",
        "kind": "test_runner_machine",
        "host_hint": "",
        "os": "linux",
        "workspace_root": "/srv/projects",
        "artifact_root": "/srv/artifacts",
        "status": "online",
        "capabilities": ["build", "test", "screenshot", "gpu"],
        "notes": "i5-12400 / RTX 3060.",
    }
    assert client.put("/registry/machines/test_runner_12400_3060", json=machine).status_code == 200

    artifact_payload = {
        "artifact_id": "shot-001",
        "project_id": project["id"],
        "task_id": task["id"],
        "worker_id": "test-runner-1",
        "machine_id": "test_runner_12400_3060",
        "artifact_type": "screenshot",
        "filename": "screen.png",
        "content_type": "image/png",
        "summary": "First visual check.",
        "tags": ["visual", "smoke"],
        "retention_policy": "important_keep_forever",
        "important": True,
        "release_or_milestone": False,
    }
    created = client.post("/artifacts", json=artifact_payload)
    assert created.status_code == 200
    assert created.json()["artifact_id"] == "shot-001"
    assert created.json()["important"] is True
    assert created.json()["tags"] == ["visual", "smoke"]
    assert created.json()["path"] == ""

    uploaded = client.put(
        "/artifacts/shot-001/content",
        params={"filename": "../screen.png", "content_type": "image/png"},
        content=b"fake png bytes",
    )
    assert uploaded.status_code == 200
    assert uploaded.json()["filename"] == "screen.png"
    assert uploaded.json()["size_bytes"] == len(b"fake png bytes")
    assert uploaded.json()["path"].endswith("/shot-001/screen.png")

    listed = client.get(
        "/artifacts",
        params={"project_id": project["id"], "artifact_type": "screenshot", "important": True},
    )
    assert listed.status_code == 200
    assert [item["artifact_id"] for item in listed.json()] == ["shot-001"]

    downloaded = client.get("/artifacts/shot-001/content")
    assert downloaded.status_code == 200
    assert downloaded.content == b"fake png bytes"

    large_artifact = client.post(
        "/artifacts",
        json={
            "artifact_id": "large-log-001",
            "project_id": project["id"],
            "artifact_type": "log",
            "filename": "large.log",
        },
    )
    assert large_artifact.status_code == 200
    too_large = client.put(
        "/artifacts/large-log-001/content",
        params={"filename": "large.log", "content_type": "text/plain"},
        content=b"x" * 2048,
    )
    assert too_large.status_code == 413


def test_approval_request_and_decision_flow(client: TestClient) -> None:
    project = client.post(
        "/projects",
        json={
            "name": "Approval Project",
            "description": "",
            "engine": "undecided",
            "repo_url": "https://example.test/approval.git",
            "workspace_path": "/tmp/approval-workspace",
            "base_branch": "main",
        },
    ).json()

    payload = {
        "approval_id": "repo-setup-1",
        "project_id": project["id"],
        "target_type": "repo_setup",
        "target_id": "approval-project",
        "requested_by": "owner",
        "request_summary": "Create GitHub private repo and project workspace.",
        "risk_summary": "Creates external GitHub repo and local workspace.",
        "approval_message": "좋아 진행해 라고 답하면 진행.",
        "discord_message_id": "123",
        "discord_thread_id": "456",
        "decision_memory_key": "decision_repo_setup_1",
    }
    created = client.post("/approvals", json=payload)
    assert created.status_code == 200
    body = created.json()
    assert body["approval_id"] == "repo-setup-1"
    assert body["status"] == "pending"
    assert body["approved_by"] is None
    assert body["decided_at"] is None

    pending = client.get("/approvals", params={"status": "pending", "project_id": project["id"]})
    assert pending.status_code == 200
    assert [item["approval_id"] for item in pending.json()] == ["repo-setup-1"]

    fetched = client.get("/approvals/repo-setup-1")
    assert fetched.status_code == 200
    assert fetched.json()["target_type"] == "repo_setup"

    decided = client.post(
        "/approvals/repo-setup-1/decision",
        json={
            "status": "approved",
            "approved_by": "user",
            "approval_message": "좋아 진행해.",
            "decision_memory_key": "decision_repo_setup_approved",
        },
    )
    assert decided.status_code == 200
    assert decided.json()["status"] == "approved"
    assert decided.json()["approved_by"] == "user"
    assert decided.json()["approval_message"] == "좋아 진행해."
    assert decided.json()["decided_at"] is not None

    duplicate_decision = client.post(
        "/approvals/repo-setup-1/decision",
        json={"status": "rejected", "approved_by": "user", "approval_message": "Never mind."},
    )
    assert duplicate_decision.status_code == 409

    invalid_status = client.post(
        "/approvals",
        json={
            "target_type": "merge",
            "request_summary": "Merge worker branch.",
        },
    ).json()
    invalid_decision = client.post(
        f"/approvals/{invalid_status['approval_id']}/decision",
        json={"status": "done"},
    )
    assert invalid_decision.status_code == 422


def test_discord_mapping_lifecycle(client: TestClient) -> None:
    project = client.post(
        "/projects",
        json={
            "name": "Discord Project",
            "description": "",
            "engine": "undecided",
            "repo_url": "https://example.test/discord.git",
            "workspace_path": "/tmp/discord-workspace",
            "base_branch": "main",
        },
    ).json()

    payload = {
        "discord_guild_id": "guild-1",
        "discord_channel_id": "channel-1",
        "discord_thread_id": "thread-owner-design",
        "project_id": project["id"],
        "conversation_kind": "project",
        "thread_role": "owner-design",
        "created_by": "owner",
        "summary_memory_key": "thread_thread-owner-design_summary_current",
        "notes": "Owner design thread for this project.",
    }
    created = client.post("/discord/mappings", json=payload)
    assert created.status_code == 200
    body = created.json()
    assert body["mapping_id"].startswith("discord_")
    assert body["project_id"] == project["id"]
    assert body["archived_at"] is None

    repeated = client.post("/discord/mappings", json={**payload, "notes": "Updated by bot sync."})
    assert repeated.status_code == 200
    assert repeated.json()["mapping_id"] == body["mapping_id"]
    assert repeated.json()["notes"] == "Updated by bot sync."

    listed = client.get(
        "/discord/mappings",
        params={
            "project_id": project["id"],
            "conversation_kind": "project",
            "thread_role": "owner-design",
            "discord_guild_id": "guild-1",
            "discord_channel_id": "channel-1",
            "discord_thread_id": "thread-owner-design",
        },
    )
    assert listed.status_code == 200
    assert [item["mapping_id"] for item in listed.json()] == [body["mapping_id"]]

    fetched = client.get(f"/discord/mappings/{body['mapping_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["discord_thread_id"] == "thread-owner-design"

    archived = client.post(
        f"/discord/mappings/{body['mapping_id']}/archive",
        json={"reason": "Thread rotated after context summary."},
    )
    assert archived.status_code == 200
    assert archived.json()["archived_at"] is not None
    assert "Archive reason" in archived.json()["notes"]

    active = client.get("/discord/mappings", params={"active": True})
    assert active.status_code == 200
    assert active.json() == []

    inactive = client.get("/discord/mappings", params={"active": False})
    assert inactive.status_code == 200
    assert [item["mapping_id"] for item in inactive.json()] == [body["mapping_id"]]

    mismatch = client.put("/discord/mappings/custom-id", json={**payload, "mapping_id": "other-id"})
    assert mismatch.status_code == 400

    duplicate_location = client.put("/discord/mappings/custom-id", json={**payload, "mapping_id": "custom-id"})
    assert duplicate_location.status_code == 409

    invalid_project = client.post("/discord/mappings", json={**payload, "project_id": 999})
    assert invalid_project.status_code == 404


def test_discord_thread_compaction_stores_summary_and_continuation(client: TestClient) -> None:
    project = client.post(
        "/projects",
        json={
            "name": "Context Project",
            "description": "",
            "engine": "undecided",
            "repo_url": "https://example.test/context.git",
            "workspace_path": "/tmp/context-workspace",
            "base_branch": "main",
        },
    ).json()

    mapping = client.post(
        "/discord/mappings",
        json={
            "discord_guild_id": "guild-1",
            "discord_channel_id": "channel-1",
            "discord_thread_id": "thread-owner-tasks",
            "project_id": project["id"],
            "conversation_kind": "project",
            "thread_role": "owner-tasks",
            "created_by": "owner",
            "notes": "Owner task planning thread.",
        },
    ).json()

    first = client.post(
        f"/discord/mappings/{mapping['mapping_id']}/compact",
        json={
            "summary": "Owner wants compact context instead of full raw Discord history.",
            "tags": ["context", "owner"],
        },
    )
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["memory"]["type"] == "thread_summary"
    assert first_body["memory"]["body"].startswith("Owner wants compact context")
    assert f"project:{project['id']}" in first_body["memory"]["tags"]
    assert "thread:thread-owner-tasks" in first_body["memory"]["tags"]
    assert first_body["mapping"]["summary_memory_key"] == first_body["memory"]["key"]
    assert first_body["archived_memory"] is None
    assert first_body["continuation_mapping"] is None

    second = client.post(
        f"/discord/mappings/{mapping['mapping_id']}/compact",
        json={
            "summary": "Current summary now includes a continuation thread.",
            "archive_mapping": True,
            "continuation_discord_thread_id": "thread-owner-tasks-part-2",
            "continuation_notes": "Part 2 after compaction.",
        },
    )
    assert second.status_code == 200
    second_body = second.json()
    assert second_body["memory"]["body"] == "Current summary now includes a continuation thread."
    assert second_body["archived_memory"]["body"].startswith("Owner wants compact context")
    assert "summary_archive" in second_body["archived_memory"]["tags"]
    assert second_body["archived_mapping"]["archived_at"] is not None
    assert second_body["continuation_mapping"]["discord_thread_id"] == "thread-owner-tasks-part-2"
    assert second_body["continuation_mapping"]["archived_at"] is None

    summaries = client.get(
        "/memory",
        params={
            "type": "thread_summary",
            "tag": "thread:thread-owner-tasks",
            "q": "continuation",
        },
    )
    assert summaries.status_code == 200
    assert summaries.json()[0]["key"] == second_body["memory"]["key"]


def test_discord_context_status_requires_or_runs_compaction(client: TestClient) -> None:
    mapping = client.post(
        "/discord/mappings",
        json={
            "discord_guild_id": "guild-1",
            "discord_channel_id": "channel-1",
            "discord_thread_id": "thread-context-status",
            "conversation_kind": "project",
            "thread_role": "owner-design",
            "created_by": "owner",
        },
    ).json()

    ok = client.post(
        f"/discord/mappings/{mapping['mapping_id']}/context-status",
        json={
            "recent_messages": ["short message"],
            "threshold_tokens": 100,
            "warning_tokens": 80,
        },
    )
    assert ok.status_code == 200
    assert ok.json()["status"] == "ok"
    assert ok.json()["compact_action"] == "not_needed"

    required = client.post(
        f"/discord/mappings/{mapping['mapping_id']}/context-status",
        json={
            "recent_messages": ["x" * 400],
            "threshold_tokens": 100,
            "warning_tokens": 80,
        },
    )
    assert required.status_code == 200
    assert required.json()["status"] == "compact_now"
    assert required.json()["compact_required"] is True
    assert required.json()["compact_action"] == "summary_required"

    compacted = client.post(
        f"/discord/mappings/{mapping['mapping_id']}/context-status",
        json={
            "recent_messages": ["x" * 400],
            "threshold_tokens": 100,
            "warning_tokens": 80,
            "auto_compact": True,
            "compact_summary": "Summarized before crossing the configured context threshold.",
            "archive_mapping": False,
        },
    )
    assert compacted.status_code == 200
    body = compacted.json()
    assert body["compact_action"] == "compacted"
    assert body["compact_result"]["memory"]["type"] == "thread_summary"
    assert body["compact_result"]["memory"]["body"].startswith("Summarized before crossing")


def test_owner_run_dry_run_records_prompt(client: TestClient) -> None:
    response = client.post(
        "/owner/runs",
        json={
            "objective": "Break combat system into worker tasks",
            "context": "No game engine selected yet.",
            "dry_run": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "dry_run"
    assert "Break combat system" in body["prompt"]
    assert "No game engine selected yet." in body["prompt"]
    assert "Return exactly these sections" in body["prompt"]
    assert "user_questions" in body["prompt"]
    assert "workspace task branches must start with worker/" in body["prompt"]
    assert "project engine may stay undecided" in body["prompt"]

    runs = client.get("/owner/runs")
    assert runs.status_code == 200
    assert runs.json()[0]["id"] == body["id"]


def git(args: list[str], cwd: Path) -> str:
    completed = subprocess.run(
        [git_executable(), *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout
    return completed.stdout.strip()


def make_git_repo(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "source"
    source.mkdir()
    git(["init", "-b", "main"], cwd=source)
    git(["config", "user.email", "test@example.com"], cwd=source)
    git(["config", "user.name", "Test User"], cwd=source)
    (source / "README.md").write_text("# Demo\n", encoding="utf-8")
    git(["add", "README.md"], cwd=source)
    git(["commit", "-m", "Initial"], cwd=source)
    remote = tmp_path / "remote.git"
    git(["clone", "--bare", str(source), str(remote)], cwd=tmp_path)
    workspace = tmp_path / "workspace"
    return remote, workspace


def test_owner_task_merge_api_reviews_and_merges_successful_task(client: TestClient, tmp_path: Path) -> None:
    remote, workspace = make_git_repo(tmp_path)
    project = client.post(
        "/projects",
        json={
            "name": "Merge API Game",
            "description": "",
            "engine": "undecided",
            "repo_url": str(remote),
            "workspace_path": str(workspace),
            "base_branch": "main",
        },
    )
    epic = client.post(f"/projects/{project.json()['id']}/epics", json={"name": "Docs", "goal": ""})
    sub_epic = client.post(f"/epics/{epic.json()['id']}/sub-epics", json={"name": "Notes", "goal": ""})
    task = client.post(
        f"/sub-epics/{sub_epic.json()['id']}/tasks",
        json={
            "role": "code_worker",
            "goal": "Create notes",
            "requirements": ["Write notes.txt"],
            "success_criteria": ["Merged to main"],
            "estimated_minutes": 15,
            "memory_refs": [],
            "branch": "worker/merge-api-notes",
        },
    ).json()
    package = client.get(f"/tasks/{task['id']}/package").json()
    prepare_branch(package, str(remote), workspace, "main")
    (workspace / "notes.txt").write_text("merged by api\n", encoding="utf-8")
    commit_changes(workspace, package["task"], ["notes.txt"])
    push_branch(workspace, "worker/merge-api-notes")
    claimed = client.post(f"/workers/code-1/tasks/{task['id']}/claim", json={"lease_minutes": 30})
    assert claimed.status_code == 200
    report = {
        "status": "success",
        "estimated_minutes": 15,
        "actual_minutes": 1,
        "productive_minutes": 1,
        "error_minutes": 0,
        "retry_count": 0,
        "files_changed": ["notes.txt"],
        "tests": ["manual"],
        "summary": "Ready to merge.",
        "issues": "",
    }
    assert client.post(f"/workers/code-1/tasks/{task['id']}/report", json=report).status_code == 200

    candidates = client.get("/owner/merge-candidates")
    assert candidates.status_code == 200
    candidate = next(item for item in candidates.json() if item["task"]["id"] == task["id"])
    assert candidate["review"]["eligible"] is True
    assert candidate["review"]["warnings"] == []

    preview = client.post(f"/owner/tasks/{task['id']}/merge", json={})
    assert preview.status_code == 200
    assert preview.json()["status"] == "ready"
    assert preview.json()["dry_run"] is True

    next_preview = client.post("/owner/merge-candidates/merge-next", json={})
    assert next_preview.status_code == 200
    assert next_preview.json()["status"] == "ready"
    assert next_preview.json()["candidate"]["task"]["id"] == task["id"]

    merged = client.post("/owner/merge-candidates/merge-next", json={"dry_run": False, "push": True})
    assert merged.status_code == 200
    assert merged.json()["status"] == "merged"
    assert merged.json()["selected"]["task"]["id"] == task["id"]
    assert run_git(["show", "main:notes.txt"], cwd=remote) == "merged by api"

    events = client.get(f"/tasks/{task['id']}/events").json()
    assert events[-1]["event_type"] == "merged"

    duplicate_preview = client.post(f"/owner/tasks/{task['id']}/merge", json={})
    assert duplicate_preview.status_code == 200
    assert duplicate_preview.json()["status"] == "blocked"
    assert "task has already been merged" in duplicate_preview.json()["review"]["reasons"]

    duplicate_merge = client.post(f"/owner/tasks/{task['id']}/merge", json={"dry_run": False, "push": True})
    assert duplicate_merge.status_code == 409


def test_multi_node_branch_naming(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    # 1. Create a task
    task_payload = {
        "role": "code_worker",
        "goal": "Test branch naming",
        "requirements": ["Do something"],
        "success_criteria": ["Done"],
        "estimated_minutes": 15,
        "memory_refs": [],
        "branch": "worker/branch-slug",
    }
    task = client.post("/tasks", json=task_payload).json()
    task_id = task["id"]
    assert task["branch"] == "worker/branch-slug"

    # 2. Lease with default/empty node_id (should preserve original branch naming)
    leased = client.post("/workers/node-a/lease", json={"role": "code_worker", "lease_minutes": 30}).json()
    assert leased["id"] == task_id
    assert leased["branch"] == "worker/branch-slug"

    # Complete/release task to lease it again with non-empty node_id
    client.post(f"/owner/tasks/{task_id}/release", json={})

    # 3. Lease with configured node_id (should dynamically update branch using node_id)
    monkeypatch.setenv("GAME_COMPANY_NODE_ID", "friend-a")
    leased_with_node = client.post("/workers/gemini-worker-1/lease", json={"role": "code_worker", "lease_minutes": 30}).json()
    assert leased_with_node["id"] == task_id
    # Branch naming should be: worker/{node_id}/{task_id}-{slug}
    # Here node_id = "friend-a", task_id = task_id, slug = "branch-slug"
    assert leased_with_node["branch"] == f"worker/friend-a/{task_id}-branch-slug"

    # Release task again to test claim
    client.post(f"/owner/tasks/{task_id}/release", json={})

    # 4. Claim with configured node_id (should dynamically update branch using node_id)
    # Reset env/monkeypatch first to verify empty preserves it on claim
    monkeypatch.delenv("GAME_COMPANY_NODE_ID", raising=False)
    # Re-fetch task to check branch
    task_before_claim = client.get(f"/tasks/{task_id}").json()
    # Now set GAME_COMPANY_NODE_ID again
    monkeypatch.setenv("GAME_COMPANY_NODE_ID", "friend-a")
    claimed = client.post(f"/workers/gemini-worker-2/tasks/{task_id}/claim", json={"lease_minutes": 30}).json()
    assert claimed["branch"] == f"worker/friend-a/{task_id}-branch-slug"


# ---------------------------------------------------------------------------
# base_commit tracking and stale-base detection tests
# ---------------------------------------------------------------------------

def _report_payload(status: str = "success") -> dict:
    """Minimal valid WorkerReportCreate payload."""
    return {
        "status": status,
        "estimated_minutes": 15,
        "actual_minutes": 10,
        "productive_minutes": 8,
        "error_minutes": 2,
        "retry_count": 0,
        "files_changed": [],
        "tests": [],
        "summary": "Done",
        "issues": "",
    }


def _make_project_with_repo(client: TestClient, source: Path, remote: Path) -> tuple[int, int]:
    """Create project -> epic -> sub_epic and return (project_id, sub_epic_id)."""
    project = client.post("/projects", json={
        "name": "BaseCommit Test Project",
        "engine": "undecided",
        "repo_url": str(remote),
        "workspace_path": str(source),
        "base_branch": "main",
    }).json()
    epic = client.post(f"/projects/{project['id']}/epics", json={"name": "E", "goal": ""}).json()
    sub_epic = client.post(f"/epics/{epic['id']}/sub-epics", json={"name": "SE", "goal": ""}).json()
    return project["id"], sub_epic["id"]


def test_base_commit_recorded_on_lease(client: TestClient, tmp_path: Path) -> None:
    """base_commit is recorded on the task when leased with a project that has a git workspace."""
    remote, _workspace = make_git_repo(tmp_path)
    source = tmp_path / "source"   # created by make_git_repo

    _proj_id, sub_epic_id = _make_project_with_repo(client, source, remote)

    task = client.post(f"/sub-epics/{sub_epic_id}/tasks", json={
        "role": "code_worker",
        "goal": "Test base commit recording",
        "requirements": ["Do something"],
        "success_criteria": ["Done"],
        "estimated_minutes": 15,
        "memory_refs": [],
        "branch": "worker/base-commit-test",
    }).json()
    task_id = task["id"]
    assert task.get("base_commit") is None  # not set before lease

    leased = client.post("/workers/bc-worker/lease", json={"role": "code_worker", "lease_minutes": 30}).json()
    assert leased["id"] == task_id
    assert leased.get("base_commit") is not None
    assert len(leased["base_commit"]) == 40  # full SHA-1 commit hash


def test_base_commit_null_when_no_project(client: TestClient) -> None:
    """Orphan tasks (no project / no workspace) still lease successfully; base_commit stays None."""
    task = client.post("/tasks", json={
        "role": "code_worker",
        "goal": "Orphan task",
        "requirements": ["X"],
        "success_criteria": ["Y"],
        "estimated_minutes": 10,
        "memory_refs": [],
        "branch": "worker/orphan-task",
    }).json()
    task_id = task["id"]
    assert task.get("base_commit") is None

    leased = client.post("/workers/orphan-worker/lease", json={"role": "code_worker", "lease_minutes": 30}).json()
    assert leased["id"] == task_id
    # base_commit stays None because there is no linked project with a workspace
    assert leased.get("base_commit") is None


def test_stale_base_detected_on_complete(client: TestClient, tmp_path: Path) -> None:
    """If main advances after lease, reporting success → task becomes needs_rebase."""
    remote, _workspace = make_git_repo(tmp_path)
    source = tmp_path / "source"

    _proj_id, sub_epic_id = _make_project_with_repo(client, source, remote)

    task = client.post(f"/sub-epics/{sub_epic_id}/tasks", json={
        "role": "code_worker",
        "goal": "Stale base test",
        "requirements": ["X"],
        "success_criteria": ["Y"],
        "estimated_minutes": 15,
        "memory_refs": [],
        "branch": "worker/stale-base-test",
    }).json()
    task_id = task["id"]

    # Lease — records base_commit from source/main
    leased = client.post("/workers/stale-worker/lease", json={"role": "code_worker", "lease_minutes": 30}).json()
    assert leased["id"] == task_id
    initial_commit = leased.get("base_commit")
    assert initial_commit is not None

    # Advance main in the source repo (simulates another commit landing while worker was running)
    (source / "ADVANCE.md").write_text("advance\n", encoding="utf-8")
    git(["add", "ADVANCE.md"], cwd=source)
    git(["commit", "-m", "Advance main"], cwd=source)

    # Report success → should be downgraded to needs_rebase
    reported = client.post(
        f"/workers/stale-worker/tasks/{task_id}/report",
        json=_report_payload("success"),
    ).json()
    assert reported["status"] == "needs_rebase"

    # Task events should include a needs_rebase entry
    events = client.get(f"/tasks/{task_id}/events").json()
    event_types = [e["event_type"] for e in events]
    assert "needs_rebase" in event_types


def test_no_stale_base_when_unchanged(client: TestClient, tmp_path: Path) -> None:
    """If main has not moved since lease, reporting success keeps status=success."""
    remote, _workspace = make_git_repo(tmp_path)
    source = tmp_path / "source"

    _proj_id, sub_epic_id = _make_project_with_repo(client, source, remote)

    task = client.post(f"/sub-epics/{sub_epic_id}/tasks", json={
        "role": "code_worker",
        "goal": "Fresh base test",
        "requirements": ["X"],
        "success_criteria": ["Y"],
        "estimated_minutes": 15,
        "memory_refs": [],
        "branch": "worker/fresh-base-test",
    }).json()
    task_id = task["id"]

    leased = client.post("/workers/fresh-worker/lease", json={"role": "code_worker", "lease_minutes": 30}).json()
    assert leased["id"] == task_id
    assert leased.get("base_commit") is not None

    # Do NOT advance main — report success immediately
    reported = client.post(
        f"/workers/fresh-worker/tasks/{task_id}/report",
        json=_report_payload("success"),
    ).json()
    # base_commit unchanged → status remains success
    assert reported["status"] == "success"


# ---------------------------------------------------------------------------
# Task Write Scope Tracking and Scope Violation Detection Tests
# ---------------------------------------------------------------------------

def test_scope_validation_absent_scope(client: TestClient) -> None:
    # A. Existing behavior preserved when write_scope is absent
    task = client.post("/tasks", json={
        "role": "code_worker",
        "goal": "No scope test",
        "requirements": ["X"],
        "success_criteria": ["Y"],
        "estimated_minutes": 15,
        "branch": "worker/no-scope",
    }).json()
    task_id = task["id"]
    
    leased = client.post("/workers/worker-a/lease", json={"role": "code_worker", "lease_minutes": 30}).json()
    assert leased["id"] == task_id

    report = _report_payload("success")
    report["changed_files"] = ["src/player.py", "tests/test_player.py"]
    
    reported = client.post(f"/workers/worker-a/tasks/{task_id}/report", json=report).json()
    assert reported["status"] == "success"


def test_scope_validation_valid_write_scope(client: TestClient) -> None:
    # B. Valid write_scope
    task = client.post("/tasks", json={
        "role": "code_worker",
        "goal": "Valid scope test",
        "requirements": ["X"],
        "success_criteria": ["Y"],
        "estimated_minutes": 15,
        "branch": "worker/valid-scope",
        "write_scope": ["src/player.py", "tests/test_player.py"],
    }).json()
    task_id = task["id"]
    
    leased = client.post("/workers/worker-b/lease", json={"role": "code_worker", "lease_minutes": 30}).json()
    assert leased["id"] == task_id

    report = _report_payload("success")
    report["changed_files"] = ["src/player.py", "tests/test_player.py"]
    
    reported = client.post(f"/workers/worker-b/tasks/{task_id}/report", json=report).json()
    assert reported["status"] == "success"


def test_scope_validation_glob_write_scope(client: TestClient) -> None:
    # C. Glob write_scope
    task = client.post("/tasks", json={
        "role": "code_worker",
        "goal": "Glob scope test",
        "requirements": ["X"],
        "success_criteria": ["Y"],
        "estimated_minutes": 15,
        "branch": "worker/glob-scope",
        "write_scope": ["src/**", "tests/**"],
    }).json()
    task_id = task["id"]
    
    leased = client.post("/workers/worker-c/lease", json={"role": "code_worker", "lease_minutes": 30}).json()
    assert leased["id"] == task_id

    report = _report_payload("success")
    report["changed_files"] = ["src/player.py", "tests/test_player.py"]
    
    reported = client.post(f"/workers/worker-c/tasks/{task_id}/report", json=report).json()
    assert reported["status"] == "success"


def test_scope_validation_scope_violation(client: TestClient) -> None:
    # D. Scope violation
    task = client.post("/tasks", json={
        "role": "code_worker",
        "goal": "Scope violation test",
        "requirements": ["X"],
        "success_criteria": ["Y"],
        "estimated_minutes": 15,
        "branch": "worker/violation-scope",
        "write_scope": ["src/player.py"],
    }).json()
    task_id = task["id"]
    
    leased = client.post("/workers/worker-d/lease", json={"role": "code_worker", "lease_minutes": 30}).json()
    assert leased["id"] == task_id

    report = _report_payload("success")
    report["changed_files"] = ["src/player.py", "src/enemy.py"]
    
    reported = client.post(f"/workers/worker-d/tasks/{task_id}/report", json=report).json()
    assert reported["status"] == "scope_violation"

    # Task event contains src/enemy.py
    events = client.get(f"/tasks/{task_id}/events").json()
    scope_events = [e for e in events if e["event_type"] == "scope_violation"]
    assert len(scope_events) == 1
    assert "src/enemy.py" in scope_events[0]["message"]


def test_scope_validation_forbidden_scope_violation(client: TestClient) -> None:
    # E. Forbidden scope violation
    task = client.post("/tasks", json={
        "role": "code_worker",
        "goal": "Forbidden scope test",
        "requirements": ["X"],
        "success_criteria": ["Y"],
        "estimated_minutes": 15,
        "branch": "worker/forbidden-scope",
        "write_scope": ["src/**", "tests/**"],
        "forbidden_scope": [".env", ".github/**"],
    }).json()
    task_id = task["id"]
    
    leased = client.post("/workers/worker-e/lease", json={"role": "code_worker", "lease_minutes": 30}).json()
    assert leased["id"] == task_id

    report = _report_payload("success")
    report["changed_files"] = [".github/workflows/ci.yml"]
    
    reported = client.post(f"/workers/worker-e/tasks/{task_id}/report", json=report).json()
    assert reported["status"] == "scope_violation"


def test_scope_validation_no_changed_files(client: TestClient) -> None:
    # F. No changed_files (preserves existing behavior)
    task = client.post("/tasks", json={
        "role": "code_worker",
        "goal": "No changed files test",
        "requirements": ["X"],
        "success_criteria": ["Y"],
        "estimated_minutes": 15,
        "branch": "worker/no-changed-files",
        "write_scope": ["src/**"],
    }).json()
    task_id = task["id"]
    
    leased = client.post("/workers/worker-f/lease", json={"role": "code_worker", "lease_minutes": 30}).json()
    assert leased["id"] == task_id

    # Omit changed_files from report payload
    report = _report_payload("success")
    assert "changed_files" not in report
    
    reported = client.post(f"/workers/worker-f/tasks/{task_id}/report", json=report).json()
    assert reported["status"] == "success"


def test_scope_validation_retry_and_claim_blocks(client: TestClient) -> None:
    # G. Retry behavior & Claim block
    task = client.post("/tasks", json={
        "role": "code_worker",
        "goal": "Retry block test",
        "requirements": ["X"],
        "success_criteria": ["Y"],
        "estimated_minutes": 15,
        "branch": "worker/retry-block",
        "write_scope": ["src/player.py"],
    }).json()
    task_id = task["id"]
    
    leased = client.post("/workers/worker-g/lease", json={"role": "code_worker", "lease_minutes": 30}).json()
    assert leased["id"] == task_id
    
    report = _report_payload("success")
    report["changed_files"] = ["src/enemy.py"]
    reported = client.post(f"/workers/worker-g/tasks/{task_id}/report", json=report).json()
    assert reported["status"] == "scope_violation"

    # Try claiming the task in scope_violation status -> should fail with 409
    claim_res = client.post(f"/workers/worker-g/tasks/{task_id}/claim", json={"lease_minutes": 30})
    assert claim_res.status_code == 409

    # Retry the task -> should succeed and reset to pending
    retried = client.post(f"/owner/tasks/{task_id}/retry", json={"reason": "Fix scope issue"}).json()
    assert retried["status"] == "pending"
    assert retried["retry_count"] == 1


# ---------------------------------------------------------------------------
# Task Write-Scope Lock Prevention Tests
# ---------------------------------------------------------------------------

def _make_dummy_project_sub_epic(client: TestClient) -> int:
    project = client.post("/projects", json={
        "name": "Lock Test Project",
        "engine": "undecided",
        "repo_url": "dummy_repo",
        "workspace_path": "dummy_workspace",
        "base_branch": "main",
    }).json()
    epic = client.post(f"/projects/{project['id']}/epics", json={
        "name": "Lock Test Epic",
        "goal": "Test scope locking"
    }).json()
    sub_epic = client.post(f"/epics/{epic['id']}/sub-epics", json={
        "name": "Lock Test Sub-Epic",
        "goal": "Test scope locking"
    }).json()
    return sub_epic["id"]


def test_lock_prevention_disjoint_scopes(client: TestClient) -> None:
    # A. Two tasks with disjoint write scopes can be leased by different workers.
    sub_epic_id = _make_dummy_project_sub_epic(client)

    task1 = client.post(f"/sub-epics/{sub_epic_id}/tasks", json={
        "role": "code_worker",
        "goal": "Disjoint test 1",
        "requirements": ["X"],
        "success_criteria": ["Y"],
        "estimated_minutes": 15,
        "branch": "worker/disjoint-1",
        "write_scope": ["src/player.py"],
    }).json()

    task2 = client.post(f"/sub-epics/{sub_epic_id}/tasks", json={
        "role": "code_worker",
        "goal": "Disjoint test 2",
        "requirements": ["X"],
        "success_criteria": ["Y"],
        "estimated_minutes": 15,
        "branch": "worker/disjoint-2",
        "write_scope": ["src/enemy.py"],
    }).json()

    # Lease task 1 -> should succeed
    leased1 = client.post("/workers/worker-1/lease", json={"role": "code_worker", "lease_minutes": 30}).json()
    assert leased1["id"] == task1["id"]

    # Lease task 2 -> should succeed because scopes are disjoint
    leased2 = client.post("/workers/worker-2/lease", json={"role": "code_worker", "lease_minutes": 30}).json()
    assert leased2["id"] == task2["id"]


def test_lock_prevention_overlapping_lease_skipped(client: TestClient) -> None:
    # B. Second task with same write scope is not leased while first task lock is active.
    sub_epic_id = _make_dummy_project_sub_epic(client)

    task1 = client.post(f"/sub-epics/{sub_epic_id}/tasks", json={
        "role": "code_worker",
        "goal": "Overlap test 1",
        "requirements": ["X"],
        "success_criteria": ["Y"],
        "estimated_minutes": 15,
        "branch": "worker/overlap-1",
        "write_scope": ["src/player.py"],
    }).json()

    task2 = client.post(f"/sub-epics/{sub_epic_id}/tasks", json={
        "role": "code_worker",
        "goal": "Overlap test 2",
        "requirements": ["X"],
        "success_criteria": ["Y"],
        "estimated_minutes": 15,
        "branch": "worker/overlap-2",
        "write_scope": ["src/player.py"],
    }).json()

    # Lease first -> should lease task 1
    leased1 = client.post("/workers/worker-1/lease", json={"role": "code_worker", "lease_minutes": 30}).json()
    assert leased1["id"] == task1["id"]

    # Lease second -> should return HTTP 204 (no task available) because task 2 conflicts with task 1
    leased2_res = client.post("/workers/worker-2/lease", json={"role": "code_worker", "lease_minutes": 30})
    assert leased2_res.status_code == 204


def test_lock_prevention_claim_rejected(client: TestClient) -> None:
    # C. claim_task rejects a conflicting task while another active task holds the same write scope.
    sub_epic_id = _make_dummy_project_sub_epic(client)

    task1 = client.post(f"/sub-epics/{sub_epic_id}/tasks", json={
        "role": "code_worker",
        "goal": "Claim test 1",
        "requirements": ["X"],
        "success_criteria": ["Y"],
        "estimated_minutes": 15,
        "branch": "worker/claim-1",
        "write_scope": ["src/player.py"],
    }).json()

    task2 = client.post(f"/sub-epics/{sub_epic_id}/tasks", json={
        "role": "code_worker",
        "goal": "Claim test 2",
        "requirements": ["X"],
        "success_criteria": ["Y"],
        "estimated_minutes": 15,
        "branch": "worker/claim-2",
        "write_scope": ["src/player.py"],
    }).json()

    # Lease task 1 -> holds lock
    leased1 = client.post("/workers/worker-1/lease", json={"role": "code_worker", "lease_minutes": 30}).json()
    assert leased1["id"] == task1["id"]

    # Attempt to claim task 2 -> should be rejected with 409 Conflict
    claim_res = client.post(f"/workers/worker-2/tasks/{task2['id']}/claim", json={"lease_minutes": 30})
    assert claim_res.status_code == 409
    assert "lock conflict" in claim_res.json()["detail"]


def test_lock_prevention_released_flow(client: TestClient) -> None:
    # D. Completing/releasing the first task releases its locks, then the second task can be leased/claimed.
    sub_epic_id = _make_dummy_project_sub_epic(client)

    task1 = client.post(f"/sub-epics/{sub_epic_id}/tasks", json={
        "role": "code_worker",
        "goal": "Release flow test 1",
        "requirements": ["X"],
        "success_criteria": ["Y"],
        "estimated_minutes": 15,
        "branch": "worker/release-flow-1",
        "write_scope": ["src/player.py"],
    }).json()

    task2 = client.post(f"/sub-epics/{sub_epic_id}/tasks", json={
        "role": "code_worker",
        "goal": "Release flow test 2",
        "requirements": ["X"],
        "success_criteria": ["Y"],
        "estimated_minutes": 15,
        "branch": "worker/release-flow-2",
        "write_scope": ["src/player.py"],
    }).json()

    # Lease task 1 -> active lock
    leased1 = client.post("/workers/worker-1/lease", json={"role": "code_worker", "lease_minutes": 30}).json()
    assert leased1["id"] == task1["id"]

    # Report completion (releases locks)
    report = _report_payload("success")
    report["changed_files"] = ["src/player.py"]
    completed = client.post(f"/workers/worker-1/tasks/{task1['id']}/report", json=report).json()
    assert completed["status"] == "success"

    # Now task 2 should be leasable
    leased2 = client.post("/workers/worker-2/lease", json={"role": "code_worker", "lease_minutes": 30}).json()
    assert leased2["id"] == task2["id"]


def test_lock_prevention_no_write_scope(client: TestClient) -> None:
    # E. Task with no write_scope leases normally.
    sub_epic_id = _make_dummy_project_sub_epic(client)

    task1 = client.post(f"/sub-epics/{sub_epic_id}/tasks", json={
        "role": "code_worker",
        "goal": "No scope lease 1",
        "requirements": ["X"],
        "success_criteria": ["Y"],
        "estimated_minutes": 15,
        "branch": "worker/no-scope-lease-1",
    }).json()

    task2 = client.post(f"/sub-epics/{sub_epic_id}/tasks", json={
        "role": "code_worker",
        "goal": "No scope lease 2",
        "requirements": ["X"],
        "success_criteria": ["Y"],
        "estimated_minutes": 15,
        "branch": "worker/no-scope-lease-2",
    }).json()

    # Lease both successfully
    leased1 = client.post("/workers/worker-1/lease", json={"role": "code_worker", "lease_minutes": 30}).json()
    assert leased1["id"] == task1["id"]

    leased2 = client.post("/workers/worker-2/lease", json={"role": "code_worker", "lease_minutes": 30}).json()
    assert leased2["id"] == task2["id"]


def test_lock_prevention_glob_conflict(client: TestClient) -> None:
    # F. Glob conflict works for src/** vs src/player.py.
    sub_epic_id = _make_dummy_project_sub_epic(client)

    task1 = client.post(f"/sub-epics/{sub_epic_id}/tasks", json={
        "role": "code_worker",
        "goal": "Glob lock test 1",
        "requirements": ["X"],
        "success_criteria": ["Y"],
        "estimated_minutes": 15,
        "branch": "worker/glob-lock-1",
        "write_scope": ["src/**"],
    }).json()

    task2 = client.post(f"/sub-epics/{sub_epic_id}/tasks", json={
        "role": "code_worker",
        "goal": "Glob lock test 2",
        "requirements": ["X"],
        "success_criteria": ["Y"],
        "estimated_minutes": 15,
        "branch": "worker/glob-lock-2",
        "write_scope": ["src/player.py"],
    }).json()

    # Lease task 1 (lock is src/**)
    leased1 = client.post("/workers/worker-1/lease", json={"role": "code_worker", "lease_minutes": 30}).json()
    assert leased1["id"] == task1["id"]

    # Lease task 2 -> fails with HTTP 204 (no task available) because src/player.py conflicts with src/**
    leased2_res = client.post("/workers/worker-2/lease", json={"role": "code_worker", "lease_minutes": 30})
    assert leased2_res.status_code == 204


# ---------------------------------------------------------------------------
# Stale Task Lock Prevention Tests
# ---------------------------------------------------------------------------

def test_lock_prevention_non_expired_blocks(client: TestClient) -> None:
    # A. Active non-expired lock still blocks conflicting lease/claim.
    sub_epic_id = _make_dummy_project_sub_epic(client)

    task1 = client.post(f"/sub-epics/{sub_epic_id}/tasks", json={
        "role": "code_worker",
        "goal": "Non-expired test 1",
        "requirements": ["X"],
        "success_criteria": ["Y"],
        "estimated_minutes": 15,
        "branch": "worker/non-expired-1",
        "write_scope": ["src/player.py"],
    }).json()

    task2 = client.post(f"/sub-epics/{sub_epic_id}/tasks", json={
        "role": "code_worker",
        "goal": "Non-expired test 2",
        "requirements": ["X"],
        "success_criteria": ["Y"],
        "estimated_minutes": 15,
        "branch": "worker/non-expired-2",
        "write_scope": ["src/player.py"],
    }).json()

    # Lease task 1 (lock created with expires_at far in the future)
    leased1 = client.post("/workers/worker-1/lease", json={"role": "code_worker", "lease_minutes": 30}).json()
    assert leased1["id"] == task1["id"]

    # Try claiming task 2 -> should fail because lock is not expired
    claim_res = client.post(f"/workers/worker-2/tasks/{task2['id']}/claim", json={"lease_minutes": 30})
    assert claim_res.status_code == 409


def test_lock_prevention_expired_does_not_block(client: TestClient) -> None:
    # B. Expired active lock does not block conflicting lease/claim.
    sub_epic_id = _make_dummy_project_sub_epic(client)

    task1 = client.post(f"/sub-epics/{sub_epic_id}/tasks", json={
        "role": "code_worker",
        "goal": "Expired test 1",
        "requirements": ["X"],
        "success_criteria": ["Y"],
        "estimated_minutes": 15,
        "branch": "worker/expired-1",
        "write_scope": ["src/player.py"],
    }).json()

    task2 = client.post(f"/sub-epics/{sub_epic_id}/tasks", json={
        "role": "code_worker",
        "goal": "Expired test 2",
        "requirements": ["X"],
        "success_criteria": ["Y"],
        "estimated_minutes": 15,
        "branch": "worker/expired-2",
        "write_scope": ["src/player.py"],
    }).json()

    # Lease task 1
    leased1 = client.post("/workers/worker-1/lease", json={"role": "code_worker", "lease_minutes": 30}).json()
    assert leased1["id"] == task1["id"]

    # Manually set task 1's lock to be expired in the past
    repo = app.dependency_overrides[get_repo]()
    repo.conn.execute(
        "UPDATE task_locks SET expires_at = '2020-01-01T00:00:00' WHERE task_id = ?",
        (task1["id"],)
    )
    repo.conn.commit()

    # Now task 2 should be leasable because task 1's lock is expired
    leased2 = client.post("/workers/worker-2/lease", json={"role": "code_worker", "lease_minutes": 30}).json()
    assert leased2["id"] == task2["id"]


def test_lock_prevention_expired_status_updated(client: TestClient) -> None:
    # C. Expired active lock is marked expired with released_at set during lease/claim cleanup.
    sub_epic_id = _make_dummy_project_sub_epic(client)

    task1 = client.post(f"/sub-epics/{sub_epic_id}/tasks", json={
        "role": "code_worker",
        "goal": "Status expired test 1",
        "requirements": ["X"],
        "success_criteria": ["Y"],
        "estimated_minutes": 15,
        "branch": "worker/status-expired-1",
        "write_scope": ["src/player.py"],
    }).json()

    # Lease task 1
    leased1 = client.post("/workers/worker-1/lease", json={"role": "code_worker", "lease_minutes": 30}).json()
    assert leased1["id"] == task1["id"]

    # Manually set task 1's lock to be expired in the past
    repo = app.dependency_overrides[get_repo]()
    repo.conn.execute(
        "UPDATE task_locks SET expires_at = '2020-01-01T00:00:00' WHERE task_id = ?",
        (task1["id"],)
    )
    repo.conn.commit()

    # Call lease again to trigger cleanup
    client.post("/workers/worker-2/lease", json={"role": "code_worker", "lease_minutes": 30})

    # Verify task 1's lock in the DB is updated to status='expired' and released_at is set
    lock = repo.conn.execute("SELECT * FROM task_locks WHERE task_id = ?", (task1["id"],)).fetchone()
    assert lock["status"] == "expired"
    assert lock["released_at"] is not None


def test_lock_prevention_lease_has_expires_at(client: TestClient) -> None:
    # D. Lock acquired on a normal lease has expires_at matching the task lease deadline if available.
    sub_epic_id = _make_dummy_project_sub_epic(client)

    task = client.post(f"/sub-epics/{sub_epic_id}/tasks", json={
        "role": "code_worker",
        "goal": "Expires matching test",
        "requirements": ["X"],
        "success_criteria": ["Y"],
        "estimated_minutes": 15,
        "branch": "worker/expires-matching",
        "write_scope": ["src/player.py"],
    }).json()

    leased = client.post("/workers/worker-1/lease", json={"role": "code_worker", "lease_minutes": 30}).json()
    assert leased["id"] == task["id"]

    repo = app.dependency_overrides[get_repo]()
    lock = repo.conn.execute("SELECT * FROM task_locks WHERE task_id = ?", (task["id"],)).fetchone()
    db_task = repo.conn.execute("SELECT * FROM tasks WHERE id = ?", (task["id"],)).fetchone()
    
    assert lock["expires_at"] == db_task["leased_until"]
    assert lock["expires_at"] is not None


def test_lock_prevention_null_expires_at_blocks(client: TestClient) -> None:
    # E. Lock with expires_at = NULL still blocks until explicitly released.
    sub_epic_id = _make_dummy_project_sub_epic(client)

    task1 = client.post(f"/sub-epics/{sub_epic_id}/tasks", json={
        "role": "code_worker",
        "goal": "Null expires test 1",
        "requirements": ["X"],
        "success_criteria": ["Y"],
        "estimated_minutes": 15,
        "branch": "worker/null-expires-1",
        "write_scope": ["src/player.py"],
    }).json()

    task2 = client.post(f"/sub-epics/{sub_epic_id}/tasks", json={
        "role": "code_worker",
        "goal": "Null expires test 2",
        "requirements": ["X"],
        "success_criteria": ["Y"],
        "estimated_minutes": 15,
        "branch": "worker/null-expires-2",
        "write_scope": ["src/player.py"],
    }).json()

    # Lease task 1
    leased1 = client.post("/workers/worker-1/lease", json={"role": "code_worker", "lease_minutes": 30}).json()
    assert leased1["id"] == task1["id"]

    # Manually set task 1's lock expires_at to NULL
    repo = app.dependency_overrides[get_repo]()
    repo.conn.execute(
        "UPDATE task_locks SET expires_at = NULL WHERE task_id = ?",
        (task1["id"],)
    )
    repo.conn.commit()

    # Try claiming/leasing task 2 -> should still fail because expires_at = NULL means it never expires naturally
    leased2_res = client.post("/workers/worker-2/lease", json={"role": "code_worker", "lease_minutes": 30})
    assert leased2_res.status_code == 204

