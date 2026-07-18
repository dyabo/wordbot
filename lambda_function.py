"""Telegram vocabulary bot.

Runs as an AWS Lambda function exposed via a Lambda Function URL, registered
with Telegram as a webhook (no API Gateway involved). Message it:

    /addfile <link> -> register YOUR word sheet (Google Sheets or CSV link)
    /words 5        -> 5 random words, word shown, translation blurred
    /words 5 ru     -> 5 random words, translation shown, word blurred
    /words          -> defaults to 5 words

Each user registers their own sheet with /addfile; one link per user,
a new /addfile replaces the old one.

The bot token is read from the WORDBOT_TOKEN environment variable. If
WORDBOT_WEBHOOK_SECRET is set, incoming requests must carry a matching
X-Telegram-Bot-Api-Secret-Token header (set the same value when calling
setWebhook's secret_token parameter).
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import subprocess
import sys
from typing import Any

subprocess.call(
    "pip install python-telegram-bot -t /tmp/ --no-cache-dir".split(),
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
sys.path.insert(1, "/tmp/")

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


def _build_app(token: str) -> Application:
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("addfile", addfile_cmd))
    app.add_handler(CommandHandler("words", words_cmd))
    return app


async def _process_update(token: str, payload: dict[str, Any]) -> None:
    app = _build_app(token)
    async with app:
        update = Update.de_json(payload, app.bot)
        await app.process_update(update)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Entry point for the Lambda Function URL Telegram calls on every update."""
    token = os.environ.get("WORDBOT_TOKEN")
    if not token:
        log.error("WORDBOT_TOKEN is not set")
        return {"statusCode": 500, "body": "Server misconfigured"}

    secret = os.environ.get("WORDBOT_WEBHOOK_SECRET")
    if secret:
        headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
        if headers.get("x-telegram-bot-api-secret-token") != secret:
            log.warning("Rejected webhook call with missing/invalid secret token")
            return {"statusCode": 403, "body": "Forbidden"}

    body = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        log.warning("Received non-JSON body")
        return {"statusCode": 400, "body": "Bad Request"}

    try:
        asyncio.run(_process_update(token, payload))
    except Exception:
        log.exception("Failed to process update")
        # Still return 200 so Telegram doesn't retry-storm a failing update.
        return {"statusCode": 200, "body": "OK"}

    return {"statusCode": 200, "body": "OK"}
