from __future__ import annotations

import argparse
import logging

from .app import run
from .chouseisan import ChouseisanError
from .config import ConfigError
from .discord import DiscordWebhookError

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create configured Chouseisan events and notify Discord.",
    )
    parser.add_argument(
        "--config",
        default="config.toml",
        help="TOML configuration file (default: config.toml)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration and dates without creating or posting anything",
    )
    parser.add_argument(
        "--show-browser",
        action="store_true",
        help="Show Chrome while running (local debugging only)",
    )
    return parser


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = build_parser().parse_args()
    try:
        run(args.config, dry_run=args.dry_run, headless=not args.show_browser)
    except (ChouseisanError, ConfigError, DiscordWebhookError, RuntimeError) as error:
        LOGGER.error("%s", error)
        raise SystemExit(1) from None
