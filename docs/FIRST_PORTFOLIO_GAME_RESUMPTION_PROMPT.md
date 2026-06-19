# First Portfolio Game Resumption Guide

This guide is the safe restart prompt for beginning the first portfolio game,
**Neon Survival Prototype**.

Scope: **Task 1 Project Bootstrap only**.

Do not start any later task.
Do not lease any task after Task 1.
Do not approve or execute a merge.
Stop after the Task 1 worker branch is pushed and the worker report is
submitted for Owner review.

## Task 1: Project Bootstrap

- Role: `code_worker`
- Branch: `worker/project-bootstrap`
- Estimated minutes: 30

Goal:
Initialize the project workspace with baseline folders, `.game-company`
configuration, pytest smoke checks, and project documentation stubs.

Requirements:

- Scaffold the project structure inside the assigned workspace directory.
- Create empty directories:
  - `src/`
  - `src/game/`
  - `tests/`
  - `scripts/`
  - `assets/`
  - `docs/`
- Ensure `src/__init__.py` and `src/game/__init__.py` exist.
- Create `.game-company/project.json`:

```json
{
  "project_name": "Neon Survival Prototype",
  "engine": "pygame",
  "version": "1.0.0"
}
```

- Create `.game-company/test_runner.json`:

```json
{
  "phases": {
    "setup": "pip install -r requirements.txt",
    "test": "python -m pytest",
    "smoke": "python scripts/smoke_check.py"
  }
}
```

- Create `requirements.txt` containing either `pygame-ce>=2.5.0` or
  `pygame>=2.5.0`.
- Create `.gitignore` containing:

```text
__pycache__/
*.pyc
.venv/
*.log
.game-company/artifacts/
```

- Create `README.md` with the project overview.
- Create `scripts/smoke_check.py` as a minimal smoke stub that prints a short
  message and exits with status 0.
- Create `tests/test_bootstrap.py` as a minimal pytest test that passes.

Success criteria:

- `src/game`, `tests`, and `scripts` exist.
- `.game-company/test_runner.json` exists and is valid JSON.
- `requirements.txt` lists Pygame.
- `python -m pytest` passes.
- `python scripts/smoke_check.py` exits with status 0.

Evidence required:

- Worker output log showing the files and directories created.
- Pytest output.
- Smoke check output.
- Git branch name.
- Git commit SHA.

## Execution Prompt

Use this prompt when restarting the first portfolio game from Codex CLI or
another coding CLI.

```text
You are the code worker for Neon Survival Prototype.

Run only Task 1: Project Bootstrap.

Do not implement the game loop.
Do not implement player movement.
Do not lease any later task.
Do not approve or execute a merge.

Create only the project bootstrap structure described in
docs/FIRST_PORTFOLIO_GAME_RESUMPTION_PROMPT.md.

Work on the assigned branch only.
Modify only files required for bootstrap.
Run pytest and the smoke check.
Commit the bootstrap result.
Push the worker branch if a remote is configured.
Submit the worker report with the real head_commit.

Stop after the branch/report is ready for manual Owner review.
```

## Owner Stop Condition

After Task 1 is reported:

1. Review the worker report.
2. Review changed files and test evidence.
3. Decide manually whether to approve, retry, or cancel.
4. Continue with later work only after manual Owner review is complete.
