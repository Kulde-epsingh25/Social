"""CrewAI Philosopher Agent – applies ethical frameworks to political events."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    from crewai import Agent, Task, Crew
    _CREWAI_AVAILABLE = True
except ImportError:
    logger.warning("crewai not installed – PhilosopherAgent running in mock mode.")
    _CREWAI_AVAILABLE = False


_PHILOSOPHER_BACKSTORY = (
    "You are a moral philosopher with deep expertise in Kantian deontology, "
    "Millian utilitarianism, Lockean political philosophy, Rawlsian justice, "
    "and Machiavellian realism. You specialise in applying classical frameworks "
    "to contemporary Indian political events, producing rigorous, citation-backed "
    "normative critiques."
)

_PHILOSOPHER_GOAL = (
    "Analyse political events through multiple ethical lenses and produce "
    "structured philosophical critiques grounded in primary source citations."
)


class PhilosopherAgent:
    """CrewAI agent that applies philosophical frameworks to political events."""

    def __init__(self) -> None:
        self._agent = self._build_agent() if _CREWAI_AVAILABLE else None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyse(self, event: dict[str, Any]) -> str:
        """Return a philosophical critique of *event*."""
        if self._agent is None:
            return self._mock_analysis(event)
        task = Task(
            description=(
                f"Apply Kant, Locke, Mill, Rawls, and Machiavelli to critique "
                f"the following political event and explain each framework's "
                f"verdict step-by-step:\n\n{event}"
            ),
            expected_output=(
                "A structured philosophical critique with one paragraph per "
                "framework and a synthesis conclusion."
            ),
            agent=self._agent,
        )
        crew = Crew(agents=[self._agent], tasks=[task], verbose=False)
        result = crew.kickoff()
        return str(result)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_agent():  # noqa: ANN
        from crewai import Agent, LLM  # noqa: PLC0415
        from src.config.settings import settings  # noqa: PLC0415

        if not settings.openai_api_key:
            logger.warning("OPENAI_API_KEY not set – PhilosopherAgent running in mock mode.")
            return None
        try:
            llm = LLM(model=settings.openai_model, api_key=settings.openai_api_key)
            return Agent(
                role="Moral Philosopher",
                goal=_PHILOSOPHER_GOAL,
                backstory=_PHILOSOPHER_BACKSTORY,
                llm=llm,
                verbose=False,
                allow_delegation=False,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not build PhilosopherAgent: %s", exc)
            return None

    @staticmethod
    def _mock_analysis(event: dict) -> str:
        actor = event.get("actor", "The political actor")
        action = event.get("action", "their reported action")
        return (
            f"[MOCK PHILOSOPHICAL ANALYSIS]\n\n"
            f"**Kantian**: '{actor}' performing '{action}' must be tested against "
            f"universalisability. If every public servant acted this way, would the "
            f"moral order collapse? The categorical imperative suggests it would.\n\n"
            f"**Utilitarian (Mill)**: Does '{action}' maximise aggregate welfare "
            f"for Indian citizens? Available evidence indicates net harm to "
            f"democratic institutions.\n\n"
            f"**Lockean**: '{action}' potentially violates the social contract "
            f"through which '{actor}' derives their authority.\n\n"
            f"**Rawlsian**: Behind the veil of ignorance, would any rational agent "
            f"choose a society where '{action}' is permissible?\n\n"
            f"**Machiavellian**: Even pragmatic statecraft cannot justify actions "
            f"that erode the trust necessary for stable governance.\n\n"
            f"**Synthesis**: Across all frameworks, accountability and transparency "
            f"are non-negotiable norms that '{actor}' appears to have violated."
        )
