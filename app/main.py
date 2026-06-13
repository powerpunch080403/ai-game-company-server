from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from app.config import Settings, load_settings
from app.db import connect, init_db
from app.git_merge import merge_worker_branch
from app.git_workspace import GitWorkspaceError
from app.owner_runner import build_owner_prompt, run_owner_command
from app.repository import Repository
from app.schemas import (
    EpicCreate,
    MemoryCreate,
    OwnerRunCreate,
    OwnerTaskCancelRequest,
    OwnerTaskMergeRequest,
    OwnerTaskReleaseRequest,
    OwnerTaskRetryRequest,
    ProjectConfigUpdate,
    ProjectCreate,
    SubEpicCreate,
    TaskCreate,
    WorkerLeaseRequest,
    WorkerReportCreate,
    WorkerTaskClaimRequest,
)

settings = load_settings()
init_db(settings.db_path)
connection = connect(settings.db_path)

app = FastAPI(
    title="AI Game Company Server",
    version="0.1.0",
    description="Owner, memory, task queue, and worker reporting API for game development automation.",
)

PUBLIC_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


def get_settings() -> Settings:
    return settings


def get_repo() -> Repository:
    return Repository(connection)


def not_found(error: KeyError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(error))


def build_merge_review(
    package: dict[str, Any],
    reports: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    task = package["task"]
    project = package.get("project")
    reasons: list[str] = []
    warnings: list[str] = []
    merged = any(event["event_type"] == "merged" for event in events)
    if merged:
        reasons.append("task has already been merged")
    if task["status"] != "success":
        reasons.append("task status must be success")
    if not task["branch"].startswith("worker/"):
        reasons.append("task branch must start with worker/")
    if not reports:
        reasons.append("task must have at least one worker report")
    elif reports[0]["status"] != "success":
        reasons.append("latest worker report must be success")
    else:
        if not reports[0]["files_changed"]:
            warnings.append("latest worker report has no changed files")
        if not reports[0]["tests"]:
            warnings.append("latest worker report has no test evidence")
        if reports[0]["issues"]:
            warnings.append("latest worker report contains issues")
    if not project:
        reasons.append("task must belong to a project")
    else:
        if not project.get("repo_url"):
            reasons.append("project repo_url is required")
        if not project.get("workspace_path"):
            reasons.append("project workspace_path is required")
    return {
        "eligible": not reasons,
        "reasons": reasons,
        "warnings": warnings,
        "merged": merged,
        "task_id": task["id"],
        "task_status": task["status"],
        "goal": task["goal"],
        "branch": task["branch"],
        "latest_report_status": reports[0]["status"] if reports else None,
        "project_id": project["id"] if project else None,
        "project_name": project["name"] if project else None,
    }


def collect_merge_candidates(repo: Repository) -> list[dict[str, Any]]:
    candidates = []
    for task in repo.list_tasks(status="success"):
        try:
            package = repo.get_task_package(task["id"])
            reports = repo.list_task_reports(task["id"])
            events = repo.list_task_events(task["id"])
        except KeyError:
            continue
        review = build_merge_review(package, reports, events)
        candidates.append(
            {
                "task": task,
                "latest_report": reports[0] if reports else None,
                "review": review,
            }
        )
    return candidates


def build_task_queue_review(package: dict[str, Any]) -> dict[str, Any]:
    task = package["task"]
    project = package.get("project")
    reasons: list[str] = []
    warnings: list[str] = []
    if task["status"] not in {"pending", "running"}:
        reasons.append("task is not queued or running")
    if not task["branch"].startswith("worker/"):
        reasons.append("task branch must start with worker/")
    if not project:
        reasons.append("task is not attached to a project")
    else:
        if not project.get("repo_url"):
            reasons.append("project repo_url is required")
        if not project.get("workspace_path"):
            reasons.append("project workspace_path is required")
        if not project.get("base_branch"):
            warnings.append("project base_branch is empty; main will be assumed by tools")
    if not task["requirements"]:
        warnings.append("task has no requirements")
    if not task["success_criteria"]:
        warnings.append("task has no success criteria")
    return {
        "workspace_ready": not reasons,
        "reasons": reasons,
        "warnings": warnings,
        "task_id": task["id"],
        "task_status": task["status"],
        "goal": task["goal"],
        "branch": task["branch"],
        "project_id": project["id"] if project else None,
        "project_name": project["name"] if project else None,
    }


@app.middleware("http")
async def require_api_token(request: Request, call_next):
    if settings.api_token and request.url.path not in PUBLIC_PATHS:
        auth_header = request.headers.get("authorization", "")
        token_header = request.headers.get("x-api-token", "")
        bearer_token = auth_header.removeprefix("Bearer ").strip()
        if bearer_token != settings.api_token and token_header != settings.api_token:
            return JSONResponse({"detail": "Missing or invalid API token"}, status_code=401)
    return await call_next(request)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/projects")
def create_project(payload: ProjectCreate, repo: Repository = Depends(get_repo)) -> dict:
    return repo.create_project(payload)


@app.get("/projects")
def list_projects(repo: Repository = Depends(get_repo)) -> list[dict]:
    return repo.list_projects()


@app.get("/projects/{project_id}")
def get_project(project_id: int, repo: Repository = Depends(get_repo)) -> dict:
    try:
        return repo.get_project(project_id)
    except KeyError as exc:
        raise not_found(exc) from exc


@app.get("/projects/{project_id}/tree")
def get_project_tree(project_id: int, repo: Repository = Depends(get_repo)) -> dict:
    try:
        return repo.get_project_tree(project_id)
    except KeyError as exc:
        raise not_found(exc) from exc


@app.patch("/projects/{project_id}/config")
def update_project_config(project_id: int, payload: ProjectConfigUpdate, repo: Repository = Depends(get_repo)) -> dict:
    try:
        return repo.update_project_config(project_id, payload)
    except KeyError as exc:
        raise not_found(exc) from exc


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


@app.get("/tasks/{task_id}/package")
def get_task_package(task_id: int, repo: Repository = Depends(get_repo)) -> dict:
    try:
        return repo.get_task_package(task_id)
    except KeyError as exc:
        raise not_found(exc) from exc


@app.get("/tasks/{task_id}/reports")
def list_task_reports(task_id: int, repo: Repository = Depends(get_repo)) -> list[dict]:
    try:
        return repo.list_task_reports(task_id)
    except KeyError as exc:
        raise not_found(exc) from exc


@app.get("/tasks/{task_id}/events")
def list_task_events(task_id: int, repo: Repository = Depends(get_repo)) -> list[dict]:
    try:
        return repo.list_task_events(task_id)
    except KeyError as exc:
        raise not_found(exc) from exc


@app.post("/workers/{worker_id}/lease")
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


@app.post("/workers/{worker_id}/tasks/{task_id}/claim")
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
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/owner/dashboard")
def owner_dashboard(
    repo: Repository = Depends(get_repo),
    config: Settings = Depends(get_settings),
) -> dict:
    return repo.dashboard(config.owner_recall_minutes)


@app.get("/owner/task-history")
def owner_task_history(
    status: str | None = Query(default=None),
    role: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    repo: Repository = Depends(get_repo),
) -> list[dict]:
    return repo.list_task_history(limit=limit, status=status, role=role)


@app.get("/owner/task-history/summary")
def owner_task_history_summary(repo: Repository = Depends(get_repo)) -> list[dict]:
    return repo.task_history_summary()


@app.get("/owner/task-queue")
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


@app.get("/owner/merge-candidates")
def list_owner_merge_candidates(repo: Repository = Depends(get_repo)) -> list[dict]:
    return collect_merge_candidates(repo)


@app.post("/owner/merge-candidates/merge-next")
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


@app.post("/owner/tasks/{task_id}/merge")
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


@app.post("/owner/tasks/{task_id}/retry")
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


@app.post("/owner/tasks/{task_id}/cancel")
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


@app.post("/owner/tasks/{task_id}/release")
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


@app.post("/owner/runs")
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


@app.get("/owner/runs")
def list_owner_runs(repo: Repository = Depends(get_repo)) -> list[dict]:
    return repo.list_owner_runs()


@app.get("/owner/runs/{run_id}")
def get_owner_run(run_id: int, repo: Repository = Depends(get_repo)) -> dict:
    try:
        return repo.get_owner_run(run_id)
    except KeyError as exc:
        raise not_found(exc) from exc
