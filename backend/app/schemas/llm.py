from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class LlmMessage:
    role: str
    content: str | list[dict[str, Any]]


@dataclass(slots=True)
class LlmMessageResult:
    content: str
    reasoning_content: str | None
    provider: str
    model: str
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    provider_request_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

