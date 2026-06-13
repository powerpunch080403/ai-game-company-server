from __future__ import annotations

from app.config import load_settings
from app.db import connect, init_db
from app.repository import Repository
from app.schemas import MemoryCreate, ModelProfileUpsert, ProjectCreate, TaskCreate


def main() -> None:
    settings = load_settings()
    init_db(settings.db_path)
    repo = Repository(connect(settings.db_path))

    project = repo.create_project(
        ProjectCreate(
            name="Maldhalla-class Game",
            description="AI employee driven game development project.",
        )
    )
    repo.upsert_memory(
        MemoryCreate(
            type="project_rules",
            key="project_rules_v1",
            title="Project operating rules",
            body="Engine: Unity 6\nLanguage: C#\nTask size: <= 15m\nGit: worker/* branches only",
            tags=["rules", "unity", "git"],
        )
    )
    repo.upsert_memory(
        MemoryCreate(
            type="coding_rules",
            key="coding_rules_csharp_v1",
            title="C# coding rules",
            body="Classes use PascalCase. Private fields use _camelCase. Avoid new singletons unless approved.",
            tags=["rules", "csharp"],
        )
    )
    repo.upsert_model_profile(
        ModelProfileUpsert(
            role="owner",
            provider="codex-cli",
            model="configured-by-command",
            api_key_env="",
            notes="Owner currently runs through GAME_COMPANY_OWNER_COMMAND.",
        )
    )
    repo.upsert_model_profile(
        ModelProfileUpsert(
            role="code_worker",
            provider="openai-compatible",
            model="GAME_COMPANY_WORKER_MODEL",
            base_url="GAME_COMPANY_WORKER_API_BASE_URL",
            api_key_env="GAME_COMPANY_WORKER_API_KEY",
            notes="API worker can override this with environment variables in v1.",
        )
    )
    repo.create_task(
        None,
        TaskCreate(
            role="code_worker",
            goal="Create initial Unity repository skeleton",
            requirements=[
                "Create worker branch only",
                "Add basic folder layout",
                "Do not implement gameplay yet",
            ],
            success_criteria=[
                "Repository opens cleanly",
                "No main branch direct edits",
            ],
            estimated_minutes=15,
            memory_refs=["project_rules_v1", "coding_rules_csharp_v1"],
            branch="worker/initial-unity-skeleton",
        ),
    )
    print(f"Seeded project id={project['id']} at {settings.db_path}")


if __name__ == "__main__":
    main()
