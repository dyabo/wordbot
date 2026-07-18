"""Telegram vocabulary bot.

Runs on your laptop via long polling. Message it:

    /words 5        -> 5 random words, Polish shown, Russian blurred (tap to reveal)
    /words 5 ru     -> 5 random words, Russian shown, Polish blurred
    /words          -> defaults to 5 words, Polish shown

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
    "/words N        — N random words, Polish shown, Russian blurred\n"
    "/words N ru     — N random words, Russian shown, Polish blurred\n"
    "/words          — 5 words, Polish shown\n\n"
    "Tap the blurred text to reveal the translation."
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT)


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


async def words_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    count, direction = _parse_args(context.args)
    count = max(1, min(count, MAX_COUNT))

    try:
        pairs = words.load_pairs()
    except Exception as exc:  # network / sheet errors
        log.exception("Failed to load sheet")
        await update.message.reply_text(f"Couldn't load the word list: {exc}")
        return

    if not pairs:
        await update.message.reply_text("The sheet has no usable word pairs.")
        return

    chosen = words.pick(pairs, count)
    message = words.format_message(chosen, direction)
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN_V2)


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
    app.add_handler(CommandHandler("words", words_cmd))

    log.info("Bot started. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
