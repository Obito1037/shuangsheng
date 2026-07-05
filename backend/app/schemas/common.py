from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class BoundingBox:
    x_min: float | None = None
    y_min: float | None = None
    x_max: float | None = None
    y_max: float | None = None
    points: dict[str, dict[str, float]] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ProviderUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None

