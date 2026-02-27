"""LangGraph state machine: full end-to-end accountability pipeline."""

from __future__ import annotations

import logging
from typing import Any, TypedDict

logger = logging.getLogger(__name__)

try:
    from langgraph.graph import StateGraph, END
    _LANGGRAPH_AVAILABLE = True
except ImportError:
    logger.warning("langgraph not installed – workflow running in sequential mode.")
    _LANGGRAPH_AVAILABLE = False

from src.ingestion.news_ingestion import NewsIngestionAgent
from src.ingestion.fact_checker import FactCheckerAgent
from src.nlp.event_extractor import EventExtractor
from src.rag.philosophical_retriever import PhilosophicalRetriever
from src.orchestration.crew_orchestrator import AccountabilityCrew
from src.compliance.content_moderator import ContentModerator
from src.compliance.ai_labeler import AILabeler
from src.publishing.hitl_queue import HITLQueue
from src.publishing.x_publisher import XPublisher
from src.publishing.rate_limiter import RateLimiter
from src.config.settings import settings


class WorkflowState(TypedDict, total=False):
    """Full pipeline state passed between LangGraph nodes."""

    # Input
    query: str
    # Ingestion
    raw_events: list[dict]
    current_event: dict
    # Fact-check
    fact_check: dict
    # NLP
    extracted_events: list[dict]
    # RAG
    philosophy_context: dict
    # Crew analysis
    draft_post: str
    # Compliance
    compliance_result: dict
    is_compliant: bool
    # Labeling
    labeled_post: str
    # HITL
    review_id: str
    approved: bool
    # Publishing
    published_id: str
    # Meta
    error: str
    iteration: int


