from __future__ import annotations

from app.core.config import VivoSettings
from app.integrations.capabilities import build_capability_registry
from app.integrations.fakes import (
    FakeEmbeddingProvider,
    FakeLlmProvider,
    FakeOcrProvider,
    FakeQueryRewriteProvider,
    FakeSimilarityProvider,
)
from app.integrations.registry import create_provider_registry
from app.schemas.llm import LlmMessage


def test_provider_registry_returns_abstract_provider_instances() -> None:
    registry = create_provider_registry(settings=VivoSettings(vivo_app_id="id", vivo_app_key="key"))

    assert registry.get_llm_provider().__class__.__name__ == "VivoLlmProvider"
    assert registry.get_ocr_provider().__class__.__name__ == "VivoOcrProvider"
    assert registry.get_embedding_provider().__class__.__name__ == "VivoEmbeddingProvider"
    assert registry.get_similarity_provider().__class__.__name__ == "VivoSimilarityProvider"
    assert registry.get_query_rewrite_provider().__class__.__name__ == "VivoQueryRewriteProvider"


def test_capability_registry_records_required_metadata() -> None:
    settings = VivoSettings(
        vivo_app_id="id",
        vivo_app_key="key",
        vivo_llm_text_model="text-model",
        vivo_llm_stream_model="stream-model",
        vivo_image_understanding_model="image-model",
    )
    capabilities = build_capability_registry(settings)

    assert capabilities["llm_chat"].default_model == "text-model"
    assert capabilities["llm_stream_chat"].supports_streaming is True
    assert capabilities["image_understanding"].supports_image is True
    assert capabilities["query_rewrite"].provider_unavailable is True
    assert capabilities["android_side_llm"].android_side is True
    assert capabilities["text_translation"].documented_only is True


def test_fake_providers_match_business_facing_interfaces() -> None:
    llm = FakeLlmProvider()
    assert llm.chat([LlmMessage(role="user", content="hello")]).provider == "fake"
    assert llm.stream_chat([LlmMessage(role="user", content="hello")]).content
    assert llm.understand_image("fake.jpg", "describe").description

    assert FakeOcrProvider().recognize("fake.jpg").full_text
    assert FakeEmbeddingProvider().embed(["a", "b"]).dimension == 2
    assert FakeSimilarityProvider().rerank("q", ["a", "b"]).scores == [0.0, 0.0]
    assert FakeQueryRewriteProvider().rewrite("q").rewritten_queries == ["q"]

