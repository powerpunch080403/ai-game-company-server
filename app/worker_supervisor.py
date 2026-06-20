from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


DEFAULT_CODEX_WORKER_PROMPT = """Read the task package path from GAME_COMPANY_TASK_PACKAGE and implement only that task.

You are a code_worker for AI Game Company v1.

Rules:
- Work only inside the assigned workspace.
- Follow the task requirements, success criteria, read scope, write scope, and forbidden scope.
- Keep the change small and directly tied to the task.
- Do not merge branches.
- Do not edit secrets, .env files, .git metadata, or unrelated files.
- Leave changed files in the workspace; the workspace worker wrapper will commit, push, and report.
"""


def quote_shell_path(path: Path) -> str:
    escaped = str(path).replace('"', '\\"')
    return f'"{escaped}"'


def write_default_codex_prompt(runs_dir: Path) -> Path:
    runs_dir.mkdir(parents=True, exist_ok=True)
    prompt_file = runs_dir / "workspace-worker-default-prompt.md"
    prompt_file.write_text(DEFAULT_CODEX_WORKER_PROMPT, encoding="utf-8")
    return prompt_file


def resolve_worker_command(args: argparse.Namespace) -> str:
    configured = os.getenv("GAME_COMPANY_WORKSPACE_WORKER_COMMAND", "").strip()
    if configured:
        return configured
    prompt_file = write_default_codex_prompt(Path(args.runs_dir))
    return f"codex exec --cd . --sandbox workspace-write - < {quote_shell_path(prompt_file)}"


def build_workspace_worker_argv(args: argparse.Namespace, command: str) -> list[str]:
    argv = [
        sys.executable,
        "-m",
        "app.workspace_worker",
        "--server",
        args.server,
        "--worker-id",
        args.worker_id,
        "--role",
        args.role,
        "--lease-minutes",
        str(args.lease_minutes),
        "--runs-dir",
        args.runs_dir,
        "--command",
        command,
        "--report",
    ]
    if args.push:
        argv.append("--push")
    if args.allow_dirty:
        argv.append("--allow-dirty")
    return argv


def run_supervisor_once(args: argparse.Namespace) -> int:
    command = resolve_worker_command(args)
    argv = build_workspace_worker_argv(args, command)
    completed = subprocess.run(
        argv,
        cwd=args.server_repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.stdout:
        print(completed.stdout, end="", flush=True)
    return completed.returncode


def run_supervisor_loop(args: argparse.Namespace) -> int:
    iterations = 0
    while True:
        code = run_supervisor_once(args)
        iterations += 1
        if code != 0 and not args.continue_on_error:
            return code
        if args.max_iterations and iterations >= args.max_iterations:
            return code
        time.sleep(args.interval_seconds)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Poll for workspace tasks and run the workspace worker.")
    parser.add_argument("--server", default=os.getenv("GAME_COMPANY_SERVER", "http://127.0.0.1:8080"))
    parser.add_argument("--worker-id", default=os.getenv("GAME_COMPANY_WORKSPACE_SUPERVISOR_WORKER_ID", "codex-workspace-1"))
    parser.add_argument("--role", default="code_worker", choices=["code_worker", "image_worker", "voice_worker", "test_runner"])
    parser.add_argument("--lease-minutes", type=int, default=int(os.getenv("GAME_COMPANY_WORKSPACE_LEASE_MINUTES", "60")))
    parser.add_argument("--runs-dir", default=os.getenv("GAME_COMPANY_WORKSPACE_RUNS_DIR", "./runs"))
    parser.add_argument("--server-repo", default=os.getenv("GAME_COMPANY_SERVER_REPO", os.getcwd()))
    parser.add_argument("--push", action="store_true", default=os.getenv("GAME_COMPANY_WORKSPACE_PUSH", "0") == "1")
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--interval-seconds", type=float, default=float(os.getenv("GAME_COMPANY_WORKSPACE_SUPERVISOR_INTERVAL_SECONDS", "15")))
    parser.add_argument("--max-iterations", type=int, default=0, help="0 means unlimited when --loop is set.")
    parser.add_argument("--continue-on-error", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.server_repo = str(Path(args.server_repo).resolve())
    if args.loop:
        return run_supervisor_loop(args)
    return run_supervisor_once(args)


if __name__ == "__main__":
    raise SystemExit(main())