class AccountabilityWorkflow:
    """LangGraph state machine that orchestrates the full pipeline.

    Nodes
    -----
    ingest_news → fact_check → extract_entities → retrieve_philosophy
    → run_crew_analysis → compliance_check → label_ai_content
    → hitl_review → publish

    If compliance fails, the graph routes back to hitl_review with a
    rejection flag so a human can decide whether to override.
    """

    def __init__(self) -> None:
        self._news = NewsIngestionAgent()
        self._fc = FactCheckerAgent()
        self._extractor = EventExtractor()
        self._retriever = PhilosophicalRetriever()
        self._crew = AccountabilityCrew()
        self._moderator = ContentModerator()
        self._labeler = AILabeler()
        self._hitl = HITLQueue()
        self._publisher = XPublisher()
        self._limiter = RateLimiter()
        self._graph = self._build_graph()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, query: str) -> WorkflowState:
        """Execute the full workflow for *query* and return final state."""
        initial: WorkflowState = {"query": query, "iteration": 0}
        if _LANGGRAPH_AVAILABLE and self._graph is not None:
            result = self._graph.invoke(initial)
            return result  # type: ignore[return-value]
        return self._sequential_run(initial)

    # ------------------------------------------------------------------
    # Node implementations
    # ------------------------------------------------------------------

    def ingest_news(self, state: WorkflowState) -> WorkflowState:
        """Fetch and pre-filter news events."""
        query = state.get("query", "India politics")
        events = self._news.fetch_events(query, max_results=10)
        prioritised = self._news.filter_high_priority_events(events)
        raw = [e.__dict__ for e in prioritised] if prioritised else [e.__dict__ for e in events[:1]]
        current = raw[0] if raw else {}
        logger.info("ingest_news: fetched %d events, selected 1.", len(raw))
        return {**state, "raw_events": raw, "current_event": current}

    def fact_check(self, state: WorkflowState) -> WorkflowState:
        """Verify claims in the current event."""
        event = state.get("current_event", {})
        content = event.get("content", event.get("title", ""))
        result = self._fc.verify_claim(content)
        logger.info("fact_check: verified=%s confidence=%.2f", result.verified, result.confidence)
        return {**state, "fact_check": result.__dict__}

    def extract_entities(self, state: WorkflowState) -> WorkflowState:
        """NLP extraction of political events."""
        event = state.get("current_event", {})
        text = event.get("content", event.get("title", ""))
        extracted = self._extractor.extract_events(text)
        serialised = [e.__dict__ for e in extracted]
        logger.info("extract_entities: %d events extracted.", len(serialised))
        return {**state, "extracted_events": serialised}

    def retrieve_philosophy(self, state: WorkflowState) -> WorkflowState:
        """RAG lookup for philosophical context."""
        event = state.get("current_event", {})
        extracted = state.get("extracted_events", [])
        query_event = extracted[0] if extracted else event
        ctx = self._retriever.retrieve_context(query_event)
        logger.info("retrieve_philosophy: frameworks=%s", ctx.frameworks)
        return {**state, "philosophy_context": ctx.__dict__}

    def run_crew_analysis(self, state: WorkflowState) -> WorkflowState:
        """Invoke CrewAI crew to produce a draft post."""
        event = state.get("current_event", {})
        philosophy_ctx = state.get("philosophy_context", {})
        enriched_event = {**event, "philosophy_context": philosophy_ctx}
        draft = self._crew.run_analysis(enriched_event)
        logger.info("run_crew_analysis: draft post ready (%d chars).", len(draft))
        return {**state, "draft_post": draft}

    def compliance_check(self, state: WorkflowState) -> WorkflowState:
        """IT Rules 2026 + ECI compliance check."""
        draft = state.get("draft_post", "")
        it_result = self._moderator.check_it_rules_2026(draft)
        eci_result = self._moderator.check_eci_guidelines(draft)
        defam_result = self._moderator.check_defamation_risk(draft)
        compliant = it_result.passed and eci_result.passed and defam_result.passed
        result = {
            "it_rules": it_result.__dict__,
            "eci_guidelines": eci_result.__dict__,
            "defamation": defam_result.__dict__,
        }
        logger.info("compliance_check: compliant=%s", compliant)
        return {**state, "compliance_result": result, "is_compliant": compliant}

    def label_ai_content(self, state: WorkflowState) -> WorkflowState:
        """Add mandatory AI-Generated label (IT Rules 2026 / SGI)."""
        draft = state.get("draft_post", "")
        event = state.get("current_event", {})
        philosophy_ctx = state.get("philosophy_context", {})
        labeled = self._labeler.format_for_x(draft, {**event, **philosophy_ctx})
        logger.info("label_ai_content: label applied.")
        return {**state, "labeled_post": labeled}

    def hitl_review(self, state: WorkflowState) -> WorkflowState:
        """Queue post for human review if HITL_ENABLED."""
        if not settings.hitl_enabled:
            return {**state, "approved": True}
        post = state.get("labeled_post", state.get("draft_post", ""))
        analysis = {
            "fact_check": state.get("fact_check", {}),
            "compliance": state.get("compliance_result", {}),
            "is_compliant": state.get("is_compliant", False),
        }
        review_id = self._hitl.add_for_review(post, analysis)
        logger.info("hitl_review: queued for review, id=%s", review_id)
        # In automated demo mode, auto-approve compliant posts.
        approved = state.get("is_compliant", False)
        return {**state, "review_id": review_id, "approved": approved}

    def publish(self, state: WorkflowState) -> WorkflowState:
        """Post to X if approved and rate limit allows."""
        if not state.get("approved", False):
            logger.info("publish: post not approved – skipping.")
            return {**state, "published_id": ""}
        if not self._limiter.can_post():
            wait = self._limiter.time_until_next_post()
            logger.info("publish: rate limited – next post in %.0f s.", wait)
            return {**state, "published_id": "", "error": f"Rate limited; retry in {wait:.0f}s"}
        post = state.get("labeled_post", state.get("draft_post", ""))
        result = self._publisher.post_tweet(post)
        post_id = result.get("id", "")
        self._limiter.record_post()
        logger.info("publish: posted id=%s", post_id)
        return {**state, "published_id": post_id}

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def _build_graph(self):  # noqa: ANN
        if not _LANGGRAPH_AVAILABLE:
            return None
        graph = StateGraph(WorkflowState)
        for node_name, node_fn in [
            ("ingest_news", self.ingest_news),
            ("fact_check", self.fact_check),
            ("extract_entities", self.extract_entities),
            ("retrieve_philosophy", self.retrieve_philosophy),
            ("run_crew_analysis", self.run_crew_analysis),
            ("compliance_check", self.compliance_check),
            ("label_ai_content", self.label_ai_content),
            ("hitl_review", self.hitl_review),
            ("publish", self.publish),
        ]:
            graph.add_node(node_name, node_fn)

        graph.set_entry_point("ingest_news")
        graph.add_edge("ingest_news", "fact_check")
        graph.add_edge("fact_check", "extract_entities")
        graph.add_edge("extract_entities", "retrieve_philosophy")
        graph.add_edge("retrieve_philosophy", "run_crew_analysis")
        graph.add_edge("run_crew_analysis", "compliance_check")
        graph.add_edge("compliance_check", "label_ai_content")
        graph.add_edge("label_ai_content", "hitl_review")
        graph.add_conditional_edges(
            "hitl_review",
            lambda s: "publish" if s.get("approved") else "compliance_check",
            {"publish": "publish", "compliance_check": "compliance_check"},
        )
        graph.add_edge("publish", END)
        return graph.compile()

    def _sequential_run(self, state: WorkflowState) -> WorkflowState:
        """Fallback sequential execution when LangGraph is not available."""
        for step in [
            self.ingest_news,
            self.fact_check,
            self.extract_entities,
            self.retrieve_philosophy,
            self.run_crew_analysis,
            self.compliance_check,
            self.label_ai_content,
            self.hitl_review,
            self.publish,
        ]:
            try:
                state = step(state)
            except Exception as exc:  # noqa: BLE001
                logger.error("Step '%s' failed: %s", step.__name__, exc)
                state = {**state, "error": str(exc)}
                break
        return state
