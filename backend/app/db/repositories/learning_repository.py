from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.learning_record import LearningRecord


class LearningRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, *, user_id: str, record_type: str, content: str, conversation_id: str | None = None) -> LearningRecord:
        record = LearningRecord(user_id=user_id, record_type=record_type, content=content, conversation_id=conversation_id)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def list_for_user(self, user_id: str) -> list[LearningRecord]:
        return list(self.db.scalars(select(LearningRecord).where(LearningRecord.user_id == user_id)))

