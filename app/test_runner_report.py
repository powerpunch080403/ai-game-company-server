from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


VALID_STATUSES = {"success", "failed", "blocked"}


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    clean = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(clean)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def duration_minutes(report: dict[str, Any]) -> int:
    started = parse_timestamp(report.get("started_at"))
    completed = parse_timestamp(report.get("completed_at"))
    if started and completed and completed >= started:
        return max(0, round((completed - started).total_seconds() / 60))
    phase_seconds = sum(float(phase.get("duration_seconds") or 0) for phase in report.get("phases", []))
    return max(0, round(phase_seconds / 60))


def normalize_issues(issues: Any) -> str:
    if isinstance(issues, str):
        return issues
    if isinstance(issues, list):
        return "\n".join(str(issue) for issue in issues if str(issue).strip())
    if issues is None:
        return ""
    return str(issues)


def phase_entries(phases: list[dict[str, Any]]) -> list[str]:
    entries: list[str] = []
    for phase in phases:
        name = str(phase.get("name") or "phase")
        command = str(phase.get("command") or "").strip()
        if command:
            entries.append(f"{name}: {command}")
        else:
            entries.append(name)
    return entries


def failed_phase_issue(phases: list[dict[str, Any]]) -> str:
    for phase in phases:
        exit_code = phase.get("exit_code")
        if isinstance(exit_code, int) and exit_code != 0:
            name = str(phase.get("name") or "phase")
            log = str(phase.get("log") or "").strip()
            suffix = f" See {log}." if log else ""
            return f"{name} exited {exit_code}.{suffix}"
    return ""


def report_artifact_entries(artifacts: list[str]) -> list[str]:
    return [f"test-runner-report: {artifact}" for artifact in artifacts if artifact.endswith("test-runner-report.json")]


def summary_for_status(status: str, phases: list[dict[str, Any]]) -> str:
    if status == "success":
        return "Test runner completed successfully."
    if status == "blocked":
        return "Test runner is blocked."
    failed = next((phase for phase in phases if phase.get("exit_code") not in (0, None)), None)
    if failed:
        return f"Test runner failed during {failed.get('name') or 'a phase'}."
    return "Test runner failed."


def map_test_runner_report(package: dict[str, Any], local_report: dict[str, Any]) -> dict[str, Any]:
    task = package["task"]
    status = str(local_report.get("status") or "failed").lower()
    if status not in VALID_STATUSES:
        status = "failed"

    phases = list(local_report.get("phases") or [])
    artifacts = [str(item) for item in local_report.get("artifacts") or []]
    actual_minutes = duration_minutes(local_report)
    phase_tests = phase_entries(phases)
    tests = [*phase_tests, *report_artifact_entries(artifacts)]
    issue_text = normalize_issues(local_report.get("issues"))
    if status == "failed" and not issue_text:
        issue_text = failed_phase_issue(phases)

    error_minutes = 0 if status == "success" else actual_minutes
    productive_minutes = max(0, actual_minutes - error_minutes)
    files_changed = artifacts if status == "success" else []
    summary = str(local_report.get("summary") or "").strip() or summary_for_status(status, phases)

    return {
        "status": status,
        "estimated_minutes": int(task["estimated_minutes"]),
        "actual_minutes": actual_minutes,
        "productive_minutes": productive_minutes,
        "error_minutes": error_minutes,
        "retry_count": int(task.get("retry_count") or 0),
        "files_changed": files_changed,
        "tests": tests,
        "summary": summary,
        "issues": issue_text,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Map a local test runner report to WorkerReportCreate JSON.")
    parser.add_argument("--package", required=True, help="Path to task_package.json.")
    parser.add_argument("--report", required=True, help="Path to local test-runner-report.json.")
    parser.add_argument("--output", default="", help="Optional output path. Defaults to stdout.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    package = json.loads(Path(args.package).read_text(encoding="utf-8"))
    local_report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    mapped = map_test_runner_report(package, local_report)
    output = json.dumps(mapped, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
