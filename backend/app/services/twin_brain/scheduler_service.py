from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.learning_twin import LearningTwin
from app.db.models.twin_brain import KnowledgePoint, MasteryState, Mistake
from app.schemas.twin_brain import ReviewQueueItemRead


class ReviewSchedulerService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def review_queue(self, *, user_id: str, twin_id: str, limit: int = 12) -> list[ReviewQueueItemRead]:
        self._require_twin(user_id=user_id, twin_id=twin_id)
        items: list[ReviewQueueItemRead] = []
        now = datetime.now(UTC)
        rows = list(
            self.db.execute(
                select(MasteryState, KnowledgePoint)
                .join(KnowledgePoint, KnowledgePoint.id == MasteryState.kp_id)
                .where(MasteryState.user_id == user_id, MasteryState.twin_id == twin_id)
            )
        )
        for state, kp in rows:
            retention = self._retention(state, now=now)
            due = bool(state.due_at and self._aware(state.due_at) <= now) or retention < 0.9
            if not due and state.p_mastery >= 0.6:
                continue
            priority = (1.0 - retention) + max(0.0, 0.6 - state.p_mastery) + min(0.25, state.attempt_count * 0.02)
            items.append(
                ReviewQueueItemRead(
                    id=f"kp:{kp.id}",
                    type="knowledge_point",
                    title=kp.name,
                    detail=f"掌握 {round(state.p_mastery * 100)}% · 记忆保持率 {round(retention * 100)}%",
                    priority=round(priority, 4),
                    retention=round(retention, 4),
                    due_at=state.due_at,
                    kp_id=kp.id,
                    action="完成 1 道复测题或用自己的话复述该知识点。",
                )
            )
        mistakes = list(
            self.db.scalars(
                select(Mistake)
                .where(Mistake.user_id == user_id, Mistake.twin_id == twin_id, Mistake.status.in_(["open", "reviewing"]))
                .order_by(Mistake.created_at.desc())
            )
        )
        for mistake in mistakes:
            question_id = mistake.question_id
            priority = 0.9 if mistake.status == "open" else 0.65
            items.append(
                ReviewQueueItemRead(
                    id=f"mistake:{mistake.id}",
                    type="mistake",
                    title=(mistake.source_text or "错题复盘")[:60],
                    detail=f"{mistake.error_type} · {mistake.status}",
                    priority=priority,
                    mistake_id=mistake.id,
                    question_id=question_id,
                    action="复盘错因，完成同源变式题后再标记 resolved。",
                )
            )
        items.sort(key=lambda item: item.priority, reverse=True)
        return items[: max(1, min(limit, 50))]

    def _retention(self, state: MasteryState, *, now: datetime) -> float:
        if not state.last_review_at:
            return 0.0
        last = self._aware(state.last_review_at)
        days = max(0.0, (now - last).total_seconds() / 86400.0)
        stability = max(0.1, state.stability or 1.0)
        return max(0.0, min(1.0, (1.0 + days / (9.0 * stability)) ** -1))

    def _aware(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def _require_twin(self, *, user_id: str, twin_id: str) -> LearningTwin:
        twin = self.db.scalar(select(LearningTwin).where(LearningTwin.user_id == user_id, LearningTwin.id == twin_id))
        if not twin:
            raise ValueError("Learning twin not found")
        return twin
