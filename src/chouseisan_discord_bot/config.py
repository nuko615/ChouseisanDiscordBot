from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from string import Formatter
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ENV_NAME_PATTERN = re.compile(r"^[A-Z_][A-Z0-9_]*$")
EVENT_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
SUPPORTED_TEMPLATE_FIELDS = {
    "deadline",
    "event_id",
    "mention",
    "message",
    "month",
    "url",
    "week",
}


class ConfigError(ValueError):
    """Raised when the TOML configuration is invalid."""


@dataclass(frozen=True)
class EventConfig:
    event_id: str
    title_template: str
    memo: str
    discord_message: str
    role_id_env: str | None = None


@dataclass(frozen=True)
class BotConfig:
    timezone: str
    week_label_anchor: str
    deadline_days_before: int
    deadline_template: str
    discord_template: str
    chouseisan_base_url: str
    events: tuple[EventConfig, ...]


def _required_string(data: dict[str, object], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{context}.{key} must be a non-empty string")
    return value


def _validate_template(template: str, allowed_fields: set[str], context: str) -> set[str]:
    try:
        parsed_fields = tuple(Formatter().parse(template))
    except ValueError as error:
        raise ConfigError(f"{context} has invalid braces: {error}") from error

    fields: set[str] = set()
    for _, field_name, format_spec, conversion in parsed_fields:
        if field_name is None:
            continue
        if (
            not field_name
            or not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", field_name)
            or format_spec
            or conversion
        ):
            raise ConfigError(f"{context} only supports simple named fields")
        fields.add(field_name)

    unknown = fields - allowed_fields
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ConfigError(f"{context} contains unsupported fields: {names}")
    return fields


def load_config(path: str | Path) -> BotConfig:
    config_path = Path(path)
    try:
        with config_path.open("rb") as file:
            raw = tomllib.load(file)
    except FileNotFoundError as error:
        raise ConfigError(f"configuration file not found: {config_path}") from error
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"invalid TOML in {config_path}: {error}") from error

    timezone = _required_string(raw, "timezone", "config")
    try:
        ZoneInfo(timezone)
    except ZoneInfoNotFoundError as error:
        raise ConfigError(f"unknown timezone: {timezone}") from error

    anchor = _required_string(raw, "week_label_anchor", "config").lower()
    if anchor not in {"monday", "sunday"}:
        raise ConfigError("config.week_label_anchor must be 'monday' or 'sunday'")

    deadline_days_before = raw.get("deadline_days_before")
    if not isinstance(deadline_days_before, int) or not 0 <= deadline_days_before <= 30:
        raise ConfigError("config.deadline_days_before must be an integer from 0 to 30")

    deadline_template = _required_string(raw, "deadline_template", "config")
    _validate_template(
        deadline_template,
        {"day", "month", "weekday"},
        "config.deadline_template",
    )

    discord_template = _required_string(raw, "discord_template", "config")
    discord_fields = _validate_template(
        discord_template,
        SUPPORTED_TEMPLATE_FIELDS,
        "config.discord_template",
    )
    for required_field in ("message", "url"):
        if required_field not in discord_fields:
            raise ConfigError(f"config.discord_template must include {{{required_field}}}")

    base_url = _required_string(raw, "chouseisan_base_url", "config").rstrip("/")
    parsed_url = urlparse(base_url)
    if parsed_url.scheme != "https" or parsed_url.hostname != "chouseisan.com":
        raise ConfigError("config.chouseisan_base_url must be https://chouseisan.com")

    raw_events = raw.get("events")
    if not isinstance(raw_events, list) or not raw_events:
        raise ConfigError("config must define at least one [[events]] entry")

    events: list[EventConfig] = []
    event_ids: set[str] = set()
    for index, raw_event in enumerate(raw_events):
        context = f"events[{index}]"
        if not isinstance(raw_event, dict):
            raise ConfigError(f"{context} must be a table")

        event_id = _required_string(raw_event, "id", context)
        if not EVENT_ID_PATTERN.fullmatch(event_id):
            raise ConfigError(f"{context}.id must use lowercase letters, numbers, '-' or '_'")
        if event_id in event_ids:
            raise ConfigError(f"duplicate event id: {event_id}")
        event_ids.add(event_id)

        title_template = _required_string(raw_event, "title_template", context)
        _validate_template(
            title_template, {"event_id", "month", "week"}, f"{context}.title_template"
        )

        role_id_env = raw_event.get("role_id_env")
        if role_id_env is not None and (
            not isinstance(role_id_env, str) or not ENV_NAME_PATTERN.fullmatch(role_id_env)
        ):
            raise ConfigError(
                f"{context}.role_id_env must be an uppercase environment variable name"
            )

        events.append(
            EventConfig(
                event_id=event_id,
                title_template=title_template,
                memo=_required_string(raw_event, "memo", context),
                discord_message=_required_string(raw_event, "discord_message", context),
                role_id_env=role_id_env,
            )
        )

    return BotConfig(
        timezone=timezone,
        week_label_anchor=anchor,
        deadline_days_before=deadline_days_before,
        deadline_template=deadline_template,
        discord_template=discord_template,
        chouseisan_base_url=base_url,
        events=tuple(events),
    )
