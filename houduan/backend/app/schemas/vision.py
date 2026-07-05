from __future__ import annotations

from dataclasses import asdict, dataclass

from app.schemas.common import BoundingBox


@dataclass(slots=True)
class OcrBlock:
    text: str
    confidence: float | None
    bounding_box: BoundingBox | None


@dataclass(slots=True)
class OcrResult:
    full_text: str
    blocks: list[OcrBlock]
    angle: int | None
    provider: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class ImageUnderstandingResult:
    description: str
    provider: str
    model: str
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None

    def to_dict(self) -> dict:
        return asdict(self)

