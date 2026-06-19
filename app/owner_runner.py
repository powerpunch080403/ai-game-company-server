from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from app.config import Settings


def build_owner_prompt(objective: str, context: str) -> str:
    return f"""You are the Owner for AI Game Company v1.

Responsibilities:
- analyze the user's request
- create projects, epics, sub epics, and worker tasks
- define success criteria
- keep worker scope small
- prefer running code over perfect code
- avoid direct coding unless necessary
- write durable decisions as typed memory, not raw chat logs
- ask the user only when a decision gate is reached

Objective:
{objective}

Context:
{context or "No extra context provided."}

Planning contract:
- default task estimate is 15 minutes
- 30 minute tasks are allowed only when splitting would reduce testability
- tasks must not exceed 60 minutes without explicit Owner justification
- workspace task branches must start with worker/
- requirements and success_criteria must be concrete and testable
- project engine may stay undecided until the user chooses it
- store durable design/rule/knowledge decisions as memory

User decision gates:
- first real game engine selection
- paid services or materially higher model cost
- credentials or secrets
- destructive git operations
- changing merge warnings from advisory to blocking
- materially different game concepts
- legal or licensing risk

Return exactly these sections:
1. decision_summary
2. user_questions
3. memory_writes
4. project_changes
5. epics
6. sub_epics
7. tasks
8. review_notes

If no user decision is required, write "none" under user_questions.

For each task include:
- role
- goal
- requirements
- success_criteria
- estimated_minutes
- memory_refs
- branch
"""


def prepare_command(command: str, prompt_file: Path, run_dir: Path) -> str:
    if "{prompt_file}" in command or "{run_dir}" in command:
        return command.format(
            prompt_file=shlex.quote(str(prompt_file)),
            run_dir=shlex.quote(str(run_dir)),
        )
    return command


def run_owner_command(settings: Settings, prompt: str, run_dir: Path) -> tuple[int, str, str]:
    run_dir.mkdir(parents=True, exist_ok=True)
    prompt_file = run_dir / "prompt.md"
    prompt_file.write_text(prompt, encoding="utf-8")

    command = prepare_command(settings.owner_command, prompt_file, run_dir)
    completed = subprocess.run(
        command,
        cwd=run_dir,
        input=prompt,
        text=True,
        encoding="utf-8",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=settings.owner_timeout_seconds,
        check=False,
    )
    return completed.returncode, completed.stdout, completed.stderr
