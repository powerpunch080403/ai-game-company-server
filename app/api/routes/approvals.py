from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_repo, not_found
from app.repository import Repository
from app.schemas import ApprovalCreate, ApprovalDecision


router = APIRouter()


@router.post("/approvals")
def create_approval(payload: ApprovalCreate, repo: Repository = Depends(get_repo)) -> dict:
    try:
        return repo.create_approval(payload)
    except KeyError as exc:
        raise not_found(exc) from exc


@router.get("/approvals")
def list_approvals(
    status: str | None = Query(default=None),
    project_id: int | None = Query(default=None),
    target_type: str | None = Query(default=None),
    repo: Repository = Depends(get_repo),
) -> list[dict]:
    return repo.list_approvals(status=status, project_id=project_id, target_type=target_type)


@router.get("/approvals/{approval_id}")
def get_approval(approval_id: str, repo: Repository = Depends(get_repo)) -> dict:
    try:
        return repo.get_approval(approval_id)
    except KeyError as exc:
        raise not_found(exc) from exc


@router.post("/approvals/{approval_id}/decision")
def decide_approval(approval_id: str, payload: ApprovalDecision, repo: Repository = Depends(get_repo)) -> dict:
    try:
        return repo.decide_approval(approval_id, payload)
    except KeyError as exc:
        raise not_found(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
