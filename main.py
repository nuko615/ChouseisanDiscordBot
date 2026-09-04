import argparse
import logging
import os
import sys
import tomllib
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


# ログ設定
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def load_config(path):
    """TOML設定ファイルを読み込み、最低限の内容を確認する。"""
    with Path(path).open("rb") as file:
        config = tomllib.load(file)

    required = [
        "timezone",
        "week_label_anchor",
        "deadline_days_before",
        "deadline_template",
        "discord_template",
        "chouseisan_base_url",
        "events",
    ]
    missing = [key for key in required if key not in config]
    if missing:
        raise ValueError(f"設定が不足しています: {', '.join(missing)}")

    # タイトルの月・第何週を、月曜日または日曜日のどちらで決めるか
    if config["week_label_anchor"] not in {"monday", "sunday"}:
        raise ValueError("week_label_anchor は monday または sunday を指定してください。")

    if not isinstance(config["events"], list) or not config["events"]:
        raise ValueError("[[events]] を1件以上設定してください。")

    event_ids = set()
    for event in config["events"]:
        for key in ["id", "title_template", "memo", "discord_message"]:
            if not event.get(key):
                raise ValueError(f"events の {key} が不足しています。")
        if event["id"] in event_ids:
            raise ValueError(f"イベントIDが重複しています: {event['id']}")
        event_ids.add(event["id"])

    # タイムゾーン名が有効か、実行前に確認する
    ZoneInfo(config["timezone"])
    return config


