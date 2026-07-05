from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentParseRequest(BaseModel):
    file_id: str | None = None
    text: str | None = None
    title: str | None = None
    twin_id: str | None = None


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    twin_id: str | None = None
    file_id: str | None = None
    title: str
    status: str
    parse_status: str | None = None
    source_type: str = "document"
    original_name: str | None = None
    content_type: str | None = None
    size_bytes: int | None = None
    category: str | None = None
    tags: list[str] = []
    created_at: datetime


class DocumentChunkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    twin_id: str | None = None
    document_id: str
    chunk_index: int
    source: str
    text: str


class DocumentDetail(DocumentRead):
    raw_text: str | None = None
    chunks: list[DocumentChunkRead] = []
