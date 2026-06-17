from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

class MCPServerConfig(BaseModel):
    name: str = Field(min_length=1)
    command: list[str] = Field(default_factory=list)
    args: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    required_roles: dict[str, str] = Field(default_factory=dict)  # tool_name -> minimum required role
    allowed_roots: list[str] = Field(default_factory=list)
    approval_required_tools: list[str] = Field(default_factory=list)
    timeout_seconds: int = Field(default=30, ge=1)

class MCPCallResult(BaseModel):
    is_allowed: bool
    reason: str
    approval_required: bool
    dry_run_action: dict[str, Any] | None = None
