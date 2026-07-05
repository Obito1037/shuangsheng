from __future__ import annotations

import json
from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.learning_twin import LearningTwin
from app.db.models.twin_brain import Attempt, KnowledgePoint, MasteryState, Mistake
from app.schemas.twin_brain import ErrorDistributionRead, MasteryPointRead, MistakeRead, TwinProfileResponse


class TwinProfileService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_profile(self, *, user_id: str, twin_id: str) -> TwinProfileResponse:
        twin = self.db.scalar(select(LearningTwin).where(LearningTwin.user_id == user_id, LearningTwin.id == twin_id))
        if not twin:
            raise ValueError("Learning twin not found")
        mastery = self._mastery_points(user_id=user_id, twin_id=twin_id)
        attempts_used = int(
            self.db.scalar(select(func.count()).select_from(Attempt).where(Attempt.user_id == user_id, Attempt.twin_id == twin_id)) or 0
        )
        mistakes = list(
            self.db.scalars(
                select(Mistake)
                .where(Mistake.user_id == user_id, Mistake.twin_id == twin_id)
                .order_by(Mistake.created_at.desc())
                .limit(5)
            )
        )
        distribution = self._error_distribution(user_id=user_id, twin_id=twin_id)
        xp = max(twin.xp or 0, attempts_used * 8 + sum(item.correct_count for item in mastery) * 2)
        level = max(twin.level or 1, 1 + xp // 120)
        sync_percent = self._sync_percent(mastery=mastery, attempts_used=attempts_used, twin=twin)
        if twin.xp != xp or twin.level != level or twin.sync_percent != sync_percent:
            twin.xp = xp
            twin.level = level
            twin.sync_percent = sync_percent
            self.db.add(twin)
            self.db.commit()
            self.db.refresh(twin)
        weak_points = [item for item in mastery if item.p_mastery < 0.6]
        weak_points.sort(key=lambda item: (item.p_mastery, -item.attempt_count))
        return TwinProfileResponse(
            twin_id=twin.id,
            level=level,
            xp=xp,
            sync_percent=sync_percent,
            evidence_mode="真实画像" if attempts_used >= 10 else "启动方案",
            attempts_used=attempts_used,
            mastery=mastery,
            weak_points=weak_points[:6],
            error_distribution=distribution,
            recent_mistakes=[self._mistake_read(item) for item in mistakes],
            next_actions=self._next_actions(mastery=mastery, attempts_used=attempts_used, mistakes=mistakes),
        )

    def _mastery_points(self, *, user_id: str, twin_id: str) -> list[MasteryPointRead]:
        rows = list(
            self.db.execute(
                select(KnowledgePoint, MasteryState)
                .join(
                    MasteryState,
                    (MasteryState.kp_id == KnowledgePoint.id)
                    & (MasteryState.user_id == KnowledgePoint.user_id)
                    & (MasteryState.twin_id == KnowledgePoint.twin_id),
                    isouter=True,
                )
                .where(KnowledgePoint.user_id == user_id, KnowledgePoint.twin_id == twin_id)
                .order_by(KnowledgePoint.created_at.asc())
            )
        )
        points: list[MasteryPointRead] = []
        for kp, state in rows:
            p_mastery = state.p_mastery if state else 0.25
            attempt_count = state.attempt_count if state else 0
            correct_count = state.correct_count if state else 0
            points.append(
                MasteryPointRead(
                    kp_id=kp.id,
                    name=kp.name,
                    subject=kp.subject,
                    p_mastery=round(p_mastery, 4),
                    ability_elo=round(state.ability_elo if state else 1200.0, 2),
                    stability=round(state.stability if state else 1.0, 2),
                    difficulty_fsrs=round(state.difficulty_fsrs if state else 5.0, 2),
                    attempt_count=attempt_count,
                    correct_count=correct_count,
                    due_at=state.due_at if state else None,
                    status=self._mastery_status(p_mastery=p_mastery, attempt_count=attempt_count),
                )
            )
        points.sort(key=lambda item: (item.p_mastery, item.attempt_count))
        return points

    def _error_distribution(self, *, user_id: str, twin_id: str) -> list[ErrorDistributionRead]:
        mistakes = list(self.db.scalars(select(Mistake).where(Mistake.user_id == user_id, Mistake.twin_id == twin_id)))
        counts = Counter(item.error_type or "待标注" for item in mistakes)
        return [ErrorDistributionRead(error_type=name, count=count) for name, count in counts.most_common()]

    def _sync_percent(self, *, mastery: list[MasteryPointRead], attempts_used: int, twin: LearningTwin) -> int:
        if not mastery:
            return min(twin.sync_percent or 0, 35)
        covered = sum(1 for item in mastery if item.attempt_count > 0)
        avg_mastery = sum(item.p_mastery for item in mastery) / len(mastery)
        coverage = covered / len(mastery)
        return max(twin.sync_percent or 0, min(100, round(25 + coverage * 35 + avg_mastery * 30 + min(10, attempts_used))))

    def _next_actions(self, *, mastery: list[MasteryPointRead], attempts_used: int, mistakes: list[Mistake]) -> list[str]:
        if not mastery:
            return ["上传一份资料或输入一道题，先建立知识点坐标。", "当前为启动方案：画像还没有足够证据。"]
        if attempts_used < 5:
            return ["先完成 5 道诊断/自评题，让 BKT 和 Elo 有第一批真实数据。", "错题会自动进入错题本并更新错因分布。"]
        weak = [item.name for item in mastery if item.p_mastery < 0.6][:3]
        actions = [f"优先练习：{'、'.join(weak)}。" if weak else "当前没有明显薄弱 KP，适合用变式题探测能力边界。"]
        if mistakes:
            actions.append("复盘最近错题，并把状态从 open 推进到 reviewing/resolved。")
        return actions

    def _mastery_status(self, *, p_mastery: float, attempt_count: int) -> str:
        if attempt_count == 0:
            return "new"
        if p_mastery < 0.6:
            return "weak"
        if p_mastery < 0.8:
            return "growing"
        return "stable"

    def _mistake_read(self, item: Mistake) -> MistakeRead:
        try:
            variants = json.loads(item.variant_question_ids_json or "[]")
        except json.JSONDecodeError:
            variants = []
        return MistakeRead(
            id=item.id,
            twin_id=item.twin_id,
            question_id=item.question_id,
            attempt_id=item.attempt_id,
            source_text=item.source_text,
            error_type=item.error_type,
            error_analysis=item.error_analysis,
            status=item.status,
            variant_question_ids=[str(v) for v in variants],
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
