from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_repo
from app.repository import Repository
from app.schemas import MemoryCreate


router = APIRouter()


@router.post("/memory")
def upsert_memory(payload: MemoryCreate, repo: Repository = Depends(get_repo)) -> dict:
    return repo.upsert_memory(payload)


@router.get("/memory")
def search_memory(
    type: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    q: str | None = Query(default=None),
    repo: Repository = Depends(get_repo),
) -> list[dict]:
    return repo.search_memory(type, tag, q)
