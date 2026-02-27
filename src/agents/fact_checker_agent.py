"""CrewAI Fact-Checker Agent – verifies claims and flags unsubstantiated assertions."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    from crewai import Agent, Task, Crew
    _CREWAI_AVAILABLE = True
except ImportError:
    logger.warning("crewai not installed – FactCheckerCrewAgent in mock mode.")
    _CREWAI_AVAILABLE = False

_BACKSTORY = (
    "You are a senior investigative fact-checker with 15 years of experience "
    "verifying claims in Indian political journalism. You cite primary sources, "
    "flag logical fallacies, and escalate any content that cannot be independently "
    "corroborated."
)

_GOAL = (
    "Verify every factual claim made by other agents, provide citation requirements, "
    "and flag any assertion that lacks evidentiary support."
)


class FactCheckerCrewAgent:
    """CrewAI agent that verifies claims from the analysis pipeline."""

    def __init__(self) -> None:
        self._agent = self._build_agent() if _CREWAI_AVAILABLE else None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def verify(self, analysis: str, original_event: dict[str, Any]) -> str:
        """Fact-check *analysis* against *original_event* and return annotated result."""
        if self._agent is None:
            return self._mock_verify(analysis, original_event)
        task = Task(
            description=(
                "You are reviewing the following political analysis for factual "
                "accuracy. Identify every factual claim, mark verified/unverified "
                "and provide citation requirements for each:\n\n"
                f"Original event: {original_event}\n\n"
                f"Analysis to verify:\n{analysis}"
            ),
            expected_output=(
                "A fact-checked version of the analysis with each claim "
                "annotated as [VERIFIED], [UNVERIFIED], or [NEEDS CITATION]."
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
        from crewai import Agent, LLM  # noqa: PLC0415
        from src.config.settings import settings  # noqa: PLC0415

        if not settings.openai_api_key:
            logger.warning("OPENAI_API_KEY not set – FactCheckerCrewAgent running in mock mode.")
            return None
        try:
            llm = LLM(model=settings.openai_model, api_key=settings.openai_api_key)
            return Agent(
                role="Senior Fact-Checker",
                goal=_GOAL,
                backstory=_BACKSTORY,
                llm=llm,
                verbose=False,
                allow_delegation=False,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not build FactCheckerCrewAgent: %s", exc)
            return None

    @staticmethod
    def _mock_verify(analysis: str, event: dict) -> str:
        title = event.get("title", "this event")
        return (
            f"[MOCK FACT-CHECK RESULT]\n\n"
            f"Reviewing analysis of: '{title}'\n\n"
            f"Claim 1: Core factual assertions about the actor's conduct "
            f"— [NEEDS CITATION: Hansard / PRS India voting record]\n\n"
            f"Claim 2: References to criminal background "
            f"— [NEEDS CITATION: ADR/MyNeta affidavit data]\n\n"
            f"Claim 3: Quoted statements attributed to the politician "
            f"— [UNVERIFIED: No primary source URL provided]\n\n"
            f"Overall assessment: The analysis is directionally accurate but "
            f"requires 3 additional citations before publication. "
            f"No demonstrably false claims detected."
        )
