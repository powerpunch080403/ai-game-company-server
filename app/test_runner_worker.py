from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from app.git_workspace import prepare_branch, resolve_git_settings
from app.test_runner import DEFAULT_CONFIG_PATH, run_test_runner
from app.test_runner_report import map_test_runner_report
from app.worker_runner import request_json, write_task_package

load_dotenv()


def load_or_lease_test_package(args: argparse.Namespace) -> tuple[dict[str, Any], bool]:
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
        json={"role": "test_runner", "lease_minutes": args.lease_minutes, "requires_project_config": True},
    )
    if leased is None:
        raise RuntimeError("No test_runner task available.")
    return request_json("GET", f"{args.server}/tasks/{leased['id']}/package"), True


def run_test_runner_for_package(package: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    task = package["task"]
    run_dir = Path(args.runs_dir) / f"test-runner-task-{task['id']}"
    write_task_package(run_dir, package)
    package_path = run_dir / "task_package.json"

    repo_url, workspace, base_branch = resolve_git_settings(args, package)
    branch_info = prepare_branch(package, repo_url, workspace, base_branch)
    local_report = run_test_runner(package_path, workspace, args.config)
    worker_report = map_test_runner_report(package, local_report)

    result = {
        "task": task,
        "workspace": branch_info["workspace"],
        "branch": branch_info["branch"],
        "run_dir": str(run_dir),
        "local_report": local_report,
        "worker_report": worker_report,
    }
    (run_dir / "test_runner_worker_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


def run_test_runner_worker(args: argparse.Namespace) -> int:
    package, should_report = load_or_lease_test_package(args)
    result = run_test_runner_for_package(package, args)
    task_id = result["task"]["id"]
    worker_report = result["worker_report"]

    print(f"Workspace: {result['workspace']}")
    print(f"Branch: {result['branch']}")
    print(f"Status: {worker_report['status']}")
    print(f"Run dir: {result['run_dir']}")

    if (should_report or args.report) and not args.no_report:
        request_json(
            "POST",
            f"{args.server}/workers/{args.worker_id}/tasks/{task_id}/report",
            json=worker_report,
        )
        print(f"Reported task {task_id} as {worker_report['status']}.")

    return 0 if worker_report["status"] == "success" else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lease or run a test_runner task against a configured project workspace.")
    parser.add_argument("--server", default=os.getenv("GAME_COMPANY_SERVER", "http://127.0.0.1:8080"))
    parser.add_argument("--worker-id", default="test-runner-1")
    parser.add_argument("--lease-minutes", type=int, default=30)
    parser.add_argument("--runs-dir", default="./runs")
    parser.add_argument("--task-id", type=int, help="Run a specific task without reporting by default.")
    parser.add_argument("--repo-url", default="")
    parser.add_argument("--workspace", default="")
    parser.add_argument("--base-branch", default="")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Workspace-relative test runner config path.")
    parser.add_argument("--no-report", action="store_true")
    parser.add_argument("--report", action="store_true", help="Report even when running a specific --task-id.")
    return parser.parse_args()


def main() -> int:
    return run_test_runner_worker(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
