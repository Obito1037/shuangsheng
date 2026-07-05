from __future__ import annotations

import io
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.models.document import Document
from app.db.models.file import FileObject
from app.db.repositories.document_repository import DocumentRepository
from app.schemas.document import DocumentChunkRead, DocumentDetail, DocumentParseRequest, DocumentRead
from app.services.chunk_service import ChunkService
from app.services.file_service import FileService

TEXT_EXTENSIONS = {".txt", ".md"}
DOCX_EXTENSION = ".docx"


class DocumentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.documents = DocumentRepository(db)
        self.files = FileService(db)
        self.chunks = ChunkService()

    def parse(self, *, user_id: str, payload: DocumentParseRequest) -> tuple[Document, int]:
        existing: Document | None = None
        twin_id = payload.twin_id
        if payload.file_id:
            file = self.files.get(user_id=user_id, file_id=payload.file_id)
            existing = self.documents.get_by_file_for_user(user_id=user_id, file_id=file.id)
            if existing and twin_id is None:
                twin_id = existing.twin_id
            try:
                text = self._extract_text(file)
            except ValueError:
                if existing:
                    existing.status = "parse_failed"
                    self.documents.save(existing)
                raise
            title = payload.title or file.original_name
        elif payload.text:
            text = payload.text
            title = payload.title or "Text document"
        else:
            raise ValueError("file_id or text is required")
        if existing:
            existing.title = title
            existing.raw_text = text
            existing.status = "parsed"
            existing.twin_id = twin_id
            document = self.documents.save(existing)
        else:
            document = self.documents.create(
                user_id=user_id,
                title=title,
                raw_text=text,
                file_id=payload.file_id,
                status="parsed",
                twin_id=twin_id,
            )
        chunks = self.chunks.split_text(text)
        for index, chunk in enumerate(chunks):
            self.documents.create_chunk(
                user_id=user_id,
                twin_id=twin_id,
                document_id=document.id,
                chunk_index=index,
                source=title,
                text=chunk,
            )
        return document, len(chunks)

    def register_upload(self, *, user_id: str, file: FileObject, twin_id: str | None = None) -> Document:
        existing = self.documents.get_by_file_for_user(user_id=user_id, file_id=file.id)
        if existing:
            if twin_id and existing.twin_id != twin_id:
                existing.twin_id = twin_id
                return self.documents.save(existing)
            return existing
        return self.documents.create(user_id=user_id, twin_id=twin_id, title=file.original_name, raw_text="", file_id=file.id, status="uploaded")

    def list(self, user_id: str, twin_id: str | None = None) -> list[DocumentRead]:
        return [self._read(document, user_id=user_id) for document in self.documents.list_for_user(user_id, twin_id=twin_id)]

    def detail(self, *, user_id: str, document_id: str) -> DocumentDetail:
        document = self.documents.get_for_user(user_id=user_id, document_id=document_id)
        if not document:
            raise ValueError("Document not found")
        chunks = [
            DocumentChunkRead.model_validate(chunk)
            for chunk in self.documents.list_chunks_for_document(user_id=user_id, document_id=document.id)
        ]
        read = self._read(document, user_id=user_id)
        return DocumentDetail(**read.model_dump(), raw_text=document.raw_text or None, chunks=chunks)

    def _read(self, document: Document, *, user_id: str) -> DocumentRead:
        file: FileObject | None = None
        if document.file_id:
            file = self.files.get(user_id=user_id, file_id=document.file_id)
        return DocumentRead(
            id=document.id,
            twin_id=document.twin_id,
            file_id=document.file_id,
            title=document.title,
            status=document.status,
            parse_status=document.status,
            original_name=file.original_name if file else None,
            content_type=file.content_type if file else None,
            size_bytes=file.size_bytes if file else None,
            created_at=document.created_at,
        )

    def _extract_text(self, file: FileObject) -> str:
        suffix = Path(file.original_name).suffix.lower()
        if suffix in TEXT_EXTENSIONS or file.content_type.startswith("text/"):
            return self.files.read_text(user_id=file.user_id, file_id=file.id)
        if suffix == DOCX_EXTENSION:
            return self._extract_docx_text(file)
        raise ValueError(f"Parsing is not yet supported for {suffix or file.content_type}. Upload was saved.")

    def _extract_docx_text(self, file: FileObject) -> str:
        raw = self.files.read_bytes(user_id=file.user_id, file_id=file.id)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                xml = archive.read("word/document.xml")
        except Exception as exc:
            raise ValueError("Unable to parse docx document") from exc
        root = ET.fromstring(xml)
        paragraphs: list[str] = []
        for paragraph in root.findall(".//w:p", ns):
            text = "".join(node.text or "" for node in paragraph.findall(".//w:t", ns)).strip()
            if text:
                paragraphs.append(text)
        return "\n".join(paragraphs)
