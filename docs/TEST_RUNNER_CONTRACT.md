# Test Runner Contract

This document defines the v1 contract for the `test_runner` role.

The test runner is a worker role. It does not decide product direction. It
builds, runs, measures, records artifacts, and reports evidence.

## Goals

- Validate that worker branches are safe to merge.
- Produce repeatable evidence for build, test, and runtime checks.
- Keep the report format compatible with the existing worker report API.
- Support engine-agnostic projects now and Unity later.
- Avoid requiring remote machine availability for local design work.

## Non Goals

- Do not replace Owner review.
- Do not run destructive cleanup outside the configured workspace.
- Do not decide whether warnings block merge in v1.
- Do not require a specific game engine.

## Role

`test_runner` leases tasks like any other worker:

```http
POST /workers/{worker_id}/lease
```

with:

```json
{
  "role": "test_runner",
  "lease_minutes": 30,
  "requires_project_config": true
}
```

It fetches the task package, prepares the project workspace branch, runs the
configured commands, writes artifacts, and reports through:

```http
POST /workers/{worker_id}/tasks/{task_id}/report
```

## Project Test Configuration

In v1, test configuration should live in the game project repository, not in the
server database. The recommended path is:

```text
.game-company/test_runner.json
```

Minimal example:

```json
{
  "version": 1,
  "engine": "undecided",
  "commands": {
    "setup": [],
    "build": ["python --version"],
    "test": [],
    "run": []
  },
  "artifacts": {
    "root": ".game-company/artifacts",
    "logs": ["test-runner.log"],
    "reports": ["test-runner-report.json"]
  },
  "timeouts": {
    "setup_seconds": 300,
    "build_seconds": 900,
    "test_seconds": 900,
    "run_seconds": 300
  }
}
```

If this file is missing, the test runner may fall back to engine-specific
defaults only when the engine is known. If no default exists, it should report
`blocked` with a clear issue.

## Command Phases

The runner executes phases in order:

1. Setup
2. Build
3. Test
4. Run
5. Collect artifacts

Each phase contains zero or more commands.

Rules:

- Stop at the first failed command unless the command is marked optional in a
  future schema.
- Capture stdout and stderr into logs.
- Record command, exit code, duration, and truncated output summary.
- Use the project workspace as the working directory.
- Pass task context through environment variables.

Required environment variables:

```text
GAME_COMPANY_TASK_ID
GAME_COMPANY_TASK_PACKAGE
GAME_COMPANY_WORKSPACE
GAME_COMPANY_TEST_ARTIFACT_DIR
```

Implemented runner wrapper:

```bash
python -m app.test_runner \
  --package runs/workspace-task-12/task_package.json \
  --workspace /path/to/game-workspace
```

Wrapper scripts:

```text
scripts/run_test_runner.sh
scripts/run_test_runner.ps1
```

This wrapper:

- Reads `.game-company/test_runner.json`.
- Creates `.game-company/artifacts/task-{task_id}/run-{timestamp}/`.
- Runs `setup`, `build`, `test`, and `run` commands in order.
- Stops at the first failed command.
- Applies the shared worker command safety gate.
- Writes phase logs and `test-runner-report.json`.
- Returns exit code 0 only when the local report status is `success`.

The full worker loop is also implemented:

```bash
python -m app.test_runner_worker --worker-id test-runner-1
```

Wrapper scripts:

```text
scripts/run_test_runner_worker.sh
scripts/run_test_runner_worker.ps1
```

The worker loop leases or claims a `test_runner` task, prepares the configured
Git workspace branch, runs `app.test_runner`, maps the local report through
`app.test_runner_report`, and submits the resulting worker report unless
`--no-report` is passed.

## Artifact Layout

The default artifact path should be:

```text
.game-company/artifacts/task-{task_id}/run-{timestamp}/
```

Recommended files:

```text
test-runner.log
test-runner-report.json
build.log
test.log
run.log
screenshots/
profiles/
coverage/
```

For visual projects, also support:

```text
screenshots/
videos/
frames/
renders/
scene_snapshots/
```

Visual artifacts should be linked to the task report and Discord preview.

Only lightweight text artifacts should be committed by default. Large binaries,
videos, captures, and build outputs should stay uncommitted unless the task
explicitly asks for them.

