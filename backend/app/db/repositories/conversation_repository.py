from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.conversation import Conversation


class ConversationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, *, user_id: str, title: str, twin_id: str | None = None) -> Conversation:
        conversation = Conversation(user_id=user_id, twin_id=twin_id, title=title)
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def list_for_user(self, user_id: str, twin_id: str | None = None) -> list[Conversation]:
        stmt = select(Conversation).where(Conversation.user_id == user_id)
        if twin_id is not None:
            stmt = stmt.where(Conversation.twin_id == twin_id)
        return list(self.db.scalars(stmt.order_by(Conversation.created_at.desc())))

    def get_for_user(self, *, user_id: str, conversation_id: str) -> Conversation | None:
        return self.db.scalar(select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user_id))

    def delete(self, conversation: Conversation) -> None:
        self.db.delete(conversation)
        self.db.commit()

    def save(self, conversation: Conversation) -> Conversation:
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation
