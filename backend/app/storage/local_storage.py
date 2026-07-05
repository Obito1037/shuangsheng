from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.core.config import load_settings
from app.storage.base import StorageBackend


class LocalStorage(StorageBackend):
    def __init__(self, root: str | Path | None = None) -> None:
        settings = load_settings()
        self.root = Path(root or settings.local_storage_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, *, user_id: str, filename: str, content: bytes) -> str:
        safe_name = Path(filename).name
        key = f"{user_id}/{uuid4()}_{safe_name}"
        path = self.resolve_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return key

    def read(self, storage_key: str) -> bytes:
        return self.resolve_path(storage_key).read_bytes()

    def delete(self, storage_key: str) -> None:
        path = self.resolve_path(storage_key)
        if path.exists():
            path.unlink()

    def resolve_path(self, storage_key: str) -> Path:
        path = (self.root / storage_key).resolve()
        root = self.root.resolve()
        if not str(path).startswith(str(root)):
            raise ValueError("Invalid storage key")
        return path

