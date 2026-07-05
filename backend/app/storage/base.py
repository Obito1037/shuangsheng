from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class StorageBackend(ABC):
    @abstractmethod
    def save(self, *, user_id: str, filename: str, content: bytes) -> str:
        raise NotImplementedError

    @abstractmethod
    def read(self, storage_key: str) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def delete(self, storage_key: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def resolve_path(self, storage_key: str) -> Path:
        raise NotImplementedError

