from __future__ import annotations

import argparse
from pathlib import Path

from app.db import connect, init_db
from app.repository import Repository
from app.schemas import EpicCreate, ModelProfileUpsert, ProjectCreate, SubEpicCreate, TaskCreate, MachineUpsert


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed database for Golden Path rehearsal.")
    parser.add_argument("--db-path", required=True, help="Path to the SQLite database file.")
    parser.add_argument("--repo-url", required=True, help="Git repository URL for the project.")
    parser.add_argument("--workspace-path", required=True, help="Workspace path for the project.")
    parser.add_argument("--base-branch", default="main", help="Base branch (default: main).")
    args = parser.parse_args()

    db_path = Path(args.db_path)
    init_db(db_path)
    repo = Repository(connect(db_path))

    # 1. Upsert model profiles
    repo.upsert_model_profile(
        ModelProfileUpsert(
            role="owner",
            provider="codex-cli",
            model="configured-by-command",
            api_key_env="",
            notes="Owner runs locally via scripts.",
        )
    )
    repo.upsert_model_profile(
        ModelProfileUpsert(
            role="code_worker",
            provider="local",
            model="mock",
            api_key_env="",
            notes="Mock worker for rehearsal.",
        )
    )
    repo.upsert_model_profile(
        ModelProfileUpsert(
            role="test_runner",
            provider="local",
            model="mock",
            api_key_env="",
            notes="Mock test runner for rehearsal.",
        )
    )

    # 2. Register test runner machine
    repo.upsert_machine(
        MachineUpsert(
            machine_id="rehearsal_machine",
            display_name="Rehearsal Machine",
            kind="test_runner",
            host_hint="local",
            os="windows",
            workspace_root=str(Path(args.workspace_path).parent / "workspaces"),
            artifact_root=str(Path(args.workspace_path).parent / "artifacts"),
            status="online",
            capabilities=["pygame", "screenshots", "logs"],
            notes="Golden Path rehearsal machine.",
        )
    )

    # 3. Create project
    project = repo.create_project(
        ProjectCreate(
            name="AI Survival Mini",
            description="Pipeline validation game for Golden Path rehearsal.",
            engine="pygame",
            repo_url=args.repo_url,
            workspace_path=args.workspace_path,
            base_branch=args.base_branch,
        )
    )
    project_id = project["id"]

    # 4. Create Epic & Sub-Epic
    epic = repo.create_epic(
        project_id,
        EpicCreate(
            name="Rehearsal Epic",
            goal="Establish robust automated end-to-end rehearsal.",
        )
    )
    sub_epic = repo.create_sub_epic(
        epic["id"],
        SubEpicCreate(
            name="Golden Path Verification",
            goal="Validate workspace worker and test runner loops.",
        )
    )

    # 5. Create Task
    task = repo.create_task(
        sub_epic["id"],
        TaskCreate(
            role="code_worker",
            goal="Add initial player movement logic stub in src/main.py",
            requirements=[
                "Create a dummy player movement function or variable",
                "Ensure unittest in tests/test_smoke.py passes",
            ],
            success_criteria=[
                "Code compiles successfully",
                "test-runner-report.json lists successful smoke phase",
            ],
            estimated_minutes=15,
            memory_refs=[],
            branch="worker/player-movement-stub",
        )
    )

    print(f"REHEARSAL_SEED_SUCCESS: project_id={project_id}, task_id={task['id']}")


if __name__ == "__main__":
    main()
