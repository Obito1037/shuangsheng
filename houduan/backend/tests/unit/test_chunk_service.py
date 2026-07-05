from __future__ import annotations

from app.services.chunk_service import ChunkService


def test_chunk_service_cleans_and_splits_text() -> None:
    service = ChunkService()
    chunks = service.split_text(" hello\n\nworld " * 80, chunk_size=80, overlap=10)

    assert chunks
    assert all("\n" not in chunk for chunk in chunks)
    assert len(chunks[0]) <= 80

