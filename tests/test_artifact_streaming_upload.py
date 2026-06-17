from __future__ import annotations

import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from tests.test_api import client

def test_streaming_upload_success(client: TestClient) -> None:
    # 1. Create Project & Task
    proj = client.post("/projects", json={"name": "P1", "engine": "undecided"}).json()
    task = client.post("/tasks", json={
        "role": "code_worker",
        "goal": "G1",
        "requirements": ["R1"],
        "success_criteria": ["S1"],
        "branch": "worker/b1",
    }).json()
    
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
    proj = client.post("/projects", json={"name": "P2", "engine": "undecided"}).json()
    task = client.post("/tasks", json={
        "role": "code_worker",
        "goal": "G2",
        "requirements": ["R2"],
        "success_criteria": ["S2"],
        "branch": "worker/b2",
    }).json()
    
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
