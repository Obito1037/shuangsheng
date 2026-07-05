from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class MediaCapabilityRecord:
    capability: str
    provider: str
    implemented: bool
    note: str

    def to_dict(self) -> dict:
        return asdict(self)

