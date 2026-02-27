"""Hypocrisy detection via stance comparison against historical record."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Literal

logger = logging.getLogger(__name__)

HypocrisyType = Literal["personal", "political", "none"]

# Positive / negative stance keyword lists (minimal lexicon).
_PRO_KEYWORDS = {
    "support",
    "endorse",
    "favour",
    "favor",
    "back",
    "promote",
    "advocate",
    "welcome",
    "approve",
}
_CON_KEYWORDS = {
    "oppose",
    "against",
    "condemn",
    "reject",
    "denounce",
    "criticise",
    "criticize",
    "resist",
    "block",
}


@dataclass
class HypocrisyResult:
    """Result of a hypocrisy analysis."""

    politician: str
    current_statement: str
    historical_record: list[str] = field(default_factory=list)
    hypocrisy_type: HypocrisyType = "none"
    confidence: float = 0.0
    evidence: list[str] = field(default_factory=list)


class HypocrisyDetector:
    """Detects hypocrisy by comparing a politician's current stance with
    their historical statements and voting record."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect_stance(self, text: str, entity: str) -> str:  # noqa: PLR6301
        """Return 'pro', 'con', or 'neutral' toward *entity* in *text*."""
        lower = text.lower()
        pro_hits = sum(1 for w in _PRO_KEYWORDS if w in lower)
        con_hits = sum(1 for w in _CON_KEYWORDS if w in lower)
        if pro_hits > con_hits:
            return "pro"
        if con_hits > pro_hits:
            return "con"
        return "neutral"

    def compare_stances(
        self, current: str, historical: list[str]
    ) -> float:
        """Return a divergence score 0–1 between *current* and *historical* stances.

        0 = identical, 1 = completely opposite.
        """
        if not historical:
            return 0.0
        current_vec = self._stance_vector(current)
        divergences: list[float] = []
        for past in historical:
            past_vec = self._stance_vector(past)
            divergences.append(self._cosine_distance(current_vec, past_vec))
        return round(sum(divergences) / len(divergences), 4)

    def classify_hypocrisy(
        self, divergence: float, context: dict
    ) -> HypocrisyResult:
        """Classify the type and confidence of detected hypocrisy."""
        politician = context.get("politician", "Unknown")
        current = context.get("current_statement", "")
        historical = context.get("historical_statements", [])

        if divergence < 0.3:
            return HypocrisyResult(
                politician=politician,
                current_statement=current,
                historical_record=historical,
                hypocrisy_type="none",
                confidence=divergence,
            )

        h_type: HypocrisyType
        is_personal = context.get("topic", "policy") in (
            "personal conduct",
            "lifestyle",
            "family",
        )
        h_type = "personal" if is_personal else "political"
        evidence = [
            f"Divergence score: {divergence:.2f}",
            f"Current stance: {current[:80]}",
        ] + [f"Past record: {h[:80]}" for h in historical[:3]]

        return HypocrisyResult(
            politician=politician,
            current_statement=current,
            historical_record=historical,
            hypocrisy_type=h_type,
            confidence=min(divergence * 1.2, 1.0),
            evidence=evidence,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _stance_vector(text: str) -> dict[str, float]:
        lower = text.lower()
        return {
            "pro": sum(1.0 for w in _PRO_KEYWORDS if w in lower),
            "con": sum(1.0 for w in _CON_KEYWORDS if w in lower),
        }

    @staticmethod
    def _cosine_distance(a: dict[str, float], b: dict[str, float]) -> float:
        keys = set(a) | set(b)
        dot = sum(a.get(k, 0.0) * b.get(k, 0.0) for k in keys)
        mag_a = math.sqrt(sum(v ** 2 for v in a.values()))
        mag_b = math.sqrt(sum(v ** 2 for v in b.values()))
        if mag_a == 0 or mag_b == 0:
            return 0.0
        similarity = dot / (mag_a * mag_b)
        return round(1.0 - similarity, 4)