def get_event_info(config, now=None):
    """イベント名に使う週情報、候補日、締切メッセージを生成する。"""
    timezone = ZoneInfo(config["timezone"])
    if now is None:
        today = datetime.now(timezone)
    elif now.tzinfo is None:
        today = now.replace(tzinfo=timezone)
    else:
        today = now.astimezone(timezone)

    # 次の月曜日を取得する。当日が月曜日の場合は翌週の月曜日とする。
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    next_monday = today.date() + timedelta(days=days_until_monday)

    # オーナーごとの要望に合わせ、タイトルの月・週番号の基準日を選ぶ
    if config["week_label_anchor"] == "sunday":
        label_date = next_monday + timedelta(days=6)
    else:
        label_date = next_monday

    event_month = label_date.month
    week_of_month = ((label_date.day - 1) // 7) + 1

    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    candidates = []
    for index in range(7):
        candidate = next_monday + timedelta(days=index)
        candidates.append(f"{candidate:%m/%d}({weekdays[candidate.weekday()]})")

    limit_day = next_monday - timedelta(days=config["deadline_days_before"])
    deadline = config["deadline_template"].format(
        month=limit_day.month,
        day=limit_day.day,
        weekday=weekdays[limit_day.weekday()],
    )

    return {
        "month": event_month,
        "week": week_of_month,
        "next_monday": next_monday,
        "candidates": candidates,
        "deadline": deadline,
    }


def make_event_title(event, event_info):
    return event["title_template"].format(
        event_id=event["id"],
        month=event_info["month"],
        week=event_info["week"],
    )


def get_role_id(event, required=True):
    """設定された環境変数からDiscordロールIDを取得する。"""
    env_name = event.get("role_id_env")
    if not env_name:
        return None

    role_id = os.getenv(env_name)
    if not role_id and required:
        raise ValueError(f"環境変数 {env_name} が設定されていません。")
    if role_id and (not role_id.isdigit() or not 15 <= len(role_id) <= 25):
        raise ValueError(f"環境変数 {env_name} のロールIDが不正です。")
    return role_id


def create_event(driver, base_url, event_name, candidates, memo):
    """調整さんでイベントを作成し、完了ページからURLを取得する。"""
    wait = WebDriverWait(driver, 15)
    try:
        driver.get(base_url)

        # フォーム入力
        name_box = wait.until(EC.presence_of_element_located((By.ID, "name")))
        comment_box = driver.find_element(By.ID, "comment")
        candidate_box = driver.find_element(By.ID, "kouho")

        name_box.clear()
        name_box.send_keys(event_name)
        comment_box.clear()
        comment_box.send_keys(memo)
        candidate_box.clear()
        candidate_box.send_keys("\n".join(candidates))

        # 作成ボタンをクリック
        wait.until(EC.element_to_be_clickable((By.ID, "createBtn"))).click()

        # 完了ページへの遷移を待ち、リンクからURLを取得
        link = wait.until(EC.presence_of_element_located((By.ID, "listLink")))
        event_url = link.get_attribute("href")
    except Exception as error:
        raise RuntimeError("調整さんの画面操作に失敗しました。") from error

    parsed = urlparse(event_url or "")
    if parsed.scheme != "https" or parsed.hostname != "chouseisan.com":
        raise RuntimeError("調整さんのイベントURLを取得できませんでした。")
    return event_url


def make_discord_message(config, event, event_info, event_url, role_id):
    """設定ファイルのテンプレートからDiscord投稿文を組み立てる。"""
    mention = f"<@&{role_id}>" if role_id else ""
    return config["discord_template"].format(
        mention=mention,
        message=event["discord_message"],
        deadline=event_info["deadline"],
        url=event_url,
        event_id=event["id"],
        month=event_info["month"],
        week=event_info["week"],
    ).strip()


def post_to_discord(webhook_url, message, role_id=None):
    """Webhook URLをログへ出さずにDiscordへ投稿する。"""
    parsed = urlparse(webhook_url)
    if parsed.scheme != "https" or parsed.hostname not in {"discord.com", "discordapp.com"}:
        raise ValueError("DISCORD_WEBHOOK_URL が正しいDiscord URLではありません。")
    if not parsed.path.startswith("/api/webhooks/"):
        raise ValueError("DISCORD_WEBHOOK_URL の形式が不正です。")
    if len(message) > 2000:
        raise ValueError("Discord投稿文が2000文字を超えています。")

    # 意図しない @everyone 等を防ぎ、指定したロールだけをメンション可能にする
    allowed_mentions = {"parse": []}
    if role_id:
        allowed_mentions["roles"] = [role_id]

    try:
        response = requests.post(
            webhook_url,
            json={"content": message, "allowed_mentions": allowed_mentions},
            timeout=15,
        )
    except requests.RequestException:
        raise RuntimeError("Discordへの接続に失敗しました。") from None

    if not 200 <= response.status_code < 300:
        raise RuntimeError(f"Discord投稿に失敗しました。HTTP {response.status_code}")


def run(config_path="config.toml", dry_run=False, show_browser=False):
    load_dotenv()
    config = load_config(config_path)
    event_info = get_event_info(config)

    # dry-runでは外部サイトへアクセスせず、設定と生成結果だけを確認する
    if dry_run:
        logging.info("dry-run: 調整さんの作成とDiscord投稿は行いません。")
        logging.info("候補週の月曜日: %s", event_info["next_monday"])
        for event in config["events"]:
            logging.info("イベント: %s", make_event_title(event, event_info))
        return

    # 環境変数。Webhook URLはコードや設定ファイルに書かない。
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        raise ValueError("DISCORD_WEBHOOK_URL が設定されていません。")

    # イベント作成後に設定不足が判明しないよう、先に全ロールIDを確認する
    role_ids = {event["id"]: get_role_id(event) for event in config["events"]}

    options = Options()
    if not show_browser:
        options.add_argument("--headless=new")
    for argument in ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]:
        options.add_argument(argument)

    # Selenium ManagerがChromeに合うWebDriverを自動準備する
    with webdriver.Chrome(options=options) as driver:
        driver.set_page_load_timeout(30)

        # 設定されたイベントを順番に作成してDiscordへ送信する
        for event in config["events"]:
            event_name = make_event_title(event, event_info)
            logging.info("イベント作成開始: %s", event_name)

            event_url = create_event(
                driver,
                config["chouseisan_base_url"],
                event_name,
                event_info["candidates"],
                event["memo"],
            )
            message = make_discord_message(
                config,
                event,
                event_info,
                event_url,
                role_ids[event["id"]],
            )

            # Discord送信
            post_to_discord(webhook_url, message, role_ids[event["id"]])
            logging.info("投稿完了: %s", event["id"])


def main():
    parser = argparse.ArgumentParser(description="調整さんのイベントを作成してDiscordへ通知します。")
    parser.add_argument("--config", default="config.toml", help="TOML設定ファイル")
    parser.add_argument("--dry-run", action="store_true", help="外部へ作成・投稿せず確認する")
    parser.add_argument("--show-browser", action="store_true", help="Chromeを表示する")
    args = parser.parse_args()

    try:
        run(args.config, args.dry_run, args.show_browser)
    except (OSError, KeyError, TypeError, ValueError, RuntimeError, WebDriverException) as error:
        logging.error("%s", error)
        sys.exit(1)


if __name__ == "__main__":
    main()
