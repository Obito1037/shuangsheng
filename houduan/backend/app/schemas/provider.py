from __future__ import annotations

from dataclasses import asdict
from typing import Any, Protocol


class EchoLearnSchema(Protocol):
    def to_dict(self) -> dict[str, Any]:
        ...


def schema_to_dict(schema: Any) -> dict[str, Any]:
    if hasattr(schema, "to_dict"):
        return schema.to_dict()
    return asdict(schema)

