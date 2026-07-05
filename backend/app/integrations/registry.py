from __future__ import annotations

from dataclasses import dataclass

from app.core.config import VivoSettings, load_settings
from app.integrations.capabilities import CapabilityMetadata, build_capability_registry
from app.integrations.embedding.base import EmbeddingProvider
from app.integrations.embedding.vivo_embedding_provider import VivoEmbeddingProvider
from app.integrations.llm.base import LlmProvider
from app.integrations.llm.vivo_llm_provider import VivoLlmProvider
from app.integrations.query_rewrite.base import QueryRewriteProvider
from app.integrations.query_rewrite.vivo_query_rewrite_provider import VivoQueryRewriteProvider
from app.integrations.similarity.base import SimilarityProvider
from app.integrations.similarity.vivo_similarity_provider import VivoSimilarityProvider
from app.integrations.vision.base import OcrProvider
from app.integrations.vision.vivo_ocr_provider import VivoOcrProvider


@dataclass(slots=True)
class ProviderRegistry:
    settings: VivoSettings
    provider_name: str = "vivo"

    def get_llm_provider(self) -> LlmProvider:
        self._ensure_provider("vivo")
        return VivoLlmProvider(settings=self.settings)

    def get_ocr_provider(self) -> OcrProvider:
        self._ensure_provider("vivo")
        return VivoOcrProvider(settings=self.settings)

    def get_embedding_provider(self) -> EmbeddingProvider:
        self._ensure_provider("vivo")
        return VivoEmbeddingProvider(settings=self.settings)

    def get_similarity_provider(self) -> SimilarityProvider:
        self._ensure_provider("vivo")
        return VivoSimilarityProvider(settings=self.settings)

    def get_query_rewrite_provider(self) -> QueryRewriteProvider:
        self._ensure_provider("vivo")
        return VivoQueryRewriteProvider(settings=self.settings)

    def get_capabilities(self) -> dict[str, CapabilityMetadata]:
        return build_capability_registry(self.settings)

    def _ensure_provider(self, supported: str) -> None:
        if self.provider_name != supported:
            raise ValueError(f"Unsupported provider: {self.provider_name}")


def create_provider_registry(
    *,
    settings: VivoSettings | None = None,
    provider_name: str = "vivo",
) -> ProviderRegistry:
    return ProviderRegistry(settings=settings or load_settings(), provider_name=provider_name)


default_registry = create_provider_registry

