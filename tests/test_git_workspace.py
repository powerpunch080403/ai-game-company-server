from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from app.git_workspace import GitWorkspaceError, git_executable, prepare_branch, validate_worker_branch


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


def make_package(branch: str) -> dict:
    return {
        "task": {
            "id": 1,
            "role": "code_worker",
            "goal": "Prepare repo",
            "requirements": ["Create branch"],
            "success_criteria": ["Branch exists"],
            "estimated_minutes": 15,
            "memory_refs": [],
            "branch": branch,
        },
        "memories": [],
    }


def test_validate_worker_branch() -> None:
    validate_worker_branch("worker/inventory")
    with pytest.raises(GitWorkspaceError):
        validate_worker_branch("main")
    with pytest.raises(GitWorkspaceError):
        validate_worker_branch("worker/")


def test_prepare_branch_clones_and_checks_out_worker_branch(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    git(["init", "-b", "main"], cwd=source)
    git(["config", "user.email", "test@example.com"], cwd=source)
    git(["config", "user.name", "Test User"], cwd=source)
    (source / "README.md").write_text("# Game\n", encoding="utf-8")
    git(["add", "README.md"], cwd=source)
    git(["commit", "-m", "Initial"], cwd=source)

    remote = tmp_path / "remote.git"
    git(["clone", "--bare", str(source), str(remote)], cwd=tmp_path)

    workspace = tmp_path / "workspace"
    result = prepare_branch(
        make_package("worker/inventory"),
        str(remote),
        workspace,
        "main",
    )

    assert result["branch"] == "worker/inventory"
    assert (workspace / ".git").exists()
    assert git(["branch", "--show-current"], cwd=workspace) == "worker/inventory"


def test_prepare_branch_rejects_origin_mismatch(tmp_path: Path) -> None:
    first = tmp_path / "first.git"
    second = tmp_path / "second.git"
    workspace = tmp_path / "workspace"
    for remote in (first, second):
        git(["init", "--bare", str(remote)], cwd=tmp_path)
    git(["clone", str(first), str(workspace)], cwd=tmp_path)

    with pytest.raises(GitWorkspaceError):
        prepare_branch(make_package("worker/test"), str(second), workspace, "main")
