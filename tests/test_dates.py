import unittest
from datetime import date, datetime
from zoneinfo import ZoneInfo

from chouseisan_discord_bot.config import BotConfig
from chouseisan_discord_bot.dates import build_week_context, next_monday


def make_config(anchor: str) -> BotConfig:
    return BotConfig(
        timezone="Asia/Tokyo",
        week_label_anchor=anchor,
        deadline_days_before=2,
        deadline_template="{month}/{day}({weekday})締切",
        discord_template="{message}\n{url}",
        chouseisan_base_url="https://chouseisan.com",
        events=(),
    )


class DateTests(unittest.TestCase):
    def test_next_monday_is_strict_when_reference_is_monday(self) -> None:
        reference = date(2026, 9, 7)
        self.assertEqual(next_monday(reference), date(2026, 9, 14))

    def test_sunday_anchor_handles_month_boundary(self) -> None:
        now = datetime(2026, 9, 24, 8, 30, tzinfo=ZoneInfo("Asia/Tokyo"))
        context = build_week_context(make_config("sunday"), now)
        self.assertEqual(context.monday, date(2026, 9, 28))
        self.assertEqual((context.month, context.week), (10, 1))
        self.assertEqual(context.candidates[0], "09/28(月)")
        self.assertEqual(context.candidates[-1], "10/04(日)")
        self.assertEqual(context.deadline, "9/26(土)締切")

    def test_monday_anchor_preserves_owner_specific_title_rule(self) -> None:
        now = datetime(2026, 9, 24, 8, 30, tzinfo=ZoneInfo("Asia/Tokyo"))
        context = build_week_context(make_config("monday"), now)
        self.assertEqual((context.month, context.week), (9, 4))


if __name__ == "__main__":
    unittest.main()
