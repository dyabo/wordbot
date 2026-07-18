"""Per-user sheet links, one per user.

If the WORDBOT_TABLE environment variable is set (Lambda), links live in a
DynamoDB table with partition key `user_id` (string). Otherwise (laptop runs)
they are persisted to user_files.json next to this file.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

_TABLE_NAME = os.environ.get("WORDBOT_TABLE")
_STORE_PATH = Path(__file__).with_name("user_files.json")


def _table():
    import boto3  # available on Lambda; only imported when a table is configured

    return boto3.resource("dynamodb").Table(_TABLE_NAME)


def _read_local() -> dict[str, str]:
    if not _STORE_PATH.exists():
        return {}
    try:
        return json.loads(_STORE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def get_link(user_id: int) -> str | None:
    """Return the stored link for this user, or None."""
    if _TABLE_NAME:
        item = _table().get_item(Key={"user_id": str(user_id)}).get("Item")
        return item["link"] if item else None
    return _read_local().get(str(user_id))


def set_link(user_id: int, link: str) -> None:
    """Store (or replace) this user's link."""
    if _TABLE_NAME:
        _table().put_item(Item={"user_id": str(user_id), "link": link})
        return
    data = _read_local()
    data[str(user_id)] = link
    _STORE_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
