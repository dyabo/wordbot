"""Load word pairs from a user-provided sheet, select randomly, format for Telegram.

Expected sheet structure (first tab or the tab in the link's gid):
column A = source word, column B = translation, first row = header.
"""

from __future__ import annotations

import csv
import io
import random
import re
from dataclasses import dataclass

import requests

# Characters that must be escaped in Telegram MarkdownV2.
_MDV2_SPECIAL = r"_*[]()~`>#+-=|{}.!"

_SHEET_URL_RE = re.compile(
    r"docs\.google\.com/spreadsheets/d/(?P<id>[A-Za-z0-9_-]+)"
)
_GID_RE = re.compile(r"[#?&]gid=(?P<gid>\d+)")


@dataclass(frozen=True)
class Pair:
    """One vocabulary pair: a source word and its translation."""

    pl: str
    ru: str


def to_csv_url(link: str) -> str:
    """Turn a user-pasted link into a CSV download URL.

    Google Sheets links are converted to their CSV export URL (keeping the
    tab from a #gid=... fragment if present). Any other http(s) link is
    assumed to already point at a CSV file and is used as-is.
    """
    link = link.strip()
    if not link.lower().startswith(("http://", "https://")):
        raise ValueError("That doesn't look like a link (must start with http/https).")

    m = _SHEET_URL_RE.search(link)
    if m:
        gid_match = _GID_RE.search(link)
        gid = gid_match.group("gid") if gid_match else "0"
        return (
            f"https://docs.google.com/spreadsheets/d/{m.group('id')}"
            f"/export?format=csv&gid={gid}"
        )
    return link


def load_pairs(csv_url: str, timeout: int = 15) -> list[Pair]:
    """Fetch a CSV and return rows that have both a word and a translation."""
    resp = requests.get(csv_url, timeout=timeout)
    resp.raise_for_status()
    resp.encoding = "utf-8"

    reader = csv.reader(io.StringIO(resp.text))
    rows = list(reader)

    pairs: list[Pair] = []
    # Skip the header row.
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


def format_pair(pair: Pair, direction: str, index: int) -> str:
    """Format a single pair as a MarkdownV2 message with a tap-to-reveal spoiler.

    direction "pl": show the source word, blur the translation.
    direction "ru": show the translation, blur the source word.

    Each pair is sent as its own message so its spoiler reveals independently —
    Telegram reveals every spoiler in a message at once when any one is tapped.
    """
    if direction == "ru":
        shown, hidden = pair.ru, pair.pl
    else:
        shown, hidden = pair.pl, pair.ru
    # Bold the prompt, spoiler (||...||) the answer.
    return f"{index}\\. *{_escape(shown)}*\n||{_escape(hidden)}||"
