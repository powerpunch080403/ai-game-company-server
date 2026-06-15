from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_repo, not_found
from app.repository import Repository
from app.schemas import MachineHeartbeat, MachineUpsert, WorkerHeartbeat, WorkerUpsert


router = APIRouter()


@router.put("/registry/machines/{machine_id}")
def upsert_machine(machine_id: str, payload: MachineUpsert, repo: Repository = Depends(get_repo)) -> dict:
    if payload.machine_id != machine_id:
        raise HTTPException(status_code=400, detail="machine_id must match path machine_id")
    return repo.upsert_machine(payload)


@router.get("/registry/machines")
def list_machines(
    kind: str | None = Query(default=None),
    status: str | None = Query(default=None),
    repo: Repository = Depends(get_repo),
) -> list[dict]:
    return repo.list_machines(kind=kind, status=status)


@router.get("/registry/machines/{machine_id}")
def get_machine(machine_id: str, repo: Repository = Depends(get_repo)) -> dict:
    try:
        return repo.get_machine(machine_id)
    except KeyError as exc:
        raise not_found(exc) from exc


@router.post("/registry/machines/{machine_id}/heartbeat")
def heartbeat_machine(machine_id: str, payload: MachineHeartbeat, repo: Repository = Depends(get_repo)) -> dict:
    try:
        return repo.heartbeat_machine(machine_id, payload)
    except KeyError as exc:
        raise not_found(exc) from exc


@router.put("/registry/workers/{worker_id}")
def upsert_worker(worker_id: str, payload: WorkerUpsert, repo: Repository = Depends(get_repo)) -> dict:
    if payload.worker_id != worker_id:
        raise HTTPException(status_code=400, detail="worker_id must match path worker_id")
    return repo.upsert_worker(payload)


@router.get("/registry/workers")
def list_workers(
    role: str | None = Query(default=None),
    status: str | None = Query(default=None),
    machine_id: str | None = Query(default=None),
    repo: Repository = Depends(get_repo),
) -> list[dict]:
    return repo.list_workers(role=role, status=status, machine_id=machine_id)


@router.get("/registry/workers/{worker_id}")
def get_worker(worker_id: str, repo: Repository = Depends(get_repo)) -> dict:
    try:
        return repo.get_worker(worker_id)
    except KeyError as exc:
        raise not_found(exc) from exc


@router.post("/registry/workers/{worker_id}/heartbeat")
def heartbeat_worker(worker_id: str, payload: WorkerHeartbeat, repo: Repository = Depends(get_repo)) -> dict:
    return repo.heartbeat_worker(worker_id, payload)
