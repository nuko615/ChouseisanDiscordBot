# Chouseisan Discord Bot

[![CI](https://github.com/nuko615/ChouseisanDiscordBot/actions/workflows/ci.yml/badge.svg)](https://github.com/nuko615/ChouseisanDiscordBot/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

調整さんのイベントを自動作成し、そのURLをDiscord Webhookへ投稿するPython製の自動化ツールです。イベント名、説明文、メンション先、週の表示方法をTOMLで変更でき、1回の実行で複数イベントを作成できます。

## 特徴

- イベント固有の文面をコードから分離
- 複数イベントに対応
- `Asia/Tokyo`などのIANAタイムゾーンを明示
- Seleniumの明示的な待機処理を使用
- Discord Webhookを環境変数／GitHub Actions Secretsで保護
- ロールメンションを指定IDのみに制限
- dry-run、設定検証、単体テストを用意
- GitHub Actionsから手動実行可能

奇数週・偶数週のような用途固有の分岐は持ちません。`config.toml`に定義されたイベントを毎回すべて作成します。

## 処理の流れ

1. 次の月曜日から日曜日までを候補日として生成
2. 設定されたイベントを調整さん上に作成
3. 作成されたイベントURLを取得
4. 指定されたDiscord Webhookへ通知

調整さんの公式APIではなく、Web画面をSeleniumで操作しています。そのため、調整さん側のHTML構造が変更された場合はセレクターの修正が必要です。

## 必要なもの

- Python 3.11以上
- Google Chrome
- Discord Webhook URL
- ロールをメンションする場合はDiscordロールID

## 導入方法

### 1. クローン

```bash
git clone https://github.com/nuko615/ChouseisanDiscordBot.git
cd ChouseisanDiscordBot
```

### 2. 仮想環境とインストール

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Selenium Managerが使用中のChromeに合うdriverを自動的に準備します。

### 3. Discord情報の設定

`.env.example`を`.env`へコピーし、値を設定します。

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS / Linux:

```bash
cp .env.example .env
```

```dotenv
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
DISCORD_ROLE_ID=123456789012345678
```

`.env`はGit管理対象外です。Webhook URLを`config.toml`やPythonコードへ書かないでください。

### 4. イベント設定

`config.toml`を編集します。

```toml
timezone = "Asia/Tokyo"
week_label_anchor = "sunday"
deadline_days_before = 2
deadline_template = "{month}/{day}({weekday})の午前までに入力お願いします。"
discord_template = """
{mention}
{message}

{deadline}
{url}
"""
chouseisan_base_url = "https://chouseisan.com"

[[events]]
id = "main"
title_template = "{month}月第{week}週"
role_id_env = "DISCORD_ROLE_ID"
discord_message = "参加可能な日を入力してください。"
memo = """
参加できる日を選択してください。

〇：参加可能
△：調整可能
×：参加不可
"""
```

複数イベントを作成する場合は`[[events]]`を追加します。タイトルの月・週番号を月曜日基準にする場合は`week_label_anchor = "monday"`、日曜日基準なら`"sunday"`を指定します。

### 5. dry-run

最初に、外部へ何も作成・投稿しない検証を実行します。

```bash
chouseisan-discord-bot --config config.toml --dry-run
```

### 6. 実行

```bash
chouseisan-discord-bot --config config.toml
```

Chromeを表示して確認したい場合は`--show-browser`を追加します。

## GitHub Actionsで実行する

`.github/workflows/run.yml`は安全のため手動実行のみ、かつdry-runを初期値にしています。

1. リポジトリの **Settings → Secrets and variables → Actions** を開く
2. Secret `DISCORD_WEBHOOK_URL`を登録
3. Variable `DISCORD_ROLE_ID`を登録
4. **Actions → Run bot → Run workflow**を開く
5. 最初は`dry_run: true`、確認後に`false`で実行

定期実行する場合は`run.yml`の`on`へ次を追加します。

```yaml
  schedule:
    - cron: "30 8 * * 4"
      timezone: "Asia/Tokyo"
```

これは毎週木曜日08:30を指定します。ただしGitHub Actionsのscheduled workflowは負荷状況により遅延・欠落する可能性があり、Publicリポジトリでは60日間活動がないと自動停止します。厳密な実行時刻が必要な用途には向きません。

## 設定項目

| 項目 | 内容 |
|---|---|
| `timezone` | 日付計算に使用するIANAタイムゾーン |
| `week_label_anchor` | タイトルの月・週番号を`monday`または`sunday`のどちらで計算するか |
| `deadline_days_before` | 次の月曜日から何日前を締切とするか |
| `deadline_template` | 締切文。`{month}`、`{day}`、`{weekday}`を利用可能 |
| `discord_template` | Discord投稿全体のテンプレート |
| `events[].title_template` | イベント名。`{month}`、`{week}`、`{event_id}`を利用可能 |
| `events[].role_id_env` | ロールIDを読む環境変数名。メンション不要なら省略可能 |

## テスト

```bash
python -m unittest discover -s tests -v
```

テストでは外部サイトやDiscordへ接続しません。

## 運用上の注意

- Webhook URLをコミットした場合、削除コミットだけでは履歴から消えません。Discord側で直ちに失効・再発行してください。
- 調整さんイベントの作成後にDiscord投稿が失敗すると、再実行時にイベントが重複する可能性があります。
- scheduled workflowの時刻精度は保証されません。
- 利用前に、対象サービスの最新の利用条件を確認してください。

## License

[MIT License](LICENSE)
