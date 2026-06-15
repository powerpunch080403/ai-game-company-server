from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from app.api.deps import settings
from app.config import Settings


PUBLIC_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


def configured_auth_tokens(config: Settings) -> dict[str, str]:
    tokens = {
        "admin": config.api_token,
        "owner": config.owner_token,
        "worker": config.worker_token,
        "readonly": config.readonly_token,
        "artifact": config.artifact_token,
    }
    return {role: token for role, token in tokens.items() if token}


def request_tokens(request: Request) -> list[str]:
    auth_header = request.headers.get("authorization", "")
    token_header = request.headers.get("x-api-token", "")
    bearer_token = auth_header.removeprefix("Bearer ").strip()
    return [token for token in (bearer_token, token_header.strip()) if token]


def token_role(token: str, config: Settings) -> str | None:
    if not token:
        return None
    for role, configured_token in configured_auth_tokens(config).items():
        if token == configured_token:
            return role
    return None


def is_task_package_path(path: str) -> bool:
    parts = path.strip("/").split("/")
    return len(parts) == 3 and parts[0] == "tasks" and parts[2] == "package"


def is_artifact_path(path: str) -> bool:
    return path == "/artifacts" or path.startswith("/artifacts/")


def is_authorized(role: str, method: str, path: str) -> bool:
    if role in {"admin", "owner"}:
        return True
    if role == "readonly":
        return method == "GET"
    if role == "artifact":
        return is_artifact_path(path)
    if role == "worker":
        return (
            (method == "POST" and path.startswith("/workers/"))
            or (method == "GET" and is_task_package_path(path))
            or (method == "POST" and path.startswith("/registry/workers/") and path.endswith("/heartbeat"))
        )
    return False


async def require_api_token(request: Request, call_next):
    path = request.url.path
    tokens = configured_auth_tokens(settings)
    if tokens and path not in PUBLIC_PATHS:
        role = None
        for candidate in request_tokens(request):
            role = token_role(candidate, settings)
            if role is not None:
                break
        if role is None:
            return JSONResponse({"detail": "Missing or invalid API token"}, status_code=401)
        if not is_authorized(role, request.method, path):
            return JSONResponse({"detail": f"Token role '{role}' is not allowed for this endpoint"}, status_code=403)
    return await call_next(request)
