"""News ingestion via newsdata.io with salience scoring."""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Any

import requests

from src.config.settings import settings

logger = logging.getLogger(__name__)

# Keywords that raise the priority of a news event for Indian politics coverage.
_HIGH_PRIORITY_KEYWORDS = [
    "parliament",
    "lok sabha",
    "rajya sabha",
    "minister",
    "BJP",
    "Congress",
    "AAP",
    "TMC",
    "election commission",
    "supreme court",
    "FIR",
    "corruption",
    "arrested",
    "scam",
]


@dataclass
class NewsEvent:
    """Represents a single ingested news event."""

    id: str
    title: str
    content: str
    source: str
    published_at: str
    entities: list[str] = field(default_factory=list)
    sentiment: float = 0.0  # –1.0 (negative) … +1.0 (positive)
    engagement_velocity: float = 0.0  # shares/hour at time of ingestion


class NewsIngestionAgent:
    """Fetches and prioritises news events from newsdata.io."""

    _BASE_URL: str = settings.news_api_url

    def __init__(self) -> None:
        self._api_key = settings.news_api_key

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_events(
        self, query: str, max_results: int = 20
    ) -> list[NewsEvent]:
        """Fetch news events matching *query*.

        Falls back to mock data when the API key is not configured.
        """
        if not self._api_key:
            logger.warning("NEWS_API_KEY not set – returning mock events.")
            return self._mock_events(query, max_results)

        params = {
            "apikey": self._api_key,
            "q": query,
            "size": min(max_results, 10),  # newsdata.io free tier max is 10
            "language": "en",
        }
        try:
            resp = requests.get(
                f"{self._BASE_URL}/news",
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            return self._parse_response(resp.json())
        except requests.RequestException as exc:
            logger.error("newsdata.io request failed: %s", exc)
            return []

    def calculate_salience_score(self, event: NewsEvent) -> float:
        """Score 0–1 indicating how salient an event is for political accountability."""
        score = 0.0
        text = (event.title + " " + event.content).lower()
        for kw in _HIGH_PRIORITY_KEYWORDS:
            if kw.lower() in text:
                score += 0.05
        # Boost negative-sentiment stories (accountability focus).
        if event.sentiment < 0:
            score += abs(event.sentiment) * 0.2
        score += min(event.engagement_velocity / 1000.0, 0.3)
        return min(round(score, 4), 1.0)

    def filter_high_priority_events(
        self, events: list[NewsEvent]
    ) -> list[NewsEvent]:
        """Return only events whose salience score exceeds 0.15."""
        scored = [
            (e, self.calculate_salience_score(e)) for e in events
        ]
        return [e for e, s in scored if s >= 0.15]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_response(self, data: dict[str, Any]) -> list[NewsEvent]:
        # newsdata.io returns {"status": "success", "results": [...]}
        articles = data.get("results", [])
        events: list[NewsEvent] = []
        for art in articles:
            url = art.get("link", art.get("article_id", ""))
            eid = hashlib.md5(url.encode()).hexdigest()
            content = art.get("content") or art.get("description") or ""
            events.append(
                NewsEvent(
                    id=eid,
                    title=art.get("title", ""),
                    content=content,
                    source=art.get("source_id", "unknown"),
                    published_at=art.get("pubDate", ""),
                    entities=[k for k in (art.get("keywords") or []) if isinstance(k, str)],
                )
            )
        return events

    @staticmethod
    def _mock_events(query: str, max_results: int) -> list[NewsEvent]:
        """Return synthetic events for demo / testing."""
        template = [
            NewsEvent(
                id=hashlib.md5(f"{query}-{i}".encode()).hexdigest(),
                title=f"[DEMO] Political development #{i} related to '{query}'",
                content=(
                    f"A senior minister today made a statement regarding {query}. "
                    "Opposition parties demanded accountability and a CBI inquiry. "
                    "The Supreme Court has taken suo motu cognizance of the matter."
                ),
                source="Demo Source",
                published_at=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                entities=["India", "Parliament", "BJP", "Congress"],
                sentiment=-0.4,
                engagement_velocity=120.0,
            )
            for i in range(1, min(max_results, 3) + 1)
        ]
        return template
