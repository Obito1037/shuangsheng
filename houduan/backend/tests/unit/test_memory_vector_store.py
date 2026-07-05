from __future__ import annotations

import json

from app.db.models.document_chunk import DocumentChunk
from app.services.rag_service import MemoryVectorStore


def test_memory_vector_store_returns_cosine_ranked_matches() -> None:
    chunks = [
        DocumentChunk(user_id="u", document_id="d", chunk_index=0, source="a", text="alpha", embedding_json=json.dumps([1.0, 0.0])),
        DocumentChunk(user_id="u", document_id="d", chunk_index=1, source="b", text="beta", embedding_json=json.dumps([0.0, 1.0])),
    ]

    matches = MemoryVectorStore().search([1.0, 0.0], chunks, top_k=1)
    assert matches[0].chunk.text == "alpha"

