from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class QueryRewriteTurn:
    question: str
    answer: str


@dataclass(slots=True)
class QueryRewriteResult:
    original_query: str
    rewritten_queries: list[str]
    provider: str

    def to_dict(self) -> dict:
        return asdict(self)

