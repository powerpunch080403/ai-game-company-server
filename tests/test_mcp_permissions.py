from __future__ import annotations

import pytest
from app.mcp.schemas import MCPServerConfig
from app.mcp.permissions import validate_mcp_call
from app.mcp.registry import get_server_config

def test_mcp_allowed_and_disallowed_tools() -> None:
    # Get filesystem config
    config = get_server_config("filesystem")
    assert config is not None
    
    # 1. Allowed tool call by proper role
    res = validate_mcp_call(config, "read_file", "readonly")
    assert res["is_allowed"] is True
    assert res["approval_required"] is False
    assert res["dry_run_action"]["status"] == "planned"
    
    # 2. Disallowed tool (not in config.allowed_tools)
    res_disallowed = validate_mcp_call(config, "delete_system_files", "admin")
    assert res_disallowed["is_allowed"] is False
    assert "is not in allowed list" in res_disallowed["reason"]

def test_mcp_role_level_hierarchy() -> None:
    config = get_server_config("filesystem")
    assert config is not None

    # 'write_file' requires 'worker' role minimum.
    # 1. Try with 'readonly' (should block)
    res_readonly = validate_mcp_call(config, "write_file", "readonly")
    assert res_readonly["is_allowed"] is False
    assert "Insufficient permission role" in res_readonly["reason"]
    
    # 2. Try with 'worker' (should allow)
    res_worker = validate_mcp_call(config, "write_file", "worker")
    assert res_worker["is_allowed"] is True
    
    # 3. Try with higher role 'owner' (should allow)
    res_owner = validate_mcp_call(config, "write_file", "owner")
    assert res_owner["is_allowed"] is True

def test_mcp_path_confinement() -> None:
    config = get_server_config("filesystem")
    assert config is not None

    # Allowed roots contains the dynamically configured scratch path
    from pathlib import Path
    root_path = Path(config.allowed_roots[0])
    safe_path = str(root_path / "src" / "main.py")
    unsafe_path = "C:\\Windows\\system32\\cmd.exe" if Path("C:\\").exists() else "/usr/bin/bash"
    
    # 1. Safe subpath (should allow)
    res_safe = validate_mcp_call(config, "read_file", "readonly", target_path=safe_path)
    assert res_safe["is_allowed"] is True
    
    # 2. Outside path (should block)
    res_unsafe = validate_mcp_call(config, "read_file", "readonly", target_path=unsafe_path)
    assert res_unsafe["is_allowed"] is False
    assert "lies outside allowed roots" in res_unsafe["reason"]

    # 3. Explicit security blacklisted files (.env)
    env_path = str(root_path / ".env")
    res_env = validate_mcp_call(config, "read_file", "readonly", target_path=env_path)
    assert res_env["is_allowed"] is False
    assert "violates system security filters" in res_env["reason"]

def test_mcp_approval_required_tools() -> None:
    config = get_server_config("git")
    assert config is not None

    # 'git.merge' is marked as approval required
    res_merge = validate_mcp_call(config, "git.merge", "owner")
    assert res_merge["is_allowed"] is True
    assert res_merge["approval_required"] is True

    # 'git.diff' is not approval required
    res_diff = validate_mcp_call(config, "git.diff", "readonly")
    assert res_diff["is_allowed"] is True
    assert res_diff["approval_required"] is False
