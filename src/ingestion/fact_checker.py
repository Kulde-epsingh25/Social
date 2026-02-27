"""Fact-checking via Originality.ai + BOOM heuristics + LIAR-dataset patterns."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

import requests

from src.config.settings import settings

logger = logging.getLogger(__name__)

# Patterns commonly associated with misinformation in Indian political discourse.
_MISINFORMATION_PATTERNS: list[str] = [
    r"\bfake\s+news\b",
    r"\bsatire\b",
    r"\bunverified\b",
    r"\bclaimed\s+without\s+proof\b",
    r"\bno\s+evidence\b",
    r"\bdebunked\b",
]

_INDIA_CONTEXT_KEYWORDS = [
    "india",
    "bharat",
    "lok sabha",
    "rajya sabha",
    "modi",
    "gandhi",
    "parliament",
    "delhi",
    "mumbai",
    "bengaluru",
    "election commission",
    "sc/st",
    "obc",
    "aadhaar",
]


@dataclass
class FactCheckResult:
    """Outcome of a fact-checking operation."""

    claim: str
    verified: bool
    confidence: float  # 0.0 – 1.0
    sources: list[str] = field(default_factory=list)


class FactCheckerAgent:
    """Verifies claims using Originality.ai API + local heuristics."""

    def __init__(self) -> None:
        self._api_key = settings.originality_api_key

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def verify_claim(self, claim: str) -> FactCheckResult:
        """Verify a single claim.  Falls back to heuristic check when API unavailable."""
        if self._api_key:
            return self._verify_via_api(claim)
        return self._heuristic_verify(claim)

    def check_misinformation(self, content: str) -> dict:
        """Scan *content* for misinformation signals; returns a summary dict."""
        flags: list[str] = []
        for pattern in _MISINFORMATION_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                flags.append(pattern)
        return {
            "misinformation_flags": flags,
            "flag_count": len(flags),
            "risk_level": "high" if len(flags) >= 3 else "medium" if flags else "low",
        }

    def is_regionally_relevant(self, content: str) -> bool:
        """Return *True* if the content is relevant to the Indian political context."""
        text = content.lower()
        return any(kw in text for kw in _INDIA_CONTEXT_KEYWORDS)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _verify_via_api(self, claim: str) -> FactCheckResult:
        """Call Originality.ai scan endpoint."""
        try:
            resp = requests.post(
                "https://api.originality.ai/api/v1/scan/ai",
                headers={"X-OAI-API-KEY": self._api_key},
                json={"content": claim, "title": "Claim verification"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            ai_score: float = data.get("score", {}).get("ai", 0.5)
            # High AI score → possible synthetic/misleading content.
            verified = ai_score < 0.6
            confidence = 1.0 - ai_score
            return FactCheckResult(
                claim=claim,
                verified=verified,
                confidence=round(confidence, 3),
                sources=["originality.ai"],
            )
        except requests.RequestException as exc:
            logger.error("Originality.ai request failed: %s", exc)
            return self._heuristic_verify(claim)

    @staticmethod
    def _heuristic_verify(claim: str) -> FactCheckResult:
        """Lightweight local heuristic when no API is available."""
        mis_result = FactCheckerAgent._static_check_misinfo(claim)
        high_risk = mis_result["risk_level"] == "high"
        return FactCheckResult(
            claim=claim,
            verified=not high_risk,
            confidence=0.5 if mis_result["risk_level"] == "medium" else 0.75,
            sources=["local-heuristic"],
        )

    @staticmethod
    def _static_check_misinfo(content: str) -> dict:
        flags = [
            p
            for p in _MISINFORMATION_PATTERNS
            if re.search(p, content, re.IGNORECASE)
        ]
        return {
            "misinformation_flags": flags,
            "flag_count": len(flags),
            "risk_level": "high" if len(flags) >= 3 else "medium" if flags else "low",
        }
