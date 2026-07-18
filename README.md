# wordbot

A small Telegram bot that runs on your laptop, picks random Polish→Russian word
pairs from a Google Sheet, and sends them with the translation **blurred**
(Telegram spoiler — tap to reveal).

## Usage (in Telegram, once running)

| Command        | Result                                                        |
| -------------- | ------------------------------------------------------------- |
| `/words 5`     | 5 random words, **Polish shown**, Russian blurred             |
| `/words 5 ru`  | 5 random words, **Russian shown**, Polish blurred             |
| `/words`       | 5 words, Polish shown (default)                               |
| `/start`       | Help                                                          |

Count is capped at 30. Word source is the public sheet's first tab
(column A = Polish, column B = Russian). Rows missing either are skipped.

## One-time setup

1. **Get a bot token**: in Telegram, message [@BotFather](https://t.me/BotFather),
   send `/newbot`, follow the prompts, and copy the token it gives you.
2. **Save the token**:
   ```bash
   cp .env.example .env
   # then edit .env and paste your token after WORDBOT_TOKEN=
   ```
3. **Install** (already done if you ran the setup):
   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

## Run

```bash
.venv/bin/python bot.py
```

Leave it running in a terminal. Open a chat with your bot in Telegram and send
`/words 5`. Stop with `Ctrl+C`.
