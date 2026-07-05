from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models.knowledge_base import KnowledgeBase
from app.db.repositories.knowledge_repository import KnowledgeRepository


class KnowledgeService:
    def __init__(self, db: Session) -> None:
        self.repository = KnowledgeRepository(db)

    def create(self, *, user_id: str, name: str, description: str | None = None) -> KnowledgeBase:
        return self.repository.create(user_id=user_id, name=name, description=description)

    def list(self, user_id: str) -> list[KnowledgeBase]:
        return self.repository.list_for_user(user_id)

