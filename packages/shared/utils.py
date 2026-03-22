from __future__ import annotations

from datetime import datetime


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value)
