from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    db_path: Path
    host: str
    port: int
    default_task_minutes: int
    owner_recall_minutes: int
    api_token: str
    owner_token: str
    worker_token: str
    readonly_token: str
    artifact_token: str
    owner_command: str
    owner_timeout_seconds: int
    owner_runs_dir: Path
    artifact_root: Path
    max_artifact_upload_bytes: int
    context_compact_threshold_tokens: int
    context_warning_tokens: int
    context_chars_per_token: float
    node_id: str = ""
    node_mode: str = "authority"
    discord_bot_token: str = ""
    discord_task_channel_id: str = ""
    allow_unsafe_no_auth: bool = False


def load_settings() -> Settings:
    return Settings(
        db_path=Path(os.getenv("GAME_COMPANY_DB_PATH", "./data/game_company.sqlite3")),
        host=os.getenv("GAME_COMPANY_HOST", "0.0.0.0"),
        port=int(os.getenv("GAME_COMPANY_PORT", "8080")),
        default_task_minutes=int(os.getenv("GAME_COMPANY_DEFAULT_TASK_MINUTES", "15")),
        owner_recall_minutes=int(os.getenv("GAME_COMPANY_OWNER_RECALL_MINUTES", "30")),
        api_token=os.getenv("GAME_COMPANY_API_TOKEN", ""),
        owner_token=os.getenv("GAME_COMPANY_OWNER_TOKEN", ""),
        worker_token=os.getenv("GAME_COMPANY_WORKER_TOKEN", ""),
        readonly_token=os.getenv("GAME_COMPANY_READONLY_TOKEN", ""),
        artifact_token=os.getenv("GAME_COMPANY_ARTIFACT_TOKEN", ""),
        owner_command=os.getenv("GAME_COMPANY_OWNER_COMMAND", ""),
        owner_timeout_seconds=int(os.getenv("GAME_COMPANY_OWNER_TIMEOUT_SECONDS", "900")),
        owner_runs_dir=Path(os.getenv("GAME_COMPANY_OWNER_RUNS_DIR", "./owner-runs")),
        artifact_root=Path(os.getenv("GAME_COMPANY_ARTIFACT_ROOT", "./artifacts")),
        max_artifact_upload_bytes=int(os.getenv("GAME_COMPANY_MAX_ARTIFACT_UPLOAD_BYTES", "104857600")),
        context_compact_threshold_tokens=int(os.getenv("GAME_COMPANY_CONTEXT_COMPACT_THRESHOLD_TOKENS", "260000")),
        context_warning_tokens=int(os.getenv("GAME_COMPANY_CONTEXT_WARNING_TOKENS", "220000")),
        context_chars_per_token=float(os.getenv("GAME_COMPANY_CONTEXT_CHARS_PER_TOKEN", "3.5")),
        node_id=os.getenv("GAME_COMPANY_NODE_ID", ""),
        node_mode=os.getenv("GAME_COMPANY_NODE_MODE", "authority"),
        discord_bot_token=os.getenv("DISCORD_BOT_TOKEN", ""),
        discord_task_channel_id=os.getenv("GAME_COMPANY_DISCORD_TASK_CHANNEL_ID", ""),
        allow_unsafe_no_auth=os.getenv("GAME_COMPANY_ALLOW_UNSAFE_NO_AUTH", "0") == "1",
    )
