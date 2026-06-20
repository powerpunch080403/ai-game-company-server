from __future__ import annotations

from app.discord_bot import (
    DiscordBotAction,
    DiscordMessageContext,
    GameCompanyApiClient,
    attach_context_status,
    attach_owner_run_payload,
    attach_owner_run_result,
    build_owner_run_payload,
    context_status_payload,
    parse_args,
    route_discord_message,
    select_mapping,
)


def test_api_client_from_env_uses_owner_run_timeout(monkeypatch) -> None:
    monkeypatch.setenv("GAME_COMPANY_SERVER", "http://server.test")
    monkeypatch.setenv("GAME_COMPANY_DISCORD_OWNER_RUN_TIMEOUT_SECONDS", "123")
    monkeypatch.delenv("GAME_COMPANY_DISCORD_SERVER_TOKEN", raising=False)
    monkeypatch.delenv("GAME_COMPANY_OWNER_TOKEN", raising=False)
    monkeypatch.delenv("GAME_COMPANY_API_TOKEN", raising=False)

    client = GameCompanyApiClient.from_env()

    assert client.server == "http://server.test"
    assert client.owner_run_timeout_seconds == 123


def test_api_client_from_env_falls_back_to_owner_timeout(monkeypatch) -> None:
    monkeypatch.delenv("GAME_COMPANY_DISCORD_OWNER_RUN_TIMEOUT_SECONDS", raising=False)
    monkeypatch.setenv("GAME_COMPANY_OWNER_TIMEOUT_SECONDS", "456")

    client = GameCompanyApiClient.from_env()

    assert client.owner_run_timeout_seconds == 456


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
        "mapping_id": "mapping-7",
        "project_id": 7,
        "conversation_kind": "project",
        "thread_role": "owner-tasks",
    }

    action = route_discord_message(context, mapping)

    assert action.action_type == "project_owner_message"
    assert action.project_id == 7
    assert action.mapping_id == "mapping-7"
    assert action.needs_owner is True


def test_route_context_status_command() -> None:
    context = DiscordMessageContext(guild_id="guild-1", channel_id="channel-1", content="/context")
    mapping = {
        "mapping_id": "mapping-context",
        "project_id": 7,
        "conversation_kind": "project",
        "thread_role": "owner-design",
    }

    action = route_discord_message(context, mapping)

    assert action.action_type == "context_status_check"
    assert action.mapping_id == "mapping-context"
    assert action.needs_owner is False


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


def test_parse_args_supports_context_status_options(monkeypatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "discord_bot",
            "--guild-id",
            "guild-1",
            "--channel-id",
            "channel-1",
            "--thread-id",
            "thread-1",
            "--content",
            "hello",
            "--check-context",
            "--estimated-extra-tokens",
            "1200",
            "--threshold-tokens",
            "260000",
            "--warning-tokens",
            "220000",
            "--auto-compact-summary",
            "summary",
            "--archive-mapping",
            "--continuation-thread-id",
            "thread-2",
            "--submit-owner-run",
            "--execute-owner-run",
        ],
    )

    args = parse_args()

    assert args.check_context is True
    assert args.estimated_extra_tokens == 1200
    assert args.threshold_tokens == 260000
    assert args.warning_tokens == 220000
    assert args.auto_compact_summary == "summary"
    assert args.archive_mapping is True
    assert args.continuation_thread_id == "thread-2"
    assert args.submit_owner_run is True
    assert args.execute_owner_run is True


def test_context_status_payload_uses_message_and_thresholds() -> None:
    payload = context_status_payload(
        DiscordMessageContext(guild_id="guild-1", channel_id="channel-1", content="hello"),
        estimated_extra_tokens=12,
        threshold_tokens=100,
        warning_tokens=80,
        auto_compact=True,
        compact_summary="summary",
        archive_mapping=True,
        continuation_discord_thread_id="thread-2",
    )

    assert payload["recent_messages"] == ["hello"]
    assert payload["estimated_extra_tokens"] == 12
    assert payload["threshold_tokens"] == 100
    assert payload["warning_tokens"] == 80
    assert payload["auto_compact"] is True
    assert payload["compact_summary"] == "summary"
    assert payload["archive_mapping"] is True
    assert payload["continuation_discord_thread_id"] == "thread-2"


def test_context_status_payload_uses_recent_discord_messages() -> None:
    payload = context_status_payload(
        DiscordMessageContext(
            guild_id="guild-1",
            channel_id="channel-1",
            content="1번",
            recent_messages=("Bot Owner: 1. Web/Canvas", "user-1: 1번"),
        )
    )

    assert payload["recent_messages"] == ["Bot Owner: 1. Web/Canvas", "user-1: 1번"]


