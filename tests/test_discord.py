import unittest

from chouseisan_discord_bot.discord import (
    DiscordWebhookError,
    validate_role_id,
    validate_webhook_url,
)


class DiscordValidationTests(unittest.TestCase):
    def test_accepts_discord_webhook(self) -> None:
        validate_webhook_url("https://discord.com/api/webhooks/123/token")

    def test_rejects_non_discord_host(self) -> None:
        with self.assertRaises(DiscordWebhookError):
            validate_webhook_url("https://example.com/api/webhooks/123/token")

    def test_validates_role_id(self) -> None:
        validate_role_id("123456789012345678")
        with self.assertRaises(DiscordWebhookError):
            validate_role_id("not-a-role")


if __name__ == "__main__":
    unittest.main()
