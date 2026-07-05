from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.document_chunk import DocumentChunk
from app.integrations.registry import ProviderRegistry, create_provider_registry


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    source: str
    text: str
    score: float
    score_type: str


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def keyword_score(question: str, text: str) -> float:
    terms = {item for item in re.split(r"\W+", question.lower()) if len(item) >= 2}
    if not terms:
        return 0.0
    lowered = text.lower()
    hits = sum(1 for term in terms if term in lowered)
    return hits / max(1, len(terms))


class RetrievalService:
    """Safe retrieval layer for local cached learning chunks.

    It prefers embedding similarity when both query and chunk embeddings are available.
    If the embedding provider is unavailable or old chunks have no vector, it falls back
    to deterministic keyword retrieval. This keeps chat stable while providers are being
    configured.
    """

    def __init__(self, db: Session, registry: ProviderRegistry | None = None) -> None:
        self.db = db
        self.registry = registry or create_provider_registry()

    def retrieve(self, *, user_id: str, question: str, limit: int = 4, scan_limit: int = 120) -> list[RetrievedChunk]:
        chunks = list(
            self.db.scalars(
                select(DocumentChunk)
                .where(DocumentChunk.user_id == user_id)
                .order_by(DocumentChunk.created_at.desc())
                .limit(scan_limit)
            )
        )
        if not chunks:
            return []
        embedded = self._embedding_rank(question=question, chunks=chunks, limit=limit)
        if embedded:
            return embedded
        return self._keyword_rank(question=question, chunks=chunks, limit=limit)

    def local_context(self, *, user_id: str, question: str, limit: int = 4) -> str:
        retrieved = self.retrieve(user_id=user_id, question=question, limit=limit)
        lines: list[str] = []
        for index, item in enumerate(retrieved, start=1):
            text = item.text.strip().replace("\n", " ")[:700]
            lines.append(f"[{index}] {item.source}（{item.score_type}:{item.score:.3f}）：{text}")
        return "\n".join(lines)

    def _embedding_rank(self, *, question: str, chunks: list[DocumentChunk], limit: int) -> list[RetrievedChunk]:
        vectors: list[tuple[DocumentChunk, list[float]]] = []
        for chunk in chunks:
            if not chunk.embedding_json:
                continue
            try:
                parsed = json.loads(chunk.embedding_json)
            except (TypeError, json.JSONDecodeError):
                continue
            if isinstance(parsed, list) and parsed and all(isinstance(item, (int, float)) for item in parsed):
                vectors.append((chunk, [float(item) for item in parsed]))
        if not vectors:
            return []
        try:
            query_vector = self.registry.get_embedding_provider().embed(question).vectors[0]
        except Exception:
            return []
        ranked = sorted(
            (
                RetrievedChunk(source=chunk.source, text=chunk.text, score=cosine_similarity(query_vector, vector), score_type="embedding")
                for chunk, vector in vectors
            ),
            key=lambda item: item.score,
            reverse=True,
        )
        return [item for item in ranked if item.score > 0][:limit]

    def _keyword_rank(self, *, question: str, chunks: list[DocumentChunk], limit: int) -> list[RetrievedChunk]:
        ranked = sorted(
            (
                RetrievedChunk(source=chunk.source, text=chunk.text, score=keyword_score(question, chunk.text), score_type="keyword")
                for chunk in chunks
            ),
            key=lambda item: item.score,
            reverse=True,
        )
        positives = [item for item in ranked if item.score > 0]
        return (positives or ranked[: min(2, len(ranked))])[:limit]
