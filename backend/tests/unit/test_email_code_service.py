from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.schemas.auth import RegisterRequest
from app.services.auth_service import AuthService
from app.services.email_code_service import EmailCodeService


def test_email_code_service_verifies_registration_token(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    service = EmailCodeService(db_session)
    monkeypatch.setattr(service, "_generate_code", lambda: "123456")

    expires = service.send_code(email="verify@example.com", purpose="register")
    assert expires > 0

    token = service.verify_code(email="verify@example.com", purpose="register", code="123456")
    response = AuthService(db_session).register(
        RegisterRequest(email="verify@example.com", password="StrongPass123", verified_token=token)
    )

    assert response.user.email == "verify@example.com"
    assert response.tokens.access_token


def test_email_enabled_registration_requires_code(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMAIL_ENABLED", "true")

    with pytest.raises(ValueError, match="Email verification is required"):
        AuthService(db_session).register(RegisterRequest(email="needs-code@example.com", password="StrongPass123"))


def test_email_code_login_issues_tokens(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    user = AuthService(db_session).register(RegisterRequest(email="login-code@example.com", password="StrongPass123"))
    service = EmailCodeService(db_session)
    monkeypatch.setattr(service, "_generate_code", lambda: "654321")

    service.send_code(email=user.user.email, purpose="login")
    response = AuthService(db_session).login_with_email_code(email=user.user.email, code="654321")

    assert response.user.email == user.user.email
    assert response.tokens.access_token
