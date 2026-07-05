from __future__ import annotations

from fastapi.testclient import TestClient


def test_rag_flow_index_and_ask(client: TestClient, auth_headers: dict[str, str]) -> None:
    kb = client.post("/api/knowledge-bases", json={"name": "Learning KB"}, headers=auth_headers)
    assert kb.status_code == 200
    knowledge_base_id = kb.json()["id"]

    indexed = client.post(
        "/api/rag/index-text",
        json={
            "knowledge_base_id": knowledge_base_id,
            "title": "EchoLearn notes",
            "text": "EchoLearn supports retrieval augmented learning with references.",
        },
        headers=auth_headers,
    )
    assert indexed.status_code == 200
    assert indexed.json()["chunks"] >= 1

    answer = client.post(
        "/api/rag/ask",
        json={"knowledge_base_id": knowledge_base_id, "question": "What does EchoLearn support?"},
        headers=auth_headers,
    )
    assert answer.status_code == 200
    assert answer.json()["answer"]
    assert answer.json()["references"]

