from __future__ import annotations

from fastapi.testclient import TestClient


def test_auth_api_contract(client: TestClient) -> None:
    response = client.post("/api/auth/register", json={"email": "contract@example.com", "password": "StrongPass123"})
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"user", "tokens"}
    assert body["tokens"]["token_type"] == "bearer"

