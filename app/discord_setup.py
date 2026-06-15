from __future__ import annotations

import argparse
import importlib.util
import json
import os
from dataclasses import asdict, dataclass
from urllib.parse import urlencode

import httpx
from dotenv import load_dotenv

load_dotenv()

DEFAULT_BOT_PERMISSIONS = 68608


@dataclass(frozen=True)
class SetupCheck:
    name: str
    ok: bool
    detail: str


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def discord_invite_url(application_id: str, permissions: int = DEFAULT_BOT_PERMISSIONS) -> str:
    query = urlencode(
        {
            "client_id": application_id,
            "permissions": str(permissions),
            "scope": "bot",
        }
    )
    return f"https://discord.com/oauth2/authorize?{query}"


def check_discord_setup(
    server: str,
    discord_bot_token: str,
    application_id: str = "",
    server_token: str = "",
    check_server: bool = True,
) -> dict:
    checks: list[SetupCheck] = []

    checks.append(
        SetupCheck(
            name="discord.py dependency",
            ok=importlib.util.find_spec("discord") is not None,
            detail="discord.py import is available" if importlib.util.find_spec("discord") else "install requirements.txt",
        )
    )
    checks.append(
        SetupCheck(
            name="DISCORD_BOT_TOKEN",
            ok=bool(discord_bot_token),
            detail=f"configured as {mask_secret(discord_bot_token)}" if discord_bot_token else "missing",
        )
    )
    checks.append(
        SetupCheck(
            name="GAME_COMPANY_DISCORD_SERVER_TOKEN",
            ok=bool(server_token),
            detail=f"configured as {mask_secret(server_token)}" if server_token else "missing; owner/admin token fallback may still work",
        )
    )
    checks.append(
        SetupCheck(
            name="DISCORD_APPLICATION_ID",
            ok=bool(application_id),
            detail="invite URL can be generated" if application_id else "missing; optional but useful for invite URL",
        )
    )

    server = server.rstrip("/")
    if check_server:
        try:
            response = httpx.get(f"{server}/health", timeout=5)
            checks.append(
                SetupCheck(
                    name="server health",
                    ok=response.status_code == 200,
                    detail=f"GET {server}/health -> {response.status_code}",
                )
            )
        except httpx.HTTPError as exc:
            checks.append(SetupCheck(name="server health", ok=False, detail=str(exc)))

    invite_url = discord_invite_url(application_id) if application_id else ""
    return {
        "ok": all(check.ok for check in checks if check.name != "DISCORD_APPLICATION_ID"),
        "server": server,
        "invite_url": invite_url,
        "checks": [asdict(check) for check in checks],
        "notes": [
            "Never paste Discord account passwords or bot tokens into chat.",
            "Enable Message Content Intent in the Discord Developer Portal for message-based routing.",
            "Invite the bot to the target Discord server, then register channel/thread mappings in the API.",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check Discord bot runtime setup.")
    parser.add_argument("--server", default=os.getenv("GAME_COMPANY_SERVER", "http://127.0.0.1:8080"))
    parser.add_argument("--no-server-check", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = check_discord_setup(
        server=args.server,
        discord_bot_token=os.getenv("DISCORD_BOT_TOKEN", ""),
        application_id=os.getenv("DISCORD_APPLICATION_ID", ""),
        server_token=(
            os.getenv("GAME_COMPANY_DISCORD_SERVER_TOKEN")
            or os.getenv("GAME_COMPANY_OWNER_TOKEN")
            or os.getenv("GAME_COMPANY_API_TOKEN")
            or ""
        ),
        check_server=not args.no_server_check,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Discord setup ok: {result['ok']}")
        for check in result["checks"]:
            marker = "OK" if check["ok"] else "MISSING"
            print(f"- {marker}: {check['name']} - {check['detail']}")
        if result["invite_url"]:
            print(f"Invite URL: {result['invite_url']}")
        for note in result["notes"]:
            print(f"Note: {note}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
