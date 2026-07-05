from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.conversation import Conversation


class ConversationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, *, user_id: str, title: str) -> Conversation:
        conversation = Conversation(user_id=user_id, title=title)
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def list_for_user(self, user_id: str) -> list[Conversation]:
        return list(self.db.scalars(select(Conversation).where(Conversation.user_id == user_id).order_by(Conversation.created_at.desc())))

    def get_for_user(self, *, user_id: str, conversation_id: str) -> Conversation | None:
        return self.db.scalar(select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user_id))

    def delete(self, conversation: Conversation) -> None:
        self.db.delete(conversation)
        self.db.commit()

