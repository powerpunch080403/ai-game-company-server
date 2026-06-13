from __future__ import annotations

import subprocess
from pathlib import Path

from app.git_merge import merge_worker_branch
from app.git_workspace import git_executable, prepare_branch, run_git
from app.workspace_worker import commit_changes, push_branch


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


def make_repo(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "source"
    source.mkdir()
    git(["init", "-b", "main"], cwd=source)
    git(["config", "user.email", "test@example.com"], cwd=source)
    git(["config", "user.name", "Test User"], cwd=source)
    (source / "README.md").write_text("# Demo\n", encoding="utf-8")
    git(["add", "README.md"], cwd=source)
    git(["commit", "-m", "Initial"], cwd=source)
    remote = tmp_path / "remote.git"
    git(["clone", "--bare", str(source), str(remote)], cwd=tmp_path)
    workspace = tmp_path / "workspace"
    return remote, workspace


def make_package() -> dict:
    return {
        "task": {
            "id": 7,
            "role": "code_worker",
            "goal": "Create merged notes",
            "requirements": ["Write notes.txt"],
            "success_criteria": ["File exists on main"],
            "estimated_minutes": 15,
            "memory_refs": [],
            "branch": "worker/merged-notes",
            "retry_count": 0,
        },
        "project": None,
        "memories": [],
    }


def test_merge_worker_branch_pushes_base_branch(tmp_path: Path) -> None:
    remote, workspace = make_repo(tmp_path)
    package = make_package()
    prepare_branch(package, str(remote), workspace, "main")
    (workspace / "notes.txt").write_text("merged\n", encoding="utf-8")
    commit_changes(workspace, package["task"], ["notes.txt"])
    push_branch(workspace, "worker/merged-notes")

    result = merge_worker_branch(package, str(remote), workspace, "main", push=True)

    assert result["base_branch"] == "main"
    assert result["branch"] == "worker/merged-notes"
    assert run_git(["show", "main:notes.txt"], cwd=remote) == "merged"
