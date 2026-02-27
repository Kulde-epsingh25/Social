"""CrewAI Political Scientist Agent – power dynamics and legislative analysis."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    from crewai import Agent, Task, Crew
    _CREWAI_AVAILABLE = True
except ImportError:
    logger.warning("crewai not installed – PoliticalScientistAgent in mock mode.")
    _CREWAI_AVAILABLE = False

_BACKSTORY = (
    "You are a political scientist specialising in Indian parliamentary democracy, "
    "legislative behaviour, electoral accountability, and power dynamics. "
    "You cross-reference voting records, public statements, and affidavit data "
    "to expose conflicts of interest and democratic deficits."
)

_GOAL = (
    "Analyse power dynamics, legislative behaviour, and identify conflicts of "
    "interest in Indian political events with empirical rigour."
)


class PoliticalScientistAgent:
    """CrewAI agent that analyses political power structures and legislative record."""

    def __init__(self) -> None:
        self._agent = self._build_agent() if _CREWAI_AVAILABLE else None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyse(self, event: dict[str, Any], legislative_record: dict | None = None) -> str:
        """Return a political science analysis of *event*."""
        if self._agent is None:
            return self._mock_analysis(event, legislative_record)
        context = f"Event: {event}\nLegislative Record: {legislative_record or 'Not provided'}"
        task = Task(
            description=(
                "Analyse the power dynamics and legislative behaviour in the "
                "following context. Identify any conflicts of interest and explain "
                "how this event reflects on democratic accountability:\n\n"
                f"{context}"
            ),
            expected_output=(
                "A structured political science analysis covering power dynamics, "
                "legislative record comparison, and accountability gaps."
            ),
            agent=self._agent,
        )
        crew = Crew(agents=[self._agent], tasks=[task], verbose=False)
        return str(crew.kickoff())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_agent():  # noqa: ANN
        from crewai import Agent  # noqa: PLC0415
        try:
            return Agent(
                role="Political Scientist",
                goal=_GOAL,
                backstory=_BACKSTORY,
                verbose=False,
                allow_delegation=False,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not build PoliticalScientistAgent: %s", exc)
            return None

    @staticmethod
    def _mock_analysis(event: dict, record: dict | None) -> str:
        actor = event.get("actor", "The politician")
        action = event.get("action", "their action")
        cases = record.get("criminal_background", {}).get("cases", 0) if record else 0
        return (
            f"[MOCK POLITICAL SCIENCE ANALYSIS]\n\n"
            f"**Power Dynamics**: '{actor}' occupies a position of institutional "
            f"authority, making '{action}' a demonstration of executive overreach "
            f"that warrants scrutiny under democratic norms.\n\n"
            f"**Legislative Record**: "
            + (
                f"{actor} has {cases} declared criminal case(s) on affidavit. "
                if cases
                else f"No criminal cases on affidavit for {actor}. "
            )
            + "Historical voting pattern shows inconsistency with current public stance.\n\n"
            f"**Conflict of Interest**: Cross-referencing available data suggests "
            f"financial or political interests that may have influenced '{action}'.\n\n"
            f"**Accountability Gap**: No formal accountability mechanism has been "
            f"triggered despite public evidence. This constitutes a democratic deficit."
        )
