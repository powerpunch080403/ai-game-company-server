from __future__ import annotations

from app.mcp.schemas import MCPServerConfig

# Default registry mapping
_REGISTRY: dict[str, MCPServerConfig] = {
    "filesystem": MCPServerConfig(
        name="filesystem",
        command=["npx", "-y", "@modelcontextprotocol/server-filesystem"],
        allowed_tools=["read_file", "write_file", "create_file", "list_dir"],
        required_roles={
            "read_file": "readonly",
            "list_dir": "readonly",
            "write_file": "worker",
            "create_file": "worker"
        },
        allowed_roots=[
            "C:\\Users\\user2\\.gemini\\antigravity\\scratch\\unity-game-workspace",
            "C:\\Users\\user2\\.gemini\\antigravity\\scratch\\ai-game-company-server\\rehearsal"
        ],
        approval_required_tools=["write_file"]
    ),
    "git": MCPServerConfig(
        name="git",
        command=["git"],
        allowed_tools=["git.diff", "git.commit", "git.push", "git.merge"],
        required_roles={
            "git.diff": "readonly",
            "git.commit": "worker",
            "git.push": "worker",
            "git.merge": "owner"
        },
        approval_required_tools=["git.merge"]
    ),
    "sqlite": MCPServerConfig(
        name="sqlite",
        command=["sqlite3"],
        allowed_tools=["db.select"],
        required_roles={
            "db.select": "readonly"
        }
    )
}

def get_server_config(name: str) -> MCPServerConfig | None:
    return _REGISTRY.get(name)

def list_registered_servers() -> list[str]:
    return list(_REGISTRY.keys())
