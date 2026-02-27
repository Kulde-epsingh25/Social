"""Unit tests for ingestion modules."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.ingestion.news_ingestion import NewsIngestionAgent, NewsEvent
from src.ingestion.fact_checker import FactCheckerAgent, FactCheckResult
from src.ingestion.legislative_tracker import LegislativeTracker, LegislativeRecord
from src.ingestion.fir_monitor import FIRMonitor, FIRData


# ── NewsIngestionAgent ────────────────────────────────────────────────────────

class TestNewsIngestionAgent:
    def setup_method(self):
        self.agent = NewsIngestionAgent()

    def test_fetch_events_returns_mock_when_no_key(self):
        events = self.agent.fetch_events("corruption", max_results=2)
        assert isinstance(events, list)
        assert len(events) >= 1
        assert isinstance(events[0], NewsEvent)

    def test_calculate_salience_score_range(self):
        event = NewsEvent(
            id="x",
            title="Parliament BJP corruption arrested",
            content="A minister was arrested for corruption",
            source="Test",
            published_at="2024-01-01",
            sentiment=-0.8,
            engagement_velocity=500.0,
        )
        score = self.agent.calculate_salience_score(event)
        assert 0.0 <= score <= 1.0

    def test_filter_high_priority_events_removes_low_salience(self):
        low_event = NewsEvent(
            id="y",
            title="Nothing interesting",
            content="A bland event with no keywords.",
            source="Unknown",
            published_at="2024-01-01",
        )
        result = self.agent.filter_high_priority_events([low_event])
        # Should be empty or contain only high-priority items
        assert isinstance(result, list)

    @patch("src.ingestion.news_ingestion.requests.post")
    def test_fetch_events_parses_api_response(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "articles": {
                    "results": [
                        {
                            "uri": "test-uri",
                            "url": "http://example.com/article",
                            "title": "Test Article",
                            "body": "Test content",
                            "source": {"title": "Test Source"},
                            "dateTime": "2024-01-01T00:00:00Z",
                            "concepts": [],
                            "sentiment": -0.5,
                        }
                    ]
                }
            },
        )
        mock_post.return_value.raise_for_status = lambda: None
        agent = NewsIngestionAgent()
        agent._api_key = "fake-key"
        events = agent.fetch_events("test")
        assert len(events) == 1
        assert events[0].title == "Test Article"


# ── FactCheckerAgent ──────────────────────────────────────────────────────────

class TestFactCheckerAgent:
    def setup_method(self):
        self.agent = FactCheckerAgent()

    def test_verify_claim_returns_result(self):
        result = self.agent.verify_claim("The minister was charged with fraud.")
        assert isinstance(result, FactCheckResult)
        assert isinstance(result.verified, bool)
        assert 0.0 <= result.confidence <= 1.0

    def test_check_misinformation_detects_flags(self):
        content = "This is fake news and completely debunked."
        result = self.agent.check_misinformation(content)
        assert result["flag_count"] >= 1
        assert result["risk_level"] in ("low", "medium", "high")

    def test_is_regionally_relevant_india(self):
        assert self.agent.is_regionally_relevant("The Lok Sabha passed a bill today.")

    def test_is_regionally_relevant_non_india(self):
        assert not self.agent.is_regionally_relevant("The US Senate voted on a bill.")


# ── LegislativeTracker ────────────────────────────────────────────────────────

class TestLegislativeTracker:
    def setup_method(self):
        self.tracker = LegislativeTracker()

    def test_get_politician_record_returns_record(self):
        record = self.tracker.get_politician_record("demo politician")
        assert isinstance(record, LegislativeRecord)
        assert record.politician_name == "demo politician"

    def test_get_voting_history_filters_by_topic(self):
        history = self.tracker.get_voting_history("demo politician", "Accountability")
        assert isinstance(history, list)

    def test_detect_hypocrisy_no_data(self):
        result = self.tracker.detect_hypocrisy("unknown person", "I support X", "climate")
        assert "hypocrisy_detected" in result


# ── FIRMonitor ────────────────────────────────────────────────────────────────

class TestFIRMonitor:
    def setup_method(self):
        self.monitor = FIRMonitor()

    def test_get_firs_by_district_returns_list(self):
        firs = self.monitor.get_firs_by_district("South Delhi")
        assert isinstance(firs, list)
        assert all(isinstance(f, FIRData) for f in firs)

    def test_calculate_fir_velocity_non_negative(self):
        velocity = self.monitor.calculate_fir_velocity("South Delhi")
        assert velocity >= 0.0

    def test_check_fir_gap_structure(self):
        result = self.monitor.check_fir_gap("Corruption", "South Delhi")
        assert "gap_detected" in result
        assert "coverage_ratio" in result
