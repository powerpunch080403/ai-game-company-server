#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, TypedDict

class ValidationResult(TypedDict):
    valid: bool
    errors: list[str]
    warnings: list[str]

def validate_task_package(package_data: dict[str, Any]) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    
    # Extract task
    task = package_data.get("task")
    if not task:
        # If the JSON is a flat task rather than a package wrapper
        task = package_data

    # 1. Goal check
    goal = task.get("goal", "").strip()
    if not goal:
        errors.append("Goal is empty or missing.")

    # 2. Requirements check
    requirements = task.get("requirements", [])
    if not isinstance(requirements, list) or not requirements:
        errors.append("Requirements must be a non-empty list.")
    else:
        if any(not str(r).strip() for r in requirements):
            errors.append("Requirements contain empty item(s).")

    # 3. Success Criteria check
    success_criteria = task.get("success_criteria", [])
    if not isinstance(success_criteria, list) or not success_criteria:
        errors.append("Success criteria must be a non-empty list.")
    else:
        if any(not str(s).strip() for s in success_criteria):
            errors.append("Success criteria contain empty item(s).")

    # 4. Role check
    role = task.get("role", "").strip()
    if not role:
        errors.append("Role is empty or missing.")

    # 5. Branch check
    branch = task.get("branch", "").strip()
    if not branch:
        errors.append("Branch is empty or missing.")
    elif not branch.startswith("worker/"):
        errors.append(f"Branch name '{branch}' must start with 'worker/'.")

    # 6. Estimated Minutes check
    est_mins = task.get("estimated_minutes")
    if est_mins is None:
        warnings.append("Estimated minutes is missing (defaulting to 15).")
    else:
        try:
            est_mins_val = int(est_mins)
            if est_mins_val > 60:
                errors.append(f"Estimated minutes ({est_mins_val}) exceeds the maximum limit of 60 minutes.")
            elif est_mins_val > 30:
                warnings.append(f"Estimated minutes ({est_mins_val}) is over 30 minutes. Verify if this task can be split.")
        except (ValueError, TypeError):
            errors.append("Estimated minutes must be a valid integer.")

    # 7. Code/Game task evidence check
    role_lower = role.lower()
    is_code_or_game = "code" in role_lower or "test" in role_lower or "game" in goal.lower()
    if is_code_or_game:
        # Search for evidence keywords in requirements or success criteria
        evidence_keywords = ["evidence", "screenshot", "log", "report", "artifact", "output", "결과", "증거", "화면", "캡처"]
        combined_text = " ".join(requirements + success_criteria).lower()
        if not any(kw in combined_text for kw in evidence_keywords):
            warnings.append("Task seems to be a code or game task, but success_criteria/requirements do not explicitly mention evidence (logs, screenshots, reports).")

    # 8. Memory Refs check
    memory_refs = task.get("memory_refs", [])
    if not isinstance(memory_refs, list) or not memory_refs:
        warnings.append("Memory refs is missing or empty. Provide context memory keys if available.")

    # 9. Project config check for workspace tasks
    is_workspace_task = role in ["code_worker", "test_runner"]
    project = package_data.get("project")
    if is_workspace_task:
        if not project:
            errors.append("Workspace task requires project config, but 'project' field is missing or null.")
        else:
            repo_url = project.get("repo_url", "").strip()
            workspace_path = project.get("workspace_path", "").strip()
            if not repo_url or not workspace_path:
                errors.append("Project config is missing repo_url or workspace_path.")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }

def main() -> int:
    parser = argparse.ArgumentParser(description="Validate owner planned task packaging structure.")
    parser.add_argument("file", help="Path to task JSON file.")
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.is_file():
        print(f"Error: File '{file_path}' does not exist.", file=sys.stderr)
        return 1

    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Error parsing JSON: {exc}", file=sys.stderr)
        return 1

    result = validate_task_package(data)
    
    print(f"=== Validation Report for {file_path.name} ===")
    print(f"Status: {'[VALID]' if result['valid'] else '[INVALID]'}")
    
    if result["errors"]:
        print("\n[ERRORS]:")
        for err in result["errors"]:
            print(f"  - {err}")
            
    if result["warnings"]:
        print("\n[WARNINGS]:")
        for warn in result["warnings"]:
            print(f"  - {warn}")

    print("========================================")
    return 0 if result["valid"] else 1

if __name__ == "__main__":
    sys.exit(main())
