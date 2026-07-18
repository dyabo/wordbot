# wordbot

A small Telegram bot that runs on your laptop, picks random word pairs from
**your** Google Sheet, and sends them with the translation **blurred**
(Telegram spoiler — tap to reveal). Each word arrives as its own message,
so translations reveal one by one.

## Usage (in Telegram, once running)

| Command           | Result                                                     |
| ----------------- | ---------------------------------------------------------- |
| `/addfile <link>` | Register your word sheet (one per user; replaces the old)  |
| `/words 5`        | 5 random words, **word shown**, translation blurred        |
| `/words 5 ru`     | 5 random words, **translation shown**, word blurred        |
| `/words`          | 5 words (default)                                          |
| `/start`          | Help                                                       |

Count is capped at 30.

### Sheet format

Any Google Sheet (shared as *"anyone with the link can view"*) or direct CSV
link with this structure:

- **Column A** — word
- **Column B** — translation
- **Row 1** — header (skipped)

Rows missing either column are skipped. If the Sheets link has `#gid=...`,
that tab is used; otherwise the first tab.

## One-time setup

1. **Get a bot token**: in Telegram, message [@BotFather](https://t.me/BotFather),
   send `/newbot`, follow the prompts, and copy the token it gives you.
2. **Save the token**:
   ```bash
   cp .env.example .env
   # then edit .env and paste your token after WORDBOT_TOKEN=
   ```
3. **Install**:
   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

## Run

```bash
.venv/bin/python bot.py
```

Leave it running in a terminal. Open a chat with your bot in Telegram, send
`/addfile <your sheet link>` once, then `/words 5` whenever you want to
practice. Stop with `Ctrl+C`.

User links are stored in `user_files.json` next to the bot (not committed).
