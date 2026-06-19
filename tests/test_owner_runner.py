from __future__ import annotations

from pathlib import Path

from app.config import Settings
from app.owner_runner import run_owner_command


def test_run_owner_command_sends_utf8_stdin(tmp_path: Path) -> None:
    script = tmp_path / "echo_stdin.py"
    script.write_text(
        "import sys\n"
        "data = sys.stdin.read()\n"
        "print(data)\n",
        encoding="utf-8",
    )
    settings = Settings(
        db_path=tmp_path / "db.sqlite3",
        host="127.0.0.1",
        port=8080,
        default_task_minutes=15,
        owner_recall_minutes=30,
        api_token="",
        owner_token="",
        worker_token="",
        readonly_token="",
        artifact_token="",
        owner_command=f'python "{script}"',
        owner_timeout_seconds=30,
        owner_runs_dir=tmp_path / "owner-runs",
        artifact_root=tmp_path / "artifacts",
        max_artifact_upload_bytes=1024,
        context_compact_threshold_tokens=260000,
        context_warning_tokens=220000,
        context_chars_per_token=3.5,
    )

    exit_code, stdout, stderr = run_owner_command(settings, "안녕, Owner", tmp_path / "run")

    assert exit_code == 0
    assert "안녕, Owner" in stdout
    assert stderr == ""
