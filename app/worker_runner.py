from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

from app.command_safety import CommandSafetyError, validate_shell_command

load_dotenv()


def request_json(method: str, url: str, **kwargs: Any) -> Any:
    headers = dict(kwargs.pop("headers", {}))
    api_token = os.getenv("GAME_COMPANY_WORKER_TOKEN") or os.getenv("GAME_COMPANY_API_TOKEN", "")
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"
    with httpx.Client(timeout=30) as client:
        response = client.request(method, url, headers=headers, **kwargs)
        if response.status_code == 204:
            return None
        response.raise_for_status()
        return response.json()


def render_instructions(package: dict[str, Any]) -> str:
    task = package["task"]
    lines = [
        f"# Task {task['id']}: {task['goal']}",
        "",
        "## Role",
        task["role"],
        "",
        "## Branch",
        task["branch"],
        "",
        "## Requirements",
    ]
    lines.extend(f"- {item}" for item in task["requirements"])
    lines.extend(["", "## Success Criteria"])
    lines.extend(f"- {item}" for item in task["success_criteria"])
    lines.extend(["", "## Memory"])
    if package["memories"]:
        for memory in package["memories"]:
            lines.extend(
                [
                    f"### {memory['key']}: {memory['title']}",
                    memory["body"],
                    "",
                ]
            )
    else:
        lines.append("- No memory refs resolved.")
    return "\n".join(lines).strip() + "\n"


def write_task_package(run_dir: Path, package: dict[str, Any]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "task_package.json").write_text(
        json.dumps(package, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (run_dir / "instructions.md").write_text(render_instructions(package), encoding="utf-8")


def build_report(
    package: dict[str, Any],
    status: str,
    started_at: float,
    summary: str,
    issues: str,
    tests: list[str],
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
        "files_changed": [],
        "tests": tests,
        "summary": summary,
        "issues": issues,
    }


def run_command(command: str, run_dir: Path, package: dict[str, Any]) -> tuple[int, str]:
    try:
        validate_shell_command(command)
    except CommandSafetyError as exc:
        return 126, f"Command blocked by safety policy: {exc}"
    env = os.environ.copy()
    env["GAME_COMPANY_TASK_PACKAGE"] = str(run_dir / "task_package.json")
    env["GAME_COMPANY_TASK_ID"] = str(package["task"]["id"])
    completed = subprocess.run(
        command,
        cwd=run_dir,
        env=env,
        shell=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return completed.returncode, completed.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description="Lease and run one AI game company worker task.")
    parser.add_argument("--server", default=os.getenv("GAME_COMPANY_SERVER", "http://127.0.0.1:8080"))
    parser.add_argument("--worker-id", required=True)
    parser.add_argument("--role", required=True, choices=["code_worker", "image_worker", "voice_worker", "test_runner"])
    parser.add_argument("--lease-minutes", type=int, default=30)
    parser.add_argument("--runs-dir", default="./runs")
    parser.add_argument("--command", help="Optional shell command to execute for the leased task.")
    parser.add_argument("--dry-run", action="store_true", help="Lease and write the task package without reporting.")
    args = parser.parse_args()

    started_at = time.monotonic()
    lease_url = f"{args.server}/workers/{args.worker_id}/lease"
    leased = request_json(
        "POST",
        lease_url,
        json={"role": args.role, "lease_minutes": args.lease_minutes},
    )
    if leased is None:
        print("No task available.")
        return 0

    package = request_json("GET", f"{args.server}/tasks/{leased['id']}/package")
    run_dir = Path(args.runs_dir) / f"task-{leased['id']}"
    write_task_package(run_dir, package)
    print(f"Leased task {leased['id']}: {leased['goal']}")
    print(f"Wrote package: {run_dir}")

    if args.dry_run:
        return 0

    if not args.command:
        report = build_report(
            package,
            "blocked",
            started_at,
            "Task package prepared, but no worker command was configured.",
            "Set --command to execute an automated worker.",
            [],
        )
    else:
        return_code, output = run_command(args.command, run_dir, package)
        (run_dir / "command.log").write_text(output, encoding="utf-8")
        status = "success" if return_code == 0 else "failed"
        report = build_report(
            package,
            status,
            started_at,
            f"Command finished with exit code {return_code}.",
            "" if return_code == 0 else output[-4000:],
            [args.command],
        )

    request_json(
        "POST",
        f"{args.server}/workers/{args.worker_id}/tasks/{leased['id']}/report",
        json=report,
    )
    print(f"Reported task {leased['id']} as {report['status']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
