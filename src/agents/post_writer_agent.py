"""CrewAI Post Writer Agent – crafts viral, empirically-grounded commentary."""

from __future__ import annotations

import logging
import textwrap
from typing import Any

logger = logging.getLogger(__name__)

try:
    from crewai import Agent, Task, Crew
    _CREWAI_AVAILABLE = True
except ImportError:
    logger.warning("crewai not installed – PostWriterAgent in mock mode.")
    _CREWAI_AVAILABLE = False

_BACKSTORY = (
    "You are an award-winning political commentator who blends investigative "
    "journalism with philosophical rigour. Your posts routinely go viral because "
    "they are precise, morally sharp, and grounded in data. You never use hollow "
    "AI phrases like 'delve', 'it's worth noting', or 'in conclusion'. "
    "Every claim you make has a citation."
)

_GOAL = (
    "Write viral political commentary posts for X (Twitter) that are factually "
    "precise, philosophically grounded, and comply with platform character limits."
)

# Phrases to avoid in generated posts.
_BANNED_PHRASES = [
    "it's worth noting",
    "delve into",
    "in conclusion",
    "it is important to note",
    "let's explore",
    "as an ai",
    "i cannot",
]

_MAX_TWEET_CHARS = 280


class PostWriterAgent:
    """CrewAI agent that writes viral political commentary within X constraints."""

    def __init__(self) -> None:
        self._agent = self._build_agent() if _CREWAI_AVAILABLE else None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def write_post(
        self,
        philosophical_critique: str,
        fact_check_result: str,
        political_analysis: str,
        event: dict[str, Any],
    ) -> str:
        """Produce a ready-to-publish post (or thread) from the analyses."""
        if self._agent is None:
            return self._mock_post(event)

        task = Task(
            description=(
                "Using the following inputs, write a viral political commentary "
                "post for X (Twitter). Rules:\n"
                "• Single tweet if content fits in 280 chars; otherwise write a "
                "numbered thread (1/, 2/ …).\n"
                "• Cite at least one source.\n"
                "• No AI-sounding filler phrases.\n"
                "• Journalistic + philosophical tone.\n\n"
                f"Event: {event}\n\n"
                f"Philosophical critique:\n{philosophical_critique}\n\n"
                f"Political analysis:\n{political_analysis}\n\n"
                f"Fact-check notes:\n{fact_check_result}"
            ),
            expected_output=(
                "A complete post or numbered thread ready for publishing on X, "
                "with citations and within character limits."
            ),
            agent=self._agent,
        )
        crew = Crew(agents=[self._agent], tasks=[task], verbose=False)
        raw = str(crew.kickoff())
        return self._sanitise(raw)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_agent():  # noqa: ANN
        from crewai import Agent, LLM  # noqa: PLC0415
        from src.config.settings import settings  # noqa: PLC0415

        if not settings.openai_api_key:
            logger.warning("OPENAI_API_KEY not set – PostWriterAgent running in mock mode.")
            return None
        try:
            llm = LLM(model=settings.openai_model, api_key=settings.openai_api_key)
            return Agent(
                role="Political Commentator",
                goal=_GOAL,
                backstory=_BACKSTORY,
                llm=llm,
                verbose=False,
                allow_delegation=False,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not build PostWriterAgent: %s", exc)
            return None

    @staticmethod
    def _mock_post(event: dict) -> str:
        actor = event.get("actor", event.get("title", "A senior official"))
        action = event.get("action", "made a controversial decision")
        return textwrap.dedent(
            f"""\
            1/ {actor} {action} — a direct violation of the social contract
            (Locke, 1689). Citizens consented to be governed, not exploited. 🧵

            2/ Rawls' veil of ignorance test: no rational agent would design
            a system permitting this. 📊 Data: ADR shows ₹X cr in undisclosed
            assets. Source: myneta.info

            3/ Kant's categorical imperative condemns this unequivocally.
            If every minister acted this way, constitutional democracy collapses.

            4/ The question is not partisan. It is constitutional.
            Demand accountability. RT if you agree. #Accountability #India
            """
        )

    @staticmethod
    def _sanitise(text: str) -> str:
        """Remove banned AI-sounding phrases from generated text (case-insensitive)."""
        import re

        for phrase in _BANNED_PHRASES:
            if phrase.lower() in text.lower():
                logger.debug("Removed banned phrase: '%s'", phrase)
                text = re.sub(re.escape(phrase), "", text, flags=re.IGNORECASE)
        return text.strip()
