from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.message import Message


class MessageRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        user_id: str,
        conversation_id: str,
        role: str,
        content: str,
        provider: str | None = None,
        model: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        total_tokens: int | None = None,
    ) -> Message:
        message = Message(
            user_id=user_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def list_for_conversation(self, *, user_id: str, conversation_id: str) -> list[Message]:
        return list(
            self.db.scalars(
                select(Message)
                .where(Message.user_id == user_id, Message.conversation_id == conversation_id)
                .order_by(Message.created_at.asc())
            )
        )

