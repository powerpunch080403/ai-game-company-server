from __future__ import annotations

import sqlite3
import subprocess
import shutil
import json
from pathlib import Path
import pytest

from app.db import SCHEMA, init_db, migrate_db
from app.git_workspace import git_executable, prepare_branch, run_git
from app.repository import Repository
from app.schemas import ProjectCreate, EpicCreate, SubEpicCreate, TaskCreate, WorkerReportCreate
from app.workspace_worker import run_workspace_worker, git_status_files

# Helper to run git commands
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

# Helper to create temporary repo
def make_repo(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "source"
    source.mkdir(parents=True, exist_ok=True)
    git(["init", "-b", "main"], cwd=source)
    git(["config", "user.email", "smoke@example.com"], cwd=source)
    git(["config", "user.name", "Smoke Tester"], cwd=source)
    (source / "README.md").write_text("# Demo\n", encoding="utf-8")
    git(["add", "README.md"], cwd=source)
    git(["commit", "-m", "Initial"], cwd=source)
    
    remote = tmp_path / "remote.git"
    git(["clone", "--bare", str(source), str(remote)], cwd=tmp_path)
    workspace = tmp_path / "workspace"
    git(["clone", str(remote), str(workspace)], cwd=tmp_path)
    git(["config", "user.email", "smoke@example.com"], cwd=workspace)
    git(["config", "user.name", "Smoke Tester"], cwd=workspace)
    
    return remote, workspace

@pytest.fixture()
def db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    return conn

@pytest.fixture()
def repo(db_conn: sqlite3.Connection) -> Repository:
    return Repository(db_conn)

def test_database_migration(tmp_path: Path) -> None:
    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE worker_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            worker_id TEXT NOT NULL,
            status TEXT NOT NULL,
            estimated_minutes INTEGER NOT NULL,
            actual_minutes INTEGER NOT NULL,
            productive_minutes INTEGER NOT NULL,
            error_minutes INTEGER NOT NULL,
            retry_count INTEGER NOT NULL,
            files_changed_json TEXT NOT NULL,
            tests_json TEXT NOT NULL,
            summary TEXT NOT NULL,
            issues TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
    """)
    conn.execute("CREATE TABLE projects (id INTEGER PRIMARY KEY AUTOINCREMENT);")
    conn.execute("CREATE TABLE tasks (id INTEGER PRIMARY KEY AUTOINCREMENT);")
    conn.commit()
    
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(worker_reports)").fetchall()}
    assert "head_commit" not in cols
    
    migrate_db(conn)
    
    cols_after = {row["name"] for row in conn.execute("PRAGMA table_info(worker_reports)").fetchall()}
    assert "head_commit" in cols_after
    conn.close()

def test_git_backed_report_without_head_commit_fails_and_creates_no_candidate(tmp_path: Path, repo: Repository) -> None:
    remote, workspace = make_repo(tmp_path)
    proj = repo.create_project(ProjectCreate(
        name="Smoke Project",
        repo_url=str(remote),
        workspace_path=str(workspace),
        base_branch="main"
    ))
    epic = repo.create_epic(proj["id"], EpicCreate(name="Test Epic", goal="Test Epic Goal"))
    sub_epic = repo.create_sub_epic(epic["id"], SubEpicCreate(name="Test Sub Epic", goal="Test Sub Epic Goal"))
    
    base_commit = git(["rev-parse", "HEAD"], cwd=workspace)
    task = repo.create_task(sub_epic["id"], TaskCreate(
        role="code_worker",
        goal="Update file",
        requirements=["Modify README.md"],
        success_criteria=["README updated"],
        branch="worker/smoke-task",
        write_scope=["README.md"]
    ))
    
    # Lease the task to worker
    leased = repo.lease_next_task("worker-1", "code_worker", 30, requires_project_config=True)
    assert leased is not None
    
    # Try to report success WITHOUT head_commit
    report = WorkerReportCreate(
        status="success",
        estimated_minutes=15,
        actual_minutes=10,
        productive_minutes=10,
        error_minutes=0,
        retry_count=0,
        files_changed=["README.md"],
        changed_files=["README.md"],
        tests=["test"],
        summary="done",
        head_commit=None
    )
    
    with pytest.raises(ValueError, match="missing_head_commit"):
        repo.complete_task(task["id"], "worker-1", report)
        
    # Verify no candidate is created
    candidates = repo.list_merge_candidates(proj["id"])
    assert len(candidates) == 0
    
    # Verify task status was downgraded to failed (recovery policy)
    updated_task = repo.get_task(task["id"])
    assert updated_task["status"] == "failed"
    assert updated_task["leased_by"] is None
    
    # Verify audit report stores supplied head_commit (which is None)
    reports = repo.list_task_reports(task["id"])
    assert len(reports) == 1
    assert reports[0]["status"] == "success"
    assert reports[0]["head_commit"] is None

def test_dry_run_reasons_and_execution_parity(tmp_path: Path, repo: Repository) -> None:
    remote, workspace = make_repo(tmp_path)
    proj = repo.create_project(ProjectCreate(
        name="Smoke Project",
        repo_url=str(remote),
        workspace_path=str(workspace),
        base_branch="main"
    ))
    epic = repo.create_epic(proj["id"], EpicCreate(name="Test Epic", goal="Test Epic Goal"))
    sub_epic = repo.create_sub_epic(epic["id"], SubEpicCreate(name="Test Sub Epic", goal="Test Sub Epic Goal"))
    
    base_commit = git(["rev-parse", "HEAD"], cwd=workspace)
    task = repo.create_task(sub_epic["id"], TaskCreate(
        role="code_worker",
        goal="Update file",
        requirements=["Modify README.md"],
        success_criteria=["README updated"],
        branch="worker/smoke-task-2",
        write_scope=["README.md"]
    ))
    
    # Lease and check out branch
    leased = repo.lease_next_task("worker-1", "code_worker", 30, requires_project_config=True)
    branch_name = leased["branch"]
    
    # Edit and commit in workspace
    git(["checkout", "-b", branch_name, base_commit], cwd=workspace)
    (workspace / "README.md").write_text("# Demo updated\n", encoding="utf-8")
    git(["add", "README.md"], cwd=workspace)
    git(["commit", "-m", "Worker commit"], cwd=workspace)
    head_commit = git(["rev-parse", "HEAD"], cwd=workspace)
    git(["push", "origin", branch_name], cwd=workspace)
    
    # Report success
    report = WorkerReportCreate(
        status="success",
        estimated_minutes=15,
        actual_minutes=10,
        productive_minutes=10,
        error_minutes=0,
        retry_count=0,
        files_changed=["README.md"],
        changed_files=["README.md"],
        tests=["test"],
        summary="done",
        head_commit=head_commit
    )
    repo.complete_task(task["id"], "worker-1", report)
    
    # Candidate created, status is queued
    candidates = repo.list_merge_candidates(proj["id"])
    assert len(candidates) == 1
    cand = candidates[0]
    
    # 1. Before approval: dry_run returns exactly ['not_approved']
    dry = repo.dry_run_merge_candidate(cand["id"])
    assert dry["ready"] is False
    assert dry["reasons"] == ["not_approved"]
    
    # Execution revalidation refuses merge immediately before approval
    with pytest.raises(ValueError, match="not_approved"):
        repo.execute_merge_candidate(cand["id"])
        
    # Approve candidate
    repo.approve_merge_candidate(cand["id"])
    
    # 2. After approval: dry_run returns ready: True
    dry_approved = repo.dry_run_merge_candidate(cand["id"])
    assert dry_approved["ready"] is True
    assert dry_approved["reasons"] == []
    
    # 3. Mismatch checks
    # Move branch tip after report to simulate stale/changed tip
    git(["checkout", branch_name], cwd=workspace)
    (workspace / "README.md").write_text("# Demo stale tip\n", encoding="utf-8")
    git(["add", "README.md"], cwd=workspace)
    git(["commit", "-m", "Stale tip commit"], cwd=workspace)
    git(["push", "origin", branch_name], cwd=workspace)
    
    # Dry run should now catch source_branch_head_mismatch
    dry_mismatch = repo.dry_run_merge_candidate(cand["id"])
    assert "source_branch_head_mismatch" in dry_mismatch["reasons"]
    
    # Revalidate execute refuses
    with pytest.raises(ValueError, match="source_branch_head_mismatch"):
        repo.execute_merge_candidate(cand["id"])

def test_missing_git_config_on_code_task_does_not_bypass(tmp_path: Path, repo: Repository) -> None:
    # Task is code_worker, but project has no git configurations
    proj = repo.create_project(ProjectCreate(
        name="No Git Project",
        repo_url="configured-but-unavailable",
        workspace_path="",
        base_branch="main"
    ))
    epic = repo.create_epic(proj["id"], EpicCreate(name="Test Epic", goal="Test Epic Goal"))
    sub_epic = repo.create_sub_epic(epic["id"], SubEpicCreate(name="Test Sub Epic", goal="Test Sub Epic Goal"))
    
    task = repo.create_task(sub_epic["id"], TaskCreate(
        role="code_worker",
        goal="Write code",
        requirements=["Write code"],
        success_criteria=["Done"],
        branch="worker/no-git-task"
    ))
    
    # Lease the task
    leased = repo.lease_next_task("worker-1", "code_worker", 30, requires_project_config=False)
    
    report = WorkerReportCreate(
        status="success",
        estimated_minutes=15,
        actual_minutes=10,
        productive_minutes=10,
        error_minutes=0,
        retry_count=0,
        files_changed=["file.py"],
        changed_files=["file.py"],
        tests=[],
        summary="done",
        head_commit="abcd123"
    )
    
    # Reporting must fail because project git configuration is missing for a code task
    with pytest.raises(ValueError, match="workspace_unavailable"):
        repo.complete_task(task["id"], "worker-1", report)

def test_non_git_role_compatibility(tmp_path: Path, repo: Repository) -> None:
    # Project has no git configs, role is image_worker (non-Git)
    proj = repo.create_project(ProjectCreate(
        name="Image Project",
        repo_url="",
        workspace_path="",
        base_branch="main"
    ))
    epic = repo.create_epic(proj["id"], EpicCreate(name="Test Epic", goal="Test Epic Goal"))
    sub_epic = repo.create_sub_epic(epic["id"], SubEpicCreate(name="Test Sub Epic", goal="Test Sub Epic Goal"))
    
    task = repo.create_task(sub_epic["id"], TaskCreate(
        role="image_worker",
        goal="Generate icon",
        requirements=["Generate icon"],
        success_criteria=["Done"],
        branch="worker/image-task"
    ))
    
    # Lease task
    leased = repo.lease_next_task("worker-1", "image_worker", 30, requires_project_config=False)
    
    # Success report with no head_commit should succeed normally
    report = WorkerReportCreate(
        status="success",
        estimated_minutes=15,
        actual_minutes=10,
        productive_minutes=10,
        error_minutes=0,
        retry_count=0,
        files_changed=["icon.png"],
        changed_files=["icon.png"],
        tests=[],
        summary="icon created",
        head_commit=None
    )
    
    completed = repo.complete_task(task["id"], "worker-1", report)
    assert completed["status"] == "success"

def test_workspace_worker_cleanliness_reset_and_pushed(tmp_path: Path) -> None:
    remote, workspace = make_repo(tmp_path)
    
    # Prepare package config
    base_commit = git(["rev-parse", "HEAD"], cwd=workspace)
    package = {
        "task": {
            "id": 101,
            "role": "code_worker",
            "goal": "Write code file",
            "requirements": ["Write hello.py"],
            "success_criteria": ["hello.py written"],
            "estimated_minutes": 15,
            "memory_refs": [],
            "branch": "worker/hello-task",
            "retry_count": 0,
            "base_commit": base_commit,
            "write_scope": ["hello.py"],
        },
        "project": {
            "repo_url": str(remote),
            "workspace_path": str(workspace),
            "base_branch": "main",
        },
        "memories": [],
    }
    
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "task_package.json").write_text(json.dumps(package), encoding="utf-8")
    
    # 1. Cleanliness check: make workspace dirty
    (workspace / "dirty.txt").write_text("dirty\n", encoding="utf-8")
    
    from unittest.mock import patch, MagicMock
    
    # Mock load_or_lease_package to return the package
    with patch("app.workspace_worker.load_or_lease_package", return_value=(package, False)):
        with patch("app.workspace_worker.request_json") as mock_req:
            args = MagicMock()
            args.command = "python -c \"from pathlib import Path; Path('hello.py').write_text('print(1)', encoding='utf-8')\""
            args.server = "http://127.0.0.1:8080"
            args.worker_id = "workspace-worker-1"
            args.role = "code_worker"
            args.lease_minutes = 30
            args.runs_dir = str(run_dir)
            args.repo_url = str(remote)
            args.workspace = str(workspace)
            args.base_branch = "main"
            args.allow_dirty = False
            args.no_commit = False
            args.push = True
            args.no_report = False
            args.report = True
            args.package = None
            args.task_id = 101
                
            # This should fail/exit with 1 because workspace is dirty
            ret = run_workspace_worker(args)
            assert ret == 1
            
            # Clean workspace
            (workspace / "dirty.txt").unlink()
            
            # Now run successfully
            ret_success = run_workspace_worker(args)
            assert ret_success == 0
            
            # Verify branch check out and head_commit
            assert git_status_files(workspace) == []
            current_branch = git(["branch", "--show-current"], cwd=workspace)
            assert current_branch == "worker/hello-task"
            
            # Remote has the branch pushed
            remote_branches = git(["branch", "--list", "worker/hello-task"], cwd=remote)
            assert "worker/hello-task" in remote_branches

def test_scope_violation_and_changed_files_mismatch(tmp_path: Path, repo: Repository) -> None:
    remote, workspace = make_repo(tmp_path)
    proj = repo.create_project(ProjectCreate(
        name="Smoke Project",
        repo_url=str(remote),
        workspace_path=str(workspace),
        base_branch="main"
    ))
    epic = repo.create_epic(proj["id"], EpicCreate(name="Test Epic", goal="Test Epic Goal"))
    sub_epic = repo.create_sub_epic(epic["id"], SubEpicCreate(name="Test Sub Epic", goal="Test Sub Epic Goal"))
    
    base_commit = git(["rev-parse", "HEAD"], cwd=workspace)
    task = repo.create_task(sub_epic["id"], TaskCreate(
        role="code_worker",
        goal="Update file",
        requirements=["Modify README.md"],
        success_criteria=["README updated"],
        branch="worker/smoke-task-3",
        write_scope=["README.md"]
    ))
    
    leased = repo.lease_next_task("worker-1", "code_worker", 30, requires_project_config=True)
    branch_name = leased["branch"]
    
    # 1. Changed files mismatch: commit changes to file.py, but report changed README.md
    git(["checkout", "-b", branch_name, base_commit], cwd=workspace)
    (workspace / "file.py").write_text("print(2)\n", encoding="utf-8")
    git(["add", "file.py"], cwd=workspace)
    git(["commit", "-m", "Worker commit on file.py"], cwd=workspace)
    head_commit = git(["rev-parse", "HEAD"], cwd=workspace)
    git(["push", "origin", branch_name], cwd=workspace)
    
    report_mismatch = WorkerReportCreate(
        status="success",
        estimated_minutes=15,
        actual_minutes=10,
        productive_minutes=10,
        error_minutes=0,
        retry_count=0,
        files_changed=["README.md"],
        changed_files=["README.md"],
        tests=["test"],
        summary="done",
        head_commit=head_commit
    )
    
    with pytest.raises(ValueError, match="changed_files_mismatch"):
        repo.complete_task(task["id"], "worker-1", report_mismatch)
        
    # Reset task back to running to retry check
    repo.conn.execute("UPDATE tasks SET status = 'running', leased_by = ? WHERE id = ?", ("worker-1", task["id"]))
    repo.conn.commit()
    
    # 2. Scope violation: commit to file.py and report file.py (outside write scope of README.md)
    report_violation = WorkerReportCreate(
        status="success",
        estimated_minutes=15,
        actual_minutes=10,
        productive_minutes=10,
        error_minutes=0,
        retry_count=0,
        files_changed=["file.py"],
        changed_files=["file.py"],
        tests=["test"],
        summary="done",
        head_commit=head_commit
    )
    
    completed = repo.complete_task(task["id"], "worker-1", report_violation)
    assert completed["status"] == "scope_violation"
