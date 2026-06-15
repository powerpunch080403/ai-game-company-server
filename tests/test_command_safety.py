from __future__ import annotations

import pytest

from app.command_safety import CommandSafetyError, validate_shell_command


def test_validate_shell_command_blocks_denied_patterns() -> None:
    with pytest.raises(CommandSafetyError, match="denied pattern"):
        validate_shell_command("python -c \"ok\" && rm -rf /tmp/demo")


def test_validate_shell_command_allows_safe_command_without_allowlist() -> None:
    validate_shell_command("python --version")


def test_validate_shell_command_enforces_allowlist() -> None:
    validate_shell_command("python -m pytest", allowed_prefixes=["python -m pytest"])
    with pytest.raises(CommandSafetyError, match="allowed prefixes"):
        validate_shell_command("npm test", allowed_prefixes=["python -m pytest"])
