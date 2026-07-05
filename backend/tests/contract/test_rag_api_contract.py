from __future__ import annotations

from fastapi.testclient import TestClient


def test_rag_api_contract(client: TestClient, auth_headers: dict[str, str]) -> None:
    kb = client.post("/api/knowledge-bases", json={"name": "KB"}, headers=auth_headers).json()
    index_response = client.post(
        "/api/rag/index-text",
        json={"knowledge_base_id": kb["id"], "title": "EchoLearn", "text": "EchoLearn helps learners review knowledge."},
        headers=auth_headers,
    )
    assert index_response.status_code == 200
    ask_response = client.post("/api/rag/ask", json={"knowledge_base_id": kb["id"], "question": "What is EchoLearn?"}, headers=auth_headers)
    assert ask_response.status_code == 200
    body = ask_response.json()
    assert {"answer", "references", "rewritten_query", "run_id"}.issubset(body)

