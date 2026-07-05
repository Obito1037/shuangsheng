from __future__ import annotations

import pytest

from app.core.errors import ProviderError, ProviderErrorType
from app.integrations.similarity.vivo_similarity_provider import VivoSimilarityProvider
from app.schemas.similarity import SimilarityResult
from tests.integrations.helpers import FakeHttpClient, fake_settings, missing_settings, real_settings_or_skip


def test_similarity_input_validation_rejects_empty_query() -> None:
    provider = VivoSimilarityProvider(settings=fake_settings(), http_client=FakeHttpClient())
    with pytest.raises(ProviderError) as exc:
        provider.rerank("", ["sentence"])
    assert exc.value.error_type == ProviderErrorType.INVALID_REQUEST


def test_similarity_missing_config_raises_missing_config() -> None:
    provider = VivoSimilarityProvider(settings=missing_settings(), http_client=FakeHttpClient())
    with pytest.raises(ProviderError) as exc:
        provider.rerank("query", ["sentence"])
    assert exc.value.error_type == ProviderErrorType.MISSING_CONFIG


def test_similarity_return_model_fields() -> None:
    provider = VivoSimilarityProvider(
        settings=fake_settings(),
        http_client=FakeHttpClient(json_response={"data": [-8.0, -4.5]}),
    )
    result = provider.rerank("query", ["a", "b"])
    assert isinstance(result, SimilarityResult)
    assert result.scores == [-8.0, -4.5]
    assert result.provider == "vivo"
    assert result.model == "bge-reranker-large"


def test_similarity_error_mapping_for_score_count_mismatch() -> None:
    provider = VivoSimilarityProvider(
        settings=fake_settings(),
        http_client=FakeHttpClient(json_response={"data": [0.1]}),
    )
    with pytest.raises(ProviderError) as exc:
        provider.rerank("query", ["a", "b"])
    assert exc.value.error_type == ProviderErrorType.PARSE_FAILED


def test_similarity_real_api() -> None:
    settings = real_settings_or_skip()
    provider = VivoSimilarityProvider(settings=settings)
    result = provider.rerank("科技品牌发展", ["自动追焦相关报表", "太古汇内云集逾180家知名品牌"])
    assert result.provider == "vivo"
    assert len(result.scores) == 2

