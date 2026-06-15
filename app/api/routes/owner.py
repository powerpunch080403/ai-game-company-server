from __future__ import annotations

import subprocess
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_repo, get_settings, not_found
from app.config import Settings
from app.git_merge import merge_worker_branch
from app.git_workspace import GitWorkspaceError
from app.owner_runner import build_owner_prompt, run_owner_command
from app.repository import Repository
from app.schemas import (
    ModelProfileUpsert,
    OwnerRunCreate,
    OwnerTaskAssignRequest,
    OwnerTaskCancelRequest,
    OwnerTaskMergeRequest,
    OwnerTaskReleaseRequest,
    OwnerTaskRetryRequest,
)
from app.services.reviews import (
    build_merge_review,
    build_owner_readiness,
    build_task_queue_review,
    collect_merge_candidates,
)


router = APIRouter()


@router.get("/owner/dashboard")
def owner_dashboard(
    repo: Repository = Depends(get_repo),
    config: Settings = Depends(get_settings),
) -> dict:
    return repo.dashboard(config.owner_recall_minutes)


@router.get("/owner/readiness")
def owner_readiness(
    repo: Repository = Depends(get_repo),
    config: Settings = Depends(get_settings),
) -> dict:
    return build_owner_readiness(repo, config.owner_recall_minutes)


@router.put("/owner/model-profiles/{role}")
def upsert_model_profile(
    role: str,
    payload: ModelProfileUpsert,
    repo: Repository = Depends(get_repo),
) -> dict:
    if payload.role != role:
        raise HTTPException(status_code=400, detail="profile role must match path role")
    return repo.upsert_model_profile(payload)


@router.get("/owner/model-profiles")
def list_model_profiles(
    enabled: bool | None = Query(default=None),
    repo: Repository = Depends(get_repo),
) -> list[dict]:
    return repo.list_model_profiles(enabled=enabled)


@router.get("/owner/model-profiles/{role}")
def get_model_profile(role: str, repo: Repository = Depends(get_repo)) -> dict:
    try:
        return repo.get_model_profile(role)
    except KeyError as exc:
        raise not_found(exc) from exc


@router.get("/owner/task-history")
def owner_task_history(
    status: str | None = Query(default=None),
    role: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    repo: Repository = Depends(get_repo),
) -> list[dict]:
    return repo.list_task_history(limit=limit, status=status, role=role)


@router.get("/owner/task-history/summary")
def owner_task_history_summary(repo: Repository = Depends(get_repo)) -> list[dict]:
    return repo.task_history_summary()


@router.get("/owner/task-queue")
def owner_task_queue(
    status: str = Query(default="pending"),
    role: str | None = Query(default=None),
    repo: Repository = Depends(get_repo),
) -> list[dict]:
    items = []
    for task in repo.list_tasks(status=status, role=role):
        try:
            package = repo.get_task_package(task["id"])
        except KeyError:
            continue
        items.append({"task": task, "review": build_task_queue_review(package)})
    return items


@router.get("/owner/merge-candidates")
def list_owner_merge_candidates(repo: Repository = Depends(get_repo)) -> list[dict]:
    return collect_merge_candidates(repo)


@router.post("/owner/merge-candidates/merge-next")
def merge_next_owner_candidate(
    payload: OwnerTaskMergeRequest,
    repo: Repository = Depends(get_repo),
) -> dict:
    candidates = collect_merge_candidates(repo)
    ready = next((candidate for candidate in candidates if candidate["review"]["eligible"]), None)
    if ready is None:
        return {"status": "no_candidates", "dry_run": payload.dry_run, "candidate_count": len(candidates)}
    if payload.dry_run:
        return {"status": "ready", "dry_run": True, "candidate": ready}
    result = merge_owner_task(ready["task"]["id"], payload, repo)
    return {"selected": ready, **result}


