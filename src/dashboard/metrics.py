"""Metrics collection backed by SQLite."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)
_DB_PATH = Path("metrics.db")


class MetricsCollector:
    """Records pipeline events and exposes aggregate summaries."""

    def __init__(self, db_path: Path = _DB_PATH) -> None:
        self._db = str(db_path)
        self._init_db()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_event_processed(self, event: dict[str, Any]) -> None:
        """Record that a news event was processed."""
        self._insert("event_processed", event)

    def record_post_published(self, post_id: str) -> None:
        """Record a successful post publication."""
        self._insert("post_published", {"post_id": post_id})

    def record_compliance_check(self, result: dict[str, Any]) -> None:
        """Record the outcome of a compliance check."""
        self._insert("compliance_check", result)

    def get_framework_usage(self) -> dict[str, int]:
        """Return counts of philosophical framework usage from recorded events."""
        with sqlite3.connect(self._db) as conn:
            rows = conn.execute(
                "SELECT payload FROM metrics WHERE event_type = 'event_processed'"
            ).fetchall()
        counts: dict[str, int] = {}
        for row in rows:
            try:
                payload = json.loads(row[0])
                for fw in payload.get("philosophy_context", {}).get("frameworks", []):
                    counts[fw] = counts.get(fw, 0) + 1
            except (json.JSONDecodeError, TypeError):
                continue
        return counts

    def get_summary(self) -> dict[str, Any]:
        """Return aggregate counts for the dashboard."""
        with sqlite3.connect(self._db) as conn:
            rows = conn.execute(
                "SELECT event_type, COUNT(*) FROM metrics GROUP BY event_type"
            ).fetchall()
        event_counts = {r[0]: r[1] for r in rows}
        return {
            "events_processed": event_counts.get("event_processed", 0),
            "posts_published": event_counts.get("post_published", 0),
            "compliance_checks": event_counts.get("compliance_check", 0),
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        with sqlite3.connect(self._db) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS metrics (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    payload    TEXT NOT NULL,
                    recorded_at TEXT NOT NULL
                )
                """
            )

    def _insert(self, event_type: str, payload: dict) -> None:
        with sqlite3.connect(self._db) as conn:
            conn.execute(
                "INSERT INTO metrics (event_type, payload, recorded_at) VALUES (?, ?, ?)",
                (
                    event_type,
                    json.dumps(payload, default=str),
                    datetime.now(tz=timezone.utc).isoformat(),
                ),
            )
