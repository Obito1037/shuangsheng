from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.file import FileObject


class FileRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, *, user_id: str, original_name: str, storage_key: str, content_type: str, size_bytes: int) -> FileObject:
        file = FileObject(
            user_id=user_id,
            original_name=original_name,
            storage_key=storage_key,
            content_type=content_type,
            size_bytes=size_bytes,
        )
        self.db.add(file)
        self.db.commit()
        self.db.refresh(file)
        return file

    def list_for_user(self, user_id: str) -> list[FileObject]:
        return list(self.db.scalars(select(FileObject).where(FileObject.user_id == user_id).order_by(FileObject.created_at.desc())))

    def get_for_user(self, *, user_id: str, file_id: str) -> FileObject | None:
        return self.db.scalar(select(FileObject).where(FileObject.id == file_id, FileObject.user_id == user_id))

    def delete(self, file: FileObject) -> None:
        self.db.delete(file)
        self.db.commit()

