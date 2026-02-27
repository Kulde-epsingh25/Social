"""Unit tests for publishing modules."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.publishing.x_publisher import XPublisher
from src.publishing.rate_limiter import RateLimiter
from src.publishing.hitl_queue import HITLQueue


class TestXPublisher:
    def setup_method(self):
        self.publisher = XPublisher()
        self.publisher._client = None  # force mock mode

    def test_post_tweet_returns_dict(self):
        result = self.publisher.post_tweet("Test tweet content.")
        assert isinstance(result, dict)

    def test_mock_post_has_id(self):
        result = self.publisher._send_tweet("Hello world!")
        assert "id" in result

    def test_split_to_thread_short_content(self):
        parts = XPublisher.split_to_thread("Short tweet.", max_chars=280)
        assert len(parts) == 1
        assert parts[0] == "Short tweet."

    def test_split_to_thread_long_content(self):
        long = "word " * 100  # ~500 chars
        parts = XPublisher.split_to_thread(long, max_chars=280)
        assert len(parts) >= 2
        for part in parts:
            assert len(part) <= 300  # allow numbering prefix

    def test_split_to_thread_existing_markers(self):
        content = "1/ First tweet\n2/ Second tweet\n3/ Third tweet"
        parts = XPublisher.split_to_thread(content)
        assert len(parts) >= 2

    def test_post_thread_returns_list(self):
        results = self.publisher.post_thread(["Tweet 1", "Tweet 2"])
        assert isinstance(results, list)
        assert len(results) == 2


class TestRateLimiter:
    def setup_method(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.limiter = RateLimiter(db_path=Path(self._tmp.name))

    def test_can_post_initially(self):
        assert self.limiter.can_post() is True

    def test_time_until_next_post_initially_zero(self):
        wait = self.limiter.time_until_next_post()
        assert wait == 0.0

    def test_record_post_does_not_crash(self):
        self.limiter.record_post()
        # Should still work without error

    def test_time_until_next_post_after_record(self):
        self.limiter.record_post()
        wait = self.limiter.time_until_next_post()
        # Should be close to interval in seconds
        assert wait > 0


class TestHITLQueue:
    def setup_method(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.queue = HITLQueue(db_path=Path(self._tmp.name))

    def test_add_for_review_returns_id(self):
        review_id = self.queue.add_for_review("Test post", {"key": "value"})
        assert isinstance(review_id, str)
        assert len(review_id) > 0

    def test_get_pending_reviews_returns_added(self):
        self.queue.add_for_review("Test post", {})
        pending = self.queue.get_pending_reviews()
        assert len(pending) >= 1
        assert "review_id" in pending[0]
        assert "post_content" in pending[0]

    def test_approve_sets_status(self):
        review_id = self.queue.add_for_review("Post to approve", {})
        result = self.queue.approve(review_id)
        assert result is True
        # Should no longer appear in pending
        pending_ids = [r["review_id"] for r in self.queue.get_pending_reviews()]
        assert review_id not in pending_ids

    def test_reject_removes_from_pending(self):
        review_id = self.queue.add_for_review("Post to reject", {})
        self.queue.reject(review_id, "Defamatory content detected.")
        pending_ids = [r["review_id"] for r in self.queue.get_pending_reviews()]
        assert review_id not in pending_ids

    def test_multiple_pending_reviews(self):
        for i in range(3):
            self.queue.add_for_review(f"Post {i}", {"index": i})
        pending = self.queue.get_pending_reviews()
        assert len(pending) >= 3
