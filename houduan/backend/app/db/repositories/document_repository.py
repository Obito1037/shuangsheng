from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.document import Document
from app.db.models.document_chunk import DocumentChunk


class DocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, *, user_id: str, title: str, raw_text: str, file_id: str | None = None, status: str = "parsed") -> Document:
        document = Document(user_id=user_id, title=title, raw_text=raw_text, file_id=file_id, status=status)
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    def save(self, document: Document) -> Document:
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    def list_for_user(self, user_id: str) -> list[Document]:
        return list(self.db.scalars(select(Document).where(Document.user_id == user_id).order_by(Document.created_at.desc())))

    def get_for_user(self, *, user_id: str, document_id: str) -> Document | None:
        return self.db.scalar(select(Document).where(Document.id == document_id, Document.user_id == user_id))

    def get_by_file_for_user(self, *, user_id: str, file_id: str) -> Document | None:
        return self.db.scalar(select(Document).where(Document.file_id == file_id, Document.user_id == user_id))

    def create_chunk(
        self,
        *,
        user_id: str,
        document_id: str,
        chunk_index: int,
        source: str,
        text: str,
        knowledge_base_id: str | None = None,
        embedding_json: str | None = None,
    ) -> DocumentChunk:
        chunk = DocumentChunk(
            user_id=user_id,
            document_id=document_id,
            chunk_index=chunk_index,
            source=source,
            text=text,
            knowledge_base_id=knowledge_base_id,
            embedding_json=embedding_json,
        )
        self.db.add(chunk)
        self.db.commit()
        self.db.refresh(chunk)
        return chunk

    def list_chunks(self, *, user_id: str, knowledge_base_id: str | None = None) -> list[DocumentChunk]:
        stmt = select(DocumentChunk).where(DocumentChunk.user_id == user_id)
        if knowledge_base_id:
            stmt = stmt.where(DocumentChunk.knowledge_base_id == knowledge_base_id)
        return list(self.db.scalars(stmt.order_by(DocumentChunk.created_at.asc())))

    def list_chunks_for_document(self, *, user_id: str, document_id: str) -> list[DocumentChunk]:
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.user_id == user_id, DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        return list(self.db.scalars(stmt))
