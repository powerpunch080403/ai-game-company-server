from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from app.git_workspace import git_executable
from app.test_runner_worker import run_test_runner_for_package


def git(args: list[str], cwd: Path) -> str:
    completed = subprocess.run(
        [git_executable(), *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout
    return completed.stdout.strip()


def make_test_project_repo(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "source"
    source.mkdir()
    git(["init", "-b", "main"], cwd=source)
    git(["config", "user.email", "test@example.com"], cwd=source)
    git(["config", "user.name", "Test User"], cwd=source)
    config_dir = source / ".game-company"
    config_dir.mkdir()
    config_dir.joinpath("test_runner.json").write_text(
        json.dumps(
            {
                "version": 1,
                "engine": "undecided",
                "commands": {
                    "setup": [],
                    "build": [f'"{sys.executable}" --version'],
                    "test": [],
                    "run": [],
                },
                "artifacts": {"root": ".game-company/artifacts"},
                "timeouts": {
                    "setup_seconds": 30,
                    "build_seconds": 30,
                    "test_seconds": 30,
                    "run_seconds": 30,
                },
            }
        ),
        encoding="utf-8",
    )
    (source / "README.md").write_text("# Test Project\n", encoding="utf-8")
    git(["add", "."], cwd=source)
    git(["commit", "-m", "Initial test project"], cwd=source)
    remote = tmp_path / "remote.git"
    git(["clone", "--bare", str(source), str(remote)], cwd=tmp_path)
    workspace = tmp_path / "workspace"
    return remote, workspace


def make_package(remote: Path, workspace: Path) -> dict:
    return {
        "task": {
            "id": 51,
            "role": "test_runner",
            "goal": "Run configured checks",
            "requirements": ["Execute test runner config"],
            "success_criteria": ["Report success"],
            "estimated_minutes": 15,
            "memory_refs": [],
            "branch": "worker/test-runner-checks",
            "retry_count": 0,
        },
        "project": {
            "id": 1,
            "name": "Test Project",
            "repo_url": str(remote),
            "workspace_path": str(workspace),
            "base_branch": "main",
        },
        "memories": [],
    }


def test_run_test_runner_for_package_prepares_workspace_and_maps_report(tmp_path: Path) -> None:
    remote, workspace = make_test_project_repo(tmp_path)
    package = make_package(remote, workspace)
    args = argparse.Namespace(
        runs_dir=str(tmp_path / "runs"),
        repo_url="",
        workspace="",
        base_branch="",
        config=".game-company/test_runner.json",
    )

    result = run_test_runner_for_package(package, args)

    assert result["branch"] == "worker/test-runner-checks"
    assert result["local_report"]["status"] == "success"
    assert result["worker_report"]["status"] == "success"
    assert result["worker_report"]["tests"][0].startswith("build:")
    assert result["worker_report"]["files_changed"][0].endswith("test-runner-report.json")
    assert Path(result["run_dir"], "task_package.json").is_file()
    assert Path(result["run_dir"], "test_runner_worker_result.json").is_file()
    assert (workspace / result["local_report"]["artifacts"][0]).is_file()
