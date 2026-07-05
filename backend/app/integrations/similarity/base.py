from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.similarity import SimilarityResult


class SimilarityProvider(ABC):
    @abstractmethod
    def rerank(self, query: str, sentences: list[str], *, model: str | None = None) -> SimilarityResult:
        raise NotImplementedError

