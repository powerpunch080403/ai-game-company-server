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

## Next Work While Main Computer Is Unavailable

Work that can be done locally:

- Owner prompt design.
- Task decomposition templates.
- Engine-agnostic project bootstrap design.
- Test runner contract.
- API response schemas and docs.
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
- Clear handoff docs
- Remote deploy script

Most of this is already implemented.

## v1 Remaining High Priority

1. Owner Task Planning
   - Turn a user request into Project/Epic/Sub Epic/Task.
   - Enforce 15-minute task sizing.
   - Store design decisions as memory.

2. Test Runner Contract
   - Define build command.
   - Define run command.
   - Define artifact/log output.
   - Define report format.

3. Game Project Template
   - Engine undecided.
   - Keep template minimal until actual game starts.
   - Support Unity later without locking the server to Unity.

4. Documentation
   - Fix or replace corrupted README.
   - Add API operation examples.
   - Add remote recovery guide.

5. Owner Review Policy
   - Decide which warnings block merge.
   - Add configurable thresholds.

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
