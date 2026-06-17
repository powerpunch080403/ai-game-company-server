from __future__ import annotations

import pytest
from app.discord_bot import parse_approval_decision
from app.discord_gateway import (
    handle_gateway_message,
    format_gateway_reply,
    discord_message_to_context,
)
from tests.test_discord_gateway import FakeApi, FakeChannel, fake_message

def test_parse_approval_decision_safety() -> None:
    # Exact and keyword matches for approve
    assert parse_approval_decision("승인합니다") == "approved"
    assert parse_approval_decision("좋아 진행해") == "approved"
    assert parse_approval_decision("ok let's go") == "approved"
    assert parse_approval_decision("y") == "approved"

    # Exact and keyword matches for reject
    assert parse_approval_decision("거절합니다") == "rejected"
    assert parse_approval_decision("반려할게요") == "rejected"
    assert parse_approval_decision("no, stop") == "rejected"
    assert parse_approval_decision("취소") == "rejected"

    # Ambiguous or non-committal answers should return None (neither approved nor rejected)
    assert parse_approval_decision("글쎄요") is None
    assert parse_approval_decision("나중에 결정할게요") is None
    assert parse_approval_decision("어떻게 생각해?") is None
    assert parse_approval_decision("hello world") is None

def test_approval_fails_when_no_pending_requests() -> None:
    # Mapping exists but there are no pending approval requests in the database
    api = FakeApi(
        mappings=[
            {
                "mapping_id": "mapping-1",
                "discord_guild_id": "guild-1",
                "discord_channel_id": "channel-1",
                "discord_thread_id": "",
                "conversation_kind": "approval_inbox",
                "thread_role": "decisions",
                "project_id": 3,
                "archived_at": None,
            }
        ],
        pending_approvals=[] # Empty pending approvals
    )

    action = handle_gateway_message(
        discord_message_to_context(fake_message("승인", FakeChannel("channel-1"))),
        api,
    )

    # Action should identify it needs approval, but approval_result should hold no_pending_approvals error
    assert action.needs_approval is True
    assert action.approval_result == {"error": "no_pending_approvals"}

    reply = format_gateway_reply(action)
    assert reply == "현재 대기 중인 승인 요청이 없습니다."

def test_unmapped_location_does_not_execute_approval() -> None:
    # No mappings exist for this channel
    api = FakeApi(mappings=[], pending_approvals=[])

    action = handle_gateway_message(
        discord_message_to_context(fake_message("승인해", FakeChannel("unmapped-channel"))),
        api,
    )

    assert action.action_type == "unmapped_context"
    assert action.needs_approval is False
    assert action.approval_result is None

    reply = format_gateway_reply(action)
    assert reply is None # Unmapped contexts return None reply by default (unless reply_unmapped=True is passed)

def test_default_safe_dry_run_for_owner_runs() -> None:
    api = FakeApi(
        mappings=[
            {
                "mapping_id": "mapping-1",
                "discord_guild_id": "guild-1",
                "discord_channel_id": "channel-1",
                "discord_thread_id": "",
                "conversation_kind": "owner_room",
                "thread_role": "owner-tasks",
                "project_id": 1,
                "archived_at": None,
            }
        ]
    )

    # Call handle_gateway_message without execute_owner_run parameter (should default to dry-run)
    action = handle_gateway_message(
        discord_message_to_context(fake_message("이 작업을 쪼개줘", FakeChannel("channel-1"))),
        api,
        submit_owner_run=True,
    )

    assert action.needs_owner is True
    assert action.owner_run_payload["dry_run"] is True
    # Verify return response matches dry run status
    reply = format_gateway_reply(action)
    assert "stored:" in reply and "(dry_run)" in reply
