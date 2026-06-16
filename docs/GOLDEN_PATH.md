# Golden Path v1

This document defines the first end-to-end loop the server must make reliable
before the first portfolio game starts.

The goal is not to add more features. The goal is to prove that the AI
development pipeline can finish one real task in a separate project repository
and leave enough evidence for Owner review.

## Core Loop

Golden Path:

```text
Project created
-> Epic / Sub Epic / Task created
-> Workspace Worker leases task
-> Worker receives task package
-> Worker creates worker/* branch
-> Worker changes files
-> Worker commits changes
-> Test Runner runs validation
-> Logs / screenshots / reports are stored as artifacts
-> Worker submits report
-> Owner reviews merge candidate
-> Owner merges or retries
```

The server is considered ready for the first real development rehearsal when
this loop works against a small demo project repo.

## Current Coverage

Already implemented:

- Project, Epic, Sub Epic, and Task records.
- Worker lease, claim, package, and report APIs.
- Workspace Worker branch preparation, command execution, commit, and push.
- Test Runner phase execution and local report mapping.
- Artifact metadata, upload, download, and upload size limits.
- Owner merge candidate review and merge API.
- Retry, cancel, release, and assign operations.
- Role-scoped API tokens and worker command safety checks.

Still needs practical rehearsal:

- One demo game repo that is separate from the server repo.
- One manual Golden Path run using that repo.
- Test Runner preset for the selected demo project type.
- Artifact evidence expectations for code/game/runtime tasks.
- README walkthrough based on the actual rehearsal commands.

## First Demo Project

Use a tiny pipeline validation game, not the portfolio game.

Recommended first project:

```text
Name: AI Survival Mini
Engine/framework: Pygame
Genre: top-down survival / dodge prototype
Goal: survive for 60 seconds
```

Initial feature slices:

- WASD movement.
- Enemy follows player.
- Collision damages health.
- Enemy count increases over time.
- Score/time display.
- Game over screen.
- Restart action.

This is intentionally small. It gives the Owner clear tasks, gives Workspace
Workers simple file changes, and gives the Test Runner something visible to
launch and capture.

Local scaffold command:

```bash
./scripts/create_project_template.sh /path/to/ai-survival-mini \
  --name "AI Survival Mini" \
  --type game-pygame-mini
```

The generated Test Runner preset starts with dependency-light commands:

```text
python -m compileall src tests scripts
python -m unittest discover -s tests
python scripts/smoke_check.py
```

The smoke command does not require Pygame. Install `pygame` later when the
interactive window should be opened.

## Evidence Policy

Golden Path merge review should use evidence, not only a success status.

Recommended v1 rules:

| Task type | Required before merge | v1 behavior |
| --- | --- | --- |
| Docs-only | Worker report with changed files | Warn if no test evidence |
| Code | Worker report with changed files and test/log evidence | Warn if missing evidence |
| Game runtime | Test Runner report plus screenshot or runtime log artifact | Warn now, block later after rehearsal |
| Release/build/deploy | Explicit approval plus build artifact | Block without approval |

Do not make all warnings hard blockers before the first demo rehearsal. Start
with warnings, observe the false positives, then promote the stable rules to
blocking policy.

## June 2026 Stabilization Plan

Target direction:

```text
2026-06-15 to 2026-06-18
  Keep feature growth small. Complete a manual Golden Path run.

2026-06-19 to 2026-06-22
  Add minimal Test Runner presets and artifact evidence checks.

2026-06-23 to 2026-06-27
  Keep Discord at dry-run/status/approval level. Improve Owner planning
  templates and practical README examples.

2026-06-28 to 2026-06-30
  Feature freeze for server v1. Run one end-to-end rehearsal with a sample
  game repo.

Early July 2026
  Start portfolio game development using the stabilized loop.
```

## What To Avoid Before Feature Freeze

Avoid broadening the server before Golden Path is proven:

- Multiple parallel workspace workers.
- Large MCP expansion.
- Unity and Godot automation at the same time.
- Local GPU worker orchestration.
- Vector memory.
- Rich web UI.
- Complex Discord natural-language operations beyond Owner/status/approval.

## Next Implementation Order

1. Add or run a Golden Path e2e test.
2. Create a demo game repo separate from the server repo.
3. Rehearse Workspace Worker branch, commit, report, and merge review.
4. Add a minimal Pygame Test Runner preset.
5. Store screenshot/log/test report artifacts for the rehearsal.
6. Tighten merge policy only after the rehearsal shows which warnings are useful.
7. Update README with the exact commands from the rehearsal.
