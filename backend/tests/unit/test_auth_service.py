from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.db.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.auth_service import AuthService


def test_auth_service_register_hashes_password(db_session: Session) -> None:
    result = AuthService(db_session).register(RegisterRequest(email="new@example.com", password="StrongPass123", display_name="New"))
    user = UserRepository(db_session).get_by_id(result.user.id)

    assert user is not None
    assert user.password_hash != "StrongPass123"
    assert verify_password("StrongPass123", user.password_hash)
    assert result.tokens.access_token
    assert result.tokens.refresh_token


def test_auth_service_rejects_bad_login(db_session: Session) -> None:
    service = AuthService(db_session)
    service.register(RegisterRequest(email="new@example.com", password="StrongPass123", display_name="New"))

    with pytest.raises(ValueError):
        service.login(LoginRequest(email="new@example.com", password="wrong"))

