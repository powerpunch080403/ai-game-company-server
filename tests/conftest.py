"""Deterministic test environment isolation.

Application settings load `.env` at import time. These test defaults prevent
local credentials and node settings from changing test behavior.
"""

import os

for key in [
    "GAME_COMPANY_API_TOKEN",
    "GAME_COMPANY_OWNER_TOKEN",
    "GAME_COMPANY_WORKER_TOKEN",
    "GAME_COMPANY_READONLY_TOKEN",
    "GAME_COMPANY_ARTIFACT_TOKEN",
    "GAME_COMPANY_NODE_ID",
    "GAME_COMPANY_NODE_MODE",
    "DISCORD_BOT_TOKEN",
    "GAME_COMPANY_DISCORD_TASK_CHANNEL_ID",
]:
    os.environ[key] = ""

os.environ["GAME_COMPANY_ALLOW_UNSAFE_NO_AUTH"] = "1"
