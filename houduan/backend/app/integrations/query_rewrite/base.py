from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.query_rewrite import QueryRewriteResult, QueryRewriteTurn


class QueryRewriteProvider(ABC):
    @abstractmethod
    def rewrite(self, query: str, history: list[QueryRewriteTurn] | None = None) -> QueryRewriteResult:
        raise NotImplementedError

