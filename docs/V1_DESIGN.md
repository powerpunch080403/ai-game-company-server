# AI Game Company Server v1 Design

## Purpose

This server coordinates an AI game development company:

- Owner decomposes requests into projects, epics, sub-epics, and tasks.
- Workers execute small tasks.
- Test runners validate builds and runtime behavior.
- Memory stores decisions and project knowledge, not raw conversation logs.

The first objective is a working automation loop, not a perfect platform.

## Core Philosophy

Use expensive intelligence sparingly.

- Owner = thinking, decomposition, review, merge decisions.
- Worker = execution, repetition, coding, simple fixes.
- Test Runner = build, run, profile, measure.

The server must make the cheap execution path easy and keep high-cost Owner calls rare.

## Current Architecture

```mermaid
flowchart TD
    User["User"] --> Owner["Owner"]
    Owner --> Server["AI Game Company Server"]
    Server --> DB["SQLite DB"]
    Server --> Queue["Task Queue"]
    Queue --> APIWorker["API Worker"]
    Queue --> WorkspaceWorker["Workspace Worker"]
    WorkspaceWorker --> GameRepo["Game Project Repo"]
    WorkspaceWorker --> Reports["Worker Reports"]
    Reports --> Server
    Server --> Merge["Owner Merge API"]
    Merge --> GameRepo
```

## Data Model

### Project Hierarchy

- Project
- Epic
- Sub Epic
- Task

### Task Contract

Each task must include:

- Goal
- Requirements
- Success Criteria
- Estimated Time
- Memory Refs
- Branch

### Memory Types

- design
- project_rules
- coding_rules
- project_knowledge
- art_guide
- narrative_guide
- task_history

### Model Profiles

Model profiles define role-level model settings:

- owner
- code_worker
- image_worker
- voice_worker
- test_runner

Secrets are not stored. Store env var names such as `GAME_COMPANY_WORKER_API_KEY`.

## Worker Lifecycle

Normal workspace worker flow:

1. Lease task requiring project config.
2. Fetch task package.
3. Prepare git workspace.
4. Checkout or create `worker/*` branch.
5. Run command.
6. Commit changed files.
7. Optionally push worker branch.
8. Report result.

Specific task flow:

1. Claim task.
2. Fetch package.
3. Run workspace command.
4. Report if requested.

Reports are rejected unless the reporting worker has leased or claimed the task.

## Owner Lifecycle

Owner responsibilities:

- Create hierarchy and tasks.
- Inspect queue readiness.
- Inspect worker reports.
- Retry, release, cancel, or assign tasks.
- Merge successful worker branches.
- Learn from task history.

Owner should not directly code except for small control-plane fixes.

## Merge Policy

Current merge requirements:

- Task status is `success`.
- Latest worker report is `success`.
- Task belongs to a project.
- Project has `repo_url` and `workspace_path`.
- Branch starts with `worker/`.
- Task was not already merged.

Warnings:

- Report has no changed files.
- Report has no test evidence.
- Report contains issues.

Future stricter policy can block merge on warnings.

## Readiness Meaning

`/owner/readiness` returns ready if:

- owner profile exists.
- code_worker profile exists.
- no failed tasks require review.

Warnings do not block readiness:

- running tasks exist.
- pending tasks are not workspace-ready.

## Known Deliberate Placeholder

Task 1 is intentionally left as a pending orphan:

- Goal: `Create initial Unity repository skeleton`
- Reason: it should be revisited when the real Unity project starts.
- Current behavior: workspace workers skip it because it is not project-attached.

Do not auto-cancel or auto-assign Task 1 without user approval.
