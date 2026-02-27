"""CrewAI orchestration: runs the analysis/drafting pipeline."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    from crewai import Crew, Task
    _CREWAI_AVAILABLE = True
except ImportError:
    logger.warning("crewai not installed – AccountabilityCrew in sequential mock mode.")
    _CREWAI_AVAILABLE = False

from src.agents.philosopher_agent import PhilosopherAgent
from src.agents.political_scientist_agent import PoliticalScientistAgent
from src.agents.fact_checker_agent import FactCheckerCrewAgent
from src.agents.post_writer_agent import PostWriterAgent


class AccountabilityCrew:
    """Coordinates all CrewAI agents through the analysis → draft pipeline.

    Pipeline:
        1. PhilosopherAgent     → philosophical critique
        2. PoliticalScientistAgent → power/legislative analysis
        3. FactCheckerCrewAgent → verification
        4. PostWriterAgent      → viral post draft
    """

    def __init__(self) -> None:
        self._philosopher = PhilosopherAgent()
        self._pol_scientist = PoliticalScientistAgent()
        self._fact_checker = FactCheckerCrewAgent()
        self._post_writer = PostWriterAgent()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_analysis(self, news_event: dict[str, Any]) -> str:
        """Run the full crew pipeline on *news_event* and return a drafted post.

        When crewai is available the agents run in sequence; otherwise
        the mock implementations provide a coherent demo output.
        """
        logger.info(
            "AccountabilityCrew starting analysis for event: %s",
            news_event.get("title", str(news_event)[:80]),
        )

        # Step 1 – philosophical critique
        philosophy = self._philosopher.analyse(news_event)
        logger.debug("Philosophy step complete.")

        # Step 2 – political science analysis
        pol_analysis = self._pol_scientist.analyse(news_event)
        logger.debug("Political science step complete.")

        # Step 3 – fact-check the combined analysis
        combined = f"{philosophy}\n\n{pol_analysis}"
        verified = self._fact_checker.verify(combined, news_event)
        logger.debug("Fact-check step complete.")

        # Step 4 – write the post
        post = self._post_writer.write_post(
            philosophical_critique=philosophy,
            fact_check_result=verified,
            political_analysis=pol_analysis,
            event=news_event,
        )
        logger.info("AccountabilityCrew draft post ready (%d chars).", len(post))
        return post

    # Expose sub-agents for inspection / independent use.
    @property
    def philosopher(self) -> PhilosopherAgent:
        return self._philosopher

    @property
    def political_scientist(self) -> PoliticalScientistAgent:
        return self._pol_scientist

    @property
    def fact_checker(self) -> FactCheckerCrewAgent:
        return self._fact_checker

    @property
    def post_writer(self) -> PostWriterAgent:
        return self._post_writer
