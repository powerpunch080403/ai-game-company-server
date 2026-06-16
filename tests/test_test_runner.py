from __future__ import annotations

import json
import sys
from pathlib import Path

from app.test_runner import run_test_runner


def write_package(tmp_path: Path, task_id: int = 12) -> Path:
    package_path = tmp_path / "task_package.json"
    package_path.write_text(
        json.dumps(
            {
                "task": {
                    "id": task_id,
                    "role": "test_runner",
                    "goal": "Run configured checks",
                    "estimated_minutes": 15,
                    "retry_count": 0,
                }
            }
        ),
        encoding="utf-8",
    )
    return package_path


def write_config(workspace: Path, commands: dict[str, list[str]]) -> None:
    config_path = workspace / ".game-company" / "test_runner.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(
            {
                "version": 1,
                "engine": "undecided",
                "commands": commands,
                "artifacts": {"root": ".game-company/artifacts"},
                "timeouts": {
                    "setup_seconds": 30,
                    "build_seconds": 30,
                    "test_seconds": 30,
                    "run_seconds": 30,
                },
            }
        ),
        encoding="utf-8",
    )


def test_run_test_runner_success_writes_report_and_logs(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    package_path = write_package(tmp_path)
    command = (
        f'"{sys.executable}" -c "from pathlib import Path; import os; '
        "assert Path(os.environ['GAME_COMPANY_TASK_PACKAGE']).is_file(); "
        "Path(os.environ['GAME_COMPANY_TEST_ARTIFACT_DIR'], 'marker.txt')"
        ".write_text(os.environ['GAME_COMPANY_TASK_ID'], encoding='utf-8')\""
    )
    write_config(workspace, {"setup": [], "build": [command], "test": [], "run": []})

    report = run_test_runner(package_path, workspace)

    assert report["status"] == "success"
    assert report["task_id"] == 12
    assert len(report["phases"]) == 1
    assert report["phases"][0]["name"] == "build"
    assert report["phases"][0]["exit_code"] == 0
    report_path = workspace / report["artifacts"][0]
    assert report_path.is_file()
    assert (report_path.parent / "build.log").is_file()
    assert (report_path.parent / "marker.txt").read_text(encoding="utf-8") == "12"


def test_run_test_runner_failure_stops_after_failed_command(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    package_path = write_package(tmp_path)
    failing = f'"{sys.executable}" -c "raise SystemExit(3)"'
    should_not_run = f'"{sys.executable}" -c "from pathlib import Path; Path(\'should-not-run.txt\').write_text(\'bad\')"'
    write_config(workspace, {"setup": [], "build": [failing], "test": [should_not_run], "run": []})

    report = run_test_runner(package_path, workspace)

    assert report["status"] == "failed"
    assert len(report["phases"]) == 1
    assert report["phases"][0]["exit_code"] == 3
    assert report["issues"] == [f"build exited 3. See {report['phases'][0]['log']}."]
    assert not (workspace / "should-not-run.txt").exists()


def test_run_test_runner_missing_config_returns_blocked_report(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    package_path = write_package(tmp_path)

    report = run_test_runner(package_path, workspace)

    assert report["status"] == "blocked"
    assert report["phases"] == []
    assert "Missing .game-company/test_runner.json" in report["issues"][0]
    assert (workspace / report["artifacts"][0]).is_file()


def test_run_test_runner_accepts_bom_json_files(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    package_path = write_package(tmp_path)
    package_text = package_path.read_text(encoding="utf-8")
    package_path.write_text(package_text, encoding="utf-8-sig")
    config_path = workspace / ".game-company" / "test_runner.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(
            {
                "version": 1,
                "engine": "undecided",
                "commands": {"setup": [], "build": ["python --version"], "test": [], "run": []},
                "artifacts": {"root": ".game-company/artifacts"},
                "timeouts": {"build_seconds": 30},
            }
        ),
        encoding="utf-8-sig",
    )

    report = run_test_runner(package_path, workspace)

    assert report["status"] == "success"
    assert report["phases"][0]["name"] == "build"
