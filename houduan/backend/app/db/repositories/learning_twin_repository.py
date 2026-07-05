from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.learning_twin import LearningTwin


class LearningTwinRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, user_id: str) -> list[LearningTwin]:
        statement = select(LearningTwin).where(LearningTwin.user_id == user_id).order_by(LearningTwin.updated_at.desc())
        return list(self.db.scalars(statement))

    def get(self, *, user_id: str, twin_id: str) -> LearningTwin | None:
        statement = select(LearningTwin).where(LearningTwin.user_id == user_id, LearningTwin.id == twin_id)
        return self.db.scalar(statement)

    def create(
        self,
        *,
        user_id: str,
        name: str,
        subject: str,
        goal: str,
        stage: str,
        status: str,
        sync_percent: int,
        memories_json: str,
        route_snapshot_json: str = "{}",
        outputs_json: str = "[]",
    ) -> LearningTwin:
        twin = LearningTwin(
            user_id=user_id,
            name=name,
            subject=subject,
            goal=goal,
            stage=stage,
            status=status,
            sync_percent=sync_percent,
            memories_json=memories_json,
            route_snapshot_json=route_snapshot_json,
            outputs_json=outputs_json,
        )
        self.db.add(twin)
        self.db.commit()
        self.db.refresh(twin)
        return twin

    def save(self, twin: LearningTwin) -> LearningTwin:
        self.db.add(twin)
        self.db.commit()
        self.db.refresh(twin)
        return twin

    def delete(self, twin: LearningTwin) -> None:
        self.db.delete(twin)
        self.db.commit()
