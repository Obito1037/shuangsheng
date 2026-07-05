from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class SpeechCapabilityRecord:
    capability: str
    provider: str
    implemented: bool
    note: str

    def to_dict(self) -> dict:
        return asdict(self)

