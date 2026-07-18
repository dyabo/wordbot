"""Telegram vocabulary bot.

Runs on your laptop via long polling. Message it:

    /addfile <link> -> register YOUR word sheet (Google Sheets or CSV link)
    /words 5        -> 5 random words, word shown, translation blurred
    /words 5 ru     -> 5 random words, translation shown, word blurred
    /words          -> defaults to 5 words

Each user registers their own sheet with /addfile; one link per user,
a new /addfile replaces the old one.

The bot token is read from the WORDBOT_TOKEN environment variable
(loaded from a local .env file if present).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

import storage
import words

DEFAULT_COUNT = 5
MAX_COUNT = 30

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO
)
log = logging.getLogger("wordbot")


def _load_env() -> None:
    """Minimal .env loader (KEY=VALUE lines) so we don't need an extra dependency."""
    env_path = Path(__file__).with_name(".env")
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


HELP_TEXT = (
    "Vocabulary practice bot.\n\n"
    "/addfile <link> — register your word sheet (Google Sheets link;\n"
    "    column A = word, column B = translation, row 1 = header)\n"
    "/words N        — N random words, word shown, translation blurred\n"
    "/words N ru     — N random words, translation shown, word blurred\n"
    "/words          — 5 words\n\n"
    "Tap the blurred text to reveal the answer."
)

NO_FILE_TEXT = (
    "You haven't registered a word sheet yet.\n"
    "Send /addfile <link> with your Google Sheets link "
    "(the sheet must be viewable by anyone with the link)."
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT)


async def addfile_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "Usage: /addfile <link>\nPaste your Google Sheets (or CSV) link."
        )
        return

    link = context.args[0]
    try:
        csv_url = words.to_csv_url(link)
    except ValueError as exc:
        await update.message.reply_text(str(exc))
        return

    # Validate before saving: fetch it and count usable rows.
    try:
        pairs = words.load_pairs(csv_url)
    except Exception as exc:
        log.exception("Failed to validate sheet")
        await update.message.reply_text(
            f"Couldn't read that link: {exc}\n"
            "Make sure the sheet is shared as 'anyone with the link can view'."
        )
        return

    if not pairs:
        await update.message.reply_text(
            "The file loaded, but no usable word pairs were found.\n"
            "Expected: column A = word, column B = translation, first row = header."
        )
        return

    storage.set_link(update.effective_user.id, csv_url)
    await update.message.reply_text(
        f"Saved! Found {len(pairs)} word pairs. Now try /words 5"
    )


async def words_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    count, direction = _parse_args(context.args)
    count = max(1, min(count, MAX_COUNT))

    csv_url = storage.get_link(update.effective_user.id)
    if not csv_url:
        await update.message.reply_text(NO_FILE_TEXT)
        return

    try:
        pairs = words.load_pairs(csv_url)
    except Exception as exc:  # network / sheet errors
        log.exception("Failed to load sheet")
        await update.message.reply_text(f"Couldn't load your word list: {exc}")
        return

    if not pairs:
        await update.message.reply_text("Your sheet has no usable word pairs.")
        return

    chosen = words.pick(pairs, count)
    # Send each pair as its own message so spoilers reveal one by one.
    for i, pair in enumerate(chosen, 1):
        text = words.format_pair(pair, direction, i)
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)


def _parse_args(args: list[str]) -> tuple[int, str]:
    """Parse `/words` arguments into (count, direction). Order-insensitive."""
    count = DEFAULT_COUNT
    direction = "pl"
    for arg in args:
        low = arg.lower()
        if low in ("pl", "ru"):
            direction = low
        elif arg.isdigit():
            count = int(arg)
    return count, direction


def main() -> None:
    _load_env()
    token = os.environ.get("WORDBOT_TOKEN")
    if not token:
        raise SystemExit(
            "WORDBOT_TOKEN is not set. Put it in wordbot/.env "
            "(see .env.example) or export it in your shell."
        )

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("addfile", addfile_cmd))
    app.add_handler(CommandHandler("words", words_cmd))

    log.info("Bot started. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
