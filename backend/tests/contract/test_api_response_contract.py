from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_contract(client: TestClient) -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_appassets_cors_preflight_contract(client: TestClient) -> None:
    response = client.options(
        "/api/users/me",
        headers={
            "Origin": "https://appassets.androidplatform.net",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://appassets.androidplatform.net"
