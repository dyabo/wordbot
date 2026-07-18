"""Per-user sheet links, persisted as JSON next to the bot (one link per user)."""

from __future__ import annotations

import json
from pathlib import Path

_STORE_PATH = Path(__file__).with_name("user_files.json")


def _read() -> dict[str, str]:
    if not _STORE_PATH.exists():
        return {}
    try:
        return json.loads(_STORE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def get_link(user_id: int) -> str | None:
    """Return the stored link for this user, or None."""
    return _read().get(str(user_id))


def set_link(user_id: int, link: str) -> None:
    """Store (or replace) this user's link."""
    data = _read()
    data[str(user_id)] = link
    _STORE_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
