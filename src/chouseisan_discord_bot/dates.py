from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from .config import BotConfig

WEEKDAYS_JA = ("月", "火", "水", "木", "金", "土", "日")


@dataclass(frozen=True)
class WeekContext:
    monday: date
    label_date: date
    month: int
    week: int
    candidates: tuple[str, ...]
    deadline: str


def next_monday(reference: date) -> date:
    """Return the Monday strictly after the reference date."""
    days_ahead = (7 - reference.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return reference + timedelta(days=days_ahead)


def build_week_context(config: BotConfig, now: datetime | None = None) -> WeekContext:
    timezone = ZoneInfo(config.timezone)
    if now is None:
        local_now = datetime.now(timezone)
    elif now.tzinfo is None:
        local_now = now.replace(tzinfo=timezone)
    else:
        local_now = now.astimezone(timezone)

    monday = next_monday(local_now.date())
    label_date = monday if config.week_label_anchor == "monday" else monday + timedelta(days=6)
    month = label_date.month
    week = ((label_date.day - 1) // 7) + 1

    candidates = tuple(
        f"{candidate:%m/%d}({WEEKDAYS_JA[candidate.weekday()]})"
        for candidate in (monday + timedelta(days=offset) for offset in range(7))
    )

    deadline_date = monday - timedelta(days=config.deadline_days_before)
    deadline = config.deadline_template.format(
        month=deadline_date.month,
        day=deadline_date.day,
        weekday=WEEKDAYS_JA[deadline_date.weekday()],
    )

    return WeekContext(
        monday=monday,
        label_date=label_date,
        month=month,
        week=week,
        candidates=candidates,
        deadline=deadline,
    )
