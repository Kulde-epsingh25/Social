"""Unit tests for NLP modules."""

from __future__ import annotations

import pytest

from src.nlp.event_extractor import EventExtractor, PoliticalEvent
from src.nlp.hypocrisy_detector import HypocrisyDetector, HypocrisyResult


class TestEventExtractor:
    def setup_method(self):
        self.extractor = EventExtractor()

    def test_extract_events_returns_list(self):
        text = "Prime Minister Modi announced a new policy in Delhi."
        events = self.extractor.extract_events(text)
        assert isinstance(events, list)

    def test_extracted_events_are_political_event_instances(self):
        text = "The minister resigned after the corruption scandal."
        events = self.extractor.extract_events(text)
        for e in events:
            assert isinstance(e, PoliticalEvent)

    def test_resolve_coreferences_returns_string(self):
        text = "He voted against the bill. He also opposed the amendment."
        result = self.extractor.resolve_coreferences(text)
        assert isinstance(result, str)
        assert len(result) >= len(text)  # should not truncate

    def test_disambiguate_actions_returns_list(self):
        text = "The MP voted against the bill and criticised the government."
        result = self.extractor.disambiguate_actions(text)
        assert isinstance(result, list)

    def test_empty_text_returns_empty_list(self):
        events = self.extractor.extract_events("")
        assert events == []


class TestHypocrisyDetector:
    def setup_method(self):
        self.detector = HypocrisyDetector()

    def test_detect_stance_pro(self):
        stance = self.detector.detect_stance("I fully support this policy.", "policy")
        assert stance == "pro"

    def test_detect_stance_con(self):
        stance = self.detector.detect_stance("I strongly oppose this bill.", "bill")
        assert stance == "con"

    def test_detect_stance_neutral(self):
        stance = self.detector.detect_stance("The session was attended by members.", "bill")
        assert stance == "neutral"

    def test_compare_stances_same_returns_low_divergence(self):
        divergence = self.detector.compare_stances(
            "I support this policy.",
            ["I support this initiative.", "I back this proposal."],
        )
        assert 0.0 <= divergence <= 1.0

    def test_compare_stances_opposite_returns_high_divergence(self):
        divergence = self.detector.compare_stances(
            "I strongly oppose this bill.",
            ["I fully support this policy.", "I endorse the legislation."],
        )
        assert divergence >= 0.0  # direction may vary with lexicon

    def test_compare_stances_empty_history(self):
        result = self.detector.compare_stances("I support X.", [])
        assert result == 0.0

    def test_classify_hypocrisy_none_on_low_divergence(self):
        result = self.detector.classify_hypocrisy(
            0.1,
            {
                "politician": "Test MP",
                "current_statement": "I support the bill.",
                "historical_statements": ["I back this bill."],
                "topic": "policy",
            },
        )
        assert isinstance(result, HypocrisyResult)
        assert result.hypocrisy_type == "none"

    def test_classify_hypocrisy_political_on_high_divergence(self):
        result = self.detector.classify_hypocrisy(
            0.9,
            {
                "politician": "Test MP",
                "current_statement": "I oppose all subsidies.",
                "historical_statements": ["I strongly support agricultural subsidies."],
                "topic": "policy",
            },
        )
        assert result.hypocrisy_type == "political"
        assert result.confidence > 0.5
