from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


MemoryType = Literal[
    "design",
    "project_rules",
    "coding_rules",
    "project_knowledge",
    "art_guide",
    "narrative_guide",
    "task_history",
]

WorkerRole = Literal["code_worker", "image_worker", "voice_worker", "test_runner"]
ModelProfileRole = Literal["owner", "code_worker", "image_worker", "voice_worker", "test_runner"]
TaskStatus = Literal["pending", "running", "success", "failed", "blocked", "canceled"]


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""
    engine: str = ""
    repo_url: str = ""
    workspace_path: str = ""
    base_branch: str = "main"


class ProjectConfigUpdate(BaseModel):
    engine: str = ""
    repo_url: str = ""
    workspace_path: str = ""
    base_branch: str = "main"


class EpicCreate(BaseModel):
    name: str = Field(min_length=1)
    goal: str = ""


class SubEpicCreate(BaseModel):
    name: str = Field(min_length=1)
    goal: str = ""


class MemoryCreate(BaseModel):
    type: MemoryType
    key: str = Field(min_length=1)
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)


class TaskCreate(BaseModel):
    role: WorkerRole
    goal: str = Field(min_length=1)
    requirements: list[str] = Field(min_length=1)
    success_criteria: list[str] = Field(min_length=1)
    estimated_minutes: int = Field(default=15, ge=1, le=240)
    memory_refs: list[str] = Field(default_factory=list)
    branch: str = Field(min_length=1)


class WorkerLeaseRequest(BaseModel):
    role: WorkerRole
    lease_minutes: int = Field(default=30, ge=1, le=240)
    requires_project_config: bool = False


class WorkerTaskClaimRequest(BaseModel):
    lease_minutes: int = Field(default=30, ge=1, le=240)


class WorkerReportCreate(BaseModel):
    status: TaskStatus
    estimated_minutes: int = Field(ge=1)
    actual_minutes: int = Field(ge=0)
    productive_minutes: int = Field(ge=0)
    error_minutes: int = Field(ge=0)
    retry_count: int = Field(ge=0)
    files_changed: list[str] = Field(default_factory=list)
    tests: list[str] = Field(default_factory=list)
    summary: str = ""
    issues: str = ""


class OwnerRunCreate(BaseModel):
    objective: str = Field(min_length=1)
    context: str = ""
    dry_run: bool = False


class OwnerTaskMergeRequest(BaseModel):
    dry_run: bool = True
    push: bool = True


class OwnerTaskRetryRequest(BaseModel):
    reason: str = ""


class OwnerTaskCancelRequest(BaseModel):
    reason: str = ""


class OwnerTaskReleaseRequest(BaseModel):
    reason: str = ""


class OwnerTaskAssignRequest(BaseModel):
    sub_epic_id: int
    reason: str = ""


class ModelProfileUpsert(BaseModel):
    role: ModelProfileRole
    provider: str = ""
    model: str = ""
    base_url: str = ""
    api_key_env: str = ""
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1)
    enabled: bool = True
    notes: str = ""


class MachineUpsert(BaseModel):
    machine_id: str = Field(min_length=1)
    display_name: str = ""
    kind: str = ""
    host_hint: str = ""
    os: str = ""
    workspace_root: str = ""
    artifact_root: str = ""
    status: str = "offline"
    capabilities: list[str] = Field(default_factory=list)
    notes: str = ""


class MachineHeartbeat(BaseModel):
    status: str = "online"
    capabilities: list[str] | None = None
    notes: str | None = None


class WorkerUpsert(BaseModel):
    worker_id: str = Field(min_length=1)
    display_name: str = ""
    role: str = ""
    machine_id: str | None = None
    status: str = "offline"
    capabilities: list[str] = Field(default_factory=list)
    assigned_projects: list[int] = Field(default_factory=list)
    workspace_root: str = ""
    trust_level: str = "limited"
    notes: str = ""


class WorkerHeartbeat(BaseModel):
    status: str = "online"
    role: str | None = None
    machine_id: str | None = None
    capabilities: list[str] | None = None
    workspace_root: str | None = None
    notes: str | None = None


class ArtifactCreate(BaseModel):
    artifact_id: str | None = None
    project_id: int
    task_id: int | None = None
    worker_id: str | None = None
    machine_id: str | None = None
    artifact_type: str = Field(min_length=1)
    filename: str = ""
    content_type: str = ""
    thumbnail_path: str = ""
    summary: str = ""
    tags: list[str] = Field(default_factory=list)
    retention_policy: str = "standard_30_days"
    important: bool = False
    release_or_milestone: bool = False
    discord_message_id: str | None = None
    discord_thread_id: str | None = None
