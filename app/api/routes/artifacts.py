from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse

from app.api.deps import get_repo, get_settings, not_found
from app.config import Settings
from app.repository import Repository
from app.schemas import ArtifactCreate
from app.services.artifact_files import artifact_relative_dir, resolve_artifact_path, safe_artifact_filename


router = APIRouter()


@router.post("/artifacts")
def create_artifact(payload: ArtifactCreate, repo: Repository = Depends(get_repo)) -> dict:
    try:
        return repo.create_artifact(payload)
    except KeyError as exc:
        raise not_found(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/artifacts")
def list_artifacts(
    project_id: int | None = Query(default=None),
    task_id: int | None = Query(default=None),
    artifact_type: str | None = Query(default=None),
    important: bool | None = Query(default=None),
    repo: Repository = Depends(get_repo),
) -> list[dict]:
    return repo.list_artifacts(
        project_id=project_id,
        task_id=task_id,
        artifact_type=artifact_type,
        important=important,
    )


@router.get("/artifacts/{artifact_id}")
def get_artifact(artifact_id: str, repo: Repository = Depends(get_repo)) -> dict:
    try:
        return repo.get_artifact(artifact_id)
    except KeyError as exc:
        raise not_found(exc) from exc


@router.put("/artifacts/{artifact_id}/content")
async def upload_artifact_content(
    artifact_id: str,
    request: Request,
    filename: str = Query(default=""),
    content_type: str = Query(default="application/octet-stream"),
    repo: Repository = Depends(get_repo),
    config: Settings = Depends(get_settings),
) -> dict:
    try:
        artifact = repo.get_artifact(artifact_id)
    except KeyError as exc:
        raise not_found(exc) from exc
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            declared_size = int(content_length)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="invalid content-length header") from exc
        if declared_size > config.max_artifact_upload_bytes:
            raise HTTPException(status_code=413, detail="artifact upload exceeds configured size limit")
    safe_name = safe_artifact_filename(filename or artifact.get("filename") or artifact_id)
    relative_path = artifact_relative_dir(artifact) / safe_name
    try:
        target_path = resolve_artifact_path(config.artifact_root, relative_path)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if target_path.parent.is_symlink() or target_path.is_symlink():
        raise HTTPException(status_code=422, detail="artifact path must not contain symlinks")

    total_bytes = 0
    try:
        with open(target_path, "wb") as f:
            async for chunk in request.stream():
                total_bytes += len(chunk)
                if total_bytes > config.max_artifact_upload_bytes:
                    raise HTTPException(status_code=413, detail="artifact upload exceeds configured size limit")
                f.write(chunk)
    except HTTPException:
        if target_path.exists():
            target_path.unlink()
        raise
    except Exception as exc:
        if target_path.exists():
            target_path.unlink()
        raise HTTPException(status_code=500, detail=f"streaming upload failed: {exc}")

    return repo.attach_artifact_file(
        artifact_id,
        relative_path.as_posix(),
        safe_name,
        content_type,
        total_bytes,
    )


@router.get("/artifacts/{artifact_id}/content")
def download_artifact_content(
    artifact_id: str,
    repo: Repository = Depends(get_repo),
    config: Settings = Depends(get_settings),
) -> FileResponse:
    try:
        artifact = repo.get_artifact(artifact_id)
    except KeyError as exc:
        raise not_found(exc) from exc
    if not artifact.get("path"):
        raise HTTPException(status_code=404, detail="artifact content not uploaded")
    try:
        path = resolve_artifact_path(config.artifact_root, artifact["path"])
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if path.is_symlink():
        raise HTTPException(status_code=422, detail="artifact path must not be a symlink")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="artifact file not found")
    return FileResponse(path, media_type=artifact.get("content_type") or None, filename=artifact.get("filename") or None)