@router.post("/owner/tasks/{task_id}/merge")
def merge_owner_task(
    task_id: int,
    payload: OwnerTaskMergeRequest,
    repo: Repository = Depends(get_repo),
) -> dict:
    try:
        package = repo.get_task_package(task_id)
        reports = repo.list_task_reports(task_id)
        events = repo.list_task_events(task_id)
    except KeyError as exc:
        raise not_found(exc) from exc

    review = build_merge_review(package, reports, events)
    if payload.dry_run:
        return {"status": "ready" if review["eligible"] else "blocked", "dry_run": True, "review": review}
    if not review["eligible"]:
        raise HTTPException(status_code=409, detail=review)

    project = package["project"]
    try:
        result = merge_worker_branch(
            package,
            project["repo_url"],
            Path(project["workspace_path"]),
            project.get("base_branch") or "main",
            push=payload.push,
        )
    except GitWorkspaceError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    repo.add_task_event(
        task_id,
        "merged",
        f"Owner merged {result['branch']} into {result['base_branch']} pushed={result['pushed']}",
    )
    return {"status": "merged", "dry_run": False, "review": review, "merge": result}


@router.post("/owner/tasks/{task_id}/retry")
def retry_owner_task(
    task_id: int,
    payload: OwnerTaskRetryRequest,
    repo: Repository = Depends(get_repo),
) -> dict:
    try:
        return repo.retry_task(task_id, payload.reason)
    except KeyError as exc:
        raise not_found(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/owner/tasks/{task_id}/cancel")
def cancel_owner_task(
    task_id: int,
    payload: OwnerTaskCancelRequest,
    repo: Repository = Depends(get_repo),
) -> dict:
    try:
        return repo.cancel_task(task_id, payload.reason)
    except KeyError as exc:
        raise not_found(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/owner/tasks/{task_id}/release")
def release_owner_task(
    task_id: int,
    payload: OwnerTaskReleaseRequest,
    repo: Repository = Depends(get_repo),
) -> dict:
    try:
        return repo.release_task(task_id, payload.reason)
    except KeyError as exc:
        raise not_found(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/owner/tasks/{task_id}/assign-sub-epic")
def assign_owner_task_to_sub_epic(
    task_id: int,
    payload: OwnerTaskAssignRequest,
    repo: Repository = Depends(get_repo),
) -> dict:
    try:
        return repo.assign_task_to_sub_epic(task_id, payload.sub_epic_id, payload.reason)
    except KeyError as exc:
        raise not_found(exc) from exc


@router.post("/owner/runs")
def create_owner_run(
    payload: OwnerRunCreate,
    repo: Repository = Depends(get_repo),
    config: Settings = Depends(get_settings),
) -> dict:
    prompt = build_owner_prompt(payload.objective, payload.context)
    owner_runs = repo.list_owner_runs()
    next_run_id = owner_runs[0]["id"] + 1 if owner_runs else 1
    run_dir = config.owner_runs_dir / f"owner-run-{next_run_id}"
    run = repo.create_owner_run(payload, prompt, config.owner_command, str(run_dir))
    if payload.dry_run or not config.owner_command:
        status = "dry_run" if payload.dry_run else "blocked"
        message = "Dry run only." if payload.dry_run else "GAME_COMPANY_OWNER_COMMAND is not configured."
        return repo.finish_owner_run(run["id"], status, None, prompt, message)

    repo.start_owner_run(run["id"])
    try:
        exit_code, stdout, stderr = run_owner_command(config, prompt, run_dir)
    except subprocess.TimeoutExpired as exc:
        return repo.finish_owner_run(
            run["id"],
            "failed",
            None,
            exc.stdout or "",
            f"Owner command timed out after {config.owner_timeout_seconds}s.",
        )
    status = "success" if exit_code == 0 else "failed"
    return repo.finish_owner_run(run["id"], status, exit_code, stdout, stderr)


@router.get("/owner/runs")
def list_owner_runs(repo: Repository = Depends(get_repo)) -> list[dict]:
    return repo.list_owner_runs()


@router.get("/owner/runs/{run_id}")
def get_owner_run(run_id: int, repo: Repository = Depends(get_repo)) -> dict:
    try:
        return repo.get_owner_run(run_id)
    except KeyError as exc:
        raise not_found(exc) from exc
