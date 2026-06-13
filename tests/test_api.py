from __future__ import annotations

import sqlite3
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main as main_module
from app.config import Settings
from app.db import SCHEMA
from app.git_workspace import git_executable, prepare_branch, run_git
from app.main import app, get_repo, get_settings
from app.repository import Repository
from app.workspace_worker import commit_changes, push_branch


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

    reports = client.get(f"/tasks/{leased_task['id']}/reports")
    assert reports.status_code == 200
    assert reports.json()[0]["summary"] == "Boss FSM implemented."
    assert reports.json()[0]["files_changed"] == ["Assets/Scripts/Boss/BossFsm.cs"]

    events = client.get(f"/tasks/{leased_task['id']}/events")
    assert events.status_code == 200
    assert [event["event_type"] for event in events.json()] == ["created", "leased", "reported"]


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
