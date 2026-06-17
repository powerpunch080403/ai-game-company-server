# Development Project Template Design

This document defines the v1 design for project repositories created or managed
by AI Game Company Server.

The first target is game development, but the template system should also work
for web, app, backend, tool, automation, research, and plugin projects.

## Goals

- Give workers a predictable repository shape.
- Keep the initial template minimal.
- Support test runner configuration from day one.
- Avoid locking the server to Unity before the first real game decision.
- Keep large generated artifacts out of git by default.
- Provide a common `.ai-company/` automation folder across project types.
- Allow thin type-specific templates.

## Non Goals

- Do not scaffold a full Unity/Unreal/Godot project in v1.
- Do not add heavy binary assets.
- Do not require remote deployment.
- Do not decide the first real game engine here.

## Repository Layout

Recommended minimal layout:

```text
README.md
.gitignore
.ai-company/
  project.json
  test_runner.json
  artifacts/
.game-company/
  project.json
  test_runner.json
  artifacts/
docs/
  DESIGN.md
  TASKS.md
  TESTING.md
src/
  README.md
tests/
  README.md
```

The template must work even when `src/` and `tests/` contain only placeholder
README files.

`.ai-company/` is the preferred forward-looking name. `.game-company/` is kept
as a compatibility alias while the server still uses game-company naming.

## `.game-company/project.json`

This file stores project-local automation metadata.

```json
{
  "version": 1,
  "name": "demo-game",
  "engine": "undecided",
  "base_branch": "main",
  "server": {
    "project_id": null
  },
  "paths": {
    "docs": "docs",
    "source": "src",
    "tests": "tests",
    "artifacts": ".game-company/artifacts"
  }
}
```

Rules:

- `engine` may stay `undecided`.
- Non-game projects may use `project_type` and `framework` instead of `engine`.
- `server.project_id` may be null until the repository is registered.
- Paths should be relative and portable.
- Do not store secrets.

Preferred future path:

```text
.ai-company/project.json
```

## `.game-company/test_runner.json`

Every template should include a no-op or lightweight test runner config.

```json
{
  "version": 1,
  "engine": "undecided",
  "commands": {
    "setup": [],
    "build": ["python --version"],
    "test": [],
    "run": []
  },
  "artifacts": {
    "root": ".game-company/artifacts",
    "logs": ["test-runner.log"],
    "reports": ["test-runner-report.json"]
  },
  "timeouts": {
    "setup_seconds": 300,
    "build_seconds": 900,
    "test_seconds": 900,
    "run_seconds": 300
  }
}
```

The default `python --version` command is intentionally tiny. It proves command
execution and artifact capture without pretending that the game itself builds.

Preferred future path:

```text
.ai-company/test_runner.json
```

## Template Types

Default template bundle:

```text
common .ai-company/
game-basic
game-pygame-mini
web-basic
app-basic
backend-basic
tool-basic
automation-basic
plugin-basic
```

All type-specific templates should be thin. They should add only the minimum
files needed to make the project understandable and runnable.

Common files:

```text
.ai-company/project.json
.ai-company/test_runner.json
docs/DESIGN.md
docs/TASKS.md
docs/TESTING.md
docs/DECISIONS.md
src/README.md
tests/README.md
```

Type-specific examples:

- `game-basic`: engine undecided, visual artifact notes, gameplay docs stub.
- `game-pygame-mini`: tiny Pygame survival scaffold for Golden Path rehearsal.
- `web-basic`: frontend/backend/design-system docs stubs.
- `app-basic`: mobile/api/release notes stubs.
- `backend-basic`: API/deployment/database docs stubs.
- `tool-basic`: CLI/packaging/docs stubs.
- `automation-basic`: scripts/config/safety docs stubs.
- `plugin-basic`: plugin manifest/docs stubs.

## `.gitignore`

Recommended engine-agnostic rules:

