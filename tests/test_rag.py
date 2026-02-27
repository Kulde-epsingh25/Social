"""Unit tests for RAG modules."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.rag.knowledge_base import KnowledgeBase, PhilosophicalChunk
from src.rag.philosophical_retriever import PhilosophicalRetriever, PhilosophicalContext


class TestKnowledgeBase:
    def setup_method(self):
        # Avoid hitting real Redis / sentence-transformers in tests
        with patch.object(KnowledgeBase, "_connect_redis", return_value=None), \
             patch.object(KnowledgeBase, "_load_embedding_model", return_value=None):
            self.kb = KnowledgeBase.__new__(KnowledgeBase)
            self.kb._store = []
            self.kb._model = None
            self.kb._redis = None
            self.kb.build_from_gutenberg_samples()

    def test_build_from_gutenberg_samples_populates_store(self):
        assert len(self.kb._store) > 0

    def test_ingest_philosophical_text_adds_to_store(self):
        initial = len(self.kb._store)
        self.kb.ingest_philosophical_text(
            "Justice is blind.",
            {"philosopher": "Test", "work": "Test Work", "category": "justice"},
        )
        assert len(self.kb._store) == initial + 1

    def test_semantic_search_returns_list(self):
        results = self.kb.semantic_search("justice and equality", top_k=3)
        assert isinstance(results, list)
        assert all(isinstance(r, PhilosophicalChunk) for r in results)

    def test_semantic_search_respects_top_k(self):
        results = self.kb.semantic_search("freedom liberty rights", top_k=2)
        assert len(results) <= 2

    def test_semantic_search_empty_store_returns_empty(self):
        with patch.object(KnowledgeBase, "_connect_redis", return_value=None), \
             patch.object(KnowledgeBase, "_load_embedding_model", return_value=None):
            kb = KnowledgeBase.__new__(KnowledgeBase)
            kb._store = []
            kb._model = None
            kb._redis = None
            results = kb.semantic_search("test query")
            assert results == []

    def test_tfidf_embed_returns_correct_length(self):
        vec = KnowledgeBase._tfidf_embed("test sentence for embedding", dim=64)
        assert len(vec) == 64

    def test_chunk_has_required_fields(self):
        chunk = self.kb._store[0]
        assert chunk.id
        assert chunk.text
        assert chunk.philosopher
        assert chunk.work
        assert chunk.category in (
            "justice", "deontology", "utilitarianism", "virtue", "liberty"
        )


class TestPhilosophicalRetriever:
    def setup_method(self):
        with patch.object(KnowledgeBase, "_connect_redis", return_value=None), \
             patch.object(KnowledgeBase, "_load_embedding_model", return_value=None):
            kb = KnowledgeBase.__new__(KnowledgeBase)
            kb._store = []
            kb._model = None
            kb._redis = None
            kb.build_from_gutenberg_samples()
        self.retriever = PhilosophicalRetriever(knowledge_base=kb)

    def test_retrieve_context_returns_context(self):
        ctx = self.retriever.retrieve_context(
            {"actor": "Minister", "action": "accepted bribe", "target": "contractor"}
        )
        assert isinstance(ctx, PhilosophicalContext)

    def test_retrieve_context_has_passages(self):
        ctx = self.retriever.retrieve_context({"description": "corruption in government"})
        assert isinstance(ctx.relevant_passages, list)

    def test_apply_framework_kantian(self):
        result = self.retriever.apply_framework(
            {"actor": "MP", "action": "voted against transparency bill"},
            "kantian",
        )
        assert "kantian" in result.lower() or "kant" in result.lower()

    def test_apply_framework_unknown(self):
        result = self.retriever.apply_framework({}, "obscure_framework")
        assert isinstance(result, str)

    def test_bridge_is_ought_returns_dict(self):
        result = self.retriever.bridge_is_ought(
            {"actor": "CM", "action": "diverted funds", "location": "Delhi"}
        )
        assert "normative_conclusions" in result
        assert "descriptive_facts" in result
