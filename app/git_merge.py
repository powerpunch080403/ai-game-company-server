from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from app.git_workspace import (
    GitWorkspaceError,
    ensure_repo,
    git_executable,
    load_package,
    resolve_git_settings,
    run_git,
    validate_worker_branch,
)

load_dotenv()


def ensure_git_identity(workspace: Path) -> None:
    email = subprocess.run(
        [git_executable(), "config", "user.email"],
        cwd=workspace,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if email.returncode != 0 or not email.stdout.strip():
        run_git(["config", "user.email", os.getenv("GAME_COMPANY_GIT_EMAIL", "ai-game-company@example.local")], cwd=workspace)
    name = subprocess.run(
        [git_executable(), "config", "user.name"],
        cwd=workspace,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if name.returncode != 0 or not name.stdout.strip():
        run_git(["config", "user.name", os.getenv("GAME_COMPANY_GIT_NAME", "AI Game Company Owner")], cwd=workspace)


def ensure_clean_workspace(workspace: Path) -> None:
    status = run_git(["status", "--porcelain", "--untracked-files=all"], cwd=workspace)
    if status:
        raise GitWorkspaceError(f"Workspace has uncommitted changes:\n{status}")


def merge_worker_branch(
    package: dict[str, Any],
    repo_url: str,
    workspace: Path,
    base_branch: str,
    push: bool = False,
) -> dict[str, str]:
    task = package["task"]
    branch = task["branch"]
    validate_worker_branch(branch)
    ensure_repo(repo_url, workspace)
    ensure_clean_workspace(workspace)
    ensure_git_identity(workspace)

    run_git(["fetch", "origin"], cwd=workspace)
    run_git(["checkout", base_branch], cwd=workspace)
    run_git(["pull", "--ff-only", "origin", base_branch], cwd=workspace)
    run_git(["merge", "--no-ff", "--no-edit", f"origin/{branch}"], cwd=workspace)
    if push:
        run_git(["push", "origin", base_branch], cwd=workspace)
    return {
        "workspace": str(workspace),
        "base_branch": base_branch,
        "branch": branch,
        "commit": run_git(["rev-parse", "HEAD"], cwd=workspace),
        "pushed": str(push).lower(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge a completed worker branch into the project base branch.")
    parser.add_argument("--server", default=os.getenv("GAME_COMPANY_SERVER", "http://127.0.0.1:8080"))
    parser.add_argument("--task-id", type=int)
    parser.add_argument("--package")
    parser.add_argument("--runs-dir", default="./runs")
    parser.add_argument("--repo-url", default="")
    parser.add_argument("--workspace", default="")
    parser.add_argument("--base-branch", default="")
    parser.add_argument("--push", action="store_true")
    args = parser.parse_args()

    package = load_package(args)
    repo_url, workspace, base_branch = resolve_git_settings(args, package)
    result = merge_worker_branch(package, repo_url, workspace, base_branch, push=args.push)
    print(f"Workspace: {result['workspace']}")
    print(f"Base: {result['base_branch']}")
    print(f"Branch: {result['branch']}")
    print(f"Commit: {result['commit']}")
    print(f"Pushed: {result['pushed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
