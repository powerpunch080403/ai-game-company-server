from __future__ import annotations

import argparse
import asyncio
import os
from dataclasses import asdict, replace
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


def discord_message_to_context(message: Any) -> DiscordMessageContext:
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
    )


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


def format_owner_run_result(result: dict[str, Any]) -> str:
    run_id = result.get("id", "?")
    status = result.get("status", "unknown")
    stdout = str(result.get("stdout") or "").strip()
    stderr = str(result.get("stderr") or "").strip()

    if stdout:
        if len(stdout) > 1800:
            return stdout[:1800].rstrip() + "\n\n[truncated]"
        return stdout
    if status == "success":
        return f"Owner run completed: #{run_id}."
    if status == "dry_run":
        return f"Owner run stored: #{run_id} (dry_run)."
    if status == "blocked":
        return f"Owner run blocked: {stderr or 'GAME_COMPANY_OWNER_COMMAND is not configured.'}"
    if stderr:
        return f"Owner run #{run_id} {status}: {stderr}"
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


async def handle_discord_message(
    message: Any,
    api: GameCompanyApiClient,
    submit_owner_run: bool = False,
    execute_owner_run: bool = False,
    check_context_for_owner: bool = True,
    reply_unmapped: bool = False,
) -> DiscordBotAction | None:
    if should_ignore_message(message):
        return None
    context = discord_message_to_context(message)
    action = await asyncio.to_thread(
        handle_gateway_message,
        context,
        api,
        submit_owner_run,
        execute_owner_run,
        check_context_for_owner,
    )
    reply = format_gateway_reply(action)
    if reply is None and action.action_type == "unmapped_context" and reply_unmapped:
        reply = "This Discord channel/thread is not mapped yet."
    if reply:
        await message.channel.send(reply)
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
            )
            if action:
                print(asdict(action))
        except Exception as exc:
            print(f"Discord message handling failed: {exc}")
            try:
                await message.channel.send("Message handling failed. Check server logs.")
            except Exception:
                pass

    client.run(token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
