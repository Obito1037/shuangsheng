from __future__ import annotations

from pathlib import Path

import pytest

from app.core.errors import ProviderError, ProviderErrorType
from app.integrations.llm.vivo_llm_provider import VivoLlmProvider
from app.schemas.llm import LlmMessage, LlmMessageResult
from app.schemas.vision import ImageUnderstandingResult
from tests.integrations.helpers import FakeHttpClient, fake_settings, missing_settings, real_settings_or_skip

ASSET_DIR = Path(__file__).resolve().parents[1] / "assets"


def test_llm_input_validation_rejects_empty_messages() -> None:
    provider = VivoLlmProvider(settings=fake_settings(), http_client=FakeHttpClient())
    with pytest.raises(ProviderError) as exc:
        provider.chat([])
    assert exc.value.error_type == ProviderErrorType.INVALID_REQUEST


def test_llm_missing_config_raises_missing_config() -> None:
    provider = VivoLlmProvider(settings=missing_settings(), http_client=FakeHttpClient())
    with pytest.raises(ProviderError) as exc:
        provider.chat([LlmMessage(role="user", content="hello")])
    assert exc.value.error_type == ProviderErrorType.MISSING_CONFIG


def test_llm_return_model_fields() -> None:
    fake_client = FakeHttpClient(
        json_response={
            "choices": [{"message": {"content": "hi", "reasoning_content": "think"}}],
            "usage": {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
        }
    )
    provider = VivoLlmProvider(settings=fake_settings(), http_client=fake_client)
    result = provider.chat([LlmMessage(role="user", content="hello")])
    assert isinstance(result, LlmMessageResult)
    assert result.content == "hi"
    assert result.reasoning_content == "think"
    assert result.provider == "vivo"
    assert result.input_tokens == 2
    assert result.output_tokens == 3
    assert result.total_tokens == 5
    assert result.provider_request_id


def test_llm_payload_disables_thinking_by_default() -> None:
    fake_client = FakeHttpClient(json_response={"choices": [{"message": {"content": "hi"}}]})
    provider = VivoLlmProvider(settings=fake_settings(), http_client=fake_client)
    provider.chat([LlmMessage(role="user", content="hello")])
    assert fake_client.calls[0]["payload"]["enable_thinking"] is False


def test_llm_payload_respects_explicit_thinking_flag() -> None:
    fake_client = FakeHttpClient(json_response={"choices": [{"message": {"content": "hi"}}]})
    provider = VivoLlmProvider(settings=fake_settings(), http_client=fake_client)
    provider.chat([LlmMessage(role="user", content="hello")], enable_thinking=True)
    assert fake_client.calls[0]["payload"]["enable_thinking"] is True


def test_llm_stream_return_model_fields() -> None:
    fake_client = FakeHttpClient(
        stream_lines=[
            'data: {"choices":[{"delta":{"reasoning_content":"r"}}]}',
            'data: {"choices":[{"delta":{"content":"h"}}]}',
            'data: {"choices":[{"delta":{"content":"i"}}],"usage":{"prompt_tokens":1,"completion_tokens":2,"total_tokens":3}}',
            "data: [DONE]",
        ]
    )
    provider = VivoLlmProvider(settings=fake_settings(), http_client=fake_client)
    result = provider.stream_chat([LlmMessage(role="user", content="hello")])
    assert result.content == "hi"
    assert result.reasoning_content == "r"
    assert result.total_tokens == 3


def test_image_understanding_return_model_fields() -> None:
    fake_client = FakeHttpClient(
        json_response={
            "choices": [{"message": {"content": "A card with EchoLearn text."}}],
            "usage": {"prompt_tokens": 4, "completion_tokens": 5, "total_tokens": 9},
        }
    )
    provider = VivoLlmProvider(settings=fake_settings(), http_client=fake_client)
    result = provider.understand_image(str(ASSET_DIR / "image_understanding_test.jpg"), "Describe it.")
    assert isinstance(result, ImageUnderstandingResult)
    assert result.description == "A card with EchoLearn text."
    assert result.provider == "vivo"
    assert result.input_tokens == 4


def test_llm_error_mapping_for_bad_response_shape() -> None:
    provider = VivoLlmProvider(settings=fake_settings(), http_client=FakeHttpClient(json_response={"bad": "shape"}))
    with pytest.raises(ProviderError) as exc:
        provider.chat([LlmMessage(role="user", content="hello")])
    assert exc.value.error_type == ProviderErrorType.PARSE_FAILED


def test_llm_empty_content_is_not_success() -> None:
    fake_client = FakeHttpClient(
        json_response={
            "choices": [{"finish_reason": "length", "message": {"content": "", "reasoning_content": "thinking"}}],
        }
    )
    provider = VivoLlmProvider(settings=fake_settings(), http_client=fake_client)
    with pytest.raises(ProviderError) as exc:
        provider.chat([LlmMessage(role="user", content="hello")])
    assert exc.value.error_type == ProviderErrorType.PARSE_FAILED


def test_llm_real_api_sync_stream_and_image_understanding() -> None:
    settings = real_settings_or_skip()
    provider = VivoLlmProvider(settings=settings)
    sync_result = provider.chat([LlmMessage(role="user", content="用一句话介绍 EchoLearn。")], max_tokens=80)
    assert sync_result.provider == "vivo"
    assert sync_result.content
    stream_result = provider.stream_chat([LlmMessage(role="user", content="用四个字回复：学习助手")], max_tokens=40)
    assert stream_result.provider == "vivo"
    assert stream_result.content
    image_result = provider.understand_image(
        str(ASSET_DIR / "image_understanding_test.jpg"),
        "用一句话描述图片内容。",
        model="Doubao-Seed-2.0-mini",
    )
    assert image_result.provider == "vivo"
    assert image_result.description
