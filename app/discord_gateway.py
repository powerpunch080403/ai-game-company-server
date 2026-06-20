from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
import traceback
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from app.discord_bot import (
    DiscordBotAction,
    DiscordMessageContext,
    GameCompanyApiClient,
    attach_context_status,
    attach_owner_run_payload,
    attach_owner_run_result,
    context_status_payload,
    route_discord_message,
    select_mapping,
    parse_approval_decision,
)

load_dotenv()


def snowflake(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def discord_message_to_context(message: Any, recent_messages: tuple[str, ...] | None = None) -> DiscordMessageContext:
    guild = getattr(message, "guild", None)
    channel = getattr(message, "channel", None)
    author = getattr(message, "author", None)
    channel_parent_id = getattr(channel, "parent_id", None)
    if channel_parent_id is not None:
        channel_id = snowflake(channel_parent_id)
        thread_id = snowflake(getattr(channel, "id", ""))
    else:
        channel_id = snowflake(getattr(channel, "id", ""))
        thread_id = ""
    return DiscordMessageContext(
        guild_id=snowflake(getattr(guild, "id", "")),
        channel_id=channel_id,
        thread_id=thread_id,
        author_id=snowflake(getattr(author, "id", "")),
        content=str(getattr(message, "content", "") or ""),
        recent_messages=recent_messages or (),
    )


def format_history_message(message: Any) -> str:
    author = getattr(message, "author", None)
    author_name = (
        getattr(author, "display_name", None)
        or getattr(author, "name", None)
        or snowflake(getattr(author, "id", "unknown"))
    )
    if bool(getattr(author, "bot", False)):
        author_name = f"Bot {author_name}"
    content = str(getattr(message, "clean_content", None) or getattr(message, "content", "") or "").strip()
    attachments = []
    for attachment in getattr(message, "attachments", []) or []:
        filename = getattr(attachment, "filename", None) or getattr(attachment, "url", "attachment")
        attachments.append(f"[attachment: {filename}]")
    if attachments:
        content = " ".join([content, *attachments]).strip()
    return f"{author_name}: {content}" if content else ""


async def collect_recent_discord_messages(message: Any, limit: int = 12) -> tuple[str, ...]:
    channel = getattr(message, "channel", None)
    history = getattr(channel, "history", None)
    messages: list[Any] = []
    if callable(history):
        try:
            async for item in history(limit=max(limit - 1, 0), before=message, oldest_first=False):
                messages.append(item)
        except Exception as exc:
            print(f"Discord history read failed: {exc}", flush=True)
            messages = []
    messages.reverse()
    messages.append(message)
    lines = [format_history_message(item) for item in messages]
    return tuple(line for line in lines if line)


def should_ignore_message(message: Any) -> bool:
    author = getattr(message, "author", None)
    if bool(getattr(author, "bot", False)):
        return True
    if getattr(message, "guild", None) is None:
        return True
    return not str(getattr(message, "content", "") or "").strip()


def handle_gateway_message(
    context: DiscordMessageContext,
    api: GameCompanyApiClient,
    submit_owner_run: bool = False,
    execute_owner_run: bool = False,
    check_context_for_owner: bool = True,
) -> DiscordBotAction:
    mappings = api.list_discord_mappings(context)
    mapping = select_mapping(mappings, context)
    action = route_discord_message(context, mapping)

    should_check_context = (
        action.action_type == "context_status_check"
        or (check_context_for_owner and action.needs_owner)
    )
    if should_check_context and mapping and mapping.get("mapping_id"):
        status_payload = context_status_payload(context)
        action = attach_context_status(action, api.context_status(mapping["mapping_id"], status_payload))

    action = attach_owner_run_payload(action, context, mapping, dry_run=not execute_owner_run)
    if submit_owner_run and action.owner_run_payload:
        action = attach_owner_run_result(action, api.create_owner_run(action.owner_run_payload))

    if action.needs_approval and mapping:
        project_id = mapping.get("project_id")
        if project_id is not None:
            try:
                approvals = api.list_approvals(status="pending", project_id=project_id)
                if not approvals:
                    action = replace(action, approval_result={"error": "no_pending_approvals"})
                else:
                    target_approval = approvals[0]
                    decision_status = parse_approval_decision(context.content)
                    if not decision_status:
                        action = replace(action, approval_result={"error": "ambiguous_decision", "target": target_approval})
                    else:
                        decision_payload = {
                            "status": decision_status,
                            "approved_by": context.author_id or "discord_user",
                            "approval_message": context.content,
                        }
                        result = api.decide_approval(target_approval["approval_id"], decision_payload)
                        action = replace(action, approval_result={"success": True, "result": result})
            except Exception as exc:
                action = replace(action, approval_result={"error": f"api_failed: {exc}"})

    return action


BOOTSTRAP_PROJECT_NAME = "Coin Arena Server Test"
BOOTSTRAP_EPIC_NAME = "Project Bootstrap"
BOOTSTRAP_SUB_EPIC_NAME = "Canvas Client Bootstrap"
BOOTSTRAP_TASK_BRANCH = "worker/canvas-client-bootstrap"
BOOTSTRAP_TASK_TITLE = "Canvas client bootstrap"


def env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def bootstrap_project_config() -> dict[str, str]:
    return {
        "engine": os.getenv("GAME_COMPANY_BOOTSTRAP_ENGINE", "Web/Canvas"),
        "repo_url": os.getenv("GAME_COMPANY_BOOTSTRAP_REPO_URL", "").strip(),
        "workspace_path": os.getenv("GAME_COMPANY_BOOTSTRAP_WORKSPACE_PATH", "").strip(),
        "base_branch": os.getenv("GAME_COMPANY_BOOTSTRAP_BASE_BRANCH", "main").strip() or "main",
    }


def project_has_worker_config(project: dict[str, Any]) -> bool:
    return bool(str(project.get("repo_url") or "").strip() and str(project.get("workspace_path") or "").strip())


@dataclass(frozen=True)
class OwnerToolCall:
    name: str
    reason: str
    recreate_thread: bool = False


def detect_owner_tool_call(context: DiscordMessageContext, action: DiscordBotAction) -> OwnerToolCall | None:
    if not action.needs_owner:
        return None
    normalized = context.content.replace(" ", "").lower()
    if not any(keyword in normalized for keyword in ("시작", "계속진행", "진행해", "진행", "start", "continue")):
        return None
    recent = "\n".join([*context.recent_messages, context.content]).lower()
    cues = ("30초 코인", "coin arena", "web/canvas", "canvas", "서버 테스트", "작은 게임", "작은게임")
    if not any(cue in recent for cue in cues):
        return None
    return OwnerToolCall(
        name="create_coin_arena_bootstrap_task",
        reason="Owner conversation approved the Web/Canvas coin arena bootstrap task.",
        recreate_thread=should_recreate_bootstrap_thread(context),
    )


def should_create_bootstrap_task(context: DiscordMessageContext, action: DiscordBotAction) -> bool:
    return detect_owner_tool_call(context, action) is not None


def should_recreate_bootstrap_thread(context: DiscordMessageContext) -> bool:
    normalized = "\n".join([*context.recent_messages, context.content]).replace(" ", "").lower()
    return any(keyword in normalized for keyword in ("삭제", "다시", "재생성", "스레드", "thread"))


def find_project_by_name(projects: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for project in projects:
        if project.get("name") == name:
            return project
    return None


def find_tree_epic(tree: dict[str, Any], name: str) -> dict[str, Any] | None:
    for epic in tree.get("epics", []):
        if epic.get("name") == name:
            return epic
    return None


def find_tree_sub_epic(epic: dict[str, Any] | None, name: str) -> dict[str, Any] | None:
    if not epic:
        return None
    for sub_epic in epic.get("sub_epics", []):
        if sub_epic.get("name") == name:
            return sub_epic
    return None


def find_tree_task(tree: dict[str, Any], branch: str) -> dict[str, Any] | None:
    for epic in tree.get("epics", []):
        for sub_epic in epic.get("sub_epics", []):
            for task in sub_epic.get("tasks", []):
                if task.get("branch") == branch:
                    return task
    return None


def ensure_bootstrap_task(api: GameCompanyApiClient) -> dict[str, Any]:
    projects = api.list_projects()
    project = find_project_by_name(projects, BOOTSTRAP_PROJECT_NAME)
    created_project = False
    configured_project = False
    project_config = bootstrap_project_config()
    if project is None:
        project = api.create_project(
            {
                "name": BOOTSTRAP_PROJECT_NAME,
                "description": "Tiny Web/Canvas 30-second coin arena used to validate the AI Game Company server loop.",
                **project_config,
            }
        )
        created_project = True
        configured_project = project_has_worker_config(project)
    elif not project_has_worker_config(project) and project_has_worker_config(project_config):
        project = api.update_project_config(project["id"], project_config)
        configured_project = True

    tree = api.get_project_tree(project["id"])
    existing_task = find_tree_task(tree, BOOTSTRAP_TASK_BRANCH)
    if existing_task is not None:
        return {
            "project": project,
            "task": existing_task,
            "created_project": created_project,
            "configured_project": configured_project,
            "created_task": False,
            "thread_reference": None,
        }

    epic = find_tree_epic(tree, BOOTSTRAP_EPIC_NAME)
    if epic is None:
        epic = api.create_epic(
            project["id"],
            {
                "name": BOOTSTRAP_EPIC_NAME,
                "goal": "Create the smallest runnable Web/Canvas game project structure for server pipeline testing.",
            },
        )

    sub_epic = find_tree_sub_epic(epic, BOOTSTRAP_SUB_EPIC_NAME)
    if sub_epic is None:
        sub_epic = api.create_sub_epic(
            epic["id"],
            {
                "name": BOOTSTRAP_SUB_EPIC_NAME,
                "goal": "Prepare static Canvas client scaffolding without implementing the full game loop.",
            },
        )

    task = api.create_task(
        sub_epic["id"],
        {
            "role": "code_worker",
            "goal": "Bootstrap the 30-second coin arena Web/Canvas client scaffold.",
            "requirements": [
                "Create a minimal static Canvas client structure.",
                "Show server connection status placeholder text.",
                "Add room create/join button placeholders.",
                "Do not implement the full realtime game loop yet.",
            ],
            "success_criteria": [
                "Client can be opened locally without a build step.",
                "Canvas renders a visible bootstrap screen.",
                "Smoke-check instructions or stub are present.",
                "Changes stay inside the bootstrap write scope.",
            ],
            "estimated_minutes": 15,
            "memory_refs": [],
            "branch": BOOTSTRAP_TASK_BRANCH,
            "write_scope": ["client/coin-arena/**", "tests/**", "README.md"],
            "read_scope": ["README.md", "docs/**", "client/coin-arena/**", "tests/**"],
            "forbidden_scope": [
                ".env",
                ".env.*",
                "**/.env",
                "**/.env.*",
                ".git/**",
                ".github/**",
                "node_modules/**",
                ".venv/**",
                "venv/**",
                "__pycache__/**",
            ],
        },
    )
    return {
        "project": project,
        "task": task,
        "created_project": created_project,
        "configured_project": configured_project,
        "created_task": True,
        "thread_reference": None,
    }


async def create_task_thread_for_bootstrap(message: Any, api: GameCompanyApiClient, result: dict[str, Any]) -> dict[str, Any]:
    task = result["task"]
    project = result["project"]
    channel = getattr(message, "channel", None)
    create_thread = getattr(channel, "create_thread", None)
    if not callable(create_thread):
        return {"created": False, "reason": "channel_does_not_support_threads"}

    thread_name = f"Task-{task['id']}: {BOOTSTRAP_TASK_TITLE}"
    if len(thread_name) > 100:
        thread_name = thread_name[:97] + "..."
    thread = await create_thread(name=thread_name, auto_archive_duration=1440)
    thread_id = snowflake(getattr(thread, "id", ""))
    guild_id = snowflake(getattr(getattr(message, "guild", None), "id", ""))
    parent_id = snowflake(getattr(channel, "id", ""))
    thread_url = f"https://discord.com/channels/{guild_id}/{parent_id}/{thread_id}" if guild_id and thread_id else ""
    initial_message = (
        f"Task #{task['id']}: {BOOTSTRAP_TASK_TITLE}\n\n"
        f"Project: {project['name']} (#{project['id']})\n"
        f"Branch: {task['branch']}\n\n"
        "Goal:\n"
        f"{task['goal']}\n\n"
        "Write scope:\n"
        + "\n".join(f"- {item}" for item in task.get("write_scope", []))
        + "\n\nWorker notes:\n"
        "- Work only inside write_scope.\n"
        "- Do not run a merge.\n"
        "- Report the real head_commit after committing."
    )
    send = getattr(thread, "send", None)
    if callable(send):
        await send(initial_message)

    ref = api.upsert_task_thread_reference(
        task["id"],
        {
            "provider": "discord",
            "channel_id": parent_id,
            "thread_id": thread_id,
            "thread_url": thread_url,
            "title": BOOTSTRAP_TASK_TITLE,
            "summary": initial_message[:200],
            "created_by": "discord_owner",
            "metadata": {"kind": "bootstrap_task"},
        },
    )
    mapping = api.upsert_discord_mapping(
        {
            "discord_guild_id": guild_id,
            "discord_channel_id": parent_id,
            "discord_thread_id": thread_id,
            "project_id": project["id"],
            "conversation_kind": "ai_internal",
            "thread_role": "ai-internal-task",
            "created_by": "discord_gateway",
            "notes": f"Task thread for task #{task['id']}.",
        }
    )
    return {
        "created": True,
        "thread_id": thread_id,
        "thread_url": thread_url,
        "thread_reference": ref,
        "mapping": mapping,
    }


def existing_bootstrap_thread_reference(api: GameCompanyApiClient, task_id: int) -> dict[str, Any]:
    ref = api.get_task_thread_reference(task_id)
    if not ref:
        return {"created": False, "reason": "missing_thread_reference"}
    if ref.get("thread_url"):
        return {
            "created": False,
            "reason": "existing_thread_reference",
            "thread_id": ref.get("thread_id"),
            "thread_url": ref.get("thread_url"),
            "thread_reference": ref,
        }
    return {
        "created": False,
        "reason": "existing_thread_reference_without_url",
        "thread_id": ref.get("thread_id"),
        "thread_reference": ref,
    }


def start_workspace_worker_for_task(
    *,
    server: str,
    task_id: int,
    server_repo: str,
    runs_dir: str,
    worker_id: str,
    push: bool,
) -> dict[str, Any]:
    repo_path = Path(server_repo).resolve()
    log_dir = Path(os.getenv("GAME_COMPANY_DISCORD_WORKER_LOG_DIR", "logs/discord-workers")).resolve()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"task-{task_id}.log"
    argv = [
        sys.executable,
        "-m",
        "app.worker_supervisor",
        "--server",
        server,
        "--worker-id",
        worker_id,
        "--role",
        "code_worker",
        "--task-id",
        str(task_id),
        "--runs-dir",
        runs_dir,
        "--server-repo",
        str(repo_path),
    ]
    if push:
        argv.append("--push")

    flags = 0
    if os.name == "nt":
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    log_file = log_path.open("ab")
    try:
        process = subprocess.Popen(
            argv,
            cwd=repo_path,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            creationflags=flags,
            close_fds=False if os.name == "nt" else True,
        )
    except Exception:
        log_file.close()
        raise
    log_file.close()
    return {
        "started": True,
        "pid": process.pid,
        "task_id": task_id,
        "worker_id": worker_id,
        "log_path": str(log_path),
    }


async def run_owner_tool_call(message: Any, api: GameCompanyApiClient, tool_call: OwnerToolCall) -> dict[str, Any]:
    if tool_call.name != "create_coin_arena_bootstrap_task":
        return {
            "kind": "owner_tool_executed",
            "tool_name": tool_call.name,
            "created": False,
            "reason": "unknown_owner_tool",
        }

    task_result = await asyncio.to_thread(ensure_bootstrap_task, api)
    thread_result = await asyncio.to_thread(
        existing_bootstrap_thread_reference,
        api,
        task_result["task"]["id"],
    )
    if (
        task_result.get("created_task")
        or tool_call.recreate_thread
        or thread_result.get("reason") == "missing_thread_reference"
    ):
        thread_result = await create_task_thread_for_bootstrap(message, api, task_result)
    return {
        "kind": "owner_tool_executed",
        "tool_name": tool_call.name,
        "reason": tool_call.reason,
        **task_result,
        "thread": thread_result,
    }


def format_context_status(status: dict[str, Any] | None) -> str:
    if not status:
        return ""
    state = status.get("status", "unknown")
    estimated = status.get("estimated_tokens", "?")
    threshold = status.get("threshold_tokens", "?")
    if state == "compact_now":
        return f"Context: compact now ({estimated}/{threshold} estimated tokens)."
    if state == "warning":
        return f"Context: warning ({estimated}/{threshold} estimated tokens)."
    return f"Context: ok ({estimated}/{threshold} estimated tokens)."


def compact_owner_run_text(text: str, limit: int = 1800) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n\n[truncated]"


def compact_owner_run_error(stderr: str) -> str:
    lines = [line.strip() for line in stderr.splitlines() if line.strip()]
    meaningful = [
        line
        for line in lines
        if line.startswith("ERROR:")
        or "usage limit" in line.lower()
        or "timed out" in line.lower()
        or "not configured" in line.lower()
        or "invalid" in line.lower()
    ]
    selected = meaningful[-3:] if meaningful else lines[-5:]
    return compact_owner_run_text("\n".join(selected) or stderr)


def format_owner_run_result(result: dict[str, Any]) -> str:
    run_id = result.get("id", "?")
    status = result.get("status", "unknown")
    stdout = str(result.get("stdout") or "").strip()
    stderr = str(result.get("stderr") or "").strip()

    if stdout:
        return compact_owner_run_text(stdout)
    if status == "success":
        return f"Owner run completed: #{run_id}."
    if status == "dry_run":
        return f"Owner run stored: #{run_id} (dry_run)."
    if status == "blocked":
        reason = compact_owner_run_error(stderr) if stderr else "GAME_COMPANY_OWNER_COMMAND is not configured."
        return f"Owner run blocked: {reason}"
    if stderr:
        return f"Owner run #{run_id} {status}: {compact_owner_run_error(stderr)}"
    return f"Owner run #{run_id} {status}."


def format_gateway_reply(action: DiscordBotAction) -> str | None:
    if action.action_type == "unmapped_context":
        return None
    if action.action_type == "health_check":
        return "AI Game Company bot is online."
    if action.action_type == "context_status_check":
        return format_context_status(action.context_status) or "Context status is unavailable."
    if action.needs_approval:
        if not action.approval_result:
            return "Approval message received. Decision handling failed or was not executed."
        res_data = action.approval_result
        if "error" in res_data:
            err = res_data["error"]
            if err == "no_pending_approvals":
                return "현재 대기 중인 승인 요청이 없습니다."
            elif err == "ambiguous_decision":
                target = res_data["target"]
                req_summary = target.get("request_summary", "요청")
                return f"결재 요청 '{req_summary}'에 대한 승인 여부를 명확히 판단할 수 없습니다. '승인' 또는 '거절'을 포함하여 명확하게 답변해 주세요."
            else:
                return f"결재 처리 중 오류가 발생했습니다: {err}"
        if res_data.get("success"):
            res = res_data["result"]
            status = res.get("status", "unknown")
            req_summary = res.get("request_summary", "요청")
            status_kor = "승인" if status == "approved" else "거절(반려)"
            return f"결재 건 #{res.get('approval_id')} '{req_summary}'이(가) 성공적으로 {status_kor} 처리되었습니다."
    if action.needs_owner:
        operation_result = getattr(action, "operation_result", None)
        if (
            operation_result
            and operation_result.get("kind") == "owner_tool_executed"
            and operation_result.get("tool_name") == "create_coin_arena_bootstrap_task"
        ):
            result = operation_result
            task = result["task"]
            project = result["project"]
            thread = result.get("thread") or {}
            if thread.get("created") and thread.get("thread_url"):
                thread_line = f"스레드도 만들었어: {thread.get('thread_url')}"
            elif thread.get("thread_url"):
                thread_line = f"이미 연결된 스레드가 있어: {thread.get('thread_url')}"
            else:
                thread_line = f"스레드는 아직 못 만들었어: {thread.get('reason', 'unknown')}"
            if project_has_worker_config(project):
                config_line = "프로젝트 Git workspace 설정: 준비됨"
            else:
                config_line = "프로젝트 Git workspace 설정: 없음. repo_url/workspace_path를 설정해야 워커가 가져갈 수 있어."
            worker = result.get("worker")
            if not worker:
                worker_line = "워커 자동 시작: 꺼짐. 별도 Worker Runner를 켜야 작업을 가져가."
            elif worker.get("started"):
                worker_line = f"워커 자동 시작: 시작됨 (pid {worker.get('pid')}, log {worker.get('log_path')})"
            else:
                worker_line = f"워커 자동 시작: 건너뜀 ({worker.get('reason', 'unknown')})"
            return (
                "좋아, 말만 한 게 아니라 서버에 첫 작업을 실제로 만들었어.\n\n"
                f"프로젝트: {project['name']} (#{project['id']})\n"
                f"태스크: #{task['id']} {BOOTSTRAP_TASK_TITLE}\n"
                f"브랜치: {task['branch']}\n"
                f"{thread_line}\n"
                f"{config_line}\n"
                f"{worker_line}"
            )
        if action.owner_run_result:
            return format_owner_run_result(action.owner_run_result)
        if action.owner_run_payload:
            context_note = format_context_status(action.context_status)
            suffix = f" {context_note}" if context_note else ""
            return f"Owner run prepared as dry-run payload.{suffix}"
        return "Owner message routed."
    if action.action_type in {"ai_internal_observation", "artifact_observation", "test_runner_observation"}:
        return action.summary
    return None


async def send_discord_reply(channel: Any, reply: str, chunk_size: int = 1900) -> None:
    chunks = [reply[i : i + chunk_size] for i in range(0, len(reply), chunk_size)] or [reply]
    for chunk in chunks:
        await channel.send(chunk)


async def handle_discord_message(
    message: Any,
    api: GameCompanyApiClient,
    submit_owner_run: bool = False,
    execute_owner_run: bool = False,
    check_context_for_owner: bool = True,
    reply_unmapped: bool = False,
    auto_start_worker: bool = False,
    worker_server_repo: str | None = None,
    worker_runs_dir: str | None = None,
    worker_id: str = "codex-workspace-1",
    worker_push: bool = False,
) -> DiscordBotAction | None:
    if should_ignore_message(message):
        return None
    channel = getattr(message, "channel", None)
    typing = getattr(channel, "typing", None)

    async def process_message() -> DiscordBotAction:
        recent_messages = await collect_recent_discord_messages(message)
        context = discord_message_to_context(message, recent_messages=recent_messages)
        action = await asyncio.to_thread(
            handle_gateway_message,
            context,
            api,
            submit_owner_run,
            execute_owner_run,
            check_context_for_owner,
        )
        tool_call = detect_owner_tool_call(context, action)
        if tool_call:
            operation_result = await run_owner_tool_call(message, api, tool_call)
            if auto_start_worker:
                task = operation_result.get("task") or {}
                project = operation_result.get("project") or {}
                if not project_has_worker_config(project):
                    operation_result["worker"] = {
                        "started": False,
                        "reason": "project_missing_repo_url_or_workspace_path",
                    }
                else:
                    try:
                        operation_result["worker"] = await asyncio.to_thread(
                            start_workspace_worker_for_task,
                            server=api.server,
                            task_id=int(task["id"]),
                            server_repo=worker_server_repo or os.getcwd(),
                            runs_dir=worker_runs_dir or os.getenv("GAME_COMPANY_WORKSPACE_RUNS_DIR", "./runs"),
                            worker_id=worker_id,
                            push=worker_push,
                        )
                    except Exception as exc:
                        operation_result["worker"] = {
                            "started": False,
                            "reason": f"worker_start_failed: {exc}",
                        }
            action = replace(action, operation_result=operation_result)
        return action

    if callable(typing):
        typing_context = typing()
        try:
            await typing_context.__aenter__()
        except Exception as exc:
            print(f"Discord typing indicator failed: {exc}", flush=True)
            action = await process_message()
        else:
            try:
                action = await process_message()
            finally:
                await typing_context.__aexit__(None, None, None)
    else:
        action = await process_message()

    reply = format_gateway_reply(action)
    if reply is None and action.action_type == "unmapped_context" and reply_unmapped:
        reply = "This Discord channel/thread is not mapped yet."
    if reply:
        await send_discord_reply(message.channel, reply)
    return action


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Discord Gateway runtime.")
    parser.add_argument("--submit-owner-run", action="store_true", help="Store Owner-routed messages in /owner/runs.")
    parser.add_argument(
        "--execute-owner-run",
        action="store_true",
        help="Request dry_run=false for submitted Owner runs. Use only after Owner command setup.",
    )
    parser.add_argument(
        "--no-context-check-for-owner",
        action="store_true",
        help="Do not call context-status automatically for Owner-routed messages.",
    )
    parser.add_argument("--reply-unmapped", action="store_true", help="Reply when a Discord location is unmapped.")
    parser.add_argument(
        "--auto-start-worker",
        action="store_true",
        default=env_flag("GAME_COMPANY_DISCORD_AUTO_START_WORKER", False),
        help="Start one workspace worker process for a newly created Discord task thread.",
    )
    parser.add_argument(
        "--worker-server-repo",
        default=os.getenv("GAME_COMPANY_SERVER_REPO", os.getcwd()),
        help="Server repository path used as cwd for the spawned workspace worker.",
    )
    parser.add_argument(
        "--worker-runs-dir",
        default=os.getenv("GAME_COMPANY_WORKSPACE_RUNS_DIR", "./runs"),
        help="Runs directory passed to the spawned workspace worker.",
    )
    parser.add_argument(
        "--worker-id",
        default=os.getenv("GAME_COMPANY_WORKSPACE_SUPERVISOR_WORKER_ID", "codex-workspace-1"),
        help="Worker id used by the spawned workspace worker.",
    )
    parser.add_argument(
        "--worker-push",
        action="store_true",
        default=env_flag("GAME_COMPANY_WORKSPACE_PUSH", False),
        help="Push the worker branch after the spawned workspace worker commits.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    token = os.getenv("DISCORD_BOT_TOKEN", "")
    if not token:
        print("DISCORD_BOT_TOKEN is required.")
        return 2
    try:
        import discord
    except ImportError:
        print("discord.py is not installed. Run: python -m pip install -r requirements.txt")
        return 2

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)
    api = GameCompanyApiClient.from_env()

    @client.event
    async def on_ready() -> None:
        user = getattr(client, "user", None)
        print(f"Discord Gateway connected as {user}")

    @client.event
    async def on_message(message: Any) -> None:
        try:
            action = await handle_discord_message(
                message,
                api,
                submit_owner_run=args.submit_owner_run,
                execute_owner_run=args.execute_owner_run,
                check_context_for_owner=not args.no_context_check_for_owner,
                reply_unmapped=args.reply_unmapped,
                auto_start_worker=args.auto_start_worker,
                worker_server_repo=args.worker_server_repo,
                worker_runs_dir=args.worker_runs_dir,
                worker_id=args.worker_id,
                worker_push=args.worker_push,
            )
            if action:
                print(asdict(action), flush=True)
        except Exception as exc:
            print(f"Discord message handling failed: {exc}", flush=True)
            print(traceback.format_exc(), flush=True)
            try:
                await message.channel.send("Message handling failed. Check server logs.")
            except Exception:
                pass

    client.run(token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
