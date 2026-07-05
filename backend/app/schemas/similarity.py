from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class SimilarityResult:
    query: str
    sentences: list[str]
    scores: list[float]
    provider: str
    model: str

    def to_dict(self) -> dict:
        return asdict(self)

