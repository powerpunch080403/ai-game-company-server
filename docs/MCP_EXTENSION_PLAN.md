# MCP Extension Plan

MCP is useful for giving Owner and Workers controlled access to external tools,
but it should not be added in bulk before Golden Path is stable.

The FastAPI server remains the source of truth. MCP tools should be adapters
for file, git, browser, engine, memory, artifact, and notification operations.

## Design Principle

```text
Owner / Worker
-> MCP Tool Router
-> approved MCP server/tool
-> audited result
-> Task report, memory, artifact, or approval record
```

Do not let MCP tools write directly to SQLite or bypass the task queue. The
server API owns state changes.

## Suggested Package Layout

```text
app/mcp/
  client.py
  registry.py
  permissions.py
  tool_router.py
  audit_log.py
```

Responsibilities:

- `client.py`: low-level MCP client calls.
- `registry.py`: known MCP servers and tools.
- `permissions.py`: role/tool/path approval rules.
- `tool_router.py`: checks policy before calling a tool.
- `audit_log.py`: durable tool call summaries for later review.

## Initial MCP Priority

Start with only the tools that directly support Golden Path:

1. Filesystem MCP.
2. Git MCP.
3. SQLite/DB MCP read-only.
4. Playwright MCP.
5. Custom Task Package MCP.

Later:

6. Custom Memory MCP.
7. GitHub MCP.
8. Unity or Godot MCP, one engine at a time.
9. Error Tracking MCP.
10. Discord/Notification MCP.
11. Package Manager MCP.

## Filesystem MCP

Purpose:

- Read project files.
- Write project workspace files.
- List/search workspace files.
- Save local logs or task outputs.

Allowed roots must be explicit:

```text
workspaces/{project_id}/
artifacts/{project_id}/
logs/{task_id}/
```

Blocked paths:

```text
/
~/
C:/
.env
.ssh/
secrets/
.git/config
```

## Git MCP

Purpose:

- Inspect branch and diff.
- Create or switch `worker/*` branches.
- Read changed files.
- Commit worker changes.
- Create PRs later.
- Check conflicts and merge eligibility.

Suggested future API wrapper shape:

```text
POST /mcp/git/diff/{task_id}
POST /mcp/git/create-pr/{task_id}
POST /mcp/git/review-pr/{task_id}
POST /mcp/git/merge/{task_id}
```

Actual merge still goes through Owner review and approval policy.

## SQLite / DB MCP

Start read-only.

Allowed first tools:

```text
get_project_status(project_id)
get_open_tasks(project_id)
get_task_history(task_id)
search_memory(project_id, query)
get_worker_health()
list_artifacts(project_id, task_id)
```

Do not add write tools until the approval model is stable.

## Playwright MCP

Purpose:

- Verify web dashboards and browser games.
- Capture screenshots.
- Collect console errors.
- Attach screenshots/logs as artifacts.

Game/web validation loop:

```text
Worker changes code
-> Test Runner opens game/app
-> Playwright captures screenshot and console errors
-> Server stores artifacts
-> Owner reviews before merge
```

## Custom Task Package MCP

This project should expose its own task package operations instead of relying
only on generic tools:

```text
get_task_package(task_id)
get_success_criteria(task_id)
get_required_memory(task_id)
submit_worker_report(task_id)
upload_artifact(task_id)
```

## Permission Model

Recommended role levels:

```text
readonly:
  filesystem.read
  git.diff
  db.select
  memory.search

worker:
  filesystem.write_workspace
  git.commit_worker_branch
  artifact.upload
  report.submit

owner:
  task.create
  task.assign
  approval.request
  github.pr_create

admin:
  merge
  dependency.install
  migration.run
  deploy
```

Policy records should include:

```text
mcp_allowed_servers
mcp_allowed_tools
mcp_tool_call_logs
mcp_approval_rules
mcp_timeout_policy
mcp_sandbox_policy
```

## Approval Required

Require Owner/user approval before:

- Git merge.
- Dependency install or major update.
- Database migration.
- External paid API call.
- Release build.
- Deploy.
- Any command outside the project workspace.

## v1 Boundary

For v1, design the MCP boundary and maybe add a small registry skeleton only
after Golden Path is rehearsed.

Do not connect broad MCP tool execution before command safety, audit logging,
and approval routing are in place.
