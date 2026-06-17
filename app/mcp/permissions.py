from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from app.mcp.schemas import MCPServerConfig, MCPCallResult

ROLE_LEVELS = {
    "readonly": 1,
    "worker": 2,
    "owner": 3,
    "admin": 4,
}

def is_subpath(target_path: str, root_path: str) -> bool:
    try:
        target = Path(target_path).resolve()
        root = Path(root_path).resolve()
        target.relative_to(root)
        return True
    except ValueError:
        return False

def validate_mcp_call(
    config: MCPServerConfig,
    tool_name: str,
    role: str,
    target_path: str | None = None
) -> dict[str, Any]:
    # 1. Check if the tool is in allowed_tools
    if tool_name not in config.allowed_tools:
        return {
            "is_allowed": False,
            "reason": f"Tool '{tool_name}' is not in allowed list for server '{config.name}'.",
            "approval_required": False,
            "dry_run_action": None,
        }

    # 2. Check role constraints
    req_role = config.required_roles.get(tool_name, "readonly")
    user_level = ROLE_LEVELS.get(role, 0)
    required_level = ROLE_LEVELS.get(req_role, 1)
    
    if user_level < required_level:
        return {
            "is_allowed": False,
            "reason": f"Insufficient permission role: '{role}' (required: '{req_role}').",
            "approval_required": False,
            "dry_run_action": None,
        }

    # 3. Path containment (if target_path is specified)
    if target_path:
        # Check against allowed_roots
        is_safe = False
        for root in config.allowed_roots:
            if is_subpath(target_path, root):
                is_safe = True
                break
        
        # Block dangerous system indicators explicitly
        resolved_tgt = str(Path(target_path).resolve()).lower()
        if not is_safe or ".git/config" in resolved_tgt or ".env" in resolved_tgt or "secrets" in resolved_tgt:
            return {
                "is_allowed": False,
                "reason": f"Target path '{target_path}' lies outside allowed roots or violates system security filters.",
                "approval_required": False,
                "dry_run_action": None,
            }

    # 4. Check approval requirement
    approval_required = tool_name in config.approval_required_tools
    
    # 5. Return dry-run action description
    dry_run_action = {
        "tool": tool_name,
        "server": config.name,
        "executor_role": role,
        "target_path": target_path,
        "status": "planned"
    }

    return {
        "is_allowed": True,
        "reason": "Request successfully validated.",
        "approval_required": approval_required,
        "dry_run_action": dry_run_action,
    }
