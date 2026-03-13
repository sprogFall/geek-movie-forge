from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class JsonFileStore:
    """Simple JSON-file persistence for local development."""

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, namespace: str, data: dict) -> None:
        target = self._base_dir / f"{namespace}.json"
        tmp = target.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, default=str), encoding="utf-8")
        tmp.replace(target)

    def load(self, namespace: str) -> dict | None:
        target = self._base_dir / f"{namespace}.json"
        if not target.exists():
            return None
        try:
            return json.loads(target.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load %s: %s — starting fresh", target, exc)
            return None
