"""Content moderation: IT Rules 2026, ECI guidelines, defamation risk."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pattern libraries
# ---------------------------------------------------------------------------
_IT_RULES_PROHIBITED: list[str] = [
    r"\bhate\s+speech\b",
    r"\bincite[sd]?\s+violence\b",
    r"\bterror(?:ism|ist)\b",
    r"\bfake\s+news\b",
    r"\bseditious\b",
]

_ECI_PROHIBITED: list[str] = [
    r"\bvote\s+for\b",
    r"\bvoting\s+on\s+\w+\s+day\b",
    r"\bdon't\s+vote\s+for\b",
    r"\bellection\s+bribe\b",
    r"\bpaid\s+news\b",
]

_DEFAMATION_PATTERNS: list[str] = [
    r"\b(?:is|are)\s+a\s+(?:thief|criminal|murderer|rapist|terrorist)\b",
    r"\bproved\s+corrupt\b",
    r"\bstole\s+public\s+money\b",
]


@dataclass
class ComplianceResult:
    """Result of a compliance check."""

    passed: bool
    violations: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class ContentModerator:
    """Checks content against IT Rules 2026, ECI guidelines, and defamation law."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_it_rules_2026(self, content: str) -> ComplianceResult:
        """Check *content* against IT Rules 2026 prohibited categories."""
        violations = self._scan(content, _IT_RULES_PROHIBITED)
        recs = [
            f"Remove or rephrase content matching pattern: '{v}'" for v in violations
        ]
        if violations:
            recs.append(
                "Ensure AI-Generated label is present per IT Rules 2026 SGI guidelines."
            )
        return ComplianceResult(passed=not violations, violations=violations, recommendations=recs)

    def check_eci_guidelines(self, content: str) -> ComplianceResult:
        """Check *content* against Election Commission of India guidelines."""
        violations = self._scan(content, _ECI_PROHIBITED)
        recs = [
            f"ECI violation detected: '{v}'. Remove electoral call-to-action." for v in violations
        ]
        return ComplianceResult(passed=not violations, violations=violations, recommendations=recs)

    def check_defamation_risk(self, content: str) -> ComplianceResult:
        """Flag content that may constitute actionable defamation."""
        violations = self._scan(content, _DEFAMATION_PATTERNS)
        recs: list[str] = []
        if violations:
            recs.append(
                "Replace unverified defamatory assertions with attributed, "
                "source-backed reporting language (e.g. 'according to …')."
            )
        return ComplianceResult(passed=not violations, violations=violations, recommendations=recs)

    def is_compliant(self, content: str) -> bool:
        """Return ``True`` only when content passes all compliance checks."""
        return (
            self.check_it_rules_2026(content).passed
            and self.check_eci_guidelines(content).passed
            and self.check_defamation_risk(content).passed
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _scan(content: str, patterns: list[str]) -> list[str]:
        hits: list[str] = []
        for pattern in patterns:
            if re.search(pattern, content, re.IGNORECASE):
                hits.append(pattern)
        return hits
