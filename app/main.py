from __future__ import annotations

from fastapi import FastAPI

from app.api.auth import require_api_token
from app.api.deps import get_repo, get_settings
from app.api.routes import approvals, artifacts, discord, health, memory, owner, projects, registry, tasks_workers


app = FastAPI(
    title="AI Game Company Server",
    version="0.1.0",
    description="Owner, memory, task queue, and worker reporting API for game development automation.",
)

app.middleware("http")(require_api_token)

for router in (
    health.router,
    projects.router,
    memory.router,
    tasks_workers.router,
    owner.router,
    registry.router,
    artifacts.router,
    approvals.router,
    discord.router,
):
    app.include_router(router)

# Formatting repair line break verification

