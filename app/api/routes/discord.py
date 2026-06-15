from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_repo, get_settings, not_found
from app.config import Settings
from app.context_compaction import context_status, estimate_context_tokens
from app.repository import Repository
from app.schemas import (
    DiscordContextStatusRequest,
    DiscordMappingArchive,
    DiscordMappingUpsert,
    DiscordThreadCompactRequest,
)


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


@router.post("/discord/mappings/{mapping_id}/compact")
def compact_discord_thread(
    mapping_id: str,
    payload: DiscordThreadCompactRequest,
    repo: Repository = Depends(get_repo),
) -> dict:
    try:
        return repo.compact_discord_thread(mapping_id, payload)
    except KeyError as exc:
        raise not_found(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/discord/mappings/{mapping_id}/context-status")
def discord_context_status(
    mapping_id: str,
    payload: DiscordContextStatusRequest,
    repo: Repository = Depends(get_repo),
    config: Settings = Depends(get_settings),
) -> dict:
    try:
        mapping = repo.get_discord_mapping(mapping_id)
    except KeyError as exc:
        raise not_found(exc) from exc

    current_summary = payload.current_summary
    summary_memory_key = mapping.get("summary_memory_key")
    if not current_summary and summary_memory_key:
        try:
            current_summary = repo.get_memory(summary_memory_key)["body"]
        except KeyError:
            current_summary = ""

    text_parts = [
        payload.system_rules,
        current_summary,
        *payload.project_memory,
        *payload.recent_messages,
        *payload.task_context,
        *payload.artifact_context,
        payload.next_user_message,
    ]
    threshold_tokens = payload.threshold_tokens or config.context_compact_threshold_tokens
    warning_tokens = payload.warning_tokens or config.context_warning_tokens
    if warning_tokens > threshold_tokens:
        warning_tokens = threshold_tokens
    estimated_tokens = estimate_context_tokens(
        text_parts,
        estimated_extra_tokens=payload.estimated_extra_tokens,
        chars_per_token=config.context_chars_per_token,
    )
    status = context_status(
        estimated_tokens=estimated_tokens,
        threshold_tokens=threshold_tokens,
        warning_tokens=warning_tokens,
    )

    compact_result = None
    compact_action = "not_needed"
    if status.compact_required:
        compact_action = "summary_required"
        if payload.auto_compact and payload.compact_summary.strip():
            try:
                compact_result = repo.compact_discord_thread(
                    mapping_id,
                    DiscordThreadCompactRequest(
                        summary=payload.compact_summary,
                        tags=["context", "auto_compact"],
                        archive_mapping=payload.archive_mapping,
                        archive_reason=payload.archive_reason,
                        continuation_discord_thread_id=payload.continuation_discord_thread_id,
                        continuation_notes=payload.continuation_notes,
                    ),
                )
            except ValueError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            compact_action = "compacted"
    elif status.compact_recommended:
        compact_action = "recommended"

    return {
        "mapping_id": mapping_id,
        "summary_memory_key": summary_memory_key,
        "estimated_tokens": status.estimated_tokens,
        "threshold_tokens": status.threshold_tokens,
        "warning_tokens": status.warning_tokens,
        "remaining_tokens": status.remaining_tokens,
        "usage_ratio": status.usage_ratio,
        "status": status.status,
        "compact_required": status.compact_required,
        "compact_recommended": status.compact_recommended,
        "compact_action": compact_action,
        "compact_result": compact_result,
    }
