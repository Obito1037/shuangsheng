from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


TEXT_SUFFIXES = {".txt", ".md", ".docx", ".pdf"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
VOICE_SUFFIXES = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"}


@dataclass(frozen=True, slots=True)
class LearningAssetPlan:
    kind: str
    extractor: str
    cache_policy: str
    rag_ready: bool
    user_visible_status: str


class LearningAssetPipeline:
    """Classifies uploaded learning assets before parsing, caching, indexing, and twin training.

    This is the central contract for the next implementation step:
    upload -> local cache -> modality extraction -> chunks -> embeddings -> twin memory -> learning path.
    It is deliberately strict: unsupported capabilities must stay pending instead of pretending to be complete.
    """

    def plan_for(self, filename: str, content_type: str | None = None) -> LearningAssetPlan:
        suffix = Path(filename).suffix.lower()
        content_type = (content_type or "").lower()
        if suffix in {".txt", ".md", ".docx", ".pdf"} or content_type.startswith("text/"):
            return LearningAssetPlan(
                kind="document",
                extractor="document_text_extractor",
                cache_policy="store_original_and_extracted_text",
                rag_ready=True,
                user_visible_status="可解析为文本并进入 RAG",
            )
        if suffix in IMAGE_SUFFIXES or content_type.startswith("image/"):
            return LearningAssetPlan(
                kind="image",
                extractor="vision_ocr_and_image_understanding",
                cache_policy="store_original_image_and_extracted_text",
                rag_ready=True,
                user_visible_status="需要 OCR / 图像理解后进入 RAG",
            )
        if suffix in VOICE_SUFFIXES or content_type.startswith("audio/"):
            return LearningAssetPlan(
                kind="voice",
                extractor="asr_and_oral_english_scoring",
                cache_policy="store_original_voice_transcript_and_score",
                rag_ready=False,
                user_visible_status="需要语音转写和口语评分后进入 RAG",
            )
        return LearningAssetPlan(
            kind="unknown",
            extractor="unsupported",
            cache_policy="store_original_only",
            rag_ready=False,
            user_visible_status="暂不支持解析，只保留原始文件",
        )
