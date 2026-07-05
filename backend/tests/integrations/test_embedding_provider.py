from __future__ import annotations

import pytest

from app.core.errors import ProviderError, ProviderErrorType
from app.integrations.embedding.vivo_embedding_provider import VivoEmbeddingProvider
from app.schemas.embedding import EmbeddingResult
from tests.integrations.helpers import FakeHttpClient, fake_settings, missing_settings, real_settings_or_skip


def test_embedding_input_validation_rejects_empty_text() -> None:
    provider = VivoEmbeddingProvider(settings=fake_settings(), http_client=FakeHttpClient())
    with pytest.raises(ProviderError) as exc:
        provider.embed("")
    assert exc.value.error_type == ProviderErrorType.INVALID_REQUEST


def test_embedding_missing_config_raises_missing_config() -> None:
    provider = VivoEmbeddingProvider(settings=missing_settings(), http_client=FakeHttpClient())
    with pytest.raises(ProviderError) as exc:
        provider.embed("EchoLearn")
    assert exc.value.error_type == ProviderErrorType.MISSING_CONFIG


def test_embedding_return_model_fields() -> None:
    provider = VivoEmbeddingProvider(
        settings=fake_settings(),
        http_client=FakeHttpClient(json_response={"data": [[0.1, 0.2], [0.3, 0.4]]}),
    )
    result = provider.embed(["alpha", "beta"])
    assert isinstance(result, EmbeddingResult)
    assert result.texts == ["alpha", "beta"]
    assert result.dimension == 2
    assert result.provider == "vivo"
    assert result.model == "m3e-base"


def test_embedding_error_mapping_for_inconsistent_dimensions() -> None:
    provider = VivoEmbeddingProvider(
        settings=fake_settings(),
        http_client=FakeHttpClient(json_response={"data": [[0.1], [0.2, 0.3]]}),
    )
    with pytest.raises(ProviderError) as exc:
        provider.embed(["alpha", "beta"])
    assert exc.value.error_type == ProviderErrorType.PARSE_FAILED


def test_embedding_real_api() -> None:
    settings = real_settings_or_skip()
    provider = VivoEmbeddingProvider(settings=settings)
    result = provider.embed(["豫章故郡，洪都新府", "星分翼轸，地接衡庐"])
    assert result.provider == "vivo"
    assert len(result.vectors) == 2
    assert result.dimension > 0

