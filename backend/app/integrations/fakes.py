from __future__ import annotations

from app.integrations.embedding.base import EmbeddingProvider
from app.integrations.llm.base import LlmProvider
from app.integrations.query_rewrite.base import QueryRewriteProvider
from app.integrations.similarity.base import SimilarityProvider
from app.integrations.vision.base import OcrProvider
from app.schemas.common import BoundingBox
from app.schemas.embedding import EmbeddingResult
from app.schemas.llm import LlmMessage, LlmMessageResult
from app.schemas.query_rewrite import QueryRewriteResult, QueryRewriteTurn
from app.schemas.similarity import SimilarityResult
from app.schemas.vision import ImageUnderstandingResult, OcrBlock, OcrResult


class FakeLlmProvider(LlmProvider):
    def chat(self, messages: list[LlmMessage], **kwargs: object) -> LlmMessageResult:
        return LlmMessageResult(
            content="fake llm response",
            reasoning_content=None,
            provider="fake",
            model=str(kwargs.get("model", "fake-chat")),
            input_tokens=1,
            output_tokens=1,
            total_tokens=2,
            provider_request_id="fake-request",
        )

    def stream_chat(self, messages: list[LlmMessage], **kwargs: object) -> LlmMessageResult:
        return self.chat(messages, model=kwargs.get("model", "fake-stream"))

    def understand_image(self, image: str, prompt: str, **kwargs: object) -> ImageUnderstandingResult:
        return ImageUnderstandingResult(
            description="fake image description",
            provider="fake",
            model=str(kwargs.get("model", "fake-vision")),
            input_tokens=1,
            output_tokens=1,
            total_tokens=2,
        )


class FakeOcrProvider(OcrProvider):
    def recognize(self, image_path: str, *, pos: int = 2) -> OcrResult:
        return OcrResult(
            full_text="fake ocr text",
            blocks=[
                OcrBlock(
                    text="fake ocr text",
                    confidence=1.0,
                    bounding_box=BoundingBox(x_min=0, y_min=0, x_max=1, y_max=1),
                )
            ],
            angle=0,
            provider="fake",
        )


class FakeEmbeddingProvider(EmbeddingProvider):
    def embed(self, texts: str | list[str], *, model: str | None = None) -> EmbeddingResult:
        normalized = [texts] if isinstance(texts, str) else texts
        return EmbeddingResult(
            texts=normalized,
            vectors=[[1.0, 0.0] for _ in normalized],
            dimension=2,
            provider="fake",
            model=model or "fake-embedding",
        )


class FakeSimilarityProvider(SimilarityProvider):
    def rerank(self, query: str, sentences: list[str], *, model: str | None = None) -> SimilarityResult:
        return SimilarityResult(
            query=query,
            sentences=sentences,
            scores=[0.0 for _ in sentences],
            provider="fake",
            model=model or "fake-rerank",
        )


class FakeQueryRewriteProvider(QueryRewriteProvider):
    def rewrite(self, query: str, history: list[QueryRewriteTurn] | None = None) -> QueryRewriteResult:
        return QueryRewriteResult(
            original_query=query,
            rewritten_queries=[query],
            provider="fake",
        )

