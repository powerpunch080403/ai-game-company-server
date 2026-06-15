from __future__ import annotations

from typing import Any

from app.repository import Repository


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


def build_owner_readiness(repo: Repository, owner_recall_minutes: int) -> dict[str, Any]:
    dashboard = repo.dashboard(owner_recall_minutes)
    profiles = repo.list_model_profiles(enabled=True)
    profile_roles = {profile["role"] for profile in profiles}
    pending_reviews = []
    for task in repo.list_tasks(status="pending"):
        try:
            pending_reviews.append(build_task_queue_review(repo.get_task_package(task["id"])))
        except KeyError:
            continue
    blockers: list[str] = []
    warnings: list[str] = []
    if "owner" not in profile_roles:
        blockers.append("owner model profile is not configured")
    if "code_worker" not in profile_roles:
        blockers.append("code_worker model profile is not configured")
    if dashboard["task_counts"].get("failed", 0):
        blockers.append("failed tasks need owner review")
    if dashboard["task_counts"].get("running", 0):
        warnings.append("running tasks exist")
    blocked_pending = [review for review in pending_reviews if not review["workspace_ready"]]
    if blocked_pending:
        warnings.append(f"{len(blocked_pending)} pending tasks are not workspace-ready")
    return {
        "ready": not blockers,
        "blockers": blockers,
        "warnings": warnings,
        "task_counts": dashboard["task_counts"],
        "model_profiles": sorted(profile_roles),
        "pending_workspace_ready": sum(1 for review in pending_reviews if review["workspace_ready"]),
        "pending_workspace_blocked": len(blocked_pending),
    }
