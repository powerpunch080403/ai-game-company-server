# Roadmap

## Current Status

Estimated v1 completion: about 80%.

The server can already run the core loop:

1. Create tasks.
2. Lease or claim tasks.
3. Execute API or workspace workers.
4. Report results.
5. Review history.
6. Merge successful worker branches.
7. Retry, cancel, release, or assign tasks.
8. Register machines and workers.
9. Track worker/machine heartbeat and worker last-seen activity.
10. Store artifact metadata and raw artifact files.
11. Store approval requests and one-way approval decisions.
12. Store Discord guild/channel/thread mappings for project operation rooms.
13. Protect APIs with role-scoped Owner, Worker, Readonly, and Artifact tokens.
14. Block dangerous worker shell command patterns and support command allowlists.
15. Limit artifact upload size with a configurable server setting.
16. Split FastAPI endpoints into route modules under `app/api/routes`.
17. Add a dry-run Discord bot routing skeleton against stored mapping APIs.
18. Add Test Runner local report to WorkerReport mapping helper.
19. Add Test Runner configured phase execution wrapper.
20. Add full Test Runner worker loop for lease, workspace prep, phase run,
    report mapping, and server submission.
21. Add engine-agnostic project scaffold tooling with `.game-company` and
    `.ai-company` automation folders.
22. Add Discord thread context compaction API for Codex-style rolling
    summaries, continuation thread mappings, and 260k-token estimate checks.
23. Connect Discord bot dry-run routing to the context-status endpoint.
24. Add Discord bot dry-run Owner run payload and optional safe submission to
    `/owner/runs`.
25. Add Discord Gateway runtime skeleton that reuses the dry-run router and can
    reply to mapped messages.
26. Add Discord bot setup doctor and credential-safe setup guide.
27. Add Golden Path design and an API-level e2e evidence loop test.
28. Add `game-pygame-mini` project scaffold with runnable Test Runner preset.

The next v1 priority is no longer broad feature growth. It is Golden Path
stabilization: make one separate demo project repo complete the task -> worker
-> commit -> test -> artifact -> report -> Owner review -> merge/retry loop.

Detailed target: [GOLDEN_PATH.md](GOLDEN_PATH.md).

## Next Work While Main Computer Is Unavailable

Work that can be done locally:

- Owner prompt design.
- Task decomposition templates.
- Engine-agnostic project bootstrap design.
- Test runner contract.
- API response schemas and docs.
- Server configuration design.
- Architecture blueprint and document map.
- Discord operator console design.
- Long-term project memory design.
- Visual tool and MCP integration design.
- README rewrite in clean UTF-8 Korean.
- Local unit tests.
- CLI UX improvements.

## v1 Must Have

- Stable server API
- Durable task and memory DB
- Owner readiness and dashboard
- Worker lease/claim/report
- Workspace worker branch/commit/push
- Merge candidate review
- Retry/cancel/release/assign tools
- Model profile settings
- Worker/Machine Registry
- Machine/Worker heartbeat
- Artifact metadata/upload/download API
- Approval/Decision API
- Role-scoped API tokens
- Clear handoff docs
- Remote deploy script

Most of this is already implemented.

## v1 Remaining High Priority

1. Golden Path Stabilization
   - Baseline contract documented in `docs/GOLDEN_PATH.md`.
   - API-level evidence loop test is implemented.
   - `game-pygame-mini` scaffold and Test Runner preset are implemented.
   - Next: run the loop manually against a separate demo game repo.
   - Next: add exact rehearsal commands to README after the manual run.

2. Owner Task Planning
   - Baseline contract documented in `docs/OWNER_TASK_PLANNING.md`.
   - Owner prompt now follows the planning contract.
   - Next: add optional local validation helper.

3. Security and Execution Control
   - Role-scoped tokens are implemented.
   - Worker command denylist and optional allowlist are implemented.
   - Artifact upload size limit is implemented.
   - Next: add true streaming upload for large artifacts.
   - FastAPI route modules are split out of `app/main.py`.

