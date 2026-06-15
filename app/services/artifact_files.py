from __future__ import annotations

from pathlib import Path
from typing import Any


def safe_artifact_filename(filename: str) -> str:
    cleaned = Path(filename).name.strip()
    return cleaned or "artifact.bin"


def artifact_relative_dir(artifact: dict[str, Any]) -> Path:
    task_segment = f"task-{artifact['task_id']}" if artifact.get("task_id") is not None else "manual"
    return Path(f"project-{artifact['project_id']}") / task_segment / artifact["artifact_id"]
