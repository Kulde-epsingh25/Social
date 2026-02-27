"""Unit tests for CrewAI agents (mock mode)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.agents.philosopher_agent import PhilosopherAgent
from src.agents.political_scientist_agent import PoliticalScientistAgent
from src.agents.fact_checker_agent import FactCheckerCrewAgent
from src.agents.post_writer_agent import PostWriterAgent
from src.orchestration.crew_orchestrator import AccountabilityCrew

_SAMPLE_EVENT = {
    "id": "test-123",
    "title": "Minister accused of diverting public funds",
    "content": "The Union Minister was today accused by opposition MPs of diverting ₹500 crore.",
    "source": "Demo News",
    "published_at": "2024-01-01T12:00:00Z",
    "actor": "Union Minister",
    "action": "diverting public funds",
    "target": "public exchequer",
}


class TestPhilosopherAgent:
    def setup_method(self):
        self.agent = PhilosopherAgent()
        self.agent._agent = None  # force mock mode

    def test_analyse_returns_string(self):
        result = self.agent.analyse(_SAMPLE_EVENT)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_mock_analysis_contains_frameworks(self):
        result = self.agent._mock_analysis(_SAMPLE_EVENT)
        for keyword in ("Kantian", "Utilitarian", "Lockean", "Rawlsian", "Machiavellian"):
            assert keyword in result


class TestPoliticalScientistAgent:
    def setup_method(self):
        self.agent = PoliticalScientistAgent()
        self.agent._agent = None

    def test_analyse_returns_string(self):
        result = self.agent.analyse(_SAMPLE_EVENT)
        assert isinstance(result, str)

    def test_analyse_with_record(self):
        record = {"criminal_background": {"cases": 2, "pending_trial": 1}}
        result = self.agent.analyse(_SAMPLE_EVENT, record)
        assert "2" in result


class TestFactCheckerCrewAgent:
    def setup_method(self):
        self.agent = FactCheckerCrewAgent()
        self.agent._agent = None

    def test_verify_returns_string(self):
        result = self.agent.verify("The minister accepted ₹500 crore.", _SAMPLE_EVENT)
        assert isinstance(result, str)

    def test_mock_result_contains_citation_notes(self):
        result = self.agent._mock_verify("Some analysis.", _SAMPLE_EVENT)
        assert "CITATION" in result or "VERIFIED" in result or "UNVERIFIED" in result


class TestPostWriterAgent:
    def setup_method(self):
        self.agent = PostWriterAgent()
        self.agent._agent = None

    def test_write_post_returns_string(self):
        result = self.agent.write_post(
            philosophical_critique="Kant condemns this.",
            fact_check_result="Verified.",
            political_analysis="Power abuse detected.",
            event=_SAMPLE_EVENT,
        )
        assert isinstance(result, str)

    def test_sanitise_removes_banned_phrases(self):
        text = "It's worth noting that delve into the issue."
        cleaned = PostWriterAgent._sanitise(text)
        assert "it's worth noting" not in cleaned.lower()
        assert "delve into" not in cleaned.lower()

    def test_mock_post_under_char_limit_per_tweet(self):
        post = self.agent._mock_post(_SAMPLE_EVENT)
        # Thread tweets should each be ≤280 chars
        from src.publishing.x_publisher import XPublisher
        parts = XPublisher.split_to_thread(post)
        for part in parts:
            assert len(part) <= 300  # allow slight buffer for numbered prefix


class TestAccountabilityCrew:
    def setup_method(self):
        self.crew = AccountabilityCrew()
        # Force mock mode for all sub-agents
        self.crew._philosopher._agent = None
        self.crew._pol_scientist._agent = None
        self.crew._fact_checker._agent = None
        self.crew._post_writer._agent = None

    def test_run_analysis_returns_string(self):
        result = self.crew.run_analysis(_SAMPLE_EVENT)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_run_analysis_non_empty_draft(self):
        draft = self.crew.run_analysis(_SAMPLE_EVENT)
        assert draft.strip() != ""
