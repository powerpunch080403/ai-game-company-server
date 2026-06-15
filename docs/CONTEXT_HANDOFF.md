# Context Handoff

This document is the durable handoff note for continuing work after context compaction or a new session.

## Current Goal

Build AI Game Company Server v1.

Target direction:

- Owner uses an expensive model or Codex CLI for design, decomposition, judgment, and review.
- Workers use cheaper API or local models for repeated execution.
- Game/app/web/tool project repos are separated from the development server.
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
- Hardware and machine inventory: `docs/HARDWARE_ENVIRONMENT.md`
- Architecture overview for future AI sessions: `docs/ARCHITECTURE_BLUEPRINT.md`
- Main server specs: Intel Core i5-14600KF, NVIDIA RTX 4070, 32 GB DDR5 RAM,
  Ubuntu Desktop

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
- Worker and Machine Registry APIs
- Machine and Worker heartbeat endpoints
- Worker registry `last_seen_at` updates from task lease, claim, and report
- Artifact metadata, raw upload, and raw download APIs
- Approval/Decision request and decision APIs
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

## Latest Local Design Baselines

Added local v1 contracts:

- `docs/ARCHITECTURE_BLUEPRINT.md`
  - First-read architecture map for future AI sessions.
  - Summarizes implemented capabilities, machine layout, runtime topology,
    role boundaries, Discord operations, memory, artifacts, security, v1 scope,
    v1.5 deferrals, document reading order, and recommended next
    implementation sequence.
- `docs/OWNER_TASK_PLANNING.md`
  - Owner planning output shape.
  - 15-minute task sizing rules.
  - Memory write rules.
  - User decision gates.
- `docs/TEST_RUNNER_CONTRACT.md`
  - `test_runner` lease/report behavior.
  - `.game-company/test_runner.json` project config.
  - Artifact layout and worker report mapping.
- `docs/GAME_PROJECT_TEMPLATE.md`
  - Engine-agnostic minimal game repository layout.
  - `.game-company/project.json`.
  - Template creation flow and later engine migration rules.
- `docs/SERVER_CONFIGURATION.md`
  - Main server component placement.
  - Server repo vs game repo/workspace separation.
  - Owner/API Worker/Workspace Worker/Test Runner execution model.
  - SQLite, network, secret, backup, recovery, and systemd design.
- `docs/HARDWARE_ENVIRONMENT.md`
  - Known machine roles, known/unknown hardware details, and do-not-assume
    rules for the local Windows workspace, main server, test runner machine,
    future friend workers, and future GPU/local LLM workers.
- `docs/SERVER_CONFIGURATION_DECISIONS.md`
  - User decision questions for workspace/worker placement, network exposure,
    database choice, Owner invocation, model strategy, test runner placement,
    and backup retention.
  - Current direction: v1 starts simple but leaves room for multiple friends and
    multiple servers later; worker services are managed separately; public access
    is desired behind HTTPS/token auth; SQLite stays for v1; API Worker uses
    OpenAI-compatible API first; Test Runner is designed around an i5-12400 /
    RTX 3060 test machine; backup starts with daily 7-day plus weekly 4-week
    retention.
- `docs/DISCORD_OPERATOR_CONSOLE.md`
  - Discord is the v1 operator console for alerts, approvals, Owner
    conversation, worker summaries, and artifacts.
  - Discord uses a new server.
  - Channel structure is operations + project channels.
  - Project conversations stay inside project threads.
  - `#owner-room` is for casual/general Owner conversation and can answer
    project status by querying server state.
  - Project threads share project memory, while context windows use summaries,
    scoped memory, and recent relevant messages instead of raw full chat logs.
  - User/Owner conversation and AI-internal conversation are separated.
  - Long threads should be summarized, archived, and continued rather than
    cleared or deleted.
  - Current transparency decision: each project should have AI-internal
    discussion threads; humans can see internal AI dialogue and attachments,
    but AI prompts should use summaries by default to control token use.
  - Current role boundary: project threads split Owner/user design
    (`owner-design`) from Owner/user task planning (`owner-tasks`) and AI
    internal coordination (`ai-internal`). Owner owns task creation and
    decomposition. API Worker is only a helper for summaries, logs, drafts, and
    research.
  - New project defaults: Owner infers project type, asks only if ambiguous,
    creates Discord project channel/default threads and server Project record,
    then posts GitHub repo/template/workspace setup to `#approval-inbox`.
    Approved real projects create GitHub private repos automatically; temporary
    projects may use local bare repos.
  - Default project threads: `owner-design`, `owner-tasks`, `decisions`,
    `ai-internal`, `artifacts`, `test-runner`.
  - Decision style: use recommended default bundles and ask separately only for
    high-risk decisions.
  - Approval style: `#approval-inbox` acts like a manager approval inbox.
    Natural-language approval with Owner is primary; buttons are optional
    helpers. Risky actions require a clear approval request and decision log.
  - Approval gates are judgment-based, not exhaustive checklists. Owner should
    stop for risky, costly, security-sensitive, public, destructive,
    hard-to-reverse, direction-changing, main/release-impacting, or ambiguous
    actions.
  - Natural-language understanding is preferred over rigid single-intent
    classification. Owner can split one message into multiple actions, while
    storage/search uses actions, tags, decisions, and summaries.
