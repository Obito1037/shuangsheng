from __future__ import annotations

from abc import ABC, abstractmethod


class SpeechProvider(ABC):
    @abstractmethod
    def capability_name(self) -> str:
        raise NotImplementedError

