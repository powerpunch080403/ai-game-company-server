import os
import httpx
from typing import Any
from app.config import load_settings

def create_discord_task_thread(
    *,
    channel_id: str,
    task_id: int,
    title: str,
    initial_message: str,
) -> dict[str, Any]:
    settings = load_settings()
    bot_token = settings.discord_bot_token or os.getenv("DISCORD_BOT_TOKEN", "")
    if not bot_token:
        raise ValueError("DISCORD_BOT_TOKEN is not configured")
    if not channel_id:
        raise ValueError("channel_id is required")

    headers = {
        "Authorization": f"Bot {bot_token}",
        "Content-Type": "application/json",
    }

    # 1. Create the thread
    # POST /channels/{channel_id}/threads
    create_url = f"https://discord.com/api/v10/channels/{channel_id}/threads"
    thread_name = f"Task-{task_id}: {title}"
    if len(thread_name) > 100:
        thread_name = thread_name[:97] + "..."

    thread_payload = {
        "name": thread_name,
        "auto_archive_duration": 1440,
        "type": 11,  # GUILD_PUBLIC_THREAD
    }

    with httpx.Client(timeout=15) as client:
        res = client.post(create_url, json=thread_payload, headers=headers)
        res.raise_for_status()
        thread_data = res.json()

        thread_id = thread_data["id"]
        guild_id = thread_data.get("guild_id", "@me")

        # 2. Post the initial message into the thread
        # POST /channels/{thread_id}/messages
        msg_url = f"https://discord.com/api/v10/channels/{thread_id}/messages"
        msg_payload = {
            "content": initial_message
        }
        msg_res = client.post(msg_url, json=msg_payload, headers=headers)
        msg_res.raise_for_status()

    thread_url = f"https://discord.com/channels/{guild_id}/{channel_id}/{thread_id}"

    return {
        "provider": "discord",
        "channel_id": channel_id,
        "thread_id": thread_id,
        "thread_url": thread_url,
        "title": title,
        "summary": initial_message[:200]
    }


def post_discord_thread_message(
    *,
    thread_id: str,
    message: str,
) -> dict[str, Any]:
    settings = load_settings()
    bot_token = settings.discord_bot_token or os.getenv("DISCORD_BOT_TOKEN", "")
    if not bot_token:
        raise ValueError("DISCORD_BOT_TOKEN is not configured")
    if not thread_id:
        raise ValueError("thread_id is required")

    headers = {
        "Authorization": f"Bot {bot_token}",
        "Content-Type": "application/json",
    }

    msg_url = f"https://discord.com/api/v10/channels/{thread_id}/messages"
    msg_payload = {
        "content": message
    }

    with httpx.Client(timeout=15) as client:
        res = client.post(msg_url, json=msg_payload, headers=headers)
        res.raise_for_status()
        msg_data = res.json()

    return {
        "provider": "discord",
        "thread_id": thread_id,
        "message_id": msg_data["id"],
        "message_url": f"https://discord.com/channels/{msg_data.get('guild_id', '@me')}/{thread_id}/{msg_data['id']}"
    }


def format_task_report_thread_message(
    *,
    task_id: int,
    title: str | None,
    status: str,
    summary: str | None,
    changed_files: list[str],
    merge_candidate_status: str | None = None,
    violation_reason: str | None = None,
) -> str:
    lines = []
    
    header = f"Task #{task_id}"
    if title:
        header += f" ({title})"
    header += f" report: {status}"
    lines.append(header)
    lines.append("")
    
    lines.append("Summary:")
    lines.append(summary if summary else "No summary provided.")
    lines.append("")
    
    lines.append("Changed files:")
    if changed_files:
        lines.extend(f"- {f}" for f in changed_files)
    else:
        lines.append("- None")
    lines.append("")
    
    lines.append("Merge candidate:")
    lines.append(merge_candidate_status if merge_candidate_status else "none")
    lines.append("")
    
    lines.append("Notes:")
    notes = []
    if violation_reason:
        notes.append(violation_reason)
    if not notes:
        notes.append("None")
    lines.extend(notes)
    
    return "\n".join(lines)