```gitignore
.game-company/artifacts/**
!.game-company/artifacts/.gitkeep

.env
.venv/
venv/
__pycache__/

build/
dist/
tmp/
temp/
logs/
*.log

.DS_Store
Thumbs.db
```

Engine-specific ignore rules should be appended only after engine selection.

## Docs

`docs/DESIGN.md`:

- Game concept.
- Current engine decision.
- Core constraints.
- Durable design decisions.

`docs/TASKS.md`:

- Human-readable task plan.
- Links to server task ids when known.
- Open questions.

`docs/TESTING.md`:

- Local build/test commands.
- Test runner artifact locations.
- Known missing coverage.

## Source Placeholder

`src/README.md` should say where game code will live after engine selection.

For Unity later:

```text
Unity project root may replace this directory or live under src/unity.
The final layout should be chosen when the first real Unity project starts.
```

No final Unity layout is chosen in v1.

## Template Creation Flow

1. Create a separate project repository.
2. Add the minimal template files.
3. Commit to `main`.
4. Register the repository in the server project config.
5. Create an initial epic such as `Project Bootstrap`.
6. Create only design or template-hardening tasks until engine selection.

## Local Scaffold Command

The v1 local scaffold tool creates the minimal repository shape described in
this document:

```bash
./scripts/create_project_template.sh /path/to/new-project \
  --name "Demo Game" \
  --type game-basic
```

Golden Path Pygame demo:

```bash
./scripts/create_project_template.sh /path/to/ai-survival-mini \
  --name "AI Survival Mini" \
  --type game-pygame-mini
```

Windows PowerShell:

```powershell
.\scripts\create_project_template.ps1 C:\path\to\new-project `
  --name "Demo Game" `
  --type game-basic
```

Supported template types:

```text
game-basic
game-pygame-mini
web-basic
app-basic
backend-basic
tool-basic
automation-basic
plugin-basic
```

The command refuses to overwrite existing files unless `--force` is passed.
It creates both `.game-company/` and `.ai-company/` automation folders. The
server and Test Runner use `.game-company/` in v1; `.ai-company/` is kept as
the future neutral name for non-game development projects.

## Server Project Config

Recommended initial project API payload:

```json
{
  "name": "Demo Game",
  "description": "Engine-agnostic starting repository for AI Game Company v1.",
  "engine": "undecided",
  "repo_url": "https://github.com/example/demo-game.git",
  "workspace_path": "<WORKSPACE_PATH>",
  "base_branch": "main"
}
```

If the remote or workspace is unavailable, the project may be designed locally
without registering it yet.

Default repo creation policy:

- Real projects use GitHub private repos.
- Temporary/test projects may use local bare repos on the main server.
- GitHub repo/template/workspace creation requires `#approval-inbox` approval.
- Default repo visibility is private.
- Public repo creation requires separate approval.

## Worker Expectations

Workers may assume:

- Branch names start with `worker/`.
- Project-local automation config is under `.game-company/`.
- Durable project docs are under `docs/`.
- Generated artifacts should not be committed unless explicitly requested.
- Build/test evidence should appear in worker reports.

Workers may not assume:

- A specific game engine.
- Unity `Assets/` exists.
- A graphical desktop is available.
- Remote deployment is reachable.

## Engine Selection Later

When the user chooses an engine, add a migration task rather than silently
rewriting the template.

Engine migration task should:

- Update `.game-company/project.json`.
- Append engine-specific `.gitignore` rules.
- Add engine-specific build/test commands.
- Preserve existing docs and task history.
- Report the new layout and validation evidence.

## v1 Implementation Plan

1. Keep this document as the template contract.
2. Add a local scaffold script: done with `app.project_template` and
   `scripts/create_project_template.*`.
3. Include `.game-company/test_runner.json` in generated templates: done.
4. Add tests for scaffold output before adding engine-specific template modes:
   done in `tests/test_project_template.py`.
5. Ask the user before choosing Unity/Godot/Unreal for the first real game.
