"""Actor-action-object extraction from political text using spaCy / ConfliBERT."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Attempt to load spaCy; gracefully degrade if not installed.
try:
    import spacy

    try:
        _nlp = spacy.load("en_core_web_sm")
    except OSError:
        logger.warning(
            "spaCy model 'en_core_web_sm' not found. "
            "Run: python -m spacy download en_core_web_sm"
        )
        _nlp = None
except ImportError:
    logger.warning("spaCy not installed – event extraction will use regex fallback.")
    _nlp = None


@dataclass
class PoliticalEvent:
    """Structured representation of a political event extracted from text."""

    actor: str
    action: str
    target: str
    instrument: str = ""
    reason: str = ""
    reporter: str = ""
    timestamp: str = ""
    location: str = ""
    confidence: float = 0.0
    raw_sentence: str = ""


class EventExtractor:
    """Extracts structured political events from unstructured text.

    Primary method: spaCy dependency parsing.
    Fallback:        regex heuristics when spaCy model is unavailable.
    """

    def extract_events(self, text: str) -> list[PoliticalEvent]:
        """Return a list of :class:`PoliticalEvent` objects found in *text*."""
        resolved = self.resolve_coreferences(text)
        if _nlp is not None:
            return self._spacy_extract(resolved)
        return self._regex_extract(resolved)

    def resolve_coreferences(self, text: str) -> str:  # noqa: PLR6301
        """Lightweight pronoun resolution via named-entity repetition heuristic.

        A full coref model (e.g. spaCy-experimental) can replace this.
        """
        # Without a dedicated coref model we return the text unchanged.
        return text

    def disambiguate_actions(self, text: str) -> list[dict]:  # noqa: PLR6301
        """Return candidate action interpretations for ambiguous verbs in *text*."""
        if _nlp is None:
            return []
        doc = _nlp(text)
        actions: list[dict] = []
        for token in doc:
            if token.pos_ == "VERB":
                actions.append(
                    {
                        "verb": token.lemma_,
                        "surface": token.text,
                        "subject": next(
                            (
                                str(child)
                                for child in token.children
                                if child.dep_ in ("nsubj", "nsubjpass")
                            ),
                            "",
                        ),
                        "object": next(
                            (
                                str(child)
                                for child in token.children
                                if child.dep_ in ("dobj", "attr", "pobj")
                            ),
                            "",
                        ),
                    }
                )
        return actions

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _spacy_extract(self, text: str) -> list[PoliticalEvent]:
        """Use spaCy dependency parse to extract events sentence-by-sentence."""
        assert _nlp is not None
        doc = _nlp(text)
        events: list[PoliticalEvent] = []
        for sent in doc.sents:
            event = self._extract_from_sentence(sent)
            if event:
                events.append(event)
        return events

    @staticmethod
    def _extract_from_sentence(sent: Any) -> PoliticalEvent | None:
        """Extract a single event from a spaCy *Span* (sentence)."""
        actor = target = action = location = ""
        for token in sent:
            if token.pos_ == "VERB" and not action:
                action = token.lemma_
                for child in token.children:
                    if child.dep_ in ("nsubj", "nsubjpass") and not actor:
                        actor = child.text
                    if child.dep_ in ("dobj", "attr", "pobj") and not target:
                        target = child.text
        for ent in sent.ents:
            if ent.label_ in ("GPE", "LOC") and not location:
                location = ent.text
            if ent.label_ in ("PERSON", "ORG") and not actor:
                actor = ent.text

        if not (actor or action):
            return None
        return PoliticalEvent(
            actor=actor,
            action=action,
            target=target,
            location=location,
            confidence=0.6,
            raw_sentence=sent.text.strip(),
        )

    @staticmethod
    def _regex_extract(text: str) -> list[PoliticalEvent]:
        """Fallback regex-based extraction returning low-confidence events."""
        import re

        events: list[PoliticalEvent] = []
        pattern = re.compile(
            r"(?P<actor>[A-Z][a-z]+(?: [A-Z][a-z]+)?)"
            r"\s+(?P<action>\w+ed|\w+ing|\w+s)"
            r"(?:\s+(?P<target>[a-z ]{2,30}))?",
        )
        for m in pattern.finditer(text):
            events.append(
                PoliticalEvent(
                    actor=m.group("actor") or "",
                    action=m.group("action") or "",
                    target=m.group("target") or "",
                    confidence=0.3,
                    raw_sentence=m.group(0),
                )
            )
        return events
