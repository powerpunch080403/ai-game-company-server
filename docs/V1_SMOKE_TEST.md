# V1 Owner Smoke Test

## Purpose
This document provides the necessary structure and the complete Owner Agent prompt to run a manual E2E smoke test verifying the V1 workflow.

## V1 Acceptance Gate
V1 is considered complete only after the Owner runs the manual smoke test verifying the E2E workflow and the result is recorded as PASS.

## Current Status
Status: Pending Owner smoke test result.

## Owner Agent Prompt
```text
You are the Owner agent for the AI Game Company Server smoke test.

Repository:
https://github.com/powerpunch080403/ai-game-company-server

Role:
Act as the Owner, not as a coding worker.

Goal:
Run a practical smoke test of the current V1 workflow and produce a clear report for the human project owner.

Current implemented workflow:
Project Search
→ Task Plan Search
→ Tasks From Plan
→ optional Discord task thread creation
→ task_thread_reference storage
→ Worker lease
→ Worker report
→ best-effort Discord report posting
→ merge candidate queue
→ Owner approval/rejection
→ dry-run readiness check

Known stable baseline:
- Full pytest recently passed: 196 tests passed.
- `.env` is untracked and must remain untracked.
- Latest workflow is documented in `README.md`, `docs/README.ko.md`, and `docs/ROADMAP.md`.

Important:
This is a smoke test, not a feature implementation task.

Do NOT:
- add new features
- refactor code
- update docs
- use subagents
- create `implementation_plan.md`, `task.md`, `walkthrough.md`, or artifact files
- commit `.env`
- force-push
- call Codex CLI
- run unrelated experiments
- approve final merge execution automatically
- modify unrelated repository files

You may:
- run the server if needed
- use local API requests
- use a temporary test git workspace
- create a small dummy project for testing
- create from-plan tasks
- lease/report tasks
- check Discord task thread behavior if Discord is configured
- inspect relevant server responses
- run focused tests if needed

Before starting:
1. Check:
   git status
   git rev-parse HEAD
   git ls-files .env
2. Confirm `.env` is not tracked.
3. Check whether Discord is configured:
   - DISCORD_BOT_TOKEN
   - GAME_COMPANY_DISCORD_TASK_CHANNEL_ID
4. Do not print secret values. Only report whether each value is present or missing.
5. Record the server base URL and token method you use, but do not print secret token values.

Smoke test target:
Verify that the practical workflow works end-to-end:

Owner creates a task from planning search
→ Discord thread is created if configured
→ task_thread_reference is stored
→ Worker leases the task
→ Worker reports success
→ Server validates changed_files
→ Discord thread receives worker report summary if configured
→ Merge candidate is queued
→ Owner can approve/reject
→ Dry-run reports readiness or clear reasons

Use a temporary smoke project workspace:
- Create a tiny local git repo outside the main repository.
- Example files:
  - src/player.py
  - tests/test_player.py
  - README.md
- Make sure `src/player.py` contains searchable text:
  player movement logic
- Commit initial files.
- Configure local git identity inside the temporary repo if needed:
  git config user.email "smoke@example.com"
  git config user.name "Smoke Tester"

Example temporary file content:

# src/player.py

# player movement logic

def move_player():
    return "old movement"

Commit:
git init
git add .
git commit -m "initial smoke project"

Smoke Test A: Success Path

A1. Create/register project

Call:
POST /projects

Use a payload like:

{
  "name": "Smoke Game",
  "description": "Temporary smoke test project",
  "engine": "python",
  "repo_url": "",
  "workspace_path": "ABSOLUTE_PATH_TO_TEMP_SMOKE_WORKSPACE",
  "base_branch": "main"
}

Record:
- project_id
- workspace path
- base branch

Verify:
- project was created
- workspace path is accepted
- no main repository files were modified

A2. Create task from planning search

Call:
POST /projects/{project_id}/tasks/from-plan

First try with Discord thread creation if Discord is configured:

{
  "title": "Update player movement",
  "goal": "Update player movement logic",
  "queries": ["player movement"],
  "glob": "src/**",
  "confirm": true,
  "create_thread": true
}

If Discord is not configured, or if this fails with `discord_thread_creation_not_configured`, retry with:

{
  "title": "Update player movement",
  "goal": "Update player movement logic",
  "queries": ["player movement"],
  "glob": "src/**",
  "confirm": true,
  "create_thread": false
}

Verify:
- task was created
- response includes task
- response includes plan
- task prompt contains the goal
- plan includes src/player.py
- task read scope includes src/player.py
- task write scope includes src/player.py
- forbidden scope exists
- if create_thread=true succeeded:
  - response includes thread_reference
  - GET /tasks/{task_id}/thread-reference returns the same reference
  - Discord thread exists
  - Discord thread contains initial task context

Important:
Do not use manual thread_reference together with create_thread=true.

A3. Lease task as worker

Call:
POST /workers/smoke-worker-1/lease

Use payload:

{
  "role": "code_worker",
  "lease_minutes": 30,
  "requires_project_config": true
}

Verify:
- the leased task id matches the created task
- branch name uses this style:
  worker/{node_id}/{task_id}-{slug}
- base_commit is recorded
- task locks are active
- task is not already completed

Record:
- worker_id
- task_id
- branch_name
- base_commit

A4. Modify only allowed file

Modify only:
src/player.py

Example change:

def move_player():
    return "new movement"

Do not modify files outside write_scope.

A5. Submit worker success report

Call:
POST /workers/smoke-worker-1/tasks/{task_id}/report

Use a payload matching the actual worker report schema:

{
  "status": "success",
  "estimated_minutes": 15,
  "actual_minutes": 5,
  "productive_minutes": 5,
  "error_minutes": 0,
  "retry_count": 0,
  "files_changed": ["src/player.py"],
  "changed_files": ["src/player.py"],
  "tests": ["smoke: manual file update"],
  "summary": "Updated player movement logic.",
  "issues": ""
}

Verify:
- report request succeeds
- final task status is success
- active task locks are released
- a merge candidate is queued
- if Discord thread exists, worker report summary was posted to the thread
- Discord failure, if any, does not break the worker report result

A6. Check merge candidate

Call:
GET /projects/{project_id}/merge-candidates

Verify:
- exactly one candidate exists for the task, or clearly identify the matching candidate
- candidate status is queued
- candidate has task id
- candidate has branch name
- candidate has base commit

Record:
- candidate_id
- candidate status

A7. Dry-run before approval

Call:
POST /merge-candidates/{candidate_id}/dry-run

Before approval, it may return a reason like:
not_approved

Record the response.

A8. Approve candidate

Call:
POST /merge-candidates/{candidate_id}/approve

Verify:
- status becomes approved

Do not execute final merge in this smoke test unless explicitly instructed by the human project owner.

A9. Dry-run after approval

Call again:
POST /merge-candidates/{candidate_id}/dry-run

Verify:
- dry-run returns readiness or clear reasons
- no ambiguous failure occurs
- record all returned reasons if not ready

Do not execute final merge.

Smoke Test B: Scope Violation Path

B1. Create another from-plan task

Create a second task using:
POST /projects/{project_id}/tasks/from-plan

Payload:

{
  "title": "Scope violation smoke task",
  "goal": "Update player movement again",
  "queries": ["player movement"],
  "glob": "src/**",
  "confirm": true,
  "create_thread": false
}

Record the new task_id.

B2. Lease second task

Call:
POST /workers/smoke-worker-2/lease

Payload:

{
  "role": "code_worker",
  "lease_minutes": 30,
  "requires_project_config": true
}

Verify:
- the leased task id matches the second task
- task locks are active

B3. Submit out-of-scope report

Do not actually need to modify README in the main repository.

Submit a report claiming an out-of-scope changed file:

POST /workers/smoke-worker-2/tasks/{task_id}/report

Payload:

{
  "status": "success",
  "estimated_minutes": 15,
  "actual_minutes": 3,
  "productive_minutes": 3,
  "error_minutes": 0,
  "retry_count": 0,
  "files_changed": ["README.md"],
  "changed_files": ["README.md"],
  "tests": ["scope violation smoke"],
  "summary": "Accidentally changed README.",
  "issues": "Changed file outside write_scope."
}

Important:
The worker report status is still success.
The server should derive the final task status as scope_violation because changed_files is outside write_scope.

Verify:
- report request succeeds or returns a clear validation result
- final task status becomes scope_violation
- no merge candidate is created for this task
- task locks are released
- if a Discord thread exists, report message indicates no merge candidate or scope violation

Smoke Test C: Missing Discord Config Behavior

Run this only if Discord config is missing or can be safely disabled without exposing secrets.

Call:
POST /projects/{project_id}/tasks/from-plan

Payload:

{
  "title": "Discord missing config smoke",
  "goal": "Verify missing Discord config behavior",
  "queries": ["player movement"],
  "glob": "src/**",
  "confirm": true,
  "create_thread": true
}

Verify:
- response clearly fails with:
  discord_thread_creation_not_configured
- no fake thread reference is stored
- task creation with create_thread=false still works

Smoke Test D: Thread Reference Search

If any task thread references exist:

Call:
GET /projects/{project_id}/thread-references

Then query with a keyword:

GET /projects/{project_id}/thread-references?query=movement&limit=10

Verify:
- endpoint returns references
- returned references belong only to the project
- thread title/summary/thread_id/thread_url are present when available
- truncated is correct

Final cleanup/checks

After smoke tests:
git status
git ls-files .env

Verify:
- main repository working tree is clean
- `.env` remains untracked
- temporary smoke workspace can be deleted or clearly identified as temporary
- no secret values were printed

Final report format:

# Owner Smoke Test Report

## Environment
- HEAD:
- Working tree before:
- Working tree after:
- `.env` tracked:
- Discord bot token present: yes/no
- Discord task channel present: yes/no
- Server base URL used:
- Real Discord thread test performed: yes/no

## Temporary Workspace
- Path:
- Initial commit:
- Files:

## Success Path
- Project created:
- Project ID:
- From-plan task created:
- Task ID:
- Plan found src/player.py:
- Read scope:
- Write scope:
- Forbidden scope present:
- Discord thread created:
- Thread reference stored:
- Worker lease succeeded:
- Branch:
- Base commit:
- Task locks active after lease:
- Worker report accepted:
- Final task status:
- Task locks released:
- Merge candidate queued:
- Candidate ID:
- Discord report posted:
- Dry-run before approval:
- Approval result:
- Dry-run after approval:

## Scope Violation Path
- Task created:
- Task ID:
- Worker lease succeeded:
- Scope violation detected:
- Final task status:
- Merge candidate prevented:
- Task locks released:
- Discord report posted/skipped:

## Missing Discord Config Path
- Tested:
- Result:

## Thread Reference Search
- Tested:
- Result count:
- Query used:
- Notes:

## Problems Found
- List any failures, confusing API behavior, missing config, or manual steps.

## Owner Judgment
Choose one:
- PASS: V1 smoke flow is usable.
- PARTIAL: usable except listed issues.
- FAIL: blocking issue found.

## Recommended Next Action
Give one next action only.

If a real bug is found:
- Do not silently fix it unless it is tiny and clearly safe.
- Report it first.
- If you fix it, keep the fix minimal.
- Run targeted tests.
- Commit only real fixes, not temporary smoke artifacts.
```

## Smoke Test Result

* Status: Pending
* Date: TBD
* Owner judgment: TBD
* Notes: TBD
