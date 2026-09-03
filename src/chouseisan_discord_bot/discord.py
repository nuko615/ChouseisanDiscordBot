from __future__ import annotations

from urllib.parse import urlparse

import requests


class DiscordWebhookError(RuntimeError):
    """Raised without including the secret webhook URL in its message."""


def validate_webhook_url(webhook_url: str) -> None:
    parsed = urlparse(webhook_url)
    allowed_hosts = {"discord.com", "discordapp.com"}
    if parsed.scheme != "https" or parsed.hostname not in allowed_hosts:
        raise DiscordWebhookError("DISCORD_WEBHOOK_URL is not a Discord HTTPS webhook URL")
    if not parsed.path.startswith("/api/webhooks/"):
        raise DiscordWebhookError("DISCORD_WEBHOOK_URL has an unexpected path")


def validate_role_id(role_id: str) -> None:
    if not role_id.isdigit() or not 15 <= len(role_id) <= 25:
        raise DiscordWebhookError("Discord role ID must contain 15 to 25 digits")


def post_message(webhook_url: str, content: str, role_id: str | None = None) -> None:
    validate_webhook_url(webhook_url)
    if len(content) > 2_000:
        raise DiscordWebhookError("Discord message exceeds 2,000 characters")

    allowed_mentions: dict[str, object] = {"parse": []}
    if role_id:
        validate_role_id(role_id)
        allowed_mentions["roles"] = [role_id]

    try:
        response = requests.post(
            webhook_url,
            json={"content": content, "allowed_mentions": allowed_mentions},
            timeout=15,
        )
    except requests.RequestException:
        raise DiscordWebhookError("Discord webhook request failed") from None

    if not 200 <= response.status_code < 300:
        raise DiscordWebhookError(f"Discord webhook returned HTTP {response.status_code}")
