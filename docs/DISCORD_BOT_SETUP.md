# Discord Bot Setup

This guide explains how to prepare the Discord bot without sharing account
credentials or bot tokens in chat.

## Safety Rule

Do not paste these into any chat:

- Discord account email.
- Discord account password.
- Discord bot token.
- Server API tokens.

Store tokens only in the local `.env` file or in the service manager
environment on the machine that runs the bot.

## Manual Discord Steps

1. Open the Discord Developer Portal.
2. Create an application.
3. Add a bot to the application.
4. Enable Message Content Intent for the bot.
5. Copy the bot token into local `.env` as `DISCORD_BOT_TOKEN`.
6. Copy the application id into local `.env` as `DISCORD_APPLICATION_ID`.
7. Invite the bot to your Discord server.
8. Give it permission to read messages and send messages in the mapped channels
   and threads.

## Local `.env`

```env
DISCORD_BOT_TOKEN=your-discord-bot-token
DISCORD_APPLICATION_ID=your-discord-application-id
GAME_COMPANY_DISCORD_SERVER_TOKEN=owner-or-admin-token-for-server-api
GAME_COMPANY_SERVER=http://127.0.0.1:8080
```

## Check Setup

Linux/macOS:

```bash
./scripts/check_discord_setup.sh
```

Windows PowerShell:

```powershell
.\scripts\check_discord_setup.ps1
```

The check command verifies:

- `discord.py` is installed.
- `DISCORD_BOT_TOKEN` is present.
- A server API token is present.
- `DISCORD_APPLICATION_ID` is present for invite URL generation.
- The FastAPI server responds to `/health`.

## Run Gateway

```bash
./scripts/run_discord_gateway.sh
```

Windows:

```powershell
.\scripts\run_discord_gateway.ps1
```

Safe Owner run storage:

```bash
./scripts/run_discord_gateway.sh --submit-owner-run
```

This stores Owner-routed messages as `dry_run=true`.

Only use this after Owner command setup:

```bash
./scripts/run_discord_gateway.sh --submit-owner-run --execute-owner-run
```

## Required Server Mapping

The bot only knows what to do after a Discord channel/thread is mapped:

```bash
curl -X POST http://localhost:8080/discord/mappings \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "discord_guild_id":"guild-1",
    "discord_channel_id":"channel-1",
    "discord_thread_id":"thread-owner-design",
    "project_id":1,
    "conversation_kind":"project",
    "thread_role":"owner-design",
    "created_by":"owner",
    "summary_memory_key":"project:1:thread:thread-owner-design:summary:current"
  }'
```

In a real Discord Gateway message:

- A normal channel maps to `discord_channel_id`.
- A thread maps to parent channel id as `discord_channel_id` and thread id as
  `discord_thread_id`.

## Current Limitations

- The Gateway runtime skeleton has local tests, but still needs real Discord
  server testing.
- Approval natural-language handling is not connected yet.
- Historical Discord thread fetching is not implemented.
- Automatic LLM summarization of raw Discord messages is not implemented.
