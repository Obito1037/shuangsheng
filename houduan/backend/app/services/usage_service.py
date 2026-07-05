from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.repositories.usage_repository import UsageRepository
from app.schemas.usage import UsageSummary


class UsageService:
    def __init__(self, db: Session) -> None:
        self.repository = UsageRepository(db)

    def record(
        self,
        *,
        user_id: str,
        capability: str,
        provider: str,
        model: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        total_tokens: int | None = None,
    ) -> None:
        self.repository.create(
            user_id=user_id,
            capability=capability,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )

    def summary(self, user_id: str) -> UsageSummary:
        records = self.repository.list_for_user(user_id)
        return UsageSummary(total_tokens=self.repository.total_tokens_for_user(user_id), records=len(records))

