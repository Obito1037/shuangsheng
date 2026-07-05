from __future__ import annotations

import pytest

from app.core.config import VivoSettings
from app.core.errors import ProviderError, ProviderErrorType
from app.integrations.llm.vivo_llm_provider import VivoLlmProvider
from app.schemas.llm import LlmMessage
from tests.integrations.helpers import FakeHttpClient


def test_image_understanding_rejects_known_text_only_model() -> None:
    provider = VivoLlmProvider(
        settings=VivoSettings(vivo_app_id="id", vivo_app_key="key", vivo_image_understanding_model="Volc-DeepSeek-V3.2"),
        http_client=FakeHttpClient(),
    )

    with pytest.raises(ProviderError) as exc:
        provider.understand_image("https://example.test/image.jpg", "describe")

    assert exc.value.error_type == ProviderErrorType.INVALID_REQUEST


def test_chat_and_stream_use_independent_model_routes() -> None:
    fake_client = FakeHttpClient(
        json_response={
            "choices": [{"message": {"content": "ok"}}],
            "usage": {},
        },
        stream_lines=['data: {"choices":[{"delta":{"content":"ok"}}]}', "data: [DONE]"],
    )
    provider = VivoLlmProvider(
        settings=VivoSettings(
            vivo_app_id="id",
            vivo_app_key="key",
            vivo_llm_text_model="text-model",
            vivo_llm_stream_model="stream-model",
        ),
        http_client=fake_client,
    )

    provider.chat([LlmMessage(role="user", content="hello")])
    provider.stream_chat([LlmMessage(role="user", content="hello")])

    assert fake_client.calls[0]["payload"]["model"] == "text-model"
    assert fake_client.calls[1]["payload"]["model"] == "stream-model"