4. Test Runner Contract
   - Baseline contract documented in `docs/TEST_RUNNER_CONTRACT.md`.
   - Local report mapping helper and tests are implemented.
   - Local runner wrapper executes configured phases and writes local reports.
   - Full test runner worker loop is implemented.
   - `.game-company/test_runner.json` is included in generated project templates.
   - Minimal Pygame preset for the Golden Path demo game is implemented.
   - Next: add project-specific screenshot/runtime capture after the first
     rehearsal proves the smoke loop.

5. Game Project Template
   - Engine undecided.
   - Keep template minimal until actual game starts.
   - Support Unity later without locking the server to Unity.
   - Baseline contract documented in `docs/GAME_PROJECT_TEMPLATE.md`.
   - Local scaffold script and tests are implemented.
   - Next: connect approved Discord/Owner repo creation flow to the scaffold
     tool.

6. Documentation
   - Architecture blueprint documented in `docs/ARCHITECTURE_BLUEPRINT.md`.
   - Hardware/machine inventory documented in `docs/HARDWARE_ENVIRONMENT.md`.
   - Add API operation examples.
   - Add remote recovery guide.
   - Baseline server configuration documented in `docs/SERVER_CONFIGURATION.md`.
   - Baseline Discord operator console documented in `docs/DISCORD_OPERATOR_CONSOLE.md`.
   - Baseline long-term project memory documented in `docs/LONG_TERM_PROJECT_MEMORY.md`.
   - Baseline visual/MCP tool integration documented in `docs/VISUAL_TOOL_INTEGRATION.md`.
   - Baseline MCP extension plan documented in `docs/MCP_EXTENSION_PLAN.md`.

7. Owner Review Policy
   - Decide which warnings block merge.
   - Add configurable thresholds.
   - Keep code/game evidence gaps as warnings until one demo rehearsal shows
     which rules should become blockers.

8. Discord Bot Runtime
   - Mapping API and dry-run routing skeleton are implemented.
   - Context compaction API is implemented for storing thread summaries,
     archiving old summaries, creating continuation mappings, and estimating
     whether a mapped conversation should compact before a 260k context
     threshold.
   - Discord bot dry-run can call context-status and include the result in its
     action JSON.
   - Discord bot dry-run now builds `owner_run_payload` for Owner-routed
     messages and can submit it to `/owner/runs` as `dry_run=true` unless
     explicitly told to execute.
   - Discord Gateway runtime skeleton is implemented with message receive,
     mapping lookup, context-status replies, and optional safe Owner run
     submission.
   - Discord setup doctor and setup guide are implemented.
   - Next: test the Gateway runtime in a real Discord server.
   - Next: connect natural-language approval conversations.

## v1.5 Later

- Vector search for memory.
- Multiple parallel workers.
- Test runner machine integration.
- Image worker pipeline.
- Voice worker pipeline.
- Local model hosting.
- Systemd service for always-on server.
- Web UI.

## Decisions Needed Later

These should be asked when implementation reaches them:

- Which engine to use for the first real game.
- Whether merge warnings should block or only warn.
- Which OpenAI/API model to use for each worker role.
- Whether to run workers on API first or local GPU first.
- When to enable always-on systemd service.

Until then, keep defaults conservative and continue implementation.

## Local-Only Next Steps

These do not require the main computer:

- Run or extend Golden Path e2e tests locally.
- Create a separate demo game repo and rehearse the Golden Path manually.
- Reuse the implemented `game-pygame-mini` Test Runner preset for rehearsal.
- Connect template scaffold tooling to approved project bootstrap flows after
  the Golden Path rehearsal.
- Add artifact streaming upload design/tests.
- Add API examples for the project planning flow.
- Turn `docs/SERVER_CONFIGURATION.md` into systemd unit files when always-on
  mode is approved.
- Add Discord bot/operator console schema after the conversation model is
  finalized.
- Connect Discord memory ingestion to `docs/CONTEXT_COMPACTION.md`.
- Add visual artifact and MCP tool operation schemas before connecting Blender
  or game engine tools.
- Connect Discord bot actions to Owner/approval/artifact server workflows.

## Scope Discipline Until Early July 2026

Do not expand these areas before the first demo rehearsal unless they directly
unblock Golden Path:

- Large MCP rollout.
- Unity and Godot automation at the same time.
- Parallel multi-worker scheduling.
- Local GPU worker orchestration.
- Vector memory.
- Rich web UI.
