from __future__ import annotations

import asyncio

from app.discord_gateway import (
    collect_recent_discord_messages,
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
    def __init__(
        self,
        channel_id: str,
        parent_id: str | None = None,
        typing_fails: bool = False,
        history_messages: list[object] | None = None,
    ):
        self.id = channel_id
        self.parent_id = parent_id
        self.sent: list[str] = []
        self.typing_entered = 0
        self.typing_fails = typing_fails
        self.history_messages = history_messages or []
        self.created_threads: list[FakeThread] = []

    async def send(self, content: str) -> None:
        self.sent.append(content)

    async def create_thread(self, name: str, auto_archive_duration: int = 1440):
        thread = FakeThread(f"thread-{len(self.created_threads) + 1}", name)
        self.created_threads.append(thread)
        return thread

    async def history(self, limit: int, before=None, oldest_first: bool = False):
        selected = self.history_messages[-limit:] if limit else []
        if not oldest_first:
            selected = list(reversed(selected))
        for item in selected:
            yield item

    def typing(self):
        channel = self

        class FakeTyping:
            async def __aenter__(self):
                if channel.typing_fails:
                    raise RuntimeError("typing denied")
                channel.typing_entered += 1

            async def __aexit__(self, exc_type, exc, tb):
                return False

        return FakeTyping()


class FakeThread:
    def __init__(self, thread_id: str, name: str):
        self.id = thread_id
        self.name = name
        self.sent: list[str] = []

    async def send(self, content: str) -> None:
        self.sent.append(content)


class FakeApi:
    def __init__(self, mappings: list[dict], pending_approvals: list[dict] | None = None):
        self.mappings = mappings
        self.pending_approvals = pending_approvals if pending_approvals is not None else []
        self.context_payloads: list[tuple[str, dict]] = []
        self.owner_payloads: list[dict] = []
        self.decided_payloads: list[tuple[str, dict]] = []
        self.projects: list[dict] = []
        self.trees: dict[int, dict] = {}
        self.created_tasks: list[dict] = []
        self.thread_refs: list[tuple[int, dict]] = []
        self.discord_mappings: list[dict] = []

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

    def list_approvals(self, status=None, project_id=None, target_type=None):
        return self.pending_approvals

    def decide_approval(self, approval_id: str, payload: dict):
        self.decided_payloads.append((approval_id, payload))
        return {
            "approval_id": approval_id,
            "status": payload.get("status"),
            "request_summary": "Test private repo creation",
            "approved_by": payload.get("approved_by"),
        }

    def list_projects(self):
        return self.projects

    def create_project(self, payload: dict):
        project = {"id": len(self.projects) + 1, **payload}
        self.projects.append(project)
        self.trees[project["id"]] = {**project, "epics": []}
        return project

    def get_project_tree(self, project_id: int):
        return self.trees[project_id]

    def create_epic(self, project_id: int, payload: dict):
        epic = {"id": 10 + len(self.trees[project_id]["epics"]), "project_id": project_id, **payload, "sub_epics": []}
        self.trees[project_id]["epics"].append(epic)
        return epic

    def create_sub_epic(self, epic_id: int, payload: dict):
        for tree in self.trees.values():
            for epic in tree["epics"]:
                if epic["id"] == epic_id:
                    sub_epic = {"id": 20 + len(epic["sub_epics"]), "epic_id": epic_id, **payload, "tasks": []}
                    epic["sub_epics"].append(sub_epic)
                    return sub_epic
        raise KeyError("epic not found")

    def create_task(self, sub_epic_id: int, payload: dict):
        task = {"id": 30 + len(self.created_tasks), "sub_epic_id": sub_epic_id, "status": "pending", **payload}
        self.created_tasks.append(task)
        for tree in self.trees.values():
            for epic in tree["epics"]:
                for sub_epic in epic["sub_epics"]:
                    if sub_epic["id"] == sub_epic_id:
                        sub_epic["tasks"].append(task)
                        return task
        raise KeyError("sub epic not found")

    def upsert_task_thread_reference(self, task_id: int, payload: dict):
        ref = {"id": len(self.thread_refs) + 1, "task_id": task_id, "project_id": 1, **payload}
        self.thread_refs.append((task_id, payload))
        return ref

    def get_task_thread_reference(self, task_id: int):
        for ref_task_id, payload in reversed(self.thread_refs):
            if ref_task_id == task_id:
                return {"id": 1, "task_id": task_id, "project_id": 1, **payload}
        return None

    def upsert_discord_mapping(self, payload: dict):
        mapping = {"mapping_id": f"mapping-{len(self.discord_mappings) + 1}", **payload}
        self.discord_mappings.append(mapping)
        return mapping


def fake_message(
    content: str,
    channel: FakeChannel | None = None,
    bot: bool = False,
    name: str = "user-1",
    display_name: str | None = None,
):
    return FakeObject(
        guild=FakeObject(id="guild-1"),
        channel=channel or FakeChannel("channel-1"),
        author=FakeObject(id="user-1", bot=bot, name=name, display_name=display_name or name),
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


def test_collect_recent_discord_messages_includes_bot_context_and_current_message() -> None:
    channel = FakeChannel(
        "channel-1",
        history_messages=[
            fake_message("선택지: 1. Web/Canvas 2. Godot", bot=True, name="OwnerBot"),
            fake_message("시작하자", name="sonyeongha"),
        ],
    )
    message = fake_message("1번", channel, name="sonyeongha")

    lines = asyncio.run(collect_recent_discord_messages(message))

    assert lines == (
        "Bot OwnerBot: 선택지: 1. Web/Canvas 2. Godot",
        "sonyeongha: 시작하자",
        "sonyeongha: 1번",
    )


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

    success_reply = format_gateway_reply(
        FakeObject(
            action_type="owner_room_message",
            context_status=None,
            needs_owner=True,
            needs_approval=False,
            owner_run_result={"id": 6, "status": "success", "stdout": "안녕! 무엇을 도와줄까?"},
            owner_run_payload=None,
            summary="",
        )
    )
    assert success_reply == "안녕! 무엇을 도와줄까?"

    failed_reply = format_gateway_reply(
        FakeObject(
            action_type="owner_room_message",
            context_status=None,
            needs_owner=True,
            needs_approval=False,
            owner_run_result={
                "id": 7,
                "status": "failed",
                "stdout": "",
                "stderr": "WARN noisy line\nERROR: You've hit your usage limit. Try again later.",
            },
            owner_run_payload=None,
            summary="",
        )
    )
    assert failed_reply == "Owner run #7 failed: ERROR: You've hit your usage limit. Try again later."


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
    assert channel.typing_entered == 1


def test_handle_discord_message_sends_recent_history_to_owner() -> None:
    channel = FakeChannel(
        "channel-1",
        history_messages=[
            fake_message("선택지: 1. Web/Canvas 2. Godot", bot=True, name="OwnerBot"),
        ],
    )
    message = fake_message("1번", channel, name="sonyeongha")
    api = FakeApi(
        [
            {
                "mapping_id": "mapping-1",
                "discord_guild_id": "guild-1",
                "discord_channel_id": "channel-1",
                "discord_thread_id": "",
                "conversation_kind": "owner_room",
                "thread_role": "owner-design",
                "project_id": None,
                "archived_at": None,
            }
        ]
    )

    action = asyncio.run(handle_discord_message(message, api, submit_owner_run=True, execute_owner_run=True))

    assert action.action_type == "owner_room_message"
    assert "Bot OwnerBot: 선택지: 1. Web/Canvas 2. Godot" in api.owner_payloads[0]["context"]
    assert "sonyeongha: 1번" in api.owner_payloads[0]["context"]


def test_handle_discord_message_start_creates_bootstrap_task_and_thread() -> None:
    channel = FakeChannel(
        "channel-1",
        history_messages=[
            fake_message("Web/Canvas 기반 30초 코인 아레나로 시작하자", bot=True, name="OwnerBot"),
        ],
    )
    message = fake_message("시작해줘", channel, name="sonyeongha")
    api = FakeApi(
        [
            {
                "mapping_id": "mapping-1",
                "discord_guild_id": "guild-1",
                "discord_channel_id": "channel-1",
                "discord_thread_id": "",
                "conversation_kind": "owner_room",
                "thread_role": "owner-design",
                "project_id": None,
                "archived_at": None,
            }
        ]
    )

    action = asyncio.run(handle_discord_message(message, api, submit_owner_run=True, execute_owner_run=True))

    assert action.operation_result["kind"] == "owner_tool_executed"
    assert action.operation_result["tool_name"] == "create_coin_arena_bootstrap_task"
    assert api.projects[0]["name"] == "Coin Arena Server Test"
    assert api.created_tasks[0]["branch"] == "worker/canvas-client-bootstrap"
    assert api.thread_refs[0][0] == api.created_tasks[0]["id"]
    assert api.discord_mappings[0]["discord_thread_id"] == "thread-1"
    assert api.discord_mappings[0]["conversation_kind"] == "ai_internal"
    assert api.discord_mappings[0]["thread_role"] == "ai-internal-task"
    assert channel.created_threads[0].name.startswith("Task-")
    assert "Branch: worker/canvas-client-bootstrap" in channel.created_threads[0].sent[0]
    assert "말만 한 게 아니라 서버에 첫 작업을 실제로 만들었어" in channel.sent[0]


def test_handle_discord_message_start_reuses_existing_bootstrap_task() -> None:
    channel = FakeChannel(
        "channel-1",
        history_messages=[
            fake_message("Web/Canvas 기반 30초 코인 아레나로 시작하자", bot=True, name="OwnerBot"),
        ],
    )
    message = fake_message("시작해줘", channel, name="sonyeongha")
    api = FakeApi(
        [
            {
                "mapping_id": "mapping-1",
                "discord_guild_id": "guild-1",
                "discord_channel_id": "channel-1",
                "discord_thread_id": "",
                "conversation_kind": "owner_room",
                "thread_role": "owner-design",
                "project_id": None,
                "archived_at": None,
            }
        ]
    )
    project = api.create_project({"name": "Coin Arena Server Test", "description": "", "engine": "Web/Canvas"})
    epic = api.create_epic(project["id"], {"name": "Project Bootstrap", "goal": ""})
    sub_epic = api.create_sub_epic(epic["id"], {"name": "Canvas Client Bootstrap", "goal": ""})
    api.create_task(
        sub_epic["id"],
        {
            "role": "code_worker",
            "goal": "existing",
            "requirements": ["existing"],
            "success_criteria": ["existing"],
            "estimated_minutes": 15,
            "memory_refs": [],
            "branch": "worker/canvas-client-bootstrap",
        },
    )
    api.upsert_task_thread_reference(
        30,
        {
            "provider": "discord",
            "channel_id": "channel-1",
            "thread_id": "existing-thread",
            "thread_url": "https://discord.test/existing-thread",
            "title": "Canvas client bootstrap",
        },
    )

    action = asyncio.run(handle_discord_message(message, api, submit_owner_run=True, execute_owner_run=True))

    assert action.operation_result["kind"] == "owner_tool_executed"
    assert action.operation_result["tool_name"] == "create_coin_arena_bootstrap_task"
    assert action.operation_result["created_task"] is False
    assert len(api.created_tasks) == 1
    assert channel.created_threads == []
    assert action.operation_result["thread"]["reason"] == "existing_thread_reference"
    assert "태스크: #30" in channel.sent[0]
    assert "이미 연결된 스레드가 있어" in channel.sent[0]


def test_handle_discord_message_recreates_deleted_bootstrap_thread() -> None:
    channel = FakeChannel(
        "channel-1",
        history_messages=[
            fake_message("Web/Canvas 기반 30초 코인 아레나로 시작하자", bot=True, name="OwnerBot"),
        ],
    )
    message = fake_message("삭제했어 다시 진행해봐", channel, name="sonyeongha")
    api = FakeApi(
        [
            {
                "mapping_id": "mapping-1",
                "discord_guild_id": "guild-1",
                "discord_channel_id": "channel-1",
                "discord_thread_id": "",
                "conversation_kind": "owner_room",
                "thread_role": "owner-design",
                "project_id": None,
                "archived_at": None,
            }
        ]
    )
    project = api.create_project({"name": "Coin Arena Server Test", "description": "", "engine": "Web/Canvas"})
    epic = api.create_epic(project["id"], {"name": "Project Bootstrap", "goal": ""})
    sub_epic = api.create_sub_epic(epic["id"], {"name": "Canvas Client Bootstrap", "goal": ""})
    api.create_task(
        sub_epic["id"],
        {
            "role": "code_worker",
            "goal": "existing",
            "requirements": ["existing"],
            "success_criteria": ["existing"],
            "estimated_minutes": 15,
            "memory_refs": [],
            "branch": "worker/canvas-client-bootstrap",
        },
    )
    api.upsert_task_thread_reference(
        30,
        {
            "provider": "discord",
            "channel_id": "channel-1",
            "thread_id": "deleted-thread",
            "thread_url": "https://discord.test/deleted-thread",
            "title": "Canvas client bootstrap",
        },
    )

    action = asyncio.run(handle_discord_message(message, api, submit_owner_run=True, execute_owner_run=True))

    assert action.operation_result["kind"] == "owner_tool_executed"
    assert action.operation_result["tool_name"] == "create_coin_arena_bootstrap_task"
    assert action.operation_result["created_task"] is False
    assert action.operation_result["thread"]["created"] is True
    assert len(api.created_tasks) == 1
    assert len(channel.created_threads) == 1
    assert api.thread_refs[-1][1]["thread_id"] == "thread-1"
    assert "스레드도 만들었어" in channel.sent[0]


def test_handle_discord_message_splits_long_replies() -> None:
    channel = FakeChannel("channel-1")
    message = fake_message("hello", channel)

    class LongReplyApi(FakeApi):
        def create_owner_run(self, payload: dict):
            self.owner_payloads.append(payload)
            return {"id": 10, "status": "success", "stdout": "x" * 4100}

    api = LongReplyApi(
        [
            {
                "mapping_id": "mapping-1",
                "discord_guild_id": "guild-1",
                "discord_channel_id": "channel-1",
                "discord_thread_id": "",
                "conversation_kind": "owner_room",
                "thread_role": "owner-design",
                "project_id": None,
                "archived_at": None,
            }
        ]
    )

    action = asyncio.run(handle_discord_message(message, api, submit_owner_run=True, execute_owner_run=True))

    assert action.action_type == "owner_room_message"
    assert len(channel.sent) == 1
    assert len(channel.sent[0]) <= 1900
    assert channel.sent[0].endswith("[truncated]")


def test_handle_discord_message_continues_when_typing_indicator_fails() -> None:
    channel = FakeChannel("channel-1", typing_fails=True)
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
    assert channel.typing_entered == 0


def test_handle_gateway_message_routes_approval_and_decides_approved() -> None:
    api = FakeApi(
        mappings=[
            {
                "mapping_id": "mapping-approval",
                "discord_guild_id": "guild-1",
                "discord_channel_id": "channel-approval",
                "discord_thread_id": "",
                "conversation_kind": "approval_inbox",
                "thread_role": "decisions",
                "project_id": 3,
                "archived_at": None,
            }
        ],
        pending_approvals=[
            {
                "approval_id": "approval-001",
                "project_id": 3,
                "status": "pending",
                "request_summary": "Test private repo creation",
            }
        ]
    )

    action = handle_gateway_message(
        discord_message_to_context(fake_message("좋아 진행해", FakeChannel("channel-approval"))),
        api,
    )

    assert action.action_type == "approval_conversation"
    assert action.needs_approval is True
    assert action.approval_result["success"] is True
    assert action.approval_result["result"]["status"] == "approved"
    assert api.decided_payloads[0] == (
        "approval-001",
        {
            "status": "approved",
            "approved_by": "user-1",
            "approval_message": "좋아 진행해",
        }
    )

    reply = format_gateway_reply(action)
    assert "성공적으로 승인 처리되었습니다." in reply


def test_handle_gateway_message_routes_approval_and_decides_rejected() -> None:
    api = FakeApi(
        mappings=[
            {
                "mapping_id": "mapping-approval",
                "discord_guild_id": "guild-1",
                "discord_channel_id": "channel-approval",
                "discord_thread_id": "",
                "conversation_kind": "approval_inbox",
                "thread_role": "decisions",
                "project_id": 3,
                "archived_at": None,
            }
        ],
        pending_approvals=[
            {
                "approval_id": "approval-001",
                "project_id": 3,
                "status": "pending",
                "request_summary": "Test private repo creation",
            }
        ]
    )

    action = handle_gateway_message(
        discord_message_to_context(fake_message("거절해", FakeChannel("channel-approval"))),
        api,
    )

    assert action.approval_result["success"] is True
    assert action.approval_result["result"]["status"] == "rejected"
    assert api.decided_payloads[0][1]["status"] == "rejected"

    reply = format_gateway_reply(action)
    assert "성공적으로 거절(반려) 처리되었습니다." in reply


def test_handle_gateway_message_routes_approval_ambiguous() -> None:
    api = FakeApi(
        mappings=[
            {
                "mapping_id": "mapping-approval",
                "discord_guild_id": "guild-1",
                "discord_channel_id": "channel-approval",
                "discord_thread_id": "",
                "conversation_kind": "approval_inbox",
                "thread_role": "decisions",
                "project_id": 3,
                "archived_at": None,
            }
        ],
        pending_approvals=[
            {
                "approval_id": "approval-001",
                "project_id": 3,
                "status": "pending",
                "request_summary": "Test private repo creation",
            }
        ]
    )

    action = handle_gateway_message(
        discord_message_to_context(fake_message("글쎄 잘 모르겠네", FakeChannel("channel-approval"))),
        api,
    )

    assert "error" in action.approval_result
    assert action.approval_result["error"] == "ambiguous_decision"

    reply = format_gateway_reply(action)
    assert "명확히 판단할 수 없습니다." in reply
