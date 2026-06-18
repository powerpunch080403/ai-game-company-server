from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_repo, not_found
from app.repository import Repository
from app.schemas import EpicCreate, ProjectConfigUpdate, ProjectCreate, SubEpicCreate, MergeCandidateRead, MergeCandidateDryRunRead, MergeCandidateExecuteRead, ProjectSearchRequest, ProjectSearchResponse, TaskPlanSearchRequest, TaskPlanSearchResponse


router = APIRouter()


@router.post("/projects")
def create_project(payload: ProjectCreate, repo: Repository = Depends(get_repo)) -> dict:
    return repo.create_project(payload)


@router.get("/projects")
def list_projects(repo: Repository = Depends(get_repo)) -> list[dict]:
    return repo.list_projects()


@router.get("/projects/{project_id}")
def get_project(project_id: int, repo: Repository = Depends(get_repo)) -> dict:
    try:
        return repo.get_project(project_id)
    except KeyError as exc:
        raise not_found(exc) from exc


@router.get("/projects/{project_id}/tree")
def get_project_tree(project_id: int, repo: Repository = Depends(get_repo)) -> dict:
    try:
        return repo.get_project_tree(project_id)
    except KeyError as exc:
        raise not_found(exc) from exc


@router.patch("/projects/{project_id}/config")
def update_project_config(project_id: int, payload: ProjectConfigUpdate, repo: Repository = Depends(get_repo)) -> dict:
    try:
        return repo.update_project_config(project_id, payload)
    except KeyError as exc:
        raise not_found(exc) from exc


@router.post("/projects/{project_id}/epics")
def create_epic(project_id: int, payload: EpicCreate, repo: Repository = Depends(get_repo)) -> dict:
    try:
        return repo.create_epic(project_id, payload)
    except KeyError as exc:
        raise not_found(exc) from exc


@router.post("/epics/{epic_id}/sub-epics")
def create_sub_epic(epic_id: int, payload: SubEpicCreate, repo: Repository = Depends(get_repo)) -> dict:
    try:
        return repo.create_sub_epic(epic_id, payload)
    except KeyError as exc:
        raise not_found(exc) from exc


@router.get("/projects/{project_id}/merge-candidates", response_model=list[MergeCandidateRead])
def list_merge_candidates(project_id: int, repo: Repository = Depends(get_repo)) -> list[dict]:
    try:
        # Check project existence
        repo.get_project(project_id)
        return repo.list_merge_candidates(project_id)
    except KeyError as exc:
        raise not_found(exc) from exc


@router.post("/merge-candidates/{candidate_id}/approve", response_model=MergeCandidateRead)
def approve_merge_candidate(candidate_id: int, repo: Repository = Depends(get_repo)) -> dict:
    try:
        return repo.approve_merge_candidate(candidate_id)
    except KeyError as exc:
        raise not_found(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/merge-candidates/{candidate_id}/reject", response_model=MergeCandidateRead)
def reject_merge_candidate(candidate_id: int, repo: Repository = Depends(get_repo)) -> dict:
    try:
        return repo.reject_merge_candidate(candidate_id)
    except KeyError as exc:
        raise not_found(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/merge-candidates/{candidate_id}/dry-run", response_model=MergeCandidateDryRunRead)
def dry_run_merge_candidate(candidate_id: int, repo: Repository = Depends(get_repo)) -> dict:
    try:
        return repo.dry_run_merge_candidate(candidate_id)
    except KeyError as exc:
        raise not_found(exc) from exc


@router.post("/merge-candidates/{candidate_id}/execute", response_model=MergeCandidateExecuteRead)
def execute_merge_candidate(candidate_id: int, repo: Repository = Depends(get_repo)) -> dict:
    try:
        # 1. Run dry-run checks first
        dry_run = repo.dry_run_merge_candidate(candidate_id)
        if not dry_run["ready"]:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Merge candidate is not ready for merge execution",
                    "reasons": dry_run["reasons"]
                }
            )
        # 2. Run real git merge
        res = repo.execute_merge_candidate(candidate_id)
        return {
            "candidate_id": candidate_id,
            "merged": True,
            "status": res["status"],
            "reasons": [],
            "branch_name": res["branch_name"],
            "base_commit": res["base_commit"],
            "merged_at": res["merged_at"],
        }
    except KeyError as exc:
        raise not_found(exc) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Merge candidate execution failed",
                "reasons": [str(exc)]
            }
        ) from exc


@router.post("/projects/{project_id}/search", response_model=ProjectSearchResponse)
def search_project(project_id: int, payload: ProjectSearchRequest, repo: Repository = Depends(get_repo)) -> dict:
    query = payload.query.strip() if payload.query else ""
    if not query:
        raise HTTPException(status_code=422, detail="query must not be empty")
    max_results = min(max(payload.max_results, 1), 100)
    if payload.glob and (".." in payload.glob or payload.glob.startswith("/") or payload.glob.startswith("\\")):
        raise HTTPException(status_code=422, detail="invalid glob pattern")

    try:
        # Check project existence
        repo.get_project(project_id)
        return repo.search_project_workspace(project_id, query, payload.glob, max_results)
    except KeyError as exc:
        raise not_found(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/projects/{project_id}/task-plan/search", response_model=TaskPlanSearchResponse)
def task_plan_search(project_id: int, payload: TaskPlanSearchRequest, repo: Repository = Depends(get_repo)) -> dict:
    goal = payload.goal.strip() if payload.goal else ""
    if not goal:
        raise HTTPException(status_code=422, detail="goal must not be empty")

    cleaned_queries = []
    seen = set()
    for q in payload.queries:
        qs = q.strip()
        if qs and qs not in seen:
            seen.add(qs)
            cleaned_queries.append(qs)

    if not cleaned_queries:
        raise HTTPException(status_code=422, detail="queries must contain at least one non-empty query")

    max_results_per_query = min(max(payload.max_results_per_query, 1), 50)
    max_files = min(max(payload.max_files, 1), 50)

    if payload.glob and (".." in payload.glob or payload.glob.startswith("/") or payload.glob.startswith("\\")):
        raise HTTPException(status_code=422, detail="invalid glob pattern")

    try:
        # Check project existence
        repo.get_project(project_id)
        return repo.plan_task_search(
            project_id=project_id,
            goal=goal,
            queries=cleaned_queries,
            glob=payload.glob,
            max_results_per_query=max_results_per_query,
            max_files=max_files,
        )
    except KeyError as exc:
        raise not_found(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