- `docs/LONG_TERM_PROJECT_MEMORY.md`
  - Long-term memory design for games, apps, web projects, tools, and servers.
  - Each project keeps status, architecture, decision, thread summary, artifact,
    and change summary memories.
  - Every meaningful modification should leave a searchable summary with task id,
    commit hash, changed files, reason, tests, issues, and tags.
  - Months-old changes should be found through project memory, change summaries,
    task reports, and git history rather than raw Discord logs.
  - Search should be tag-first: infer tags such as project/type/task/thread/actor
    /status/area/tool/repo/commit/date, filter candidates, then expand summaries,
    bodies, and original sources only as needed.
  - Retention: summaries, decisions, change logs, task reports, and git
    references are kept forever. Large artifact originals are kept 30 days by
    default, while important and release/milestone artifacts are kept forever.
- `docs/VISUAL_TOOL_INTEGRATION.md`
  - Visual feedback loop for games, apps, and web projects.
  - Test Runner captures screenshots/videos/logs and posts Discord previews.
  - 12400 / RTX 3060 machine is the first visual/test execution machine.
  - Blender, browser, game engine, profiler, and build/test tools can later be
    connected through MCP-style adapters.
- `docs/WORKER_REGISTRY_AND_SCHEMA.md`
  - Discord Bot runs as a separate process/service and uses FastAPI APIs only.
  - Artifact uploads go to main server storage, separated by project.
  - GitHub repo creation uses GitHub CLI login first, after approval.
  - Discord is the primary human operation interface; public HTTPS UI/API is
    added later when needed, and raw `:8080` exposure is forbidden.
  - Defines minimal worker/machine registry and Discord/approval/artifact/memory
    schema direction for v1.

Implemented after the baseline design:

- Worker/Machine Registry API:
  - `PUT /registry/machines/{machine_id}`
  - `GET /registry/machines`
  - `GET /registry/machines/{machine_id}`
  - `POST /registry/machines/{machine_id}/heartbeat`
  - `PUT /registry/workers/{worker_id}`
  - `GET /registry/workers`
  - `GET /registry/workers/{worker_id}`
  - `POST /registry/workers/{worker_id}/heartbeat`
- Existing worker lease, claim, and report calls now create/touch worker
  registry rows and update `last_seen_at`.
- Artifact API:
  - `POST /artifacts`
  - `GET /artifacts`
  - `GET /artifacts/{artifact_id}`
  - `PUT /artifacts/{artifact_id}/content`
  - `GET /artifacts/{artifact_id}/content`
  - Content is stored under `GAME_COMPANY_ARTIFACT_ROOT`, separated by project
    and task/manual segment.
- Approval API:
  - `POST /approvals`
  - `GET /approvals`
  - `GET /approvals/{approval_id}`
  - `POST /approvals/{approval_id}/decision`
  - Decisions are one-way from `pending`; repeated decisions return conflict.

These contracts deliberately do not choose the first real game engine and do not
make merge warnings blocking. Ask the user before making either decision.

`app/owner_runner.py` has also been updated so Owner dry runs request the new
planning output shape and decision-gate behavior.

## User Preferences

- Korean conversation.
- If a decision is truly required, stop and ask.
- If a reasonable default exists, choose it and continue.
- Prefer running code over perfect architecture.
- Cost matters. Expensive models think, cheap models execute.
- Main computer may be unavailable; design work should continue locally.
