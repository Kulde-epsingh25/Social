"""X (Twitter) API v2 publisher using tweepy."""

from __future__ import annotations

import logging
import textwrap
from typing import Any

logger = logging.getLogger(__name__)

try:
    import tweepy
    _TWEEPY_AVAILABLE = True
except ImportError:
    logger.warning("tweepy not installed – XPublisher in mock mode.")
    _TWEEPY_AVAILABLE = False

from src.config.settings import settings


class XPublisher:
    """Posts content to X using the Twitter API v2 via tweepy."""

    def __init__(self) -> None:
        self._client = self._init_client()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def post_tweet(self, content: str) -> dict[str, Any]:
        """Post a single tweet.  Splits to thread if *content* exceeds 280 chars."""
        parts = self.split_to_thread(content)
        if len(parts) == 1:
            return self._send_tweet(parts[0])
        results = self.post_thread(parts)
        return results[0] if results else {}

    def post_thread(self, contents: list[str]) -> list[dict[str, Any]]:
        """Post a series of replies forming a thread."""
        results: list[dict] = []
        reply_to: str | None = None
        for part in contents:
            result = self._send_tweet(part, reply_to=reply_to)
            results.append(result)
            reply_to = result.get("id")
        return results

    @staticmethod
    def split_to_thread(
        long_content: str, max_chars: int = 280
    ) -> list[str]:
        """Split *long_content* into tweet-sized chunks.

        Existing numbered thread markers (1/, 2/) are preserved.
        """
        # If content already contains thread markers, split on them.
        if "\n1/" in long_content or long_content.startswith("1/"):
            raw_parts = [
                p.strip()
                for p in long_content.split("\n")
                if p.strip()
            ]
            # Re-chunk in case individual parts are still too long.
            parts: list[str] = []
            for part in raw_parts:
                parts.extend(textwrap.wrap(part, width=max_chars))
            return parts or [long_content[:max_chars]]

        # Plain long content → wrap into max_chars chunks.
        words = long_content.split()
        chunks: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                current = word
        if current:
            chunks.append(current)
        # Number the parts if more than one.
        if len(chunks) > 1:
            total = len(chunks)
            chunks = [f"{i + 1}/{total} {c}" for i, c in enumerate(chunks)]
        return chunks or [long_content[:max_chars]]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _send_tweet(
        self, text: str, reply_to: str | None = None
    ) -> dict[str, Any]:
        if self._client is None:
            logger.info("[MOCK] Would post tweet: %.60s…", text)
            return {"id": "mock-id", "text": text, "mock": True}
        try:
            kwargs: dict[str, Any] = {"text": text}
            if reply_to:
                kwargs["in_reply_to_tweet_id"] = reply_to
            response = self._client.create_tweet(**kwargs)
            data = response.data or {}
            return {"id": data.get("id", ""), "text": data.get("text", text)}
        except Exception as exc:  # noqa: BLE001
            logger.error("Tweet post failed: %s", exc)
            return {"error": str(exc)}

    @staticmethod
    def _init_client():  # noqa: ANN
        if not _TWEEPY_AVAILABLE:
            return None
        if not all([
            settings.x_api_key,
            settings.x_api_secret,
            settings.x_access_token,
            settings.x_access_token_secret,
        ]):
            logger.warning("X API credentials not configured – running in mock mode.")
            return None
        try:
            return tweepy.Client(
                consumer_key=settings.x_api_key,
                consumer_secret=settings.x_api_secret,
                access_token=settings.x_access_token,
                access_token_secret=settings.x_access_token_secret,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("tweepy client init failed: %s", exc)
            return None
