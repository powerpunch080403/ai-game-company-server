from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from app.command_safety import CommandSafetyError, validate_shell_command
from app.git_workspace import git_executable, prepare_branch, resolve_git_settings, run_git
from app.worker_runner import request_json, write_task_package

load_dotenv()


def git_status_files(workspace: Path) -> list[str]:
    # Use subprocess directly instead of run_git because run_git strips
    # leading whitespace from stdout. The porcelain format uses leading
    # spaces as part of the XY status code (e.g. " M src/file.py"), so
    # stripping them corrupts the filename extracted by line[3:].
    completed = subprocess.run(
        [git_executable(), "status", "--porcelain", "--untracked-files=all"],
        cwd=workspace,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    files: list[str] = []
    for line in completed.stdout.splitlines():
        if not line:
            continue
        files.append(line[3:].strip())
    return files


def run_workspace_command(command: str, workspace: Path, package: dict[str, Any], run_dir: Path) -> tuple[int, str]:
    try:
        validate_shell_command(command)
    except CommandSafetyError as exc:
        return 126, f"Command blocked by safety policy: {exc}"
    env = os.environ.copy()
    env["GAME_COMPANY_TASK_ID"] = str(package["task"]["id"])
    env["GAME_COMPANY_TASK_PACKAGE"] = str(run_dir / "task_package.json")
    env["GAME_COMPANY_WORKSPACE"] = str(workspace)
    completed = subprocess.run(
        command,
        cwd=workspace,
        env=env,
        shell=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return completed.returncode, completed.stdout


def commit_changes(workspace: Path, task: dict[str, Any], files_changed: list[str]) -> str | None:
    if not files_changed:
        return None
    ensure_git_identity(workspace)
    run_git(["add", "--", *files_changed], cwd=workspace)
    message = f"Task {task['id']}: {task['goal']}".replace("\n", " ").strip()
    run_git(["commit", "-m", message], cwd=workspace)
    return run_git(["rev-parse", "HEAD"], cwd=workspace)


def push_branch(workspace: Path, branch: str) -> None:
    run_git(["push", "-u", "origin", branch], cwd=workspace)


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
        run_git(["config", "user.name", os.getenv("GAME_COMPANY_GIT_NAME", "AI Game Company Worker")], cwd=workspace)


def build_workspace_report(
    package: dict[str, Any],
    status: str,
    started_at: float,
    files_changed: list[str],
    tests: list[str],
    summary: str,
    issues: str,
) -> dict[str, Any]:
    task = package["task"]
    actual_minutes = max(0, round((time.monotonic() - started_at) / 60))
    error_minutes = actual_minutes if status == "failed" else 0
    productive_minutes = max(0, actual_minutes - error_minutes)
    return {
        "status": status,
        "estimated_minutes": task["estimated_minutes"],
        "actual_minutes": actual_minutes,
        "productive_minutes": productive_minutes,
        "error_minutes": error_minutes,
        "retry_count": task["retry_count"],
        "files_changed": files_changed,
        "tests": tests,
        "summary": summary,
        "issues": issues,
    }


def load_or_lease_package(args: argparse.Namespace) -> tuple[dict[str, Any], bool]:
    if args.task_id:
        if args.report and not args.no_report:
            request_json(
                "POST",
                f"{args.server}/workers/{args.worker_id}/tasks/{args.task_id}/claim",
                json={"lease_minutes": args.lease_minutes},
            )
        return request_json("GET", f"{args.server}/tasks/{args.task_id}/package"), False
    leased = request_json(
        "POST",
        f"{args.server}/workers/{args.worker_id}/lease",
        json={"role": args.role, "lease_minutes": args.lease_minutes, "requires_project_config": True},
    )
    if leased is None:
        raise RuntimeError("No task available.")
    return request_json("GET", f"{args.server}/tasks/{leased['id']}/package"), True


def run_workspace_worker(args: argparse.Namespace) -> int:
    if not args.command:
        raise RuntimeError("--command is required")

    started_at = time.monotonic()
    package, should_report = load_or_lease_package(args)
    task = package["task"]
    run_dir = Path(args.runs_dir) / f"workspace-task-{task['id']}"
    write_task_package(run_dir, package)

    repo_url, workspace, base_branch = resolve_git_settings(args, package)
    branch_info = prepare_branch(package, repo_url, workspace, base_branch)
    before_files = git_status_files(workspace)
    if before_files and not args.allow_dirty:
        report = build_workspace_report(
            package,
            "failed",
            started_at,
            before_files,
            ["git status --porcelain"],
            "Workspace was dirty before running the task.",
            "Use --allow-dirty only for manual recovery.",
        )
    else:
        return_code, output = run_workspace_command(args.command, workspace, package, run_dir)
        (run_dir / "command.log").write_text(output, encoding="utf-8")
        files_changed = git_status_files(workspace)
        commit_hash = None
        if return_code == 0 and files_changed and not args.no_commit:
            commit_hash = commit_changes(workspace, task, files_changed)
        pushed = False
        if return_code == 0 and args.push:
            push_branch(workspace, branch_info["branch"])
            pushed = True
        status = "success" if return_code == 0 else "failed"
        summary = f"Workspace command finished with exit code {return_code}."
        if commit_hash:
            summary += f" Commit: {commit_hash}"
        if pushed:
            summary += f" Pushed: {branch_info['branch']}"
        report = build_workspace_report(
            package,
            status,
            started_at,
            files_changed,
            [args.command],
            summary,
            "" if return_code == 0 else output[-4000:],
        )

    (run_dir / "workspace_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Workspace: {branch_info['workspace']}")
    print(f"Branch: {branch_info['branch']}")
    print(f"Status: {report['status']}")
    print(f"Files changed: {len(report['files_changed'])}")

    if (should_report or args.report) and not args.no_report:
        request_json(
            "POST",
            f"{args.server}/workers/{args.worker_id}/tasks/{task['id']}/report",
            json=report,
        )
        print(f"Reported task {task['id']} as {report['status']}.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a command inside a prepared game workspace branch.")
    parser.add_argument("--server", default=os.getenv("GAME_COMPANY_SERVER", "http://127.0.0.1:8080"))
    parser.add_argument("--worker-id", default="workspace-worker-1")
    parser.add_argument("--role", default="code_worker", choices=["code_worker", "image_worker", "voice_worker", "test_runner"])
    parser.add_argument("--lease-minutes", type=int, default=30)
    parser.add_argument("--runs-dir", default="./runs")
    parser.add_argument("--task-id", type=int, help="Prepare and run a specific task without reporting by default.")
    parser.add_argument("--repo-url", default="")
    parser.add_argument("--workspace", default="")
    parser.add_argument("--base-branch", default="")
    parser.add_argument("--command", required=True)
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--no-commit", action="store_true")
    parser.add_argument("--push", action="store_true", help="Push the worker branch to origin after a successful command.")
    parser.add_argument("--no-report", action="store_true")
    parser.add_argument("--report", action="store_true", help="Report even when running a specific --task-id.")
    return run_workspace_worker(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
