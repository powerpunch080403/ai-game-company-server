from __future__ import annotations

from app.discord_bot import DiscordMessageContext, parse_args, route_discord_message, select_mapping


def test_select_mapping_prefers_exact_thread() -> None:
    context = DiscordMessageContext(guild_id="guild-1", channel_id="channel-1", thread_id="thread-1")
    mappings = [
        {
            "mapping_id": "channel",
            "discord_guild_id": "guild-1",
            "discord_channel_id": "channel-1",
            "discord_thread_id": "",
            "conversation_kind": "owner_room",
            "thread_role": "owner-tasks",
            "archived_at": None,
        },
        {
            "mapping_id": "thread",
            "discord_guild_id": "guild-1",
            "discord_channel_id": "channel-1",
            "discord_thread_id": "thread-1",
            "conversation_kind": "project",
            "thread_role": "owner-design",
            "project_id": 7,
            "archived_at": None,
        },
    ]

    assert select_mapping(mappings, context)["mapping_id"] == "thread"


def test_select_mapping_falls_back_to_channel_mapping() -> None:
    context = DiscordMessageContext(guild_id="guild-1", channel_id="channel-1", thread_id="missing-thread")
    mappings = [
        {
            "mapping_id": "channel",
            "discord_guild_id": "guild-1",
            "discord_channel_id": "channel-1",
            "discord_thread_id": "",
            "conversation_kind": "owner_room",
            "thread_role": "owner-tasks",
            "archived_at": None,
        }
    ]

    assert select_mapping(mappings, context)["mapping_id"] == "channel"


def test_route_project_owner_message() -> None:
    context = DiscordMessageContext(
        guild_id="guild-1",
        channel_id="channel-1",
        thread_id="thread-1",
        author_id="user-1",
        content="전투 시스템 지금 어디까지 됐어?",
    )
    mapping = {
        "project_id": 7,
        "conversation_kind": "project",
        "thread_role": "owner-tasks",
    }

    action = route_discord_message(context, mapping)

    assert action.action_type == "project_owner_message"
    assert action.project_id == 7
    assert action.needs_owner is True


def test_route_approval_inbox_message() -> None:
    context = DiscordMessageContext(guild_id="guild-1", channel_id="approval", content="좋아 진행해")
    mapping = {
        "project_id": 3,
        "conversation_kind": "approval_inbox",
        "thread_role": "decisions",
    }

    action = route_discord_message(context, mapping)

    assert action.action_type == "approval_conversation"
    assert action.needs_approval is True


def test_route_unmapped_message() -> None:
    action = route_discord_message(
        DiscordMessageContext(guild_id="guild-1", channel_id="unknown", content="hello"),
        None,
    )

    assert action.action_type == "unmapped_context"


def test_parse_args_supports_offline_mapping_options(monkeypatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "discord_bot",
            "--guild-id",
            "guild-1",
            "--channel-id",
            "channel-1",
            "--project-id",
            "7",
            "--conversation-kind",
            "project",
            "--thread-role",
            "owner-tasks",
        ],
    )

    args = parse_args()

    assert args.project_id == 7
    assert args.conversation_kind == "project"
    assert args.thread_role == "owner-tasks"
