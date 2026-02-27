"""RAG retrieval: maps political events to philosophical frameworks."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from src.rag.knowledge_base import KnowledgeBase, PhilosophicalChunk

logger = logging.getLogger(__name__)

_FRAMEWORK_QUERIES: dict[str, str] = {
    "kantian": "duty categorical imperative universal law moral obligation",
    "utilitarian": "greatest happiness consequences welfare utility outcomes",
    "lockean": "natural rights consent government liberty property",
    "rawlsian": "justice fairness veil of ignorance equality original position",
    "virtue_ethics": "character virtue courage justice prudence moral excellence",
    "machiavellian": "power realpolitik ends justify means statecraft",
}


@dataclass
class PhilosophicalContext:
    """Aggregated philosophical context retrieved for a political event."""

    frameworks: list[str] = field(default_factory=list)
    relevant_passages: list[str] = field(default_factory=list)
    primary_philosophers: list[str] = field(default_factory=list)
    normative_guidance: str = ""


class PhilosophicalRetriever:
    """Retrieves relevant philosophical context for political events via RAG."""

    def __init__(self, knowledge_base: KnowledgeBase | None = None) -> None:
        self._kb = knowledge_base or KnowledgeBase()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def retrieve_context(self, political_event: dict) -> PhilosophicalContext:
        """Retrieve philosophical context relevant to *political_event*.

        *political_event* dict expected keys: actor, action, target, description.
        """
        query = self._build_query(political_event)
        chunks: list[PhilosophicalChunk] = self._kb.semantic_search(query, top_k=5)
        frameworks = list({c.category for c in chunks})
        passages = [c.text for c in chunks]
        philosophers = list({c.philosopher for c in chunks})
        guidance = self._summarise_guidance(chunks, political_event)
        return PhilosophicalContext(
            frameworks=frameworks,
            relevant_passages=passages,
            primary_philosophers=philosophers,
            normative_guidance=guidance,
        )

    def apply_framework(self, event: dict, framework: str) -> str:
        """Apply a specific philosophical *framework* to *event* and return critique."""
        query = _FRAMEWORK_QUERIES.get(framework.lower(), framework)
        chunks = self._kb.semantic_search(query, top_k=3)
        if not chunks:
            return f"No philosophical context found for framework: {framework}"
        actor = event.get("actor", "The actor")
        action = event.get("action", "their action")
        passages = "\n".join(f"  • {c.text}" for c in chunks)
        return (
            f"Applying {framework.title()} framework to the event where "
            f"'{actor}' undertook '{action}':\n\n"
            f"Relevant passages:\n{passages}\n\n"
            f"Normative assessment: {self._normative_assessment(framework, event)}"
        )

    def bridge_is_ought(self, descriptive_facts: dict) -> dict:
        """Apply Hume's is-ought bridge to derive normative conclusions from facts.

        Takes descriptive facts (what *is* happening) and returns normative
        conclusions (what *ought* to happen), grounded in retrieved philosophy.
        """
        event_desc = " ".join(str(v) for v in descriptive_facts.values())
        ctx = self.retrieve_context({"description": event_desc})
        return {
            "descriptive_facts": descriptive_facts,
            "normative_frameworks": ctx.frameworks,
            "normative_conclusions": [
                self._normative_assessment(fw, descriptive_facts)
                for fw in ctx.frameworks
            ],
            "primary_guidance": ctx.normative_guidance,
            "supporting_passages": ctx.relevant_passages[:3],
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_query(event: dict) -> str:
        parts = [
            event.get("actor", ""),
            event.get("action", ""),
            event.get("target", ""),
            event.get("description", ""),
        ]
        return " ".join(p for p in parts if p)

    @staticmethod
    def _summarise_guidance(
        chunks: list[PhilosophicalChunk], event: dict
    ) -> str:
        if not chunks:
            return "No specific philosophical guidance retrieved."
        top = chunks[0]
        actor = event.get("actor", "The actor")
        return (
            f"From a {top.category} perspective ({top.philosopher}): "
            f"'{top.text[:120]}…' — "
            f"This framework suggests evaluating whether {actor}'s conduct "
            "respects the principles of universal moral law and the rights of "
            "all stakeholders."
        )

    @staticmethod
    def _normative_assessment(framework: str, event: dict) -> str:
        actor = event.get("actor", "The actor")
        action = event.get("action", "their action")
        assessments: dict[str, str] = {
            "kantian": (
                f"{actor}'s decision to '{action}' must be tested against "
                "universalisability: could this maxim become a universal law "
                "without contradiction?"
            ),
            "utilitarian": (
                f"'{action}' by {actor} should be evaluated by aggregate welfare: "
                "does it maximise well-being for the greatest number?"
            ),
            "lockean": (
                f"{actor}'s '{action}' raises questions about consent and natural "
                "rights – does it violate the social contract?"
            ),
            "rawlsian": (
                f"Under the veil of ignorance, would {actor}'s '{action}' be "
                "chosen as a just principle for organising society?"
            ),
            "virtue_ethics": (
                f"Does '{action}' by {actor} reflect the virtuous character "
                "expected of a public representative?"
            ),
            "machiavellian": (
                f"Machiavellian realism would ask: does {actor}'s '{action}' "
                "serve stable governance, even if by ruthless means?"
            ),
        }
        return assessments.get(
            framework.lower(),
            f"No standard assessment available for framework: {framework}.",
        )
