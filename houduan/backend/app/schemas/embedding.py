from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class EmbeddingResult:
    texts: list[str]
    vectors: list[list[float]]
    dimension: int
    provider: str
    model: str

    def to_dict(self) -> dict:
        return asdict(self)

