from __future__ import annotations

from abc import ABC, abstractmethod


class MediaProvider(ABC):
    @abstractmethod
    def capability_name(self) -> str:
        raise NotImplementedError

