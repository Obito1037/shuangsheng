from __future__ import annotations

import pytest

from app.core.errors import ProviderError, ProviderErrorType
from app.integrations.query_rewrite.vivo_query_rewrite_provider import VivoQueryRewriteProvider
from app.schemas.query_rewrite import QueryRewriteResult, QueryRewriteTurn
from tests.integrations.helpers import FakeHttpClient, fake_settings, missing_settings, real_settings_or_skip


def test_query_rewrite_input_validation_rejects_empty_query() -> None:
    provider = VivoQueryRewriteProvider(settings=fake_settings(), http_client=FakeHttpClient())
    with pytest.raises(ProviderError) as exc:
        provider.rewrite("")
    assert exc.value.error_type == ProviderErrorType.INVALID_REQUEST


def test_query_rewrite_missing_config_raises_missing_config() -> None:
    provider = VivoQueryRewriteProvider(settings=missing_settings(), http_client=FakeHttpClient())
    with pytest.raises(ProviderError) as exc:
        provider.rewrite("第一部里有他吗")
    assert exc.value.error_type == ProviderErrorType.MISSING_CONFIG


def test_query_rewrite_return_model_fields() -> None:
    provider = VivoQueryRewriteProvider(
        settings=fake_settings(),
        http_client=FakeHttpClient(json_response={"code": 0, "result": ["战狼第一部里有吴京吗"]}),
    )
    result = provider.rewrite(
        "第一部里有他吗",
        [QueryRewriteTurn(question="战狼2是谁主演的", answer="吴京")],
    )
    assert isinstance(result, QueryRewriteResult)
    assert result.original_query == "第一部里有他吗"
    assert result.rewritten_queries == ["战狼第一部里有吴京吗"]
    assert result.provider == "vivo"


def test_query_rewrite_error_mapping_for_blocked_query() -> None:
    provider = VivoQueryRewriteProvider(
        settings=fake_settings(),
        http_client=FakeHttpClient(json_response={"code": -4, "result": []}),
    )
    with pytest.raises(ProviderError) as exc:
        provider.rewrite("第一部里有他吗")
    assert exc.value.error_type == ProviderErrorType.CONTENT_BLOCKED


def test_query_rewrite_no_rewrite_code_is_normal() -> None:
    provider = VivoQueryRewriteProvider(
        settings=fake_settings(),
        http_client=FakeHttpClient(json_response={"code": -9, "result": []}),
    )
    result = provider.rewrite("今天天气怎么样")
    assert result.rewritten_queries == ["今天天气怎么样"]


def test_query_rewrite_real_api() -> None:
    settings = real_settings_or_skip()
    provider = VivoQueryRewriteProvider(settings=settings)
    try:
        result = provider.rewrite(
            "第一部里有他吗",
            [QueryRewriteTurn(question="战狼2是谁主演的", answer="《战狼2》由吴京主演。")],
        )
    except ProviderError as exc:
        if exc.error_type == ProviderErrorType.PROVIDER_UNAVAILABLE:
            pytest.skip(f"query rewrite provider unavailable: {exc.raw_error}")
        raise
    assert result.provider == "vivo"
    assert isinstance(result.rewritten_queries, list)
