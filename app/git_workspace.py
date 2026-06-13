from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from app.worker_runner import request_json, write_task_package

load_dotenv()


class GitWorkspaceError(RuntimeError):
    pass


def git_executable() -> str:
    found = shutil.which("git")
    if found:
        return found
    for candidate in (
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files\Git\bin\git.exe",
    ):
        if Path(candidate).exists():
            return candidate
    raise GitWorkspaceError("git executable was not found")


def run_git(args: list[str], cwd: Path | None = None) -> str:
    completed = subprocess.run(
        [git_executable(), *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.returncode != 0:
        command = "git " + " ".join(args)
        raise GitWorkspaceError(f"{command} failed:\n{completed.stdout}")
    return completed.stdout.strip()


def validate_worker_branch(branch: str) -> None:
    if not branch.startswith("worker/"):
        raise GitWorkspaceError(f"Task branch must start with worker/: {branch}")
    if branch in {"worker/", "worker/main", "worker/master"}:
        raise GitWorkspaceError(f"Invalid worker branch: {branch}")
    if ".." in branch or branch.startswith("/") or branch.endswith("/"):
        raise GitWorkspaceError(f"Invalid branch path: {branch}")


def ensure_repo(repo_url: str, workspace: Path) -> None:
    workspace.parent.mkdir(parents=True, exist_ok=True)
    if (workspace / ".git").exists():
        current_url = run_git(["remote", "get-url", "origin"], cwd=workspace)
        if current_url != repo_url:
            raise GitWorkspaceError(
                f"Workspace origin mismatch. expected={repo_url} actual={current_url}"
            )
        return
    if any(workspace.iterdir()) if workspace.exists() else False:
        raise GitWorkspaceError(f"Workspace exists but is not a git repository: {workspace}")
    run_git(["clone", repo_url, str(workspace)])


def prepare_branch(package: dict[str, Any], repo_url: str, workspace: Path, base_branch: str) -> dict[str, str]:
    task = package["task"]
    branch = task["branch"]
    validate_worker_branch(branch)
    ensure_repo(repo_url, workspace)
    run_git(["fetch", "origin"], cwd=workspace)
    run_git(["checkout", base_branch], cwd=workspace)
    run_git(["pull", "--ff-only", "origin", base_branch], cwd=workspace)
    existing = subprocess.run(
        [git_executable(), "rev-parse", "--verify", branch],
        cwd=workspace,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if existing.returncode == 0:
        run_git(["checkout", branch], cwd=workspace)
    else:
        run_git(["checkout", "-b", branch], cwd=workspace)
    current_branch = run_git(["branch", "--show-current"], cwd=workspace)
    return {
        "workspace": str(workspace),
        "base_branch": base_branch,
        "branch": current_branch,
        "commit": run_git(["rev-parse", "HEAD"], cwd=workspace),
    }


def load_package(args: argparse.Namespace) -> dict[str, Any]:
    if args.package:
        return __import__("json").loads(Path(args.package).read_text(encoding="utf-8"))
    if not args.task_id:
        raise GitWorkspaceError("Either --task-id or --package is required")
    package = request_json("GET", f"{args.server}/tasks/{args.task_id}/package")
    run_dir = Path(args.runs_dir) / f"git-task-{args.task_id}"
    write_task_package(run_dir, package)
    return package


def resolve_git_settings(args: argparse.Namespace, package: dict[str, Any]) -> tuple[str, Path, str]:
    project = package.get("project") or {}
    repo_url = args.repo_url or project.get("repo_url") or os.getenv("GAME_COMPANY_GAME_REPO_URL", "")
    workspace = args.workspace or project.get("workspace_path") or os.getenv("GAME_COMPANY_GAME_WORKSPACE", "")
    base_branch = args.base_branch or project.get("base_branch") or os.getenv("GAME_COMPANY_GAME_BASE_BRANCH", "main")
    if not repo_url:
        raise GitWorkspaceError("Project repo_url or GAME_COMPANY_GAME_REPO_URL is required")
    if not workspace:
        raise GitWorkspaceError("Project workspace_path or GAME_COMPANY_GAME_WORKSPACE is required")
    return repo_url, Path(workspace), base_branch


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a git workspace branch for a task.")
    parser.add_argument("--server", default=os.getenv("GAME_COMPANY_SERVER", "http://127.0.0.1:8080"))
    parser.add_argument("--task-id", type=int)
    parser.add_argument("--package")
    parser.add_argument("--runs-dir", default="./runs")
    parser.add_argument("--repo-url", default="")
    parser.add_argument("--workspace", default="")
    parser.add_argument("--base-branch", default="")
    args = parser.parse_args()

    package = load_package(args)
    repo_url, workspace, base_branch = resolve_git_settings(args, package)
    result = prepare_branch(package, repo_url, workspace, base_branch)
    print(f"Workspace: {result['workspace']}")
    print(f"Base: {result['base_branch']}")
    print(f"Branch: {result['branch']}")
    print(f"Commit: {result['commit']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
