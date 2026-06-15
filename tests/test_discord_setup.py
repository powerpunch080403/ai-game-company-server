from __future__ import annotations

from app.discord_setup import check_discord_setup, discord_invite_url, mask_secret


def test_mask_secret_keeps_only_edges() -> None:
    assert mask_secret("") == ""
    assert mask_secret("short") == "*****"
    assert mask_secret("abcdefghijklmnopqrstuvwxyz") == "abcd...wxyz"


def test_discord_invite_url_contains_application_and_permissions() -> None:
    url = discord_invite_url("12345", permissions=68608)

    assert "client_id=12345" in url
    assert "permissions=68608" in url
    assert "scope=bot" in url


def test_check_discord_setup_without_server_check() -> None:
    result = check_discord_setup(
        server="http://127.0.0.1:8080/",
        discord_bot_token="bot-token-value",
        application_id="12345",
        server_token="server-token-value",
        check_server=False,
    )

    assert result["server"] == "http://127.0.0.1:8080"
    assert result["ok"] is True
    assert result["invite_url"].startswith("https://discord.com/oauth2/authorize?")
    token_check = next(check for check in result["checks"] if check["name"] == "DISCORD_BOT_TOKEN")
    assert "bot-...alue" in token_check["detail"]
    assert any("Never paste" in note for note in result["notes"])


def test_check_discord_setup_missing_token_is_not_ok() -> None:
    result = check_discord_setup(
        server="http://127.0.0.1:8080",
        discord_bot_token="",
        application_id="",
        server_token="",
        check_server=False,
    )

    assert result["ok"] is False
    assert result["invite_url"] == ""
