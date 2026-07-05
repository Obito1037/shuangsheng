from __future__ import annotations

import io
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.models.document import Document
from app.db.models.file import FileObject
from app.schemas.document import DocumentParseRequest
from app.services.document_service import DocumentService
from app.services.learning_asset_pipeline import LearningAssetPipeline


class EnhancedDocumentService(DocumentService):
    """DocumentService extension for the real learning-asset pipeline.

    It keeps the existing database contract but adds PDF text extraction and strict pending
    errors for modalities that need provider configuration before entering RAG.
    """

    def __init__(self, db: Session) -> None:
        super().__init__(db)
        self.pipeline = LearningAssetPipeline()

    def parse(self, *, user_id: str, payload: DocumentParseRequest) -> tuple[Document, int]:
        if not payload.file_id:
            return super().parse(user_id=user_id, payload=payload)
        file = self.files.get(user_id=user_id, file_id=payload.file_id)
        plan = self.pipeline.plan_for(file.original_name, file.content_type)
        if plan.kind == "voice":
            self._mark_parse_failed(user_id=user_id, file=file)
            raise ValueError("voice_asr_pending: audio was cached, but ASR and oral English scoring are not configured yet")
        if plan.kind == "image":
            self._mark_parse_failed(user_id=user_id, file=file)
            raise ValueError("image_ocr_pending: image was cached, but OCR/image understanding must be configured before RAG indexing")
        return super().parse(user_id=user_id, payload=payload)

    def _extract_text(self, file: FileObject) -> str:
        suffix = Path(file.original_name).suffix.lower()
        if suffix == ".pdf" or (file.content_type or "").lower() == "application/pdf":
            return self._extract_pdf_text(file)
        return super()._extract_text(file)

    def _extract_pdf_text(self, file: FileObject) -> str:
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ValueError("pdf_parser_missing: install backend requirements to parse PDFs") from exc
        raw = self.files.read_bytes(user_id=file.user_id, file_id=file.id)
        try:
            reader = PdfReader(io.BytesIO(raw))
            pages = [page.extract_text() or "" for page in reader.pages]
        except Exception as exc:
            raise ValueError("pdf_parse_failed: unable to extract text from this PDF") from exc
        text = "\n\n".join(page.strip() for page in pages if page.strip())
        if not text.strip():
            raise ValueError("pdf_text_empty: scanned PDFs require OCR before entering RAG")
        return text

    def _mark_parse_failed(self, *, user_id: str, file: FileObject) -> None:
        existing = self.documents.get_by_file_for_user(user_id=user_id, file_id=file.id)
        if existing:
            existing.status = "parse_pending"
            self.documents.save(existing)
