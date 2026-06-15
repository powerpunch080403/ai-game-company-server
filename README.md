# AI Game Company Server v1

AI Game Company Server is a control server for running an AI-assisted software
development workflow. The first target is game development, but the v1 design
also supports app, web, backend, tool, automation, and plugin projects.

This is not a game runtime server. It is a project control plane:

```text
User / Owner
  -> Project / Epic / Sub Epic / Task planning
  -> Worker task lease and execution
  -> Reports, artifacts, approvals, memory, and git branches
  -> Owner review, retry, cancel, release, merge, or continue
```

The repo is currently public so friends and other AI agents can inspect the
design. Do not put real secrets in this repository.

## Current Status

Estimated v1 completion: about 80%.

Implemented:

- FastAPI server with SQLite storage.
- Project > Epic > Sub Epic > Task hierarchy.
- Typed memory store and search.
- Worker lease, claim, package, report, history, and task event APIs.
- Owner dashboard, readiness, queue review, merge review, and Owner run API.
- API Worker for OpenAI-compatible chat completions.
- Workspace Worker for git branch prep, command execution, commit, push, and report.
- Test Runner wrapper, report mapper, and full test-runner worker loop.
- Worker and Machine Registry APIs with heartbeat.
- Artifact metadata, upload, download, retention fields, and size limit.
- Approval request and one-way decision APIs.
- Role-scoped API tokens.
- Worker command denylist and optional command allowlist.
- FastAPI routes split under `app/api/routes`.
- Discord mapping API.
- Discord bot dry-run router.
- Discord Gateway runtime skeleton.
- Discord context compaction API with 260k estimated-token threshold.
- Discord dry-run bridge to `/owner/runs`.
- Engine-agnostic project template scaffold.

Not implemented yet:

- Production-tested Discord Gateway deployment.
- Automatic Discord thread history fetching.
- Automatic LLM summarization of raw Discord threads.
- Artifact streaming upload for very large files.
- Real always-on systemd deployment.
- Web UI.
- Vector memory search.

## Recommended Reading

- [Architecture Blueprint](docs/ARCHITECTURE_BLUEPRINT.md)
- [Context Handoff](docs/CONTEXT_HANDOFF.md)
- [Roadmap](docs/ROADMAP.md)
- [Server Configuration](docs/SERVER_CONFIGURATION.md)
- [Discord Operator Console](docs/DISCORD_OPERATOR_CONSOLE.md)
- [Discord Bot Setup](docs/DISCORD_BOT_SETUP.md)
- [Context Compaction](docs/CONTEXT_COMPACTION.md)
- [Test Runner Contract](docs/TEST_RUNNER_CONTRACT.md)
- [Game Project Template](docs/GAME_PROJECT_TEMPLATE.md)
- [Hardware Environment](docs/HARDWARE_ENVIRONMENT.md)

## Quick Start

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m app.seed
./scripts/run_dev.sh
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m app.seed
.\scripts\run_dev.ps1
```

Open API docs:

```text
http://localhost:8080/docs
```

Run tests:

```bash
python -m pytest
```

## Environment

Copy `.env.example` to `.env` for local configuration.

Important settings:

```env
GAME_COMPANY_DB_PATH=./data/game_company.sqlite3
GAME_COMPANY_HOST=0.0.0.0
GAME_COMPANY_PORT=8080

GAME_COMPANY_API_TOKEN=change-me-before-external-access
GAME_COMPANY_OWNER_TOKEN=
GAME_COMPANY_WORKER_TOKEN=
GAME_COMPANY_READONLY_TOKEN=
GAME_COMPANY_ARTIFACT_TOKEN=

GAME_COMPANY_ARTIFACT_ROOT=./artifacts
GAME_COMPANY_MAX_ARTIFACT_UPLOAD_BYTES=104857600

GAME_COMPANY_CONTEXT_COMPACT_THRESHOLD_TOKENS=260000
GAME_COMPANY_CONTEXT_WARNING_TOKENS=220000
GAME_COMPANY_CONTEXT_CHARS_PER_TOKEN=3.5

GAME_COMPANY_OWNER_COMMAND=
GAME_COMPANY_OWNER_TIMEOUT_SECONDS=900
GAME_COMPANY_OWNER_RUNS_DIR=./owner-runs

GAME_COMPANY_WORKER_API_BASE_URL=https://api.openai.com/v1
GAME_COMPANY_WORKER_API_KEY=
GAME_COMPANY_WORKER_MODEL=

