from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Query

from app.config import Settings, load_settings
from app.db import connect, init_db
from app.repository import Repository
from app.schemas import (
    EpicCreate,
    MemoryCreate,
    ProjectCreate,
    SubEpicCreate,
    TaskCreate,
    WorkerLeaseRequest,
    WorkerReportCreate,
)

settings = load_settings()
init_db(settings.db_path)
connection = connect(settings.db_path)

app = FastAPI(
    title="AI Game Company Server",
    version="0.1.0",
    description="Owner, memory, task queue, and worker reporting API for game development automation.",
)


def get_settings() -> Settings:
    return settings


def get_repo() -> Repository:
    return Repository(connection)


def not_found(error: KeyError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(error))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/projects")
def create_project(payload: ProjectCreate, repo: Repository = Depends(get_repo)) -> dict:
    return repo.create_project(payload)


@app.post("/projects/{project_id}/epics")
def create_epic(project_id: int, payload: EpicCreate, repo: Repository = Depends(get_repo)) -> dict:
    try:
        return repo.create_epic(project_id, payload)
    except KeyError as exc:
        raise not_found(exc) from exc


@app.post("/epics/{epic_id}/sub-epics")
def create_sub_epic(epic_id: int, payload: SubEpicCreate, repo: Repository = Depends(get_repo)) -> dict:
    try:
        return repo.create_sub_epic(epic_id, payload)
    except KeyError as exc:
        raise not_found(exc) from exc


@app.post("/memory")
def upsert_memory(payload: MemoryCreate, repo: Repository = Depends(get_repo)) -> dict:
    return repo.upsert_memory(payload)


@app.get("/memory")
def search_memory(
    type: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    q: str | None = Query(default=None),
    repo: Repository = Depends(get_repo),
) -> list[dict]:
    return repo.search_memory(type, tag, q)


@app.post("/sub-epics/{sub_epic_id}/tasks")
def create_sub_epic_task(sub_epic_id: int, payload: TaskCreate, repo: Repository = Depends(get_repo)) -> dict:
    try:
        return repo.create_task(sub_epic_id, payload)
    except KeyError as exc:
        raise not_found(exc) from exc


@app.post("/tasks")
def create_task(payload: TaskCreate, repo: Repository = Depends(get_repo)) -> dict:
    return repo.create_task(None, payload)


@app.get("/tasks")
def list_tasks(
    status: str | None = Query(default=None),
    role: str | None = Query(default=None),
    repo: Repository = Depends(get_repo),
) -> list[dict]:
    return repo.list_tasks(status=status, role=role)


@app.get("/tasks/{task_id}")
def get_task(task_id: int, repo: Repository = Depends(get_repo)) -> dict:
    try:
        return repo.get_task(task_id)
    except KeyError as exc:
        raise not_found(exc) from exc


@app.post("/workers/{worker_id}/lease")
def lease_task(worker_id: str, payload: WorkerLeaseRequest, repo: Repository = Depends(get_repo)) -> dict:
    task = repo.lease_next_task(worker_id, payload.role, payload.lease_minutes)
    if task is None:
        raise HTTPException(status_code=204, detail="no task available")
    return task


@app.post("/workers/{worker_id}/tasks/{task_id}/report")
def report_task(
    worker_id: str,
    task_id: int,
    payload: WorkerReportCreate,
    repo: Repository = Depends(get_repo),
) -> dict:
    try:
        return repo.complete_task(task_id, worker_id, payload)
    except KeyError as exc:
        raise not_found(exc) from exc


@app.get("/owner/dashboard")
def owner_dashboard(
    repo: Repository = Depends(get_repo),
    config: Settings = Depends(get_settings),
) -> dict:
    return repo.dashboard(config.owner_recall_minutes)