def test_attach_context_status_returns_action_with_status() -> None:
    action = DiscordBotAction(action_type="context_status_check", summary="check", mapping_id="mapping-1")

    updated = attach_context_status(action, {"status": "compact_now"})

    assert updated.action_type == action.action_type
    assert updated.mapping_id == "mapping-1"
    assert updated.context_status == {"status": "compact_now"}


def test_build_owner_run_payload_for_project_owner_message() -> None:
    context = DiscordMessageContext(
        guild_id="guild-1",
        channel_id="channel-1",
        thread_id="thread-1",
        author_id="user-1",
        content="작업을 다음 단계로 쪼개줘",
    )
    mapping = {
        "mapping_id": "mapping-1",
        "project_id": 7,
        "conversation_kind": "project",
        "thread_role": "owner-tasks",
        "summary_memory_key": "project:7:thread:thread-1:summary:current",
    }
    action = route_discord_message(context, mapping)
    action = attach_context_status(action, {"status": "ok", "estimated_tokens": 1200})

    payload = build_owner_run_payload(context, mapping, action)

    assert payload["objective"] == "작업을 다음 단계로 쪼개줘"
    assert payload["dry_run"] is True
    assert "Source: Discord operator console." in payload["context"]
    assert "Project id: 7" in payload["context"]
    assert "Summary memory key: project:7:thread:thread-1:summary:current" in payload["context"]
    assert '"status": "ok"' in payload["context"]


def test_build_owner_run_payload_includes_recent_discord_conversation() -> None:
    context = DiscordMessageContext(
        guild_id="guild-1",
        channel_id="channel-1",
        author_id="user-1",
        content="1번",
        recent_messages=(
            "Bot Owner: 선택지: 1. Web/Canvas 2. Godot 3. Unity",
            "sonyeongha: 1번",
        ),
    )
    mapping = {
        "mapping_id": "mapping-1",
        "conversation_kind": "owner_room",
        "thread_role": "owner-design",
    }
    action = route_discord_message(context, mapping)

    payload = build_owner_run_payload(context, mapping, action)

    assert payload["objective"] == "1번"
    assert "Recent Discord conversation, oldest to newest:" in payload["context"]
    assert "Bot Owner: 선택지: 1. Web/Canvas 2. Godot 3. Unity" in payload["context"]
    assert "Current user message:\n1번" in payload["context"]


def test_build_owner_run_payload_for_owner_room_requests_conversational_reply() -> None:
    context = DiscordMessageContext(guild_id="guild-1", channel_id="channel-1", content="continue")
    mapping = {
        "mapping_id": "mapping-1",
        "conversation_kind": "owner_room",
        "thread_role": "owner-design",
    }
    action = route_discord_message(context, mapping)

    payload = build_owner_run_payload(context, mapping, action)

    assert "This is the human-facing Owner room." in payload["context"]
    assert "Reply naturally and concisely in Korean." in payload["context"]
    assert "Do not expose raw planning sections" in payload["context"]
    assert "decision_summary" in payload["context"]


def test_build_owner_run_payload_for_project_owner_prefers_readable_summary() -> None:
    context = DiscordMessageContext(guild_id="guild-1", channel_id="channel-1", content="continue")
    mapping = {
        "mapping_id": "mapping-1",
        "project_id": 7,
        "conversation_kind": "project",
        "thread_role": "owner-tasks",
    }
    action = route_discord_message(context, mapping)

    payload = build_owner_run_payload(context, mapping, action)

    assert "This is a project Owner conversation with the human." in payload["context"]
    assert "Prefer a readable Korean summary" in payload["context"]
    assert "only when the user explicitly asks to list or create worker tasks" in payload["context"]


def test_attach_owner_run_payload_only_for_owner_actions() -> None:
    context = DiscordMessageContext(guild_id="guild-1", channel_id="channel-1", content="hello")
    mapping = {"mapping_id": "mapping-1", "conversation_kind": "owner_room", "thread_role": "owner-tasks"}
    owner_action = route_discord_message(context, mapping)

    with_payload = attach_owner_run_payload(owner_action, context, mapping, dry_run=False)

    assert with_payload.owner_run_payload is not None
    assert with_payload.owner_run_payload["dry_run"] is False

    record_action = DiscordBotAction(action_type="record_only", summary="record")
    without_payload = attach_owner_run_payload(record_action, context, mapping)
    assert without_payload.owner_run_payload is None


def test_attach_owner_run_result_returns_action_with_result() -> None:
    action = DiscordBotAction(action_type="project_owner_message", summary="owner", needs_owner=True)

    updated = attach_owner_run_result(action, {"id": 12, "status": "dry_run"})

    assert updated.owner_run_result == {"id": 12, "status": "dry_run"}
