from __future__ import annotations

from typing import Any, TypedDict

class PolicyEvaluation(TypedDict):
    is_blocked: bool
    block_reasons: list[str]
    warnings: list[str]

def evaluate_merge_policy(
    task: dict[str, Any],
    report: dict[str, Any],
    artifacts: list[dict[str, Any]],
    approval: dict[str, Any] | None = None
) -> PolicyEvaluation:
    block_reasons: list[str] = []
    warnings: list[str] = []

    role = str(task.get("role") or "").lower()
    goal = str(task.get("goal") or "").lower()
    branch = str(task.get("branch") or "").lower()
    
    files_changed = report.get("files_changed") or []
    status = str(report.get("status") or "").lower()
    issues = str(report.get("issues") or "").lower()
    summary = str(report.get("summary") or "").lower()

    # Determine Task Type
    is_docs = "docs" in role or "document" in role or "readme" in branch or "docs" in branch
    is_release = "release" in role or "build" in role or "deploy" in role or "release" in branch or "deploy" in branch or "build" in branch
    is_game_runtime = role == "test_runner" or "game" in goal or "pygame" in goal or "unity" in goal or "game" in branch or "runtime" in branch
    # If not docs, release, or game, it's code by default, or code task if explicitly marked
    is_code = not is_docs and not is_release and ("code" in role or "worker" in role or not is_game_runtime)

    # Helper checks
    has_changed_files = len(files_changed) > 0
    has_test_evidence = len(report.get("tests") or []) > 0 or len(artifacts) > 0
    
    # 1. Docs Task Policy
    if is_docs:
        if not has_changed_files:
            block_reasons.append("Docs task must contain at least one changed file.")
        if not has_test_evidence:
            warnings.append("Docs task has no test evidence or artifacts associated.")

    # 2. Code Task Policy
    if is_code:
        if not has_changed_files:
            block_reasons.append("Code task must modify files. No files were changed.")
        if status != "success":
            block_reasons.append(f"Code task cannot be merged with non-success report status: '{status}'.")
        
        # Test / Log evidence
        has_log_or_test_artifact = any(
            "log" in str(art.get("artifact_type") or "").lower() or 
            "test" in str(art.get("artifact_type") or "").lower() or
            str(art.get("filename") or "").endswith((".log", ".json", ".xml"))
            for art in artifacts
        )
        if not has_test_evidence and not has_log_or_test_artifact:
            warnings.append("Code task is missing test or log evidence. Verify test runner output.")

    # 3. Game Runtime Task Policy
    if is_game_runtime:
        # Runtime log check
        has_runtime_log = any(
            str(art.get("filename") or "").endswith(".log") or 
            "log" in str(art.get("artifact_type") or "").lower()
            for art in artifacts
        )
        if not has_runtime_log:
            block_reasons.append("Game runtime task must have at least one runtime log (.log) artifact.")
            
        # Screenshot check
        has_screenshot = any(
            str(art.get("filename") or "").lower().endswith((".png", ".jpg", ".jpeg")) or
            "screenshot" in str(art.get("artifact_type") or "").lower() or
            "image" in str(art.get("artifact_type") or "").lower()
            for art in artifacts
        )
        if not has_screenshot:
            warnings.append("Game runtime task is missing a screenshot artifact. Adding visual evidence is recommended.")
            
        # Crash/Error check
        crash_keywords = ["crash", "exception", "traceback", "fatal error", "segfault", "크래시"]
        has_crash = any(kw in issues or kw in summary for kw in crash_keywords)
        if has_crash:
            block_reasons.append("Game runtime task contains crash or error signatures in the report issues/summary.")

    # 4. Release/Build/Deploy Task Policy
    if is_release:
        # Check approval
        if not approval or str(approval.get("status") or "").lower() != "approved":
            block_reasons.append("Release/Build/Deploy task requires an explicit approved decision.")
            
        # Build artifact check
        has_build_artifact = any(
            str(art.get("filename") or "").lower().endswith((".zip", ".tar.gz", ".app", ".exe", ".pkg", ".apk")) or
            "build" in str(art.get("artifact_type") or "").lower() or
            "release" in str(art.get("artifact_type") or "").lower()
            for art in artifacts
        )
        if not has_build_artifact:
            block_reasons.append("Release/Build/Deploy task is missing a build/release artifact (.zip, .exe, etc.).")

    return {
        "is_blocked": len(block_reasons) > 0,
        "block_reasons": block_reasons,
        "warnings": warnings,
    }
