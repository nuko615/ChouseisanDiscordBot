from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from .chouseisan import ChouseisanClient
from .config import BotConfig, EventConfig, load_config
from .dates import WeekContext, build_week_context
from .discord import post_message, validate_role_id, validate_webhook_url

LOGGER = logging.getLogger(__name__)


def _title(event: EventConfig, week: WeekContext) -> str:
    return event.title_template.format(
        event_id=event.event_id,
        month=week.month,
        week=week.week,
    )


def _role_id(event: EventConfig, *, required: bool) -> str | None:
    if not event.role_id_env:
        return None
    role_id = os.getenv(event.role_id_env)
    if not role_id:
        if required:
            raise RuntimeError(f"required environment variable is not set: {event.role_id_env}")
        return None
    validate_role_id(role_id)
    return role_id


def _discord_content(
    config: BotConfig,
    event: EventConfig,
    week: WeekContext,
    event_url: str,
    role_id: str | None,
) -> str:
    mention = f"<@&{role_id}>" if role_id else ""
    return config.discord_template.format(
        deadline=week.deadline,
        event_id=event.event_id,
        mention=mention,
        message=event.discord_message,
        month=week.month,
        url=event_url,
        week=week.week,
    ).strip()


def run(config_path: str | Path, *, dry_run: bool = False, headless: bool = True) -> None:
    load_dotenv()
    config = load_config(config_path)
    week = build_week_context(config)

    if dry_run:
        LOGGER.info("Dry run: no Chouseisan event or Discord message will be created")
        LOGGER.info("Candidate week starts on %s", week.monday.isoformat())
        for event in config.events:
            role_id = _role_id(event, required=False)
            LOGGER.info(
                "event=%s title=%s role_configured=%s",
                event.event_id,
                _title(event, week),
                role_id is not None,
            )
        return

    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        raise RuntimeError("required environment variable is not set: DISCORD_WEBHOOK_URL")
    validate_webhook_url(webhook_url)

    roles = {event.event_id: _role_id(event, required=True) for event in config.events}
    with ChouseisanClient(
        config.chouseisan_base_url,
        headless=headless,
    ) as chouseisan:
        for event in config.events:
            LOGGER.info("Creating Chouseisan event: %s", event.event_id)
            event_url = chouseisan.create_event(
                _title(event, week),
                week.candidates,
                event.memo,
            )
            content = _discord_content(
                config,
                event,
                week,
                event_url,
                roles[event.event_id],
            )
            post_message(webhook_url, content, roles[event.event_id])
            LOGGER.info("Discord notification completed: %s", event.event_id)
