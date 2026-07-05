from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.errors import ProviderError, ProviderErrorType, map_http_error, map_provider_body_error
from app.integrations.embedding.vivo_embedding_provider import VivoEmbeddingProvider
from app.integrations.llm.vivo_llm_provider import VivoLlmProvider
from app.integrations.query_rewrite.vivo_query_rewrite_provider import VivoQueryRewriteProvider
from app.integrations.similarity.vivo_similarity_provider import VivoSimilarityProvider
from app.integrations.vision.vivo_ocr_provider import VivoOcrProvider
from app.schemas.llm import LlmMessage
from tests.integrations.helpers import FakeHttpClient, fake_settings

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "vivo"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_llm_chat_success_contract() -> None:
    provider = VivoLlmProvider(settings=fake_settings(), http_client=FakeHttpClient(json_response=load_fixture("llm_chat_success.json")))
    result = provider.chat([LlmMessage(role="user", content="hello")])

    assert result.content == "EchoLearn is a learning assistant."
    assert result.reasoning_content == "brief reasoning"
    assert result.total_tokens == 10


def test_llm_200_error_body_contract() -> None:
    provider = VivoLlmProvider(
        settings=fake_settings(),
        http_client=FakeHttpClient(json_response=load_fixture("llm_model_unsupported_image_error.json")),
    )

    with pytest.raises(ProviderError) as exc:
        provider.chat([LlmMessage(role="user", content="hello")])

    assert exc.value.error_type == ProviderErrorType.INVALID_REQUEST


def test_ocr_words_and_location_contracts() -> None:
    words_provider = VivoOcrProvider(
        settings=fake_settings(),
        http_client=FakeHttpClient(form_response=load_fixture("ocr_words_success.json")),
    )
    location_provider = VivoOcrProvider(
        settings=fake_settings(),
        http_client=FakeHttpClient(form_response=load_fixture("ocr_location_success.json")),
    )
    asset = Path(__file__).resolve().parents[1] / "assets" / "ocr_test.jpg"

    assert words_provider.recognize(str(asset)).full_text == "取消\n编辑"
    location_result = location_provider.recognize(str(asset))
    assert location_result.blocks[0].bounding_box is not None
    assert location_result.blocks[0].text == "EchoLearn"


def test_embedding_success_and_data_null_contracts() -> None:
    provider = VivoEmbeddingProvider(
        settings=fake_settings(),
        http_client=FakeHttpClient(json_response=load_fixture("embedding_success.json")),
    )
    result = provider.embed(["a", "b"])
    assert result.dimension == 3

    error = map_provider_body_error(load_fixture("embedding_data_null_error.json"), provider="vivo", capability="embedding")
    assert error is not None
    assert error.error_type == ProviderErrorType.PARSE_FAILED


def test_similarity_success_and_mismatch_contracts() -> None:
    provider = VivoSimilarityProvider(
        settings=fake_settings(),
        http_client=FakeHttpClient(json_response=load_fixture("similarity_success.json")),
    )
    assert provider.rerank("q", ["a", "b"]).scores == [-8.067169189453125, -5.946075439453125]

    mismatch_provider = VivoSimilarityProvider(
        settings=fake_settings(),
        http_client=FakeHttpClient(json_response=load_fixture("similarity_count_mismatch_error.json")),
    )
    with pytest.raises(ProviderError) as exc:
        mismatch_provider.rerank("q", ["a", "b"])
    assert exc.value.error_type == ProviderErrorType.PARSE_FAILED


def test_query_rewrite_success_and_provider_unavailable_contracts() -> None:
    provider = VivoQueryRewriteProvider(
        settings=fake_settings(),
        http_client=FakeHttpClient(json_response=load_fixture("query_rewrite_success.json")),
    )
    assert provider.rewrite("第一部里有他吗").rewritten_queries == ["《战狼》第一部里有吴京吗"]

    unavailable = VivoQueryRewriteProvider(
        settings=fake_settings(),
        http_client=FakeHttpClient(json_response=load_fixture("query_rewrite_provider_unavailable.json")),
    )
    with pytest.raises(ProviderError) as exc:
        unavailable.rewrite("第一部里有他吗")
    assert exc.value.error_type == ProviderErrorType.PROVIDER_UNAVAILABLE


def test_http_error_contracts() -> None:
    assert map_http_error(401, load_fixture("http_401_error.json"), provider="vivo", capability="llm").error_type == (
        ProviderErrorType.AUTH_FAILED
    )
    assert map_http_error(429, load_fixture("http_429_error.json"), provider="vivo", capability="llm").error_type == (
        ProviderErrorType.RATE_LIMITED
    )
    body_error = map_provider_body_error(load_fixture("http_200_nonzero_code_error.json"), provider="vivo", capability="media")
    assert body_error is not None
    assert body_error.error_type == ProviderErrorType.UNKNOWN_ERROR
