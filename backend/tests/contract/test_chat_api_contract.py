from __future__ import annotations

from fastapi.testclient import TestClient


def test_chat_api_contract(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post("/api/chat/message", json={"message": "hello"}, headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert {"conversation_id", "answer", "provider", "model"}.issubset(body)

