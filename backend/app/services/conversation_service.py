from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models.conversation import Conversation
from app.db.repositories.conversation_repository import ConversationRepository
from app.db.repositories.message_repository import MessageRepository
from app.services.permission_service import PermissionService


class ConversationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.conversations = ConversationRepository(db)
        self.messages = MessageRepository(db)
        self.permissions = PermissionService(db)

    def create(self, *, user_id: str, title: str) -> Conversation:
        return self.conversations.create(user_id=user_id, title=title)

    def list(self, user_id: str) -> list[Conversation]:
        return self.conversations.list_for_user(user_id)

    def detail(self, *, user_id: str, conversation_id: str):
        conversation = self.permissions.require_conversation(user_id=user_id, conversation_id=conversation_id)
        messages = self.messages.list_for_conversation(user_id=user_id, conversation_id=conversation_id)
        return conversation, messages

    def delete(self, *, user_id: str, conversation_id: str) -> None:
        conversation = self.permissions.require_conversation(user_id=user_id, conversation_id=conversation_id)
        self.conversations.delete(conversation)

