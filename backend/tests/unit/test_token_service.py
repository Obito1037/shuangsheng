from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.schemas.auth import RegisterRequest
from app.services.auth_service import AuthService
from app.services.token_service import TokenService


def test_refresh_token_can_be_rotated_and_revoked(db_session: Session) -> None:
    auth = AuthService(db_session).register(RegisterRequest(email="token@example.com", password="StrongPass123"))
    service = TokenService(db_session)

    rotated = service.refresh(auth.tokens.refresh_token)
    assert rotated.access_token
    assert rotated.refresh_token != auth.tokens.refresh_token

    with pytest.raises(ValueError):
        service.refresh(auth.tokens.refresh_token)

    service.revoke(rotated.refresh_token)
    with pytest.raises(ValueError):
        service.refresh(rotated.refresh_token)

