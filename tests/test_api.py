from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main as main_module
from app.config import Settings
from app.db import SCHEMA
from app.main import app, get_repo, get_settings
from app.repository import Repository


@pytest.fixture()
def client() -> Iterator[TestClient]:
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
            owner_command="",
            owner_timeout_seconds=900,
            owner_runs_dir=Path("./owner-runs-test"),
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


def test_api_token_required_when_configured(client: TestClient) -> None:
    original_settings = main_module.settings
    main_module.settings = Settings(
        db_path=Path(":memory:"),
        host="127.0.0.1",
        port=8080,
        default_task_minutes=15,
        owner_recall_minutes=30,
        api_token="secret-token",
        owner_command="",
        owner_timeout_seconds=900,
        owner_runs_dir=Path("./owner-runs-test"),
    )
    try:
        assert client.get("/health").status_code == 200
        unauthorized = client.get("/tasks")
        assert unauthorized.status_code == 401
        authorized = client.get("/tasks", headers={"Authorization": "Bearer secret-token"})
        assert authorized.status_code == 200
    finally:
        main_module.settings = original_settings


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

    runs = client.get("/owner/runs")
    assert runs.status_code == 200
    assert runs.json()[0]["id"] == body["id"]
