"""Unit tests for compliance modules."""

from __future__ import annotations

import pytest

from src.compliance.content_moderator import ContentModerator, ComplianceResult
from src.compliance.ai_labeler import AILabeler


class TestContentModerator:
    def setup_method(self):
        self.moderator = ContentModerator()

    def test_clean_content_passes_it_rules(self):
        result = self.moderator.check_it_rules_2026(
            "The minister was questioned in parliament today."
        )
        assert isinstance(result, ComplianceResult)
        assert result.passed is True

    def test_prohibited_content_fails_it_rules(self):
        result = self.moderator.check_it_rules_2026(
            "This is fake news and incites violence against minorities."
        )
        assert result.passed is False
        assert len(result.violations) > 0

    def test_eci_violation_detected(self):
        result = self.moderator.check_eci_guidelines(
            "Vote for Party X on election day."
        )
        assert result.passed is False

    def test_clean_content_passes_eci(self):
        result = self.moderator.check_eci_guidelines(
            "Parliament passed the Finance Bill by voice vote."
        )
        assert result.passed is True

    def test_defamation_risk_detected(self):
        result = self.moderator.check_defamation_risk(
            "The minister is a thief and proved corrupt."
        )
        assert result.passed is False

    def test_attributed_statement_passes_defamation(self):
        result = self.moderator.check_defamation_risk(
            "According to the CBI report, the minister is under investigation."
        )
        assert result.passed is True

    def test_is_compliant_clean_content(self):
        assert self.moderator.is_compliant(
            "Parliament passed a new budget allocation bill today."
        )

    def test_is_compliant_dirty_content(self):
        assert not self.moderator.is_compliant(
            "This fake news incites violence and hate speech."
        )

    def test_recommendations_populated_on_violation(self):
        result = self.moderator.check_it_rules_2026(
            "The seditious fake news must be stopped."
        )
        if not result.passed:
            assert len(result.recommendations) > 0


class TestAILabeler:
    def setup_method(self):
        self.labeler = AILabeler()

    def test_add_label_prepends_prefix(self):
        labeled = self.labeler.add_label("Parliament session begins.")
        assert labeled.startswith(self.labeler._prefix)

    def test_add_label_idempotent(self):
        content = f"{self.labeler._prefix} Some content."
        result = self.labeler.add_label(content)
        assert result == content

    def test_add_metadata_structure(self):
        meta = self.labeler.add_metadata("Some AI-generated content.")
        assert meta["ai_generated"] is True
        assert "generated_at" in meta
        assert meta["compliance"]["it_rules_2026"] is True

    def test_format_for_x_returns_string(self):
        result = self.labeler.format_for_x(
            "Parliamentary accountability matters.",
            {"frameworks": ["justice", "deontology"]},
        )
        assert isinstance(result, str)
        assert len(result) > 0