## Test Runner Report File

The local artifact report should use this shape:

```json
{
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
      "log": ".game-company/artifacts/task-12/run-20260614T120000Z/build.log"
    }
  ],
  "artifacts": [
    ".game-company/artifacts/task-12/run-20260614T120000Z/test-runner-report.json"
  ],
  "metrics": {
    "build_seconds": 1.2,
    "test_seconds": 0,
    "run_seconds": 0
  },
  "issues": []
}
```

## Server Worker Report Mapping

The server already accepts `WorkerReportCreate`. The test runner maps its local
report into that API.

Implemented helper:

```bash
python -m app.test_runner_report \
  --package runs/workspace-task-12/task_package.json \
  --report .game-company/artifacts/task-12/run-20260614T120000Z/test-runner-report.json
```

Wrapper scripts:

```text
scripts/map_test_runner_report.sh
scripts/map_test_runner_report.ps1
```

The helper converts local `status`, `phases`, `artifacts`, timestamps, and
issues into the existing worker report JSON shape. It does not run engine tests
by itself; it is the contract bridge that a future test runner machine will use
after executing configured commands.

Success:

```json
{
  "status": "success",
  "estimated_minutes": 15,
  "actual_minutes": 5,
  "productive_minutes": 5,
  "error_minutes": 0,
  "retry_count": 0,
  "files_changed": [
    ".game-company/artifacts/task-12/run-20260614T120000Z/test-runner-report.json"
  ],
  "tests": [
    "build: python --version",
    "test-runner-report: .game-company/artifacts/task-12/run-20260614T120000Z/test-runner-report.json"
  ],
  "summary": "Build and smoke checks passed.",
  "issues": ""
}
```

Failure:

```json
{
  "status": "failed",
  "estimated_minutes": 15,
  "actual_minutes": 7,
  "productive_minutes": 2,
  "error_minutes": 5,
  "retry_count": 0,
  "files_changed": [],
  "tests": [
    "build: dotnet test"
  ],
  "summary": "Build failed.",
  "issues": "Command exited 1. See build.log."
}
```

Blocked:

```json
{
  "status": "blocked",
  "estimated_minutes": 15,
  "actual_minutes": 1,
  "productive_minutes": 0,
  "error_minutes": 1,
  "retry_count": 0,
  "files_changed": [],
  "tests": [],
  "summary": "No test runner config found.",
  "issues": "Missing .game-company/test_runner.json and no engine default is available."
}
```

## Status Rules

Return `success` when:

- All required commands exit 0.
- Required artifact report is written.
- No blocking issues were found.

Return `failed` when:

- A command exits non-zero.
- A required build or test cannot complete.
- Runtime smoke check fails.

Return `blocked` when:

- Test configuration is missing.
- Required engine tooling is not installed.
- Project workspace config is missing.
- A required secret/env var is missing.

## Engine Defaults

Engine-agnostic default:

- If `.game-company/test_runner.json` exists, use it.
- If it does not exist, report `blocked`.

Unity later:

- Batchmode compile.
- EditMode tests.
- Optional PlayMode smoke test.
- Capture Editor log as artifact.

Godot later:

- Headless import.
- Script/unit tests if configured.
- Minimal scene run smoke test.

Unreal later:

- Project file generation.
- Build target.
- Automation tests if configured.

## Merge Review Interaction

Current merge review warns when reports have no test evidence.

For test runner tasks, the report should always include at least one `tests`
entry. For code worker tasks, Owner can request a separate `test_runner` task
before merge if the code worker evidence is weak.

In v1, warnings remain advisory unless the user later decides to make them
blocking.

## v1 Implementation Plan

1. Keep this document as the contract.
2. Add `.game-company/test_runner.json` to new game templates: implemented in
   `app.project_template` and `scripts/create_project_template.*`.
3. `scripts/run_test_runner.*` wrapper and `app.test_runner` phase execution
   are implemented.
4. Report mapping helper and local unit tests are implemented.
5. Full worker loop for leasing, workspace preparation, phase execution, report
   mapping, and server submission is implemented.
6. Add Unity-specific defaults only after the first real Unity project is
   selected.

Visual execution and MCP tool integration are designed in
[VISUAL_TOOL_INTEGRATION.md](VISUAL_TOOL_INTEGRATION.md).
