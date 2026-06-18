from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_repo, not_found
from app.repository import Repository
from app.schemas import TaskCreate, WorkerLeaseRequest, WorkerReportCreate, WorkerTaskClaimRequest, TaskThreadReferenceUpsert, TaskThreadReferenceRead


router = APIRouter()


@router.post("/sub-epics/{sub_epic_id}/tasks")
def create_sub_epic_task(sub_epic_id: int, payload: TaskCreate, repo: Repository = Depends(get_repo)) -> dict:
    try:
        return repo.create_task(sub_epic_id, payload)
    except KeyError as exc:
        raise not_found(exc) from exc


@router.post("/tasks")
def create_task(payload: TaskCreate, repo: Repository = Depends(get_repo)) -> dict:
    return repo.create_task(None, payload)


@router.get("/tasks")
def list_tasks(
    status: str | None = Query(default=None),
    role: str | None = Query(default=None),
    repo: Repository = Depends(get_repo),
) -> list[dict]:
    return repo.list_tasks(status=status, role=role)


@router.get("/tasks/{task_id}")
def get_task(task_id: int, repo: Repository = Depends(get_repo)) -> dict:
    try:
        return repo.get_task(task_id)
    except KeyError as exc:
        raise not_found(exc) from exc


@router.get("/tasks/{task_id}/package")
def get_task_package(task_id: int, repo: Repository = Depends(get_repo)) -> dict:
    try:
        return repo.get_task_package(task_id)
    except KeyError as exc:
        raise not_found(exc) from exc


@router.get("/tasks/{task_id}/reports")
def list_task_reports(task_id: int, repo: Repository = Depends(get_repo)) -> list[dict]:
    try:
        return repo.list_task_reports(task_id)
    except KeyError as exc:
        raise not_found(exc) from exc


@router.get("/tasks/{task_id}/events")
def list_task_events(task_id: int, repo: Repository = Depends(get_repo)) -> list[dict]:
    try:
        return repo.list_task_events(task_id)
    except KeyError as exc:
        raise not_found(exc) from exc


@router.post("/workers/{worker_id}/lease")
def lease_task(worker_id: str, payload: WorkerLeaseRequest, repo: Repository = Depends(get_repo)) -> dict:
    task = repo.lease_next_task(
        worker_id,
        payload.role,
        payload.lease_minutes,
        requires_project_config=payload.requires_project_config,
    )
    if task is None:
        raise HTTPException(status_code=204, detail="no task available")
    return task


@router.post("/workers/{worker_id}/tasks/{task_id}/claim")
def claim_task(
    worker_id: str,
    task_id: int,
    payload: WorkerTaskClaimRequest,
    repo: Repository = Depends(get_repo),
) -> dict:
    try:
        return repo.claim_task(task_id, worker_id, payload.lease_minutes)
    except KeyError as exc:
        raise not_found(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/workers/{worker_id}/tasks/{task_id}/report")
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
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.put("/tasks/{task_id}/thread-reference", response_model=TaskThreadReferenceRead)
def upsert_task_thread_reference(
    task_id: int,
    payload: TaskThreadReferenceUpsert,
    repo: Repository = Depends(get_repo),
) -> dict:
    try:
        return repo.upsert_task_thread_reference(task_id, payload)
    except KeyError as exc:
        raise not_found(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/tasks/{task_id}/thread-reference", response_model=TaskThreadReferenceRead)
def get_task_thread_reference(
    task_id: int,
    repo: Repository = Depends(get_repo),
) -> dict:
    try:
        ref = repo.get_task_thread_reference(task_id)
        if ref is None:
            raise HTTPException(status_code=404, detail="thread_reference_not_found")
        return ref
    except KeyError as exc:
        raise not_found(exc) from exc
