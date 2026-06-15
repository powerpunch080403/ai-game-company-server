from __future__ import annotations

import asyncio

from app.discord_gateway import (
    discord_message_to_context,
    format_gateway_reply,
    handle_discord_message,
    handle_gateway_message,
    should_ignore_message,
)


class FakeObject:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakeChannel:
    def __init__(self, channel_id: str, parent_id: str | None = None):
        self.id = channel_id
        self.parent_id = parent_id
        self.sent: list[str] = []

    async def send(self, content: str) -> None:
        self.sent.append(content)


class FakeApi:
    def __init__(self, mappings: list[dict]):
        self.mappings = mappings
        self.context_payloads: list[tuple[str, dict]] = []
        self.owner_payloads: list[dict] = []

    def list_discord_mappings(self, context):
        return self.mappings

    def context_status(self, mapping_id: str, payload: dict):
        self.context_payloads.append((mapping_id, payload))
        return {
            "status": "ok",
            "estimated_tokens": 1200,
            "threshold_tokens": 260000,
            "compact_required": False,
        }

    def create_owner_run(self, payload: dict):
        self.owner_payloads.append(payload)
        return {"id": 9, "status": "dry_run"}


def fake_message(content: str, channel: FakeChannel | None = None, bot: bool = False):
    return FakeObject(
        guild=FakeObject(id="guild-1"),
        channel=channel or FakeChannel("channel-1"),
        author=FakeObject(id="user-1", bot=bot),
        content=content,
    )


def test_discord_message_to_context_uses_parent_channel_for_threads() -> None:
    message = fake_message("hello", FakeChannel("thread-1", parent_id="channel-1"))

    context = discord_message_to_context(message)

    assert context.guild_id == "guild-1"
    assert context.channel_id == "channel-1"
    assert context.thread_id == "thread-1"
    assert context.author_id == "user-1"
    assert context.content == "hello"


def test_should_ignore_bot_dm_and_empty_messages() -> None:
    assert should_ignore_message(fake_message("hello", bot=True)) is True
    assert should_ignore_message(FakeObject(guild=None, author=FakeObject(bot=False), content="hello")) is True
    assert should_ignore_message(fake_message("   ")) is True
    assert should_ignore_message(fake_message("hello")) is False


def test_handle_gateway_message_routes_owner_and_submits_dry_run() -> None:
    api = FakeApi(
        [
            {
                "mapping_id": "mapping-1",
                "discord_guild_id": "guild-1",
                "discord_channel_id": "channel-1",
                "discord_thread_id": "",
                "conversation_kind": "owner_room",
                "thread_role": "owner-tasks",
                "project_id": None,
                "archived_at": None,
            }
        ]
    )

    action = handle_gateway_message(
        discord_message_to_context(fake_message("Break this into tasks.")),
        api,
        submit_owner_run=True,
    )

    assert action.action_type == "owner_room_message"
    assert action.context_status["status"] == "ok"
    assert action.owner_run_payload["dry_run"] is True
    assert action.owner_run_result == {"id": 9, "status": "dry_run"}
    assert api.context_payloads[0][0] == "mapping-1"
    assert api.owner_payloads[0]["objective"] == "Break this into tasks."


def test_format_gateway_reply_for_context_and_owner_run() -> None:
    context_reply = format_gateway_reply(
        FakeObject(
            action_type="context_status_check",
            context_status={
                "status": "compact_now",
                "estimated_tokens": 260000,
                "threshold_tokens": 260000,
            },
            needs_owner=False,
            needs_approval=False,
            owner_run_result=None,
            owner_run_payload=None,
            summary="",
        )
    )
    assert context_reply == "Context: compact now (260000/260000 estimated tokens)."

    owner_reply = format_gateway_reply(
        FakeObject(
            action_type="owner_room_message",
            context_status=None,
            needs_owner=True,
            needs_approval=False,
            owner_run_result={"id": 5, "status": "dry_run"},
            owner_run_payload=None,
            summary="",
        )
    )
    assert owner_reply == "Owner run stored: #5 (dry_run)."


def test_handle_discord_message_sends_reply() -> None:
    channel = FakeChannel("channel-1")
    message = fake_message("/context", channel)
    api = FakeApi(
        [
            {
                "mapping_id": "mapping-1",
                "discord_guild_id": "guild-1",
                "discord_channel_id": "channel-1",
                "discord_thread_id": "",
                "conversation_kind": "project",
                "thread_role": "owner-design",
                "project_id": 1,
                "archived_at": None,
            }
        ]
    )

    action = asyncio.run(handle_discord_message(message, api))

    assert action.action_type == "context_status_check"
    assert channel.sent == ["Context: ok (1200/260000 estimated tokens)."]
