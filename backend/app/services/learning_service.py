from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models.learning_record import LearningRecord
from app.db.repositories.learning_repository import LearningRepository


class LearningService:
    def __init__(self, db: Session) -> None:
        self.repository = LearningRepository(db)

    def record(self, *, user_id: str, record_type: str, content: str, conversation_id: str | None = None) -> LearningRecord:
        return self.repository.create(user_id=user_id, record_type=record_type, content=content, conversation_id=conversation_id)

    def list(self, user_id: str) -> list[LearningRecord]:
        return self.repository.list_for_user(user_id)

