from __future__ import annotations

import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from tests.test_api import client

def create_project_task(client: TestClient, project_name: str, branch: str) -> tuple[dict, dict]:
    proj = client.post("/projects", json={"name": project_name, "engine": "undecided"}).json()
    epic = client.post(f"/projects/{proj['id']}/epics", json={"name": "Artifacts", "goal": ""}).json()
    sub_epic = client.post(f"/epics/{epic['id']}/sub-epics", json={"name": "Evidence", "goal": ""}).json()
    task = client.post(f"/sub-epics/{sub_epic['id']}/tasks", json={
        "role": "code_worker",
        "goal": "Artifact task",
        "requirements": ["R"],
        "success_criteria": ["S"],
        "branch": branch,
    }).json()
    return proj, task


def test_streaming_upload_success(client: TestClient) -> None:
    # 1. Create Project & Task
    proj, task = create_project_task(client, "P1", "worker/b1")
    
    # 2. Register Artifact
    client.post("/artifacts", json={
        "artifact_id": "test-stream-ok",
        "project_id": proj["id"],
        "task_id": task["id"],
        "artifact_type": "log",
        "filename": "test.log",
        "content_type": "text/plain",
    })
    
    # 3. Content Streaming Upload (Under 1024 bytes limit)
    payload = b"A" * 500
    res = client.put(
        "/artifacts/test-stream-ok/content",
        params={"filename": "test.log", "content_type": "text/plain"},
        content=payload
    )
    assert res.status_code == 200
    assert res.json()["size_bytes"] == 500
    
    # 4. Download content to verify
    downloaded = client.get("/artifacts/test-stream-ok/content")
    assert downloaded.status_code == 200
    assert downloaded.content == payload

def test_streaming_upload_exceeds_limit_and_cleans_up(client: TestClient) -> None:
    # 1. Create Project & Task
    proj, task = create_project_task(client, "P2", "worker/b2")
    
    # 2. Register Artifact
    client.post("/artifacts", json={
        "artifact_id": "test-stream-too-large",
        "project_id": proj["id"],
        "task_id": task["id"],
        "artifact_type": "log",
        "filename": "large.log",
        "content_type": "text/plain",
    })
    
    # 3. Upload over 1024 bytes (2000 bytes)
    payload = b"B" * 2000
    res = client.put(
        "/artifacts/test-stream-too-large/content",
        params={"filename": "large.log", "content_type": "text/plain"},
        content=payload
    )
    # Assert HTTP 413
    assert res.status_code == 413
    
    # 4. Check that download content is unavailable (as it was deleted)
    downloaded = client.get("/artifacts/test-stream-too-large/content")
    assert downloaded.status_code == 404


def test_artifact_id_rejects_path_traversal(client: TestClient) -> None:
    proj = client.post("/projects", json={"name": "P3", "engine": "undecided"}).json()

    res = client.post("/artifacts", json={
        "artifact_id": "../escape",
        "project_id": proj["id"],
        "artifact_type": "log",
        "filename": "escape.log",
    })

    assert res.status_code == 422


def test_artifact_task_must_belong_to_project(client: TestClient) -> None:
    proj_a = client.post("/projects", json={"name": "P4A", "engine": "undecided"}).json()
    proj_b = client.post("/projects", json={"name": "P4B", "engine": "undecided"}).json()
    epic = client.post(f"/projects/{proj_a['id']}/epics", json={"name": "E", "goal": ""}).json()
    sub_epic = client.post(f"/epics/{epic['id']}/sub-epics", json={"name": "SE", "goal": ""}).json()
    task = client.post(f"/sub-epics/{sub_epic['id']}/tasks", json={
        "role": "code_worker",
        "goal": "Task",
        "requirements": ["R"],
        "success_criteria": ["S"],
        "branch": "worker/artifact-project-match",
    }).json()

    res = client.post("/artifacts", json={
        "artifact_id": "wrong-project-task",
        "project_id": proj_b["id"],
        "task_id": task["id"],
        "artifact_type": "log",
        "filename": "wrong.log",
    })

    assert res.status_code == 409
    assert "task_id must belong" in res.json()["detail"]
