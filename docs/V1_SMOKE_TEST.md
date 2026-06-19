# V1 Owner Smoke Test

## Purpose

This document records the V1 acceptance smoke test for the AI Game Company
Server.

V1 is accepted when the practical Owner -> Worker -> Git -> report -> merge
candidate loop works with a real project workspace and no secrets are exposed.

## Current Status

Status: **PASS** (2026-06-20 Owner live CLI smoke test).

## Verified Workflow

The accepted V1 workflow is:

1. Owner verifies server health.
2. Owner registers a project with a Git workspace.
3. Owner creates an Epic, Sub-Epic, and one `code_worker` task.
4. Owner creates a live Discord task thread when Discord is configured.
5. Worker leases the exact task.
6. Worker checks out the server-assigned branch from the recorded base commit.
7. Worker modifies only files allowed by write scope.
8. Worker runs tests.
9. Worker commits the result.
10. Worker reports the real `head_commit`.
11. Server derives changed files from Git.
12. Server verifies branch tip, commit ancestry, and changed file scope.
13. Server queues one merge candidate.
14. Owner can dry-run and review the candidate.

Final merge execution was intentionally not run during the live CLI smoke test.

## Known Stable Baseline

- Full pytest passed: 205 passed, 1 warning.
- `.env` remained untracked.
- Discord task thread creation succeeded in the live Owner smoke flow.
- Codex CLI completed a live `code_worker` task.
- Antigravity CLI (`agy.exe`) completed a live `code_worker` task.
- Both workers pushed worker branches, submitted real `head_commit` values, and
  queued merge candidates.

## Git Integrity Rules Verified

For Git-backed coding tasks, a successful Worker result requires committed Git
evidence:

1. Task branch is server-authoritative.
2. Successful Git-backed reports require a real `head_commit`.
3. Branch tip must exactly equal the reported `head_commit`.
4. `head_commit` must descend from `base_commit`.
5. Changed files are derived directly from Git history.
6. Worker-reported changed files are compared with Git-derived changed files.
7. Scope violations prevent merge-candidate creation.
8. Invalid success reports remain auditable but do not finalize as success.
9. Dry-run validates actual Git objects and workspace state.
10. Execute revalidates integrity immediately before merging.

## Smoke Test Result

- Status: PASS
- Date: 2026-06-20
- Owner judgment: PASS. V1 smoke flow is usable for local/private development.
- Full test result: 205 passed, 1 warning.
- Discord result: live task thread creation succeeded.
- Codex CLI result: worker task completed, branch pushed, merge candidate queued.
- Antigravity CLI result: worker task completed, branch pushed, merge candidate
  queued.
- Merge result: final merge was not executed during smoke validation.

## Remaining Limitations

- V1 is accepted for local/private development, not public internet operation.
- Discord remains an operator interface, not the source of truth.
- Merge execution should still be Owner-reviewed manually.
- Larger team operation, richer memory search, local GPU workers, and a web UI
  remain V1.5+ work.
