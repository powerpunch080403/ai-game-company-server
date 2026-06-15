from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class DiscordMessageContext:
    guild_id: str
    channel_id: str
    thread_id: str = ""
    author_id: str = ""
    content: str = ""


@dataclass(frozen=True)
class DiscordBotAction:
    action_type: str
    summary: str
    project_id: int | None = None
    conversation_kind: str | None = None
    thread_role: str | None = None
    needs_owner: bool = False
    needs_approval: bool = False


class GameCompanyApiClient:
    def __init__(self, server: str, token: str = ""):
        self.server = server.rstrip("/")
        self.token = token

    @classmethod
    def from_env(cls) -> GameCompanyApiClient:
        token = (
            os.getenv("GAME_COMPANY_DISCORD_SERVER_TOKEN")
            or os.getenv("GAME_COMPANY_OWNER_TOKEN")
            or os.getenv("GAME_COMPANY_API_TOKEN")
            or ""
        )
        return cls(os.getenv("GAME_COMPANY_SERVER", "http://127.0.0.1:8080"), token)

    def headers(self) -> dict[str, str]:
        if not self.token:
            return {}
        return {"Authorization": f"Bearer {self.token}"}

    def list_discord_mappings(self, context: DiscordMessageContext) -> list[dict[str, Any]]:
        params = {
            "discord_guild_id": context.guild_id,
            "discord_channel_id": context.channel_id,
            "discord_thread_id": context.thread_id,
            "active": True,
        }
        with httpx.Client(timeout=15) as client:
            response = client.get(f"{self.server}/discord/mappings", params=params, headers=self.headers())
            response.raise_for_status()
            return response.json()


def select_mapping(mappings: list[dict[str, Any]], context: DiscordMessageContext) -> dict[str, Any] | None:
    exact = [
        item
        for item in mappings
        if item.get("discord_thread_id", "") == context.thread_id
        and item.get("discord_channel_id") == context.channel_id
        and item.get("discord_guild_id") == context.guild_id
        and item.get("archived_at") is None
    ]
    if exact:
        return exact[0]
    channel_level = [
        item
        for item in mappings
        if not item.get("discord_thread_id")
        and item.get("discord_channel_id") == context.channel_id
        and item.get("discord_guild_id") == context.guild_id
        and item.get("archived_at") is None
    ]
    return channel_level[0] if channel_level else None


def route_discord_message(context: DiscordMessageContext, mapping: dict[str, Any] | None) -> DiscordBotAction:
    content = context.content.strip()
    if not mapping:
        return DiscordBotAction(
            action_type="unmapped_context",
            summary="Discord context is not mapped to a server conversation yet.",
        )

    conversation_kind = str(mapping.get("conversation_kind") or "")
    thread_role = str(mapping.get("thread_role") or "")
    project_id = mapping.get("project_id")

    if content.lower() in {"ping", "!ping", "/ping"}:
        return DiscordBotAction(
            action_type="health_check",
            summary="Reply with a short bot health acknowledgement.",
            project_id=project_id,
            conversation_kind=conversation_kind,
            thread_role=thread_role,
        )

    if conversation_kind == "approval_inbox":
        return DiscordBotAction(
            action_type="approval_conversation",
            summary="Route message to approval decision handling.",
            project_id=project_id,
            conversation_kind=conversation_kind,
            thread_role=thread_role,
            needs_approval=True,
        )

    if conversation_kind == "owner_room":
        return DiscordBotAction(
            action_type="owner_room_message",
            summary="Route message to global Owner conversation.",
            project_id=project_id,
            conversation_kind=conversation_kind,
            thread_role=thread_role,
            needs_owner=True,
        )

    if conversation_kind == "project" and thread_role in {"owner-design", "owner-tasks"}:
        return DiscordBotAction(
            action_type="project_owner_message",
            summary=f"Route message to Owner for project {project_id} {thread_role}.",
            project_id=project_id,
            conversation_kind=conversation_kind,
            thread_role=thread_role,
            needs_owner=True,
        )

    if conversation_kind == "ai_internal":
        return DiscordBotAction(
            action_type="ai_internal_observation",
            summary="Record or summarize visible AI internal discussion.",
            project_id=project_id,
            conversation_kind=conversation_kind,
            thread_role=thread_role,
        )

    if conversation_kind == "artifact":
        return DiscordBotAction(
            action_type="artifact_observation",
            summary="Link Discord artifact discussion to server artifact records.",
            project_id=project_id,
            conversation_kind=conversation_kind,
            thread_role=thread_role,
        )

    if conversation_kind == "test_runner":
        return DiscordBotAction(
            action_type="test_runner_observation",
            summary="Route test runner message to project status or artifact handling.",
            project_id=project_id,
            conversation_kind=conversation_kind,
            thread_role=thread_role,
        )

    return DiscordBotAction(
        action_type="record_only",
        summary="Record mapped Discord message without automated action.",
        project_id=project_id,
        conversation_kind=conversation_kind,
        thread_role=thread_role,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dry-run Discord operator console routing.")
    parser.add_argument("--guild-id", required=True)
    parser.add_argument("--channel-id", required=True)
    parser.add_argument("--thread-id", default="")
    parser.add_argument("--author-id", default="")
    parser.add_argument("--content", default="")
    parser.add_argument("--mapping-json", default="", help="Optional mapping JSON for offline dry runs.")
    parser.add_argument("--project-id", type=int, default=None, help="Optional offline dry-run project id.")
    parser.add_argument("--conversation-kind", default="", help="Optional offline dry-run conversation kind.")
    parser.add_argument("--thread-role", default="", help="Optional offline dry-run thread role.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    context = DiscordMessageContext(
        guild_id=args.guild_id,
        channel_id=args.channel_id,
        thread_id=args.thread_id,
        author_id=args.author_id,
        content=args.content,
    )
    if args.mapping_json:
        mapping = json.loads(args.mapping_json)
    elif args.conversation_kind or args.thread_role or args.project_id is not None:
        mapping = {
            "project_id": args.project_id,
            "conversation_kind": args.conversation_kind,
            "thread_role": args.thread_role,
        }
    else:
        mappings = GameCompanyApiClient.from_env().list_discord_mappings(context)
        mapping = select_mapping(mappings, context)
    action = route_discord_message(context, mapping)
    print(json.dumps(asdict(action), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
