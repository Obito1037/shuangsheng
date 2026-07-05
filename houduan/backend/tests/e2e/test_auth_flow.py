from __future__ import annotations

from fastapi.testclient import TestClient


def test_auth_flow_register_login_refresh_logout(client: TestClient) -> None:
    register = client.post("/api/auth/register", json={"email": "flow@example.com", "password": "StrongPass123"})
    assert register.status_code == 200
    refresh_token = register.json()["tokens"]["refresh_token"]

    login = client.post("/api/auth/login", json={"email": "flow@example.com", "password": "StrongPass123"})
    assert login.status_code == 200
    access_token = login.json()["tokens"]["access_token"]

    me = client.get("/api/users/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "flow@example.com"

    refreshed = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert refreshed.status_code == 200

    logout = client.post("/api/auth/logout", json={"refresh_token": refreshed.json()["refresh_token"]})
    assert logout.status_code == 200


def test_auth_login_accepts_account_password_contract(client: TestClient) -> None:
    register = client.post(
        "/api/auth/register",
        json={"email": "account-login@example.com", "password": "StrongPass123", "display_name": "Account Login"},
    )
    assert register.status_code == 200

    login = client.post(
        "/api/auth/login",
        json={
            "login_type": "password",
            "account": "account-login@example.com",
            "password": "StrongPass123",
            "device": {"platform": "android-webview", "app_version": "1.0.0"},
        },
    )
    assert login.status_code == 200
    body = login.json()
    assert body["user"]["email"] == "account-login@example.com"
    assert body["user"]["phone"] is None
    assert body["tokens"]["expires_in"] > 0


def test_auth_error_uses_stable_error_shape(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"login_type": "password", "account": "missing@example.com", "password": "bad-password"},
    )
    assert response.status_code == 401
    assert response.json() == {
        "code": "AUTH_INVALID_CREDENTIALS",
        "message": "Invalid email or password",
        "detail": None,
        "fields": None,
    }
