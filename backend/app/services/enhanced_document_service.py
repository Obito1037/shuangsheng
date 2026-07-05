from __future__ import annotations

import io
import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.models.document import Document
from app.db.models.file import FileObject
from app.integrations.registry import ProviderRegistry, create_provider_registry
from app.schemas.document import DocumentParseRequest
from app.services.document_service import DocumentService
from app.services.learning_asset_pipeline import LearningAssetPipeline
from app.services.twin_brain.knowledge_graph import KnowledgeGraphService

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
logger = logging.getLogger(__name__)


class EnhancedDocumentService(DocumentService):
    """DocumentService extension for the real learning-asset pipeline.

    It keeps the existing database contract and adds PDF extraction, image OCR, and
    best-effort embedding. Modalities that require unavailable providers stay pending
    instead of being marked as completed.
    """

    def __init__(self, db: Session, registry: ProviderRegistry | None = None) -> None:
        super().__init__(db)
        self.pipeline = LearningAssetPipeline()
        self.registry = registry or create_provider_registry()

    def parse(self, *, user_id: str, payload: DocumentParseRequest) -> tuple[Document, int]:
        if payload.file_id:
            file = self.files.get(user_id=user_id, file_id=payload.file_id)
            plan = self.pipeline.plan_for(file.original_name, file.content_type)
            if plan.kind == "voice":
                self._mark_parse_pending(user_id=user_id, file=file)
                raise ValueError("voice_asr_pending: audio was cached, but speech recognition and English scoring are not configured yet")
        document, chunk_count = super().parse(user_id=user_id, payload=payload)
        self._embed_document_chunks(user_id=user_id, document_id=document.id)
        try:
            KnowledgeGraphService(self.db).extract_from_document(user_id=user_id, twin_id=document.twin_id, document_id=document.id)
        except Exception:
            # Knowledge extraction is an M1 profile enrichment step. A failure here
            # must not turn a real parse into a fake success or a false failure.
            logger.exception("Knowledge extraction failed for document_id=%s", document.id)
        return document, chunk_count

    def _extract_text(self, file: FileObject) -> str:
        suffix = Path(file.original_name).suffix.lower()
        content_type = (file.content_type or "").lower()
        if suffix == ".pdf" or content_type == "application/pdf":
            return self._extract_pdf_text(file)
        if suffix in IMAGE_SUFFIXES or content_type.startswith("image/"):
            return self._extract_image_text(file)
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

    def _extract_image_text(self, file: FileObject) -> str:
        storage = self.files.storage
        if not hasattr(storage, "resolve_path"):
            raise ValueError("image_path_unavailable: OCR requires local cached image path")
        image_path = str(storage.resolve_path(file.storage_key))
        errors: list[str] = []
        try:
            result = self.registry.get_ocr_provider().recognize(image_path)
            if result.full_text.strip():
                return result.full_text
            errors.append("ocr_empty")
        except Exception as exc:
            logger.warning("OCR provider failed for file_id=%s: %s", file.id, exc)
            errors.append("ocr_failed")
        try:
            understood = self.registry.get_llm_provider().understand_image(
                image_path,
                (
                    "请尽可能识别这张学习资料图片里的手写或印刷文字、公式、题目和解题步骤。"
                    "保留原有换行；如果无法逐字识别，也要给出可信的内容转写或结构化描述。"
                    "只输出可进入学习资料库的内容，不要寒暄。"
                ),
                temperature=0.1,
                max_tokens=1200,
            )
            if understood.description.strip():
                return understood.description.strip()
            errors.append("image_understanding_empty")
        except Exception as exc:
            logger.warning("Image understanding provider failed for file_id=%s: %s", file.id, exc)
            errors.append("image_understanding_failed")
        self._mark_parse_pending(user_id=file.user_id, file=file)
        raise ValueError(f"image_recognition_pending: {'/'.join(errors) or 'no_provider_result'}")

    def _embed_document_chunks(self, *, user_id: str, document_id: str) -> None:
        chunks = self.documents.list_chunks_for_document(user_id=user_id, document_id=document_id)
        missing = [chunk for chunk in chunks if not chunk.embedding_json]
        if not missing:
            return
        try:
            vectors = self.registry.get_embedding_provider().embed([chunk.text for chunk in missing]).vectors
        except Exception:
            return
        for chunk, vector in zip(missing, vectors, strict=False):
            chunk.embedding_json = json.dumps(vector)
            self.db.add(chunk)
        self.db.commit()

    def _mark_parse_pending(self, *, user_id: str, file: FileObject) -> None:
        existing = self.documents.get_by_file_for_user(user_id=user_id, file_id=file.id)
        if existing:
            existing.status = "parse_pending"
            self.documents.save(existing)
