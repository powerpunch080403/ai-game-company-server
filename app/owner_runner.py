from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from app.config import Settings


def build_owner_prompt(objective: str, context: str) -> str:
    return f"""You are the Owner for AI Game Company v1.

Responsibilities:
- analyze the user's request
- create epics, sub epics, and <=15 minute tasks
- define success criteria
- keep worker scope small
- prefer running code over perfect code
- avoid direct coding unless necessary

Objective:
{objective}

Context:
{context or "No extra context provided."}

Return:
- decision summary
- proposed epics/sub epics/tasks
- worker assignment
- success criteria
- risks or blockers
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
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=settings.owner_timeout_seconds,
        check=False,
    )
    return completed.returncode, completed.stdout, completed.stderr
