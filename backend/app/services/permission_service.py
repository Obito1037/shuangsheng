from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.repositories.conversation_repository import ConversationRepository
from app.db.repositories.document_repository import DocumentRepository
from app.db.repositories.file_repository import FileRepository
from app.db.repositories.knowledge_repository import KnowledgeRepository


class PermissionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def require_conversation(self, *, user_id: str, conversation_id: str):
        conversation = ConversationRepository(self.db).get_for_user(user_id=user_id, conversation_id=conversation_id)
        return self._require(conversation)

    def require_file(self, *, user_id: str, file_id: str):
        return self._require(FileRepository(self.db).get_for_user(user_id=user_id, file_id=file_id))

    def require_document(self, *, user_id: str, document_id: str):
        return self._require(DocumentRepository(self.db).get_for_user(user_id=user_id, document_id=document_id))

    def require_knowledge_base(self, *, user_id: str, knowledge_base_id: str):
        return self._require(KnowledgeRepository(self.db).get_for_user(user_id=user_id, knowledge_base_id=knowledge_base_id))

    @staticmethod
    def _require(resource):
        if resource is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
        return resource

