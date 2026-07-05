from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.knowledge_base import KnowledgeBase
from app.db.models.rag_reference import RagReference
from app.db.models.rag_run import RagRun


class KnowledgeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, *, user_id: str, name: str, description: str | None = None) -> KnowledgeBase:
        kb = KnowledgeBase(user_id=user_id, name=name, description=description)
        self.db.add(kb)
        self.db.commit()
        self.db.refresh(kb)
        return kb

    def list_for_user(self, user_id: str) -> list[KnowledgeBase]:
        statement = select(KnowledgeBase).where(KnowledgeBase.user_id == user_id).order_by(KnowledgeBase.created_at.desc())
        return list(self.db.scalars(statement))

    def get_for_user(self, *, user_id: str, knowledge_base_id: str) -> KnowledgeBase | None:
        return self.db.scalar(select(KnowledgeBase).where(KnowledgeBase.id == knowledge_base_id, KnowledgeBase.user_id == user_id))

    def create_rag_run(
        self,
        *,
        user_id: str,
        knowledge_base_id: str,
        question: str,
        rewritten_query: str,
        answer: str,
        provider: str | None = None,
        model: str | None = None,
        total_tokens: int | None = None,
    ) -> RagRun:
        run = RagRun(
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
            question=question,
            rewritten_query=rewritten_query,
            answer=answer,
            provider=provider,
            model=model,
            total_tokens=total_tokens,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def create_rag_reference(
        self,
        *,
        rag_run_id: str,
        chunk_id: str,
        source: str,
        text: str,
        rank: int,
        score: float | None = None,
    ) -> RagReference:
        reference = RagReference(rag_run_id=rag_run_id, chunk_id=chunk_id, source=source, text=text, rank=rank, score=score)
        self.db.add(reference)
        self.db.commit()
        self.db.refresh(reference)
        return reference
