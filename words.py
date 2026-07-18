"""Load words from the public Google Sheet, select randomly, and format for Telegram."""

from __future__ import annotations

import csv
import io
import random
from dataclasses import dataclass

import requests

# The sheet is exported as CSV. gid=0 is the first tab.
SHEET_ID = "1-1slGoemwSWA_7Av8lPtkYjRRmQ1UBnnYAkObd2OGL8"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"

# Characters that must be escaped in Telegram MarkdownV2.
_MDV2_SPECIAL = r"_*[]()~`>#+-=|{}.!"


@dataclass(frozen=True)
class Pair:
    """One vocabulary pair: a Polish word and its Russian translation."""

    pl: str
    ru: str


def load_pairs(timeout: int = 15) -> list[Pair]:
    """Fetch the sheet and return rows that have both a Polish word and a Russian translation."""
    resp = requests.get(CSV_URL, timeout=timeout)
    resp.raise_for_status()
    resp.encoding = "utf-8"

    reader = csv.reader(io.StringIO(resp.text))
    rows = list(reader)

    pairs: list[Pair] = []
    # Skip the header row (row 0: "Слово,Автоперевод,ru -> pl").
    for row in rows[1:]:
        if len(row) < 2:
            continue
        pl = row[0].strip()
        ru = row[1].strip()
        if pl and ru:
            pairs.append(Pair(pl=pl, ru=ru))
    return pairs


def pick(pairs: list[Pair], count: int) -> list[Pair]:
    """Pick `count` random pairs without repetition (capped at what's available)."""
    count = max(1, min(count, len(pairs)))
    return random.sample(pairs, count)


def _escape(text: str) -> str:
    """Escape text for Telegram MarkdownV2."""
    return "".join("\\" + ch if ch in _MDV2_SPECIAL else ch for ch in text)


def format_message(pairs: list[Pair], direction: str) -> str:
    """Build a MarkdownV2 message where the translation is a tap-to-reveal spoiler.

    direction "pl": show Polish, blur Russian.
    direction "ru": show Russian, blur Polish.
    """
    lines: list[str] = []
    for i, p in enumerate(pairs, 1):
        if direction == "ru":
            shown, hidden = p.ru, p.pl
        else:
            shown, hidden = p.pl, p.ru
        # Bold the prompt, spoiler (||...||) the answer.
        lines.append(f"{i}\\. *{_escape(shown)}*\n   ||{_escape(hidden)}||")
    return "\n\n".join(lines)
