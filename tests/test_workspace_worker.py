from __future__ import annotations

import subprocess
from pathlib import Path

from app.git_workspace import git_executable, prepare_branch, run_git
from app.workspace_worker import commit_changes, git_status_files, push_branch, run_workspace_command
from app.worker_runner import write_task_package


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
            "id": 42,
            "role": "code_worker",
            "goal": "Create notes file",
            "requirements": ["Write docs/notes.md"],
            "success_criteria": ["File exists"],
            "estimated_minutes": 15,
            "memory_refs": [],
            "branch": "worker/create-notes",
            "retry_count": 0,
        },
        "project": None,
        "memories": [],
    }


def test_workspace_command_creates_and_commits_file(tmp_path: Path) -> None:
    remote, workspace = make_repo(tmp_path)
    package = make_package()
    prepare_branch(package, str(remote), workspace, "main")
    run_dir = tmp_path / "run"
    write_task_package(run_dir, package)

    command = "python -c \"from pathlib import Path; Path('docs').mkdir(exist_ok=True); Path('docs/notes.md').write_text('hello', encoding='utf-8')\""
    return_code, output = run_workspace_command(command, workspace, package, run_dir)
    assert return_code == 0, output

    files = git_status_files(workspace)
    assert files == ["docs/notes.md"]
    commit_hash = commit_changes(workspace, package["task"], files)
    assert commit_hash
    assert git_status_files(workspace) == []
    assert run_git(["branch", "--show-current"], cwd=workspace) == "worker/create-notes"


def test_workspace_command_decodes_utf8_cli_output(tmp_path: Path) -> None:
    remote, workspace = make_repo(tmp_path)
    package = make_package()
    prepare_branch(package, str(remote), workspace, "main")
    run_dir = tmp_path / "run"
    write_task_package(run_dir, package)

    command = "python -c \"import sys; sys.stdout.buffer.write('✓ utf8 output'.encode('utf-8'))\""
    return_code, output = run_workspace_command(command, workspace, package, run_dir)

    assert return_code == 0
    assert "utf8 output" in output


def test_push_branch_publishes_worker_branch(tmp_path: Path) -> None:
    remote, workspace = make_repo(tmp_path)
    package = make_package()
    prepare_branch(package, str(remote), workspace, "main")
    (workspace / "notes.txt").write_text("pushed\n", encoding="utf-8")
    commit_changes(workspace, package["task"], ["notes.txt"])

    push_branch(workspace, "worker/create-notes")

    remote_branches = run_git(["branch", "--list", "worker/create-notes"], cwd=remote)
    assert "worker/create-notes" in remote_branches
