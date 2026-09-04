# Chouseisan Discord Bot

[![CI](https://github.com/nuko615/ChouseisanDiscordBot/actions/workflows/ci.yml/badge.svg)](https://github.com/nuko615/ChouseisanDiscordBot/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

調整さんのイベントを自動作成し、そのURLをDiscord Webhookへ投稿するPythonスクリプトです。

イベント名、説明文、メンション先などは`config.toml`で変更できます。複数イベントを設定した場合は、1回の実行ですべて作成します。

## 主な機能

- 次の月曜日から日曜日までを候補日として自動生成
- 複数イベントの連続作成
- イベントごとのタイトル・説明文・Discord投稿文
- タイトルの月・週番号を月曜日基準または日曜日基準で計算
- Discord Webhookを環境変数／GitHub Actions Secretsで保護
- dry-runによる事前確認
- GitHub Actionsからの実行

奇数週・偶数週の分岐はありません。`config.toml`に定義したイベントを毎回作成するシンプルな構成です。

## ファイル構成

```text
ChouseisanDiscordBot/
├─ main.py
├─ config.toml
├─ requirements.txt
├─ tests/
│  └─ test_main.py
├─ .github/workflows/
│  ├─ ci.yml
│  └─ run.yml
├─ .env.example
└─ README.md
```

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

### 2. 仮想環境の作成とインストール

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### 3. Discord情報を設定

`.env.example`を`.env`へコピーします。

```dotenv
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
DISCORD_ROLE_ID=123456789012345678
```

`.env`はGit管理対象外です。実際のWebhook URLをPythonコードや`config.toml`へ書かないでください。

### 4. イベント内容を設定

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

複数イベントを作る場合は`[[events]]`を追加します。タイトルを月曜日基準にする場合は`week_label_anchor = "monday"`、日曜日基準なら`"sunday"`を指定します。

### 5. dry-run

最初に、外部へ作成・投稿しない状態で設定を確認します。

```bash
python main.py --dry-run
```

### 6. 実行

```bash
python main.py
```

Chromeを表示して確認する場合は`python main.py --show-browser`を実行します。

## GitHub Actionsで実行する

1. **Settings → Secrets and variables → Actions**を開く
2. Secret `DISCORD_WEBHOOK_URL`を登録
3. Variable `DISCORD_ROLE_ID`を登録
4. **Actions → Run bot → Run workflow**を開く
5. 最初は`dry_run: true`、確認後に`false`で実行

初期状態では誤投稿を避けるため、手動実行だけが有効です。定期実行する場合は`.github/workflows/run.yml`の`on`へ次を追加します。

```yaml
  schedule:
    - cron: "30 8 * * 4"
      timezone: "Asia/Tokyo"
```

これは毎週木曜日08:30の指定です。GitHub Actionsのscheduled workflowは遅延することがあり、Publicリポジトリでは60日間活動がないと自動停止します。

## テスト

```bash
python -m unittest discover -s tests -v
```

テストでは調整さんやDiscordへ接続しません。

## 注意点

- 調整さんの公式APIではなく、Web画面をSeleniumで操作しています。画面構造が変わると修正が必要です。
- 調整さん作成後にDiscord投稿が失敗すると、再実行でイベントが重複する可能性があります。
- Webhook URLを誤ってコミットした場合は、削除だけで済ませずDiscord側で失効・再発行してください。
- 利用前に対象サービスの最新の利用条件を確認してください。

## License

[MIT License](LICENSE)
