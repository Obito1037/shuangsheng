from __future__ import annotations

from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import load_settings
from app.db.models.file import FileObject
from app.db.repositories.file_repository import FileRepository
from app.services.permission_service import PermissionService
from app.storage.base import StorageBackend
from app.storage.local_storage import LocalStorage


class FileService:
    def __init__(self, db: Session, storage: StorageBackend | None = None) -> None:
        self.db = db
        self.files = FileRepository(db)
        self.permissions = PermissionService(db)
        self.storage = storage or LocalStorage()
        self.settings = load_settings()

    async def upload(self, *, user_id: str, upload: UploadFile) -> FileObject:
        content = await upload.read()
        self._validate(upload.filename or "upload.bin", content)
        storage_key = self.storage.save(user_id=user_id, filename=upload.filename or "upload.bin", content=content)
        return self.files.create(
            user_id=user_id,
            original_name=upload.filename or "upload.bin",
            storage_key=storage_key,
            content_type=upload.content_type or "application/octet-stream",
            size_bytes=len(content),
        )

    def list(self, user_id: str) -> list[FileObject]:
        return self.files.list_for_user(user_id)

    def get(self, *, user_id: str, file_id: str) -> FileObject:
        return self.permissions.require_file(user_id=user_id, file_id=file_id)

    def read_text(self, *, user_id: str, file_id: str) -> str:
        file = self.get(user_id=user_id, file_id=file_id)
        content = self.storage.read(file.storage_key)
        return content.decode("utf-8", errors="ignore")

    def read_bytes(self, *, user_id: str, file_id: str) -> bytes:
        file = self.get(user_id=user_id, file_id=file_id)
        return self.storage.read(file.storage_key)

    def delete(self, *, user_id: str, file_id: str) -> None:
        file = self.get(user_id=user_id, file_id=file_id)
        self.storage.delete(file.storage_key)
        self.files.delete(file)

    def _validate(self, filename: str, content: bytes) -> None:
        if len(content) > self.settings.max_upload_bytes:
            raise ValueError("File too large")
        suffix = Path(filename).suffix.lower()
        allowed = {item.strip().lower() for item in self.settings.allowed_upload_extensions.split(",")}
        if suffix not in allowed:
            raise ValueError("Unsupported file type")
