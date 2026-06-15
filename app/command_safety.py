from __future__ import annotations

import os


class CommandSafetyError(ValueError):
    pass


DEFAULT_DENIED_PATTERNS = (
    "rm -rf",
    "del /",
    "rmdir /s",
    "format ",
    "shutdown",
    "reboot",
    "sudo ",
    "curl ",
    "wget ",
    "| bash",
    "|bash",
    "powershell -enc",
    "powershell -encodedcommand",
    "git push --force",
    "git push -f",
    "git reset --hard",
)


def env_list(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def validate_shell_command(
    command: str,
    allowed_prefixes: list[str] | None = None,
    denied_patterns: list[str] | None = None,
) -> None:
    normalized = " ".join(command.lower().split())
    if not normalized:
        raise CommandSafetyError("empty command is not allowed")

    denied = denied_patterns if denied_patterns is not None else list(DEFAULT_DENIED_PATTERNS)
    for pattern in denied:
        if pattern.lower() in normalized:
            raise CommandSafetyError(f"command contains denied pattern: {pattern}")

    prefixes = allowed_prefixes if allowed_prefixes is not None else env_list("GAME_COMPANY_ALLOWED_COMMAND_PREFIXES")
    if prefixes and not any(command.strip().startswith(prefix) for prefix in prefixes):
        raise CommandSafetyError("command does not match allowed prefixes")
