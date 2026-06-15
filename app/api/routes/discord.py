from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_repo, not_found
from app.repository import Repository
from app.schemas import DiscordMappingArchive, DiscordMappingUpsert


router = APIRouter()


@router.post("/discord/mappings")
def create_discord_mapping(payload: DiscordMappingUpsert, repo: Repository = Depends(get_repo)) -> dict:
    try:
        return repo.upsert_discord_mapping(payload)
    except KeyError as exc:
        raise not_found(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.put("/discord/mappings/{mapping_id}")
def upsert_discord_mapping(
    mapping_id: str,
    payload: DiscordMappingUpsert,
    repo: Repository = Depends(get_repo),
) -> dict:
    if payload.mapping_id is not None and payload.mapping_id != mapping_id:
        raise HTTPException(status_code=400, detail="mapping_id must match path mapping_id")
    try:
        return repo.upsert_discord_mapping(payload, mapping_id=mapping_id)
    except KeyError as exc:
        raise not_found(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/discord/mappings")
def list_discord_mappings(
    project_id: int | None = Query(default=None),
    conversation_kind: str | None = Query(default=None),
    thread_role: str | None = Query(default=None),
    discord_guild_id: str | None = Query(default=None),
    discord_channel_id: str | None = Query(default=None),
    discord_thread_id: str | None = Query(default=None),
    active: bool | None = Query(default=True),
    repo: Repository = Depends(get_repo),
) -> list[dict]:
    return repo.list_discord_mappings(
        project_id=project_id,
        conversation_kind=conversation_kind,
        thread_role=thread_role,
        discord_guild_id=discord_guild_id,
        discord_channel_id=discord_channel_id,
        discord_thread_id=discord_thread_id,
        active=active,
    )


@router.get("/discord/mappings/{mapping_id}")
def get_discord_mapping(mapping_id: str, repo: Repository = Depends(get_repo)) -> dict:
    try:
        return repo.get_discord_mapping(mapping_id)
    except KeyError as exc:
        raise not_found(exc) from exc


@router.post("/discord/mappings/{mapping_id}/archive")
def archive_discord_mapping(
    mapping_id: str,
    payload: DiscordMappingArchive,
    repo: Repository = Depends(get_repo),
) -> dict:
    try:
        return repo.archive_discord_mapping(mapping_id, payload)
    except KeyError as exc:
        raise not_found(exc) from exc
