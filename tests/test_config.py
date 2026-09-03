import tempfile
import textwrap
import unittest
from pathlib import Path

from chouseisan_discord_bot.config import ConfigError, load_config

VALID_CONFIG = """
timezone = "Asia/Tokyo"
week_label_anchor = "sunday"
deadline_days_before = 2
deadline_template = "{month}/{day}({weekday})"
discord_template = "{message}\\n{url}"
chouseisan_base_url = "https://chouseisan.com"

[[events]]
id = "main"
title_template = "{month}月第{week}週"
memo = "memo"
discord_message = "message"
role_id_env = "DISCORD_ROLE_ID"
"""


class ConfigTests(unittest.TestCase):
    def write_config(self, content: str) -> Path:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".toml", delete=False, encoding="utf-8"
        ) as temporary:
            temporary.write(textwrap.dedent(content))
        self.addCleanup(Path(temporary.name).unlink, missing_ok=True)
        return Path(temporary.name)

    def test_loads_valid_config(self) -> None:
        config = load_config(self.write_config(VALID_CONFIG))
        self.assertEqual(config.timezone, "Asia/Tokyo")
        self.assertEqual(config.events[0].event_id, "main")

    def test_rejects_duplicate_event_ids(self) -> None:
        duplicate = (
            VALID_CONFIG
            + """
        [[events]]
        id = "main"
        title_template = "duplicate"
        memo = "memo"
        discord_message = "message"
        """
        )
        with self.assertRaisesRegex(ConfigError, "duplicate event id"):
            load_config(self.write_config(duplicate))

    def test_rejects_unknown_template_field(self) -> None:
        invalid = VALID_CONFIG.replace("{message}", "{unknown}")
        with self.assertRaisesRegex(ConfigError, "unsupported fields"):
            load_config(self.write_config(invalid))

    def test_rejects_compound_template_field(self) -> None:
        invalid = VALID_CONFIG.replace("{message}", "{message.__class__}")
        with self.assertRaisesRegex(ConfigError, "simple named fields"):
            load_config(self.write_config(invalid))


if __name__ == "__main__":
    unittest.main()
