from __future__ import annotations

import json

from app.test_runner_report import map_test_runner_report


def make_package() -> dict:
    return {
        "task": {
            "id": 12,
            "role": "test_runner",
            "goal": "Run project checks",
            "estimated_minutes": 15,
            "retry_count": 2,
        }
    }


def test_map_successful_test_runner_report() -> None:
    local_report = {
        "version": 1,
        "task_id": 12,
        "status": "success",
        "started_at": "2026-06-14T12:00:00Z",
        "completed_at": "2026-06-14T12:05:00Z",
        "phases": [
            {
                "name": "build",
                "command": "python --version",
                "exit_code": 0,
                "duration_seconds": 1.2,
                "log": ".game-company/artifacts/task-12/run-20260614T120000Z/build.log",
            }
        ],
        "artifacts": [
            ".game-company/artifacts/task-12/run-20260614T120000Z/test-runner-report.json",
        ],
        "issues": [],
    }

    mapped = map_test_runner_report(make_package(), local_report)

    assert mapped["status"] == "success"
    assert mapped["estimated_minutes"] == 15
    assert mapped["actual_minutes"] == 5
    assert mapped["productive_minutes"] == 5
    assert mapped["error_minutes"] == 0
    assert mapped["retry_count"] == 2
    assert mapped["files_changed"] == [
        ".game-company/artifacts/task-12/run-20260614T120000Z/test-runner-report.json"
    ]
    assert mapped["tests"] == [
        "build: python --version",
        "test-runner-report: .game-company/artifacts/task-12/run-20260614T120000Z/test-runner-report.json",
    ]
    assert mapped["issues"] == ""


def test_map_failed_test_runner_report() -> None:
    local_report = {
        "status": "failed",
        "started_at": "2026-06-14T12:00:00Z",
        "completed_at": "2026-06-14T12:07:00Z",
        "phases": [
            {
                "name": "build",
                "command": "dotnet test",
                "exit_code": 1,
                "duration_seconds": 300,
                "log": ".game-company/artifacts/task-12/run-20260614T120000Z/build.log",
            }
        ],
        "artifacts": [
            ".game-company/artifacts/task-12/run-20260614T120000Z/test-runner-report.json",
        ],
        "issues": [],
    }

    mapped = map_test_runner_report(make_package(), local_report)

    assert mapped["status"] == "failed"
    assert mapped["actual_minutes"] == 7
    assert mapped["productive_minutes"] == 0
    assert mapped["error_minutes"] == 7
    assert mapped["files_changed"] == []
    assert mapped["tests"] == [
        "build: dotnet test",
        "test-runner-report: .game-company/artifacts/task-12/run-20260614T120000Z/test-runner-report.json",
    ]
    assert mapped["summary"] == "Test runner failed during build."
    assert mapped["issues"] == "build exited 1. See .game-company/artifacts/task-12/run-20260614T120000Z/build.log."


def test_map_blocked_test_runner_report() -> None:
    local_report = {
        "status": "blocked",
        "phases": [],
        "artifacts": [],
        "metrics": {},
        "issues": ["Missing .game-company/test_runner.json"],
    }

    mapped = map_test_runner_report(make_package(), local_report)

    assert mapped["status"] == "blocked"
    assert mapped["actual_minutes"] == 0
    assert mapped["productive_minutes"] == 0
    assert mapped["error_minutes"] == 0
    assert mapped["tests"] == []
    assert mapped["summary"] == "Test runner is blocked."
    assert mapped["issues"] == "Missing .game-company/test_runner.json"


def test_mapping_output_is_worker_report_json_serializable() -> None:
    mapped = map_test_runner_report(
        make_package(),
        {
            "status": "success",
            "phases": [],
            "artifacts": [],
            "metrics": {},
            "issues": [],
        },
    )

    assert json.loads(json.dumps(mapped))["status"] == "success"
