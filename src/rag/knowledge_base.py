"""Vector knowledge base for philosophical texts with Redis or in-memory fallback."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Literal

import numpy as np

logger = logging.getLogger(__name__)

PhilosophyCategory = Literal[
    "justice", "deontology", "utilitarianism", "virtue", "liberty"
]

# ---------------------------------------------------------------------------
# Sample public-domain philosophical excerpts bundled for demo / offline use.
# ---------------------------------------------------------------------------
_GUTENBERG_SAMPLES: list[dict] = [
    {
        "text": (
            "Act only according to that maxim whereby you can at the same time "
            "will that it should become a universal law. – Kant, Groundwork (1785)"
        ),
        "philosopher": "Immanuel Kant",
        "work": "Groundwork of the Metaphysics of Morals",
        "category": "deontology",
    },
    {
        "text": (
            "The greatest happiness of the greatest number is the foundation of "
            "morals and legislation. – Bentham, Introduction to the Principles (1789)"
        ),
        "philosopher": "Jeremy Bentham",
        "work": "Introduction to the Principles of Morals and Legislation",
        "category": "utilitarianism",
    },
    {
        "text": (
            "It is better to be Socrates dissatisfied than a fool satisfied. "
            "– J.S. Mill, Utilitarianism (1863)"
        ),
        "philosopher": "John Stuart Mill",
        "work": "Utilitarianism",
        "category": "utilitarianism",
    },
    {
        "text": (
            "The liberty of man in society is to be under no other legislative "
            "power but that established by consent. – Locke, Two Treatises (1689)"
        ),
        "philosopher": "John Locke",
        "work": "Two Treatises of Government",
        "category": "liberty",
    },
    {
        "text": (
            "Justice is the first virtue of social institutions, as truth is of "
            "systems of thought. – Rawls, A Theory of Justice (1971)"
        ),
        "philosopher": "John Rawls",
        "work": "A Theory of Justice",
        "category": "justice",
    },
    {
        "text": (
            "The end justifies the means – a prince must know how to use both "
            "the beast and the man. – Machiavelli, The Prince (1532)"
        ),
        "philosopher": "Niccolò Machiavelli",
        "work": "The Prince",
        "category": "virtue",
    },
    {
        "text": (
            "Courage is not simply one of the virtues, but the form of every "
            "virtue at the testing point. – C.S. Lewis, The Screwtape Letters (1942)"
        ),
        "philosopher": "C.S. Lewis",
        "work": "The Screwtape Letters",
        "category": "virtue",
    },
    {
        "text": (
            "The worst form of inequality is to try to make unequal things equal. "
            "– Aristotle, Politics"
        ),
        "philosopher": "Aristotle",
        "work": "Politics",
        "category": "justice",
    },
]


@dataclass
class PhilosophicalChunk:
    """A chunk of philosophical text with metadata."""

    id: str
    text: str
    philosopher: str
    work: str
    category: PhilosophyCategory
    embedding: list[float] = field(default_factory=list, repr=False)


class KnowledgeBase:
    """Manages philosophical text chunks with vector search.

    Uses sentence-transformers for embeddings. Persists to Redis when available;
    otherwise keeps an in-memory store.
    """

    def __init__(self) -> None:
        self._store: list[PhilosophicalChunk] = []
        self._model = self._load_embedding_model()
        self._redis = self._connect_redis()
        # Seed with bundled texts on first instantiation.
        if not self._store:
            self.build_from_gutenberg_samples()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ingest_philosophical_text(
        self, text: str, metadata: dict
    ) -> None:
        """Embed *text* and store it with *metadata*."""
        chunk = PhilosophicalChunk(
            id=str(uuid.uuid4()),
            text=text,
            philosopher=metadata.get("philosopher", "Unknown"),
            work=metadata.get("work", "Unknown"),
            category=metadata.get("category", "justice"),
            embedding=self._embed(text),
        )
        self._store.append(chunk)
        self._persist(chunk)

    def build_from_gutenberg_samples(self) -> None:
        """Ingest the bundled public-domain philosophical excerpts."""
        for sample in _GUTENBERG_SAMPLES:
            text = sample["text"]
            # Skip if already loaded (idempotent).
            if any(c.text == text for c in self._store):
                continue
            self.ingest_philosophical_text(
                text,
                {
                    "philosopher": sample["philosopher"],
                    "work": sample["work"],
                    "category": sample["category"],
                },
            )
        logger.info("Knowledge base built with %d chunks.", len(self._store))

    def semantic_search(
        self, query: str, top_k: int = 5
    ) -> list[PhilosophicalChunk]:
        """Return the *top_k* most relevant chunks for *query*."""
        if not self._store:
            return []
        q_emb = np.array(self._embed(query))
        scored: list[tuple[float, PhilosophicalChunk]] = []
        for chunk in self._store:
            c_emb = np.array(chunk.embedding)
            if c_emb.shape != q_emb.shape or np.linalg.norm(c_emb) == 0:
                continue
            cos_sim = float(
                np.dot(q_emb, c_emb)
                / (np.linalg.norm(q_emb) * np.linalg.norm(c_emb) + 1e-9)
            )
            scored.append((cos_sim, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:top_k]]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_embedding_model():  # noqa: ANN
        try:
            from sentence_transformers import SentenceTransformer

            return SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as exc:  # noqa: BLE001
            logger.warning("sentence-transformers unavailable (%s). Using TF-IDF.", exc)
            return None

    @staticmethod
    def _connect_redis():  # noqa: ANN
        try:
            from src.config.settings import settings
            import redis

            client = redis.Redis.from_url(
                f"{settings.redis_url}:{settings.redis_port}"
            )
            client.ping()
            return client
        except Exception:  # noqa: BLE001
            return None

    def _embed(self, text: str) -> list[float]:
        if self._model is not None:
            return self._model.encode(text).tolist()  # type: ignore[no-any-return]
        # TF-IDF fallback: bag-of-words character n-gram vector.
        return self._tfidf_embed(text)

    @staticmethod
    def _tfidf_embed(text: str, dim: int = 64) -> list[float]:
        """Very lightweight hash-based embedding for offline fallback."""
        vec = [0.0] * dim
        words = text.lower().split()
        for w in words:
            idx = hash(w) % dim
            vec[idx] += 1.0
        norm = sum(v ** 2 for v in vec) ** 0.5
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    def _persist(self, chunk: PhilosophicalChunk) -> None:
        if self._redis is None:
            return
        try:
            import json

            self._redis.set(
                f"phil:{chunk.id}",
                json.dumps(
                    {
                        "text": chunk.text,
                        "philosopher": chunk.philosopher,
                        "work": chunk.work,
                        "category": chunk.category,
                    }
                ),
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("Redis persist failed: %s", exc)
