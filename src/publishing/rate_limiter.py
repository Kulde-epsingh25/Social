"""Rate limiter for X API posts respecting daily and interval constraints."""

from __future__ import annotations

import logging
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

from src.config.settings import settings

logger = logging.getLogger(__name__)
_DB_PATH = Path("rate_limiter.db")


class RateLimiter:
    """Enforces MAX_POSTS_PER_DAY and POST_INTERVAL_MINUTES constraints."""

    def __init__(self, db_path: Path = _DB_PATH) -> None:
        self._db = str(db_path)
        self._max_per_day = settings.max_posts_per_day
        self._interval_secs = settings.post_interval_minutes * 60
        self._init_db()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def can_post(self) -> bool:
        """Return ``True`` if posting is permitted right now."""
        return self._daily_count() < self._max_per_day and self._interval_ok()

    def record_post(self) -> None:
        """Record that a post was just published."""
        with sqlite3.connect(self._db) as conn:
            conn.execute(
                "INSERT INTO post_log (posted_at) VALUES (?)",
                (datetime.now(tz=timezone.utc).isoformat(),),
            )

    def time_until_next_post(self) -> float:
        """Return seconds until posting is next permitted."""
        last = self._last_post_time()
        if last is None:
            return 0.0
        elapsed = time.time() - last
        remaining = self._interval_secs - elapsed
        return max(remaining, 0.0)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        with sqlite3.connect(self._db) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS post_log "
                "(id INTEGER PRIMARY KEY AUTOINCREMENT, posted_at TEXT NOT NULL)"
            )

    def _daily_count(self) -> int:
        today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        with sqlite3.connect(self._db) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM post_log WHERE posted_at LIKE ?",
                (f"{today}%",),
            ).fetchone()
        return row[0] if row else 0

    def _interval_ok(self) -> bool:
        last = self._last_post_time()
        if last is None:
            return True
        return time.time() - last >= self._interval_secs

    def _last_post_time(self) -> float | None:
        with sqlite3.connect(self._db) as conn:
            row = conn.execute(
                "SELECT posted_at FROM post_log ORDER BY id DESC LIMIT 1"
            ).fetchone()
        if not row:
            return None
        try:
            dt = datetime.fromisoformat(row[0])
            return dt.timestamp()
        except ValueError:
            return None
