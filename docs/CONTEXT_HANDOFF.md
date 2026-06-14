# Context Handoff

This document is the durable handoff note for continuing work after context compaction or a new session.

## Current Goal

Build AI Game Company Server v1.

Target direction:

- Owner uses an expensive model or Codex CLI for design, decomposition, judgment, and review.
- Workers use cheaper API or local models for repeated execution.
- Game project repos are separated from the development server.
- Human intervention should be minimized, but risky decisions require Owner or user approval.

## Current Deployment

- Local workspace: current Codex workspace on the Windows laptop
- GitHub repo: `powerpunch080403/ai-game-company-server`
- Main server target: `powerpunch@100.92.73.19`
- Remote deploy path: `/home/powerpunch/ai-game-company-server`
- Remote API URL: `http://100.92.73.19:8080`
- Remote game demo bare repo: `/home/powerpunch/game-repos/demo-game.git`
- Remote demo workspace: `/home/powerpunch/game-workspaces/demo-game`
- Remote demo worker workspace: `/home/powerpunch/game-workspaces/demo-game-worker`

Do not rely on the remote being available. If the main computer is down, continue local design and repo work.

## Implemented Server Capabilities

- FastAPI server with token auth
- SQLite storage
- Project > Epic > Sub Epic > Task hierarchy
- Memory DB with typed memory
- Task lease, claim, report
- Worker report history
- Task event log
- Owner dashboard
- Owner readiness summary
- Owner run adapter
- Model profile settings API
- API Worker with OpenAI-compatible chat completions
- Workspace Worker for git branch, command run, commit, push, report
- Git merge tool and Owner merge API
- Merge candidate review and merge-next endpoint
- Retry, cancel, release, assign-sub-epic owner operations
- Project tree and task queue review APIs
- DB backup script
- Remote deploy script

## Important Runtime Rules

- `main` branch must not be edited directly by workers.
- Worker branches must start with `worker/`.
- Workspace workers only lease tasks attached to a project with `repo_url` and `workspace_path`.
- Worker report requires a lease or explicit claim by the same worker.
- Successful or merged tasks are protected from retry/cancel.
- API keys should not be stored in DB. Store environment variable names only.

## Current Remote State

Known remote task state after the latest verification:

- Task 1: pending, orphan placeholder, not workspace-ready.
  - Goal: `Create initial Unity repository skeleton`
  - Decision: leave it for now. It should be handled when a real Unity project starts.
- Task 2: success.
- Task 3: success and merged.
- Task 4: success and merged.
- Task 5: canceled verification task.
- Task 6: canceled verification task.

Remote readiness was:

- `ready: true`
- blockers: none
- warning: one pending task is not workspace-ready
- model profiles: `owner`, `code_worker`

## If Context Is Lost

Start with:

```powershell
& 'C:\Program Files\Git\cmd\git.exe' status --short --branch
python -m pytest
```

If remote is available:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\deploy_main_server.ps1 -HostName powerpunch@100.92.73.19 -RemoteDir /home/powerpunch/ai-game-company-server
```

Then verify:

```bash
ssh powerpunch@100.92.73.19 "cd /home/powerpunch/ai-game-company-server && ./scripts/start_server.sh && curl -sS http://127.0.0.1:8080/health"
```

If remote is not available, keep working on:

- design docs
- local tests
- local API behavior
- scripts that do not need the main computer

## User Preferences

- Korean conversation.
- If a decision is truly required, stop and ask.
- If a reasonable default exists, choose it and continue.
- Prefer running code over perfect architecture.
- Cost matters. Expensive models think, cheap models execute.
- Main computer may be unavailable; design work should continue locally.
