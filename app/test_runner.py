from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from app.command_safety import CommandSafetyError, validate_shell_command

load_dotenv()

PHASES = ("setup", "build", "test", "run")
DEFAULT_CONFIG_PATH = ".game-company/test_runner.json"


def utc_now() -> datetime:
    return datetime.now(UTC)


def timestamp_slug(value: datetime) -> str:
    return value.strftime("%Y%m%dT%H%M%SZ")


def iso_z(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def relative_posix(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def load_task_package(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_test_config(workspace: Path, config_path: str = DEFAULT_CONFIG_PATH) -> dict[str, Any] | None:
    path = workspace / config_path
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def artifact_dir_for_run(workspace: Path, config: dict[str, Any] | None, task_id: int, started_at: datetime) -> Path:
    artifact_root = ".game-company/artifacts"
    if config:
        artifact_root = str(config.get("artifacts", {}).get("root") or artifact_root)
    return workspace / artifact_root / f"task-{task_id}" / f"run-{timestamp_slug(started_at)}"


def command_timeout(config: dict[str, Any], phase_name: str) -> int:
    timeouts = config.get("timeouts") or {}
    return int(timeouts.get(f"{phase_name}_seconds") or 900)


def commands_for_phase(config: dict[str, Any], phase_name: str) -> list[str]:
    commands = config.get("commands") or {}
    values = commands.get(phase_name) or []
    return [str(command) for command in values]


def phase_log_path(artifact_dir: Path, phase_name: str, index: int, command_count: int) -> Path:
    if command_count <= 1:
        return artifact_dir / f"{phase_name}.log"
    return artifact_dir / f"{phase_name}-{index + 1}.log"


def run_phase_command(
    command: str,
    phase_name: str,
    workspace: Path,
    package_path: Path,
    artifact_dir: Path,
    log_path: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    started = time.monotonic()
    try:
        validate_shell_command(command)
    except CommandSafetyError as exc:
        output = f"Command blocked by safety policy: {exc}\n"
        log_path.write_text(output, encoding="utf-8")
        return {
            "name": phase_name,
            "command": command,
            "exit_code": 126,
            "duration_seconds": 0,
            "log": relative_posix(log_path, workspace),
        }

    env = os.environ.copy()
    env["GAME_COMPANY_TASK_PACKAGE"] = str(package_path)
    env["GAME_COMPANY_WORKSPACE"] = str(workspace)
    env["GAME_COMPANY_TEST_ARTIFACT_DIR"] = str(artifact_dir)
    task_id = load_task_package(package_path)["task"]["id"]
    env["GAME_COMPANY_TASK_ID"] = str(task_id)

    try:
        completed = subprocess.run(
            command,
            cwd=workspace,
            env=env,
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_seconds,
            check=False,
        )
        output = completed.stdout
        exit_code = completed.returncode
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") + f"\nCommand timed out after {timeout_seconds}s.\n"
        exit_code = 124

    log_path.write_text(output, encoding="utf-8")
    return {
        "name": phase_name,
        "command": command,
        "exit_code": exit_code,
        "duration_seconds": round(time.monotonic() - started, 3),
        "log": relative_posix(log_path, workspace),
    }


def blocked_report(package: dict[str, Any], workspace: Path, issue: str) -> dict[str, Any]:
    now = utc_now()
    task = package["task"]
    artifact_dir = artifact_dir_for_run(workspace, None, int(task["id"]), now)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    report_path = artifact_dir / "test-runner-report.json"
    report = {
        "version": 1,
        "task_id": task["id"],
        "status": "blocked",
        "started_at": iso_z(now),
        "completed_at": iso_z(now),
        "phases": [],
        "artifacts": [relative_posix(report_path, workspace)],
        "metrics": {},
        "issues": [issue],
        "summary": "No test runner config found.",
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def run_test_config(
    package: dict[str, Any],
    package_path: Path,
    workspace: Path,
    config: dict[str, Any],
    started_at: datetime | None = None,
) -> dict[str, Any]:
    started = started_at or utc_now()
    task = package["task"]
    artifact_dir = artifact_dir_for_run(workspace, config, int(task["id"]), started)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    phases: list[dict[str, Any]] = []
    issues: list[str] = []
    metrics: dict[str, float] = {}
    status = "success"

    for phase_name in PHASES:
        commands = commands_for_phase(config, phase_name)
        phase_seconds = 0.0
        for index, command in enumerate(commands):
            log_path = phase_log_path(artifact_dir, phase_name, index, len(commands))
            phase = run_phase_command(
                command,
                phase_name,
                workspace,
                package_path,
                artifact_dir,
                log_path,
                command_timeout(config, phase_name),
            )
            phases.append(phase)
            phase_seconds += float(phase.get("duration_seconds") or 0)
            if int(phase["exit_code"]) != 0:
                status = "failed"
                issues.append(f"{phase_name} exited {phase['exit_code']}. See {phase['log']}.")
                break
        metrics[f"{phase_name}_seconds"] = round(phase_seconds, 3)
        if status != "success":
            break

    completed = utc_now()
    report_path = artifact_dir / "test-runner-report.json"
    report = {
        "version": 1,
        "task_id": task["id"],
        "status": status,
        "started_at": iso_z(started),
        "completed_at": iso_z(completed),
        "phases": phases,
        "artifacts": [relative_posix(report_path, workspace)],
        "metrics": metrics,
        "issues": issues,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def run_test_runner(package_path: Path, workspace: Path, config_path: str = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    package_path = package_path.resolve()
    workspace = workspace.resolve()
    package = load_task_package(package_path)
    config = load_test_config(workspace, config_path)
    if config is None:
        return blocked_report(
            package,
            workspace,
            f"Missing {config_path} and no engine default is available.",
        )
    return run_test_config(package, package_path, workspace, config)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run configured project test phases and write test-runner-report.json.")
    parser.add_argument("--package", required=True, help="Path to task_package.json.")
    parser.add_argument("--workspace", required=True, help="Project workspace path.")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Workspace-relative test runner config path.")
    parser.add_argument("--output", default="", help="Optional copy of the local report JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run_test_runner(Path(args.package), Path(args.workspace), args.config)
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0 if report["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
