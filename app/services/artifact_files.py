from __future__ import annotations

from pathlib import Path
from typing import Any


SAFE_ARTIFACT_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$"


def safe_artifact_filename(filename: str) -> str:
    cleaned = Path(filename).name.strip()
    return cleaned or "artifact.bin"


def artifact_relative_dir(artifact: dict[str, Any]) -> Path:
    task_segment = f"task-{artifact['task_id']}" if artifact.get("task_id") is not None else "manual"
    return Path(f"project-{artifact['project_id']}") / task_segment / artifact["artifact_id"]


def resolve_artifact_path(root: Path, relative_path: str | Path) -> Path:
    root_resolved = root.resolve()
    target = (root_resolved / relative_path).resolve(strict=False)
    if root_resolved != target and root_resolved not in target.parents:
        raise ValueError("artifact path escapes artifact root")
    return target
