import json
import sqlite3
import time
from typing import Any, cast


class Cache:
    """SQLite for Phase 1. Swap for Postgres (same get/put) when you deploy to Render."""

    def __init__(self, path: str = "khoj.db", ttl: int = 6 * 3600):
        self.ttl = ttl
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS crawls (k TEXT PRIMARY KEY, ts REAL, payload TEXT)"
        )

    def get(self, key: str) -> tuple[list[dict[str, Any]], float] | None:
        row = self.db.execute("SELECT ts, payload FROM crawls WHERE k=?", (key,)).fetchone()
        return (cast(list[dict[str, Any]], json.loads(row[1])), float(row[0])) if row else None

    def put(self, key: str, records: list[dict[str, Any]]) -> None:
        self.db.execute(
            "REPLACE INTO crawls VALUES (?,?,?)", (key, time.time(), json.dumps(records))
        )
        self.db.commit()
