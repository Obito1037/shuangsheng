from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.repositories.conversation_repository import ConversationRepository
from app.schemas.auth import RegisterRequest
from app.services.auth_service import AuthService
from app.services.permission_service import PermissionService


def test_permission_service_enforces_resource_ownership(db_session: Session) -> None:
    user_a = AuthService(db_session).register(RegisterRequest(email="a@example.com", password="StrongPass123")).user
    user_b = AuthService(db_session).register(RegisterRequest(email="b@example.com", password="StrongPass123")).user
    conversation = ConversationRepository(db_session).create(user_id=user_a.id, title="A")

    assert PermissionService(db_session).require_conversation(user_id=user_a.id, conversation_id=conversation.id).id == conversation.id
    with pytest.raises(HTTPException):
        PermissionService(db_session).require_conversation(user_id=user_b.id, conversation_id=conversation.id)