GAME_COMPANY_DISCORD_SERVER_TOKEN=
DISCORD_BOT_TOKEN=
DISCORD_APPLICATION_ID=
```

If any API token is configured, non-public API requests must include:

```text
Authorization: Bearer your-token
```

Token roles:

- `GAME_COMPANY_API_TOKEN`: legacy/admin break-glass token.
- `GAME_COMPANY_OWNER_TOKEN`: Owner and operational actions.
- `GAME_COMPANY_WORKER_TOKEN`: task lease, claim, report, heartbeat, package read.
- `GAME_COMPANY_READONLY_TOKEN`: `GET` requests only.
- `GAME_COMPANY_ARTIFACT_TOKEN`: artifact endpoints only.

## Main Concepts

Owner:

- Talks with the user.
- Designs project direction.
- Breaks work into tasks.
- Reviews reports and decides retry, cancel, release, merge, or continue.

API Worker:

- Uses OpenAI-compatible API calls.
- Helps with summaries, drafts, analysis, and lightweight generation.
- Does not directly own task decomposition.

Workspace Worker:

- Leases a task.
- Prepares a `worker/*` git branch.
- Runs a configured command inside the project workspace.
- Commits and optionally pushes changed files.
- Reports result to the server.

Test Runner:

- Runs `.game-company/test_runner.json` phases.
- Writes logs and `test-runner-report.json`.
- Maps local report data into the server worker report contract.

Discord Bot:

- v1 operator console bridge.
- Dry-run router is implemented.
- Gateway runtime skeleton is implemented.

## Worker Runner

Create a task package only:

```bash
./scripts/run_worker.sh --worker-id code-1 --role code_worker --dry-run
```

Run a command and report:

```bash
./scripts/run_worker.sh --worker-id code-1 --role code_worker --command "python --version"
```

Windows:

```powershell
.\scripts\run_worker.ps1 --worker-id code-1 --role code_worker --dry-run
```

## API Worker

Required environment:

```env
GAME_COMPANY_WORKER_API_BASE_URL=https://api.openai.com/v1
GAME_COMPANY_WORKER_API_KEY=your-api-key
GAME_COMPANY_WORKER_MODEL=your-worker-model
```

Dry-run prompt only:

```bash
./scripts/run_api_worker.sh --worker-id api-code-1 --role code_worker --dry-run
```

Run API call and report:

```bash
./scripts/run_api_worker.sh --worker-id api-code-1 --role code_worker
```

## Workspace Worker

Run a workspace command for the next leased task:

```bash
./scripts/run_workspace_worker.sh \
  --worker-id workspace-code-1 \
  --role code_worker \
  --command "python scripts/apply_task.py"
```

Run a specific task without reporting:

```bash
./scripts/run_workspace_worker.sh \
  --task-id 2 \
  --command "mkdir -p docs && echo hello > docs/worker-test.md"
```

Run a specific task and report:

```bash
./scripts/run_workspace_worker.sh \
  --task-id 2 \
  --report \
  --command "mkdir -p docs && echo hello > docs/worker-test.md"
```

Safety rules:

- Task branches must start with `worker/`.
- Dirty workspaces stop execution by default.
- Existing workspaces with the wrong git origin are rejected.
- Worker shell commands pass through a v1 safety gate.

Optional command allowlist:

```env
GAME_COMPANY_ALLOWED_COMMAND_PREFIXES=python -m pytest,npm test
```

## Test Runner

Run the full test-runner worker loop:

```bash
./scripts/run_test_runner_worker.sh --worker-id test-runner-1
```

Run a specific package locally:

```bash
./scripts/run_test_runner.sh \
  --package runs/workspace-task-12/task_package.json \
  --workspace /path/to/game-workspace
```

Map a local report to server report JSON:

```bash
./scripts/map_test_runner_report.sh \
  --package runs/workspace-task-12/task_package.json \
  --report .game-company/artifacts/task-12/run-20260614T120000Z/test-runner-report.json
```

## Project Template Scaffold

Create a minimal engine-agnostic project repo layout:

```bash
./scripts/create_project_template.sh /path/to/demo-game \
  --name "Demo Game" \
  --type game-basic
```

Windows:

```powershell
.\scripts\create_project_template.ps1 C:\path\to\demo-game `
  --name "Demo Game" `
  --type game-basic
```

Supported types:

```text
game-basic
web-basic
app-basic
backend-basic
tool-basic
automation-basic
plugin-basic
```

The template includes `.game-company/test_runner.json` and `.ai-company/`
metadata for future non-game projects.

## Owner Run

Create an Owner dry-run:

```bash
curl -X POST http://localhost:8080/owner/runs \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "objective":"Break combat system into Epic/Sub Epic/Task",
    "context":"The game engine is undecided.",
    "dry_run":true
  }'
```

Example command adapter:

```env
GAME_COMPANY_OWNER_COMMAND=cat {prompt_file}
```

`GAME_COMPANY_OWNER_COMMAND` may use `{prompt_file}` and `{run_dir}`. If no
placeholder is used, the prompt is passed through standard input.

## Discord Mapping API

Create a mapping from a Discord location to a server conversation:

```bash
curl -X POST http://localhost:8080/discord/mappings \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "discord_guild_id":"guild-1",
    "discord_channel_id":"channel-1",
    "discord_thread_id":"thread-owner-design",
    "project_id":1,
    "conversation_kind":"project",
    "thread_role":"owner-design",
    "created_by":"owner",
    "summary_memory_key":"project:1:thread:thread-owner-design:summary:current",
    "notes":"Owner design thread for this project."
  }'
```

List active mappings:

```bash
curl "http://localhost:8080/discord/mappings?project_id=1&active=true" \
  -H "Authorization: Bearer your-token"
```

## Context Compaction

The server can estimate whether a mapped Discord/Owner conversation is close to
the configured context limit.

Check status:

```bash
curl -X POST http://localhost:8080/discord/mappings/discord_mapping_id/context-status \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "recent_messages":["Owner and AI conversation text..."],
    "estimated_extra_tokens":2000
  }'
```

Defaults:

```text
warning: 220000 estimated tokens
compact: 260000 estimated tokens
```

Store a compact summary:

```bash
curl -X POST http://localhost:8080/discord/mappings/discord_mapping_id/compact \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "summary":"Current compact summary for the thread.",
    "archive_mapping":true,
    "continuation_discord_thread_id":"thread-owner-tasks-part-2"
  }'
```

This is a server-side estimate. It does not directly read Codex CLI's internal
context meter.

## Discord Bot Dry Run

Route a message without real Discord Gateway:

```bash
./scripts/run_discord_bot.sh \
  --guild-id guild-1 \
  --channel-id channel-1 \
  --thread-id thread-owner-design \
  --content "Where are we on combat?" \
  --project-id 1 \
  --conversation-kind project \
  --thread-role owner-tasks
```

Ask the server for context status:

```bash
./scripts/run_discord_bot.sh \
  --guild-id guild-1 \
  --channel-id channel-1 \
  --thread-id thread-owner-design \
  --content "/context" \
  --check-context \
  --estimated-extra-tokens 2000
```

Submit an Owner-routed message as an Owner dry-run:

```bash
./scripts/run_discord_bot.sh \
  --guild-id guild-1 \
  --channel-id channel-1 \
  --thread-id thread-owner-tasks \
  --content "Break this into worker tasks." \
  --submit-owner-run
```

This submits `dry_run=true` by default. Add `--execute-owner-run` only after
`GAME_COMPANY_OWNER_COMMAND` is configured and you really want the command to
run.

## Discord Gateway Runtime

Create the bot in the Discord Developer Portal yourself. Do not share your
Discord account password or bot token in chat.

Set tokens locally in `.env`:

```env
DISCORD_BOT_TOKEN=your-discord-bot-token
DISCORD_APPLICATION_ID=your-discord-application-id
GAME_COMPANY_DISCORD_SERVER_TOKEN=owner-or-admin-token-for-server-api
GAME_COMPANY_SERVER=http://127.0.0.1:8080
```

Check setup:

```bash
./scripts/check_discord_setup.sh
```

Windows:

```powershell
.\scripts\check_discord_setup.ps1
```

Run the Gateway runtime:

```bash
./scripts/run_discord_gateway.sh
```

Windows:

```powershell
.\scripts\run_discord_gateway.ps1
```

Optional safe Owner run storage:

```bash
./scripts/run_discord_gateway.sh --submit-owner-run
```

This stores Owner-routed messages as `dry_run=true`. Add `--execute-owner-run`
only after `GAME_COMPANY_OWNER_COMMAND` is configured and you really want the
Owner command to run.

Discord requirements:

- The bot must be invited to the Discord server.
- Message Content Intent must be enabled for the bot application.
- The bot must be able to read messages and send messages in mapped channels or
  threads.
- Channel/thread ids must be registered through `/discord/mappings`.

## Artifact API

Create metadata:

```bash
curl -X POST http://localhost:8080/artifacts \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "artifact_id":"shot-001",
    "project_id":1,
    "task_id":2,
    "worker_id":"test-runner-1",
    "machine_id":"test_runner_12400_3060",
    "artifact_type":"screenshot",
    "filename":"screen.png",
    "content_type":"image/png",
    "summary":"First visual check",
    "tags":["visual","smoke"],
    "important":true
  }'
```

Upload content:

```bash
curl -X PUT "http://localhost:8080/artifacts/shot-001/content?filename=screen.png&content_type=image/png" \
  -H "Authorization: Bearer your-token" \
  --data-binary "@screen.png"
```

## Approval API

Create an approval request:

```bash
curl -X POST http://localhost:8080/approvals \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "approval_id":"repo-setup-1",
    "project_id":1,
    "target_type":"repo_setup",
    "target_id":"first-project",
    "requested_by":"owner",
    "request_summary":"Create GitHub private repo and project workspace.",
    "risk_summary":"Creates external repo and local workspace.",
    "approval_message":"Say approved to continue."
  }'
```

Decide:

```bash
curl -X POST http://localhost:8080/approvals/repo-setup-1/decision \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "status":"approved",
    "approved_by":"user",
    "approval_message":"Approved."
  }'
```

## Machine Notes

Current known machine plan:

- Main server: i5-14600KF, RTX 4070, 32 GB DDR5, Ubuntu Desktop.
- Planned test runner: i5-12400, RTX 3060.
- Local Windows laptop: development workspace only.

The main computer may be off. Local design, code, and tests should continue
without relying on remote SSH.

## Next Work

Recommended next steps:

1. Test Discord Gateway runtime in a real Discord server.
2. Connect approval conversations.
3. Add richer Discord replies for Owner run results and errors.
4. Add artifact streaming upload.
5. Add systemd unit files after always-on mode is approved.
