from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.deps import get_provider_registry
from app.core.errors import ProviderError, ProviderErrorType
from app.main import app
from app.schemas.llm import LlmMessage, LlmMessageResult


class FailingLlmProviderForTests:
    def chat(self, messages: list[LlmMessage], **kwargs: object) -> LlmMessageResult:
        raise ProviderError(
            provider="fake",
            capability="llm_chat",
            error_type=ProviderErrorType.TIMEOUT,
            safe_message="Provider timed out.",
        )

    def stream_chat(self, messages: list[LlmMessage], **kwargs: object) -> LlmMessageResult:
        raise ProviderError(
            provider="fake",
            capability="llm_stream_chat",
            error_type=ProviderErrorType.TIMEOUT,
            safe_message="Provider timed out.",
        )


class FailingProviderRegistryForTests:
    def get_llm_provider(self) -> FailingLlmProviderForTests:
        return FailingLlmProviderForTests()


def test_chat_flow_create_conversation_send_and_list(client: TestClient, auth_headers: dict[str, str]) -> None:
    conversation = client.post("/api/conversations", json={"title": "Study"}, headers=auth_headers)
    assert conversation.status_code == 200
    conversation_id = conversation.json()["id"]

    chat = client.post(
        "/api/chat/message",
        json={"conversation_id": conversation_id, "message": "Explain spaced repetition"},
        headers=auth_headers,
    )
    assert chat.status_code == 200
    assert chat.json()["answer"]

    detail = client.get(f"/api/conversations/{conversation_id}", headers=auth_headers)
    assert detail.status_code == 200
    assert len(detail.json()["messages"]) == 2

    usage = client.get("/api/usage/me", headers=auth_headers)
    assert usage.status_code == 200
    assert usage.json()["records"] >= 1


def test_chat_message_uses_learning_twin_fallback_when_llm_fails(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    app.dependency_overrides[get_provider_registry] = lambda: FailingProviderRegistryForTests()

    chat = client.post(
        "/api/chat/message",
        json={"message": "我数据库 GROUP BY 总是错，下一步怎么学？"},
        headers=auth_headers,
    )

    assert chat.status_code == 200
    body = chat.json()
    assert body["provider"] == "echolearn"
    assert body["model"] == "learning-twin-fallback"
    assert "学习分身" in body["answer"]
    assert "RAG" in body["answer"]

    detail = client.get(f"/api/conversations/{body['conversation_id']}", headers=auth_headers)
    assert detail.status_code == 200
    messages = detail.json()["messages"]
    assert [message["role"] for message in messages] == ["user", "assistant"]
