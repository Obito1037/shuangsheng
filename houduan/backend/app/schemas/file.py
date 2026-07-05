from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str | None = None
    source_type: str = "upload"
    original_name: str
    content_type: str
    size_bytes: int
    status: str
    category: str | None = None
    tags: list[str] = []
    created_at: datetime


class FileUploadResponse(FileRead):
    file: FileRead
    document: DocumentRead | None = None


from app.schemas.document import DocumentRead  # noqa: E402

FileUploadResponse.model_rebuild()
