"""Legislative tracker: PRS India, Digital Sansad, ADR/MyNeta integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import requests

from src.config.settings import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sample in-memory fixture used in demo / test mode.
# ---------------------------------------------------------------------------
_MOCK_RECORDS: dict[str, dict[str, Any]] = {
    "demo politician": {
        "party": "Demo Party",
        "voting_records": [
            {"bill": "The Accountability Bill 2023", "vote": "Yea"},
            {"bill": "The Transparency Amendment 2022", "vote": "Nay"},
        ],
        "statements": [
            "We must fight corruption at every level.",
            "Transparency is the cornerstone of democracy.",
        ],
        "criminal_background": {"cases": 0, "pending_trial": 0},
    }
}


@dataclass
class LegislativeRecord:
    """Consolidated public record for an elected representative."""

    politician_name: str
    party: str
    voting_records: list[dict] = field(default_factory=list)
    statements: list[str] = field(default_factory=list)
    criminal_background: dict = field(default_factory=dict)


class LegislativeTracker:
    """Aggregates legislative and affidavit data for Indian politicians."""

    def __init__(self) -> None:
        self._prs_url = settings.prs_base_url
        self._adr_url = settings.adr_base_url

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_politician_record(self, name: str) -> LegislativeRecord:
        """Return a consolidated record for *name*.

        Uses live PRS/ADR endpoints when configured; falls back to mock data.
        """
        try:
            votes = self._fetch_prs_votes(name)
            affidavit = self._fetch_adr_affidavit(name)
            return LegislativeRecord(
                politician_name=name,
                party=affidavit.get("party", "Unknown"),
                voting_records=votes,
                statements=[],
                criminal_background=affidavit.get("criminal_background", {}),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Could not fetch live record for '%s': %s – using mock.", name, exc
            )
            return self._mock_record(name)

    def get_voting_history(
        self, politician_name: str, topic: str
    ) -> list[dict]:
        """Return votes cast by *politician_name* related to *topic*."""
        record = self.get_politician_record(politician_name)
        topic_lower = topic.lower()
        return [
            v
            for v in record.voting_records
            if topic_lower in v.get("bill", "").lower()
        ]

    def get_criminal_affidavit(self, politician_name: str) -> dict:
        """Return self-declared criminal/asset affidavit data from ADR/MyNeta."""
        try:
            return self._fetch_adr_affidavit(politician_name)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Affidavit fetch failed for '%s': %s", politician_name, exc)
            return {"error": str(exc), "source": "fallback"}

    def detect_hypocrisy(
        self,
        politician_name: str,
        current_stance: str,
        topic: str,
    ) -> dict:
        """Compare *current_stance* with historical voting record on *topic*."""
        history = self.get_voting_history(politician_name, topic)
        if not history:
            return {
                "hypocrisy_detected": False,
                "reason": "No historical voting data found.",
                "evidence": [],
            }

        # Simplified: flag as hypocritical when any past vote contradicts stance.
        contradictions = []
        stance_lower = current_stance.lower()
        for vote in history:
            past = vote.get("vote", "").lower()
            if "support" in stance_lower and past in ("nay", "against", "no"):
                contradictions.append(vote)
            elif "oppose" in stance_lower and past in ("yea", "aye", "yes"):
                contradictions.append(vote)

        return {
            "hypocrisy_detected": bool(contradictions),
            "reason": "Past votes contradict current public stance." if contradictions else "No contradiction found.",
            "evidence": contradictions,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_prs_votes(self, name: str) -> list[dict]:
        resp = requests.get(
            f"{self._prs_url}/votes",
            params={"mp": name},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("votes", [])

    def _fetch_adr_affidavit(self, name: str) -> dict:
        resp = requests.get(
            f"{self._adr_url}/affidavit",
            params={"name": name},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _mock_record(name: str) -> LegislativeRecord:
        key = name.lower()
        data = _MOCK_RECORDS.get(key, _MOCK_RECORDS["demo politician"])
        return LegislativeRecord(
            politician_name=name,
            party=data["party"],
            voting_records=data["voting_records"],
            statements=data["statements"],
            criminal_background=data["criminal_background"],
        )
