from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from app.worker_supervisor import (
    build_workspace_worker_argv,
    resolve_worker_command,
    run_supervisor_once,
    write_default_codex_prompt,
)


def make_args(tmp_path: Path) -> argparse.Namespace:
    return argparse.Namespace(
        server="http://127.0.0.1:8080",
        worker_id="codex-workspace-1",
        role="code_worker",
        lease_minutes=60,
        runs_dir=str(tmp_path / "runs"),
        server_repo=str(tmp_path),
        push=True,
        allow_dirty=False,
        loop=False,
        interval_seconds=15,
        max_iterations=0,
        continue_on_error=False,
    )


def test_write_default_codex_prompt(tmp_path: Path) -> None:
    prompt_file = write_default_codex_prompt(tmp_path / "runs")

    assert prompt_file.exists()
    text = prompt_file.read_text(encoding="utf-8")
    assert "GAME_COMPANY_TASK_PACKAGE" in text
    assert "Do not merge branches." in text


def test_resolve_worker_command_uses_configured_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("GAME_COMPANY_WORKSPACE_WORKER_COMMAND", "custom worker command")

    command = resolve_worker_command(make_args(tmp_path))

    assert command == "custom worker command"


def test_resolve_worker_command_defaults_to_codex_prompt(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("GAME_COMPANY_WORKSPACE_WORKER_COMMAND", raising=False)

    command = resolve_worker_command(make_args(tmp_path))

    assert command.startswith("codex exec --cd . --sandbox workspace-write - < ")
    assert "workspace-worker-default-prompt.md" in command


def test_build_workspace_worker_argv_includes_report_and_push(tmp_path: Path) -> None:
    args = make_args(tmp_path)

    argv = build_workspace_worker_argv(args, "codex exec - < prompt.md")

    assert argv[:3] == [sys.executable, "-m", "app.workspace_worker"]
    assert "--command" in argv
    assert argv[argv.index("--command") + 1] == "codex exec - < prompt.md"
    assert "--report" in argv
    assert "--push" in argv


def test_run_supervisor_once_executes_workspace_worker(monkeypatch, tmp_path: Path) -> None:
    args = make_args(tmp_path)
    calls = []

    def fake_run(argv, cwd, text, stdout, stderr, check):
        calls.append(
            {
                "argv": argv,
                "cwd": cwd,
                "text": text,
                "stdout": stdout,
                "stderr": stderr,
                "check": check,
            }
        )
        return subprocess.CompletedProcess(argv, 0, stdout="No task available.\n")

    monkeypatch.delenv("GAME_COMPANY_WORKSPACE_WORKER_COMMAND", raising=False)
    monkeypatch.setattr(subprocess, "run", fake_run)

    code = run_supervisor_once(args)

    assert code == 0
    assert calls[0]["cwd"] == str(tmp_path)
    assert calls[0]["argv"][:3] == [sys.executable, "-m", "app.workspace_worker"]
