from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.usage_record import UsageRecord


class UsageRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        user_id: str,
        capability: str,
        provider: str,
        model: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        total_tokens: int | None = None,
    ) -> UsageRecord:
        record = UsageRecord(
            user_id=user_id,
            capability=capability,
            provider=provider,
            model=model,
            input_tokens=input_tokens or 0,
            output_tokens=output_tokens or 0,
            total_tokens=total_tokens or 0,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def list_for_user(self, user_id: str) -> list[UsageRecord]:
        return list(self.db.scalars(select(UsageRecord).where(UsageRecord.user_id == user_id).order_by(UsageRecord.created_at.desc())))

    def total_tokens_for_user(self, user_id: str) -> int:
        value = self.db.scalar(select(func.coalesce(func.sum(UsageRecord.total_tokens), 0)).where(UsageRecord.user_id == user_id))
        return int(value or 0)

