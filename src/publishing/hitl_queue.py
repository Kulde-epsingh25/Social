"""Human-in-the-Loop review queue backed by SQLite."""

from __future__ import annotations

import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DB_PATH = Path("hitl_queue.db")


class HITLQueue:
    """Persists posts for human review and tracks approval/rejection decisions."""

    def __init__(self, db_path: Path = _DB_PATH) -> None:
        self._db = str(db_path)
        self._init_db()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_for_review(
        self, post_content: str, analysis: dict[str, Any]
    ) -> str:
        """Queue *post_content* for review.  Returns a unique ``review_id``."""
        review_id = str(uuid.uuid4())
        import json

        with sqlite3.connect(self._db) as conn:
            conn.execute(
                """
                INSERT INTO hitl_queue
                    (review_id, post_content, analysis_json, status, created_at)
                VALUES (?, ?, ?, 'pending', ?)
                """,
                (review_id, post_content, json.dumps(analysis), datetime.now(tz=timezone.utc).isoformat()),
            )
        logger.info("Queued post for HITL review: id=%s", review_id)
        return review_id

    def get_pending_reviews(self) -> list[dict[str, Any]]:
        """Return all posts awaiting human review."""
        import json

        with sqlite3.connect(self._db) as conn:
            rows = conn.execute(
                "SELECT review_id, post_content, analysis_json, created_at "
                "FROM hitl_queue WHERE status = 'pending' ORDER BY created_at"
            ).fetchall()
        return [
            {
                "review_id": r[0],
                "post_content": r[1],
                "analysis": json.loads(r[2]),
                "created_at": r[3],
            }
            for r in rows
        ]

    def approve(self, review_id: str) -> bool:
        """Mark *review_id* as approved.  Returns ``True`` on success."""
        return self._set_status(review_id, "approved")

    def reject(self, review_id: str, reason: str = "") -> bool:
        """Mark *review_id* as rejected with an optional *reason*."""
        import json

        with sqlite3.connect(self._db) as conn:
            conn.execute(
                "UPDATE hitl_queue SET status = 'rejected', rejection_reason = ? "
                "WHERE review_id = ?",
                (reason, review_id),
            )
        logger.info("Rejected review id=%s reason=%s", review_id, reason)
        return True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        with sqlite3.connect(self._db) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS hitl_queue (
                    review_id        TEXT PRIMARY KEY,
                    post_content     TEXT NOT NULL,
                    analysis_json    TEXT NOT NULL,
                    status           TEXT NOT NULL DEFAULT 'pending',
                    rejection_reason TEXT,
                    created_at       TEXT NOT NULL,
                    reviewed_at      TEXT
                )
                """
            )

    def _set_status(self, review_id: str, status: str) -> bool:
        with sqlite3.connect(self._db) as conn:
            conn.execute(
                "UPDATE hitl_queue SET status = ?, reviewed_at = ? WHERE review_id = ?",
                (status, datetime.now(tz=timezone.utc).isoformat(), review_id),
            )
        logger.info("Set review id=%s status=%s", review_id, status)
        return True
