from __future__ import annotations

import json
from pathlib import Path
from app.owner_task_validator import validate_task_package

def test_validate_valid_task_package() -> None:
    valid_package = {
        "task": {
            "role": "code_worker",
            "goal": "Implement basic health points",
            "requirements": ["Create health variable", "Add take_damage method"],
            "success_criteria": ["Health points decrease when hit", "Logs confirm reduction evidence"],
            "estimated_minutes": 15,
            "memory_refs": ["health_system_v1"],
            "branch": "worker/health-base",
        },
        "project": {
            "repo_url": "https://github.com/example/game.git",
            "workspace_path": "/tmp/workspace",
        }
    }
    result = validate_task_package(valid_package)
    assert result["valid"] is True
    assert len(result["errors"]) == 0
    assert len(result["warnings"]) == 0

def test_validate_missing_fields() -> None:
    invalid_package = {
        "task": {
            "role": "",
            "goal": "   ",
            "requirements": [],
            "success_criteria": [],
            "branch": "not-starting-with-worker",
            "estimated_minutes": 75,
        }
    }
    result = validate_task_package(invalid_package)
    assert result["valid"] is False
    assert any("Goal is empty" in err for err in result["errors"])
    assert any("Requirements must be a non-empty list" in err for err in result["errors"])
    assert any("Success criteria must be a non-empty list" in err for err in result["errors"])
    assert any("Role is empty" in err for err in result["errors"])
    assert any("must start with 'worker/'" in err for err in result["errors"])
    assert any("exceeds the maximum limit" in err for err in result["errors"])

def test_validate_warnings_triggered() -> None:
    warning_package = {
        "task": {
            "role": "code_worker",
            "goal": "Draw player sprint animation",
            "requirements": ["Draw sprite"],
            "success_criteria": ["Sprite draws correctly"],
            "estimated_minutes": 45,
            "branch": "worker/player-sprint",
            # missing memory_refs
        },
        "project": {
            "repo_url": "https://github.com/example/game.git",
            "workspace_path": "/tmp/workspace",
        }
    }
    result = validate_task_package(warning_package)
    # It has no errors, so valid should be True, but warnings exist
    assert result["valid"] is True
    assert any("is over 30 minutes" in warn for warn in result["warnings"])
    assert any("do not explicitly mention evidence" in warn for warn in result["warnings"])
    assert any("Memory refs is missing or empty" in warn for warn in result["warnings"])

def test_validate_workspace_requires_project() -> None:
    # workspace task but project config is missing
    package = {
        "task": {
            "role": "code_worker",
            "goal": "Fix crash",
            "requirements": ["Inspect log evidence"],
            "success_criteria": ["No crashes"],
            "estimated_minutes": 15,
            "memory_refs": ["crash_db"],
            "branch": "worker/fix-crash",
        }
    }
    result = validate_task_package(package)
    assert result["valid"] is False
    assert any("requires project config" in err for err in result["errors"])
