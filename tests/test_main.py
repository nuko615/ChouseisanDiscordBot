import os
import unittest
from datetime import date, datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import main


def make_config(anchor="sunday"):
    return {
        "timezone": "Asia/Tokyo",
        "week_label_anchor": anchor,
        "deadline_days_before": 2,
        "deadline_template": "{month}/{day}({weekday})締切",
        "discord_template": "{mention}\n{message}\n{deadline}\n{url}",
        "chouseisan_base_url": "https://chouseisan.com",
        "events": [
            {
                "id": "main",
                "title_template": "{month}月第{week}週",
                "memo": "memo",
                "discord_message": "message",
                "role_id_env": "DISCORD_ROLE_ID",
            }
        ],
    }


class ScheduleBotTests(unittest.TestCase):
    def test_loads_example_config(self):
        config = main.load_config("config.toml")
        self.assertEqual(config["timezone"], "Asia/Tokyo")
        self.assertEqual(len(config["events"]), 1)

    def test_next_week_candidates(self):
        now = datetime(2026, 9, 24, 8, 30, tzinfo=ZoneInfo("Asia/Tokyo"))
        info = main.get_event_info(make_config(), now)

        self.assertEqual(info["next_monday"], date(2026, 9, 28))
        self.assertEqual(info["candidates"][0], "09/28(月)")
        self.assertEqual(info["candidates"][-1], "10/04(日)")
        self.assertEqual(info["deadline"], "9/26(土)締切")

    def test_title_anchor_can_follow_owner_preference(self):
        now = datetime(2026, 9, 24, 8, 30, tzinfo=ZoneInfo("Asia/Tokyo"))
        sunday = main.get_event_info(make_config("sunday"), now)
        monday = main.get_event_info(make_config("monday"), now)

        self.assertEqual((sunday["month"], sunday["week"]), (10, 1))
        self.assertEqual((monday["month"], monday["week"]), (9, 4))

    @patch.dict(os.environ, {"DISCORD_ROLE_ID": "123456789012345678"})
    def test_builds_discord_message(self):
        config = make_config()
        event = config["events"][0]
        info = main.get_event_info(
            config,
            datetime(2026, 9, 24, 8, 30, tzinfo=ZoneInfo("Asia/Tokyo")),
        )
        role_id = main.get_role_id(event)
        message = main.make_discord_message(config, event, info, "https://chouseisan.com/s?h=x", role_id)

        self.assertIn("<@&123456789012345678>", message)
        self.assertIn("9/26(土)締切", message)


if __name__ == "__main__":
    unittest.main()
