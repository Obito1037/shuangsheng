from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.embedding import EmbeddingResult


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: str | list[str], *, model: str | None = None) -> EmbeddingResult:
        raise NotImplementedError

