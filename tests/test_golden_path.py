from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.db import SCHEMA
from app.main import app, get_repo, get_settings
from app.repository import Repository


@pytest.fixture()
def client(tmp_path: Path) -> Iterator[TestClient]:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)

    def repo_override() -> Repository:
        return Repository(conn)

    def settings_override() -> Settings:
        return Settings(
            db_path=Path(":memory:"),
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
            owner_runs_dir=tmp_path / "owner-runs",
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


def test_golden_path_api_evidence_loop(client: TestClient, tmp_path: Path) -> None:
    machine = client.put(
        "/registry/machines/test_runner_12400_3060",
        json={
            "machine_id": "test_runner_12400_3060",
            "display_name": "Test Runner",
            "kind": "test_runner",
            "host_hint": "planned",
            "os": "linux",
            "workspace_root": str(tmp_path / "workspaces"),
            "artifact_root": str(tmp_path / "artifacts"),
            "status": "online",
            "capabilities": ["pygame", "screenshots", "logs"],
            "notes": "Golden Path test runner registry record.",
        },
    )
    assert machine.status_code == 200

    project = client.post(
        "/projects",
        json={
            "name": "AI Survival Mini",
            "description": "Pipeline validation game.",
            "engine": "pygame",
            "repo_url": str(tmp_path / "ai-survival-mini.git"),
            "workspace_path": str(tmp_path / "ai-survival-mini-workspace"),
            "base_branch": "main",
        },
    ).json()
    epic = client.post(
        f"/projects/{project['id']}/epics",
        json={"name": "Prototype Loop", "goal": "Create a tiny playable survival loop."},
    ).json()
    sub_epic = client.post(
        f"/epics/{epic['id']}/sub-epics",
        json={"name": "Player Movement", "goal": "Add the first controllable player slice."},
    ).json()
    task = client.post(
        f"/sub-epics/{sub_epic['id']}/tasks",
        json={
            "role": "code_worker",
            "goal": "Add WASD player movement stub",
            "requirements": ["Create a small pygame entry point", "Keep the change isolated"],
            "success_criteria": ["Runtime smoke command succeeds", "Test Runner log artifact exists"],
            "estimated_minutes": 15,
            "memory_refs": [],
            "branch": "worker/player-movement-stub",
        },
    ).json()

    leased = client.post(
        "/workers/workspace-1/lease",
        json={"role": "code_worker", "lease_minutes": 30, "requires_project_config": True},
    )
    assert leased.status_code == 200
    assert leased.json()["id"] == task["id"]

    package = client.get(f"/tasks/{task['id']}/package").json()
    assert package["project"]["id"] == project["id"]
    assert package["task"]["branch"] == "worker/player-movement-stub"

    report = {
        "status": "success",
        "estimated_minutes": 15,
        "actual_minutes": 12,
        "productive_minutes": 11,
        "error_minutes": 1,
        "retry_count": 0,
        "files_changed": ["src/main.py", ".game-company/artifacts/task-1/run-smoke/test-runner-report.json"],
        "tests": ["python -m pytest", "test-runner-report: .game-company/artifacts/task-1/run-smoke/test-runner-report.json"],
        "summary": "Player movement stub and smoke evidence are ready for Owner review.",
        "issues": "",
    }
    completed = client.post(f"/workers/workspace-1/tasks/{task['id']}/report", json=report)
    assert completed.status_code == 200
    assert completed.json()["status"] == "success"

    artifact = client.post(
        "/artifacts",
        json={
            "artifact_id": "golden-path-log-1",
            "project_id": project["id"],
            "task_id": task["id"],
            "worker_id": "test-runner-1",
            "machine_id": "test_runner_12400_3060",
            "artifact_type": "test_report",
            "filename": "test-runner-report.json",
            "content_type": "application/json",
            "summary": "Golden Path smoke report.",
            "tags": ["golden_path", "test_runner", "smoke"],
            "important": True,
        },
    )
    assert artifact.status_code == 200
    uploaded = client.put(
        "/artifacts/golden-path-log-1/content",
        params={"filename": "test-runner-report.json", "content_type": "application/json"},
        content=b'{"status":"success"}\n',
    )
    assert uploaded.status_code == 200

    candidates = client.get("/owner/merge-candidates").json()
    assert len(candidates) == 1
    assert candidates[0]["task"]["id"] == task["id"]
    assert candidates[0]["review"]["eligible"] is True
    assert candidates[0]["review"]["warnings"] == []

    artifacts = client.get(
        "/artifacts",
        params={"project_id": project["id"], "artifact_type": "test_report", "important": True},
    ).json()
    assert [item["artifact_id"] for item in artifacts] == ["golden-path-log-1"]
