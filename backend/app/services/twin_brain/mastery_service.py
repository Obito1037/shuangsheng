from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import utc_now
from app.db.models.twin_brain import KnowledgePoint, MasteryState, Question
from app.schemas.twin_brain import MasteryUpdateRead
from app.services.twin_brain.knowledge_graph import KnowledgeGraphService

BKT_L0 = 0.25
BKT_T = 0.20
BKT_SLIP = 0.10
BKT_GUESS = 0.20
STUDENT_K = 32.0
QUESTION_K = 16.0


@dataclass(frozen=True, slots=True)
class MasteryUpdate:
    kp: KnowledgePoint
    before_p_mastery: float
    after_p_mastery: float
    before_ability_elo: float
    after_ability_elo: float
    expected_correct: float

    def read(self) -> MasteryUpdateRead:
        return MasteryUpdateRead(
            kp_id=self.kp.id,
            name=self.kp.name,
            before_p_mastery=round(self.before_p_mastery, 4),
            after_p_mastery=round(self.after_p_mastery, 4),
            before_ability_elo=round(self.before_ability_elo, 2),
            after_ability_elo=round(self.after_ability_elo, 2),
            expected_correct=round(self.expected_correct, 4),
        )


class MasteryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.graph = KnowledgeGraphService(db)

    def update_for_attempt(
        self,
        *,
        user_id: str,
        twin_id: str,
        question: Question,
        kp_ids: list[str],
        is_correct: bool,
        self_rating: str | None,
    ) -> list[MasteryUpdate]:
        points = list(
            self.db.scalars(
                select(KnowledgePoint).where(
                    KnowledgePoint.user_id == user_id,
                    KnowledgePoint.twin_id == twin_id,
                    KnowledgePoint.id.in_(kp_ids),
                )
            )
        )
        if not points:
            return []
        states = [self.graph.ensure_mastery_state(user_id=user_id, twin_id=twin_id, kp_id=kp.id) for kp in points]
        avg_ability = sum(state.ability_elo for state in states) / len(states)
        expected = self.expected_correct(ability_elo=avg_ability, difficulty_elo=question.difficulty_elo)
        result = 1.0 if is_correct else 0.0
        updates: list[MasteryUpdate] = []
        now = utc_now()
        for kp, state in zip(points, states, strict=False):
            before_p = state.p_mastery if state.p_mastery is not None else BKT_L0
            before_ability = state.ability_elo if state.ability_elo is not None else 1200.0
            after_p = self._bkt_update(before_p, is_correct=is_correct)
            state.p_mastery = after_p
            state.ability_elo = before_ability + STUDENT_K * (result - expected)
            state.attempt_count += 1
            state.correct_count += 1 if is_correct else 0
            state.last_review_at = now
            self._update_memory_schedule(state, is_correct=is_correct, self_rating=self_rating)
            state.updated_at = now
            self.db.add(state)
            updates.append(
                MasteryUpdate(
                    kp=kp,
                    before_p_mastery=before_p,
                    after_p_mastery=state.p_mastery,
                    before_ability_elo=before_ability,
                    after_ability_elo=state.ability_elo,
                    expected_correct=expected,
                )
            )
        question.difficulty_elo = max(800.0, min(1800.0, question.difficulty_elo - QUESTION_K * (result - expected)))
        self.db.add(question)
        return updates

    def expected_correct(self, *, ability_elo: float, difficulty_elo: float) -> float:
        return 1.0 / (1.0 + math.pow(10.0, (difficulty_elo - ability_elo) / 400.0))

    def kp_ids_from_question(self, question: Question) -> list[str]:
        try:
            loaded = json.loads(question.kp_ids_json or "[]")
        except json.JSONDecodeError:
            return []
        return [str(item) for item in loaded if str(item).strip()]

    def _bkt_update(self, p_mastery: float, *, is_correct: bool) -> float:
        p = max(0.01, min(0.99, p_mastery))
        if is_correct:
            numerator = p * (1 - BKT_SLIP)
            denominator = numerator + (1 - p) * BKT_GUESS
        else:
            numerator = p * BKT_SLIP
            denominator = numerator + (1 - p) * (1 - BKT_GUESS)
        posterior = numerator / denominator if denominator else p
        return max(0.01, min(0.99, posterior + (1 - posterior) * BKT_T))

    def _update_memory_schedule(self, state: MasteryState, *, is_correct: bool, self_rating: str | None) -> None:
        rating_factor = {"again": 0.5, "hard": 1.2, "good": 1.8, "easy": 2.4}.get(self_rating or "", 1.5)
        if is_correct:
            state.stability = max(0.5, min(90.0, state.stability * rating_factor))
            state.difficulty_fsrs = max(1.0, state.difficulty_fsrs - (0.2 if self_rating == "easy" else 0.1))
        else:
            state.stability = max(0.5, state.stability * 0.55)
            state.difficulty_fsrs = min(10.0, state.difficulty_fsrs + 0.8)
        state.due_at = utc_now() + timedelta(days=max(0.5, state.stability))
