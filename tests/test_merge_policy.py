from __future__ import annotations

from app.merge_policy import evaluate_merge_policy

def test_docs_task_policy() -> None:
    # 1. Blocked: no files changed
    task = {"role": "docs_worker", "goal": "Update design doc", "branch": "worker/docs-update"}
    report = {"files_changed": [], "status": "success", "tests": ["validate docs"]}
    result = evaluate_merge_policy(task, report, [])
    assert result["is_blocked"] is True
    assert any("must contain at least one changed file" in r for r in result["block_reasons"])

    # 2. Warning: no test evidence
    report_ok = {"files_changed": ["docs/DESIGN.md"], "status": "success", "tests": []}
    result_warn = evaluate_merge_policy(task, report_ok, [])
    assert result_warn["is_blocked"] is False
    assert any("no test evidence or artifacts" in w for w in result_warn["warnings"])

def test_code_task_policy() -> None:
    task = {"role": "code_worker", "goal": "Fix logic error", "branch": "worker/fix-logic"}
    
    # Blocked: status is not success
    report_fail = {"files_changed": ["src/main.py"], "status": "failed", "tests": ["run pytest"]}
    result_fail = evaluate_merge_policy(task, report_fail, [])
    assert result_fail["is_blocked"] is True
    assert any("cannot be merged with non-success report status" in r for r in result_fail["block_reasons"])

    # Blocked: no files changed
    report_no_change = {"files_changed": [], "status": "success", "tests": ["run pytest"]}
    result_no_change = evaluate_merge_policy(task, report_no_change, [])
    assert result_no_change["is_blocked"] is True
    assert any("must modify files" in r for r in result_no_change["block_reasons"])

    # Warning: missing test/log evidence
    report_warn = {"files_changed": ["src/main.py"], "status": "success", "tests": []}
    result_warn = evaluate_merge_policy(task, report_warn, [])
    assert result_warn["is_blocked"] is False
    assert any("missing test or log evidence" in w for w in result_warn["warnings"])

def test_game_runtime_task_policy() -> None:
    task = {"role": "test_runner", "goal": "Verify Pygame display", "branch": "worker/verify-pygame"}
    
    # Blocked: missing runtime log
    report = {"files_changed": [], "status": "success", "tests": ["compile check"]}
    result_no_log = evaluate_merge_policy(task, report, [])
    assert result_no_log["is_blocked"] is True
    assert any("must have at least one runtime log" in r for r in result_no_log["block_reasons"])

    # Warning: missing screenshot
    artifacts_log_only = [{"filename": "game.log", "artifact_type": "log"}]
    result_no_screenshot = evaluate_merge_policy(task, report, artifacts_log_only)
    assert result_no_screenshot["is_blocked"] is False
    assert any("missing a screenshot artifact" in w for w in result_no_screenshot["warnings"])

    # Blocked: contains crash keyword
    report_crash = {
        "files_changed": [],
        "status": "success",
        "tests": ["run check"],
        "issues": "Found a pygame crash Exception during font render",
    }
    result_crash = evaluate_merge_policy(task, report_crash, artifacts_log_only)
    assert result_crash["is_blocked"] is True
    assert any("contains crash or error signatures" in r for r in result_crash["block_reasons"])

def test_release_task_policy() -> None:
    task = {"role": "code_worker", "goal": "Deploy production build", "branch": "worker/deploy-v1"}
    report = {"files_changed": ["build/game.zip"], "status": "success", "tests": []}
    
    # Blocked: no approval
    result_no_app = evaluate_merge_policy(task, report, [])
    assert result_no_app["is_blocked"] is True
    assert any("requires an explicit approved decision" in r for r in result_no_app["block_reasons"])

    # Blocked: no build artifact
    approval = {"status": "approved", "approved_by": "user"}
    result_no_build = evaluate_merge_policy(task, report, [], approval)
    assert result_no_build["is_blocked"] is True
    assert any("missing a build/release artifact" in r for r in result_no_build["block_reasons"])

    # Success
    artifacts = [{"filename": "game.zip", "artifact_type": "build"}]
    result_ok = evaluate_merge_policy(task, report, artifacts, approval)
    assert result_ok["is_blocked"] is False
