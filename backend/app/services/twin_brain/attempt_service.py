from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.learning_record import LearningRecord
from app.db.models.learning_twin import LearningTwin
from app.db.models.twin_brain import Attempt, KnowledgePoint, Question
from app.schemas.twin_brain import AttemptCreateRequest, AttemptResponse, QuestionRead
from app.services.twin_brain.knowledge_graph import KnowledgeGraphService
from app.services.twin_brain.mastery_service import MasteryService
from app.services.twin_brain.mistake_service import MistakeService


class AttemptService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.graph = KnowledgeGraphService(db)
        self.mastery = MasteryService(db)
        self.mistakes = MistakeService(db)

    def submit(self, *, user_id: str, payload: AttemptCreateRequest) -> AttemptResponse:
        twin = self._require_twin(user_id=user_id, twin_id=payload.twin_id)
        question, kp_ids = self._resolve_question_and_kps(user_id=user_id, twin=twin, payload=payload)
        attempt = Attempt(
            user_id=user_id,
            twin_id=twin.id,
            question_id=question.id,
            kp_ids_json=json.dumps(kp_ids, ensure_ascii=False),
            is_correct=payload.is_correct,
            self_rating=payload.self_rating,
            time_spent_sec=payload.time_spent_sec,
            error_type=payload.error_type,
            answer_text=payload.answer_text or "",
        )
        self.db.add(attempt)
        self.db.flush()
        updates = self.mastery.update_for_attempt(
            user_id=user_id,
            twin_id=twin.id,
            question=question,
            kp_ids=kp_ids,
            is_correct=payload.is_correct,
            self_rating=payload.self_rating,
        )
        mistake = None
        if not payload.is_correct:
            mistake = self.mistakes.create_from_attempt(
                user_id=user_id,
                twin_id=twin.id,
                attempt=attempt,
                question=question,
                error_type=payload.error_type,
            )
            self.db.flush()
        twin.xp = (twin.xp or 0) + (12 if payload.is_correct else 5)
        twin.level = max(twin.level or 1, 1 + twin.xp // 120)
        self.db.add(twin)
        self.db.add(
            LearningRecord(
                user_id=user_id,
                twin_id=twin.id,
                record_type="attempt",
                content=f"做题记录：{'答对' if payload.is_correct else '答错'} · {question.stem[:80]}",
                payload_json=json.dumps(
                    {
                        "attempt_id": attempt.id,
                        "question_id": question.id,
                        "kp_ids": kp_ids,
                        "is_correct": payload.is_correct,
                        "self_rating": payload.self_rating,
                        "mastery_updates": [item.read().model_dump() for item in updates],
                    },
                    ensure_ascii=False,
                ),
            )
        )
        self.db.commit()
        self.db.refresh(attempt)
        self.db.refresh(question)
        if mistake:
            self.db.refresh(mistake)
        return AttemptResponse(
            id=attempt.id,
            twin_id=attempt.twin_id,
            question=self._question_read(question),
            is_correct=attempt.is_correct,
            self_rating=attempt.self_rating,
            time_spent_sec=attempt.time_spent_sec,
            error_type=attempt.error_type,
            answer_text=attempt.answer_text,
            mastery_updates=[item.read() for item in updates],
            mistake=self.mistakes._read(mistake) if mistake else None,
            created_at=attempt.created_at,
        )

    def list_questions(self, *, user_id: str, twin_id: str, limit: int = 12) -> list[QuestionRead]:
        self._require_twin(user_id=user_id, twin_id=twin_id)
        questions = list(
            self.db.scalars(
                select(Question)
                .where(Question.user_id == user_id, Question.twin_id == twin_id)
                .order_by(Question.created_at.desc())
                .limit(limit)
            )
        )
        return [self._question_read(question) for question in questions]

    def _resolve_question_and_kps(
        self,
        *,
        user_id: str,
        twin: LearningTwin,
        payload: AttemptCreateRequest,
    ) -> tuple[Question, list[str]]:
        kp_ids = self._resolve_kps(
            user_id=user_id,
            twin=twin,
            kp_ids=payload.kp_ids,
            kp_names=payload.kp_names,
            allow_fallback=False,
        )
        if payload.question_id:
            question = self.db.scalar(
                select(Question).where(Question.user_id == user_id, Question.twin_id == twin.id, Question.id == payload.question_id)
            )
            if not question:
                raise ValueError("Question not found")
            if not kp_ids:
                kp_ids = self.mastery.kp_ids_from_question(question)
            if kp_ids and question.kp_ids_json in {"", "[]"}:
                question.kp_ids_json = json.dumps(kp_ids, ensure_ascii=False)
                self.db.add(question)
            return question, kp_ids or self._resolve_kps(user_id=user_id, twin=twin, kp_ids=[], kp_names=[], allow_fallback=True)
        if not kp_ids:
            kp_ids = self._resolve_kps(user_id=user_id, twin=twin, kp_ids=[], kp_names=[], allow_fallback=True)
        question = Question(
            user_id=user_id,
            twin_id=twin.id,
            kp_ids_json=json.dumps(kp_ids, ensure_ascii=False),
            stem=(payload.stem or "自定义练习题").strip() or "自定义练习题",
            options_json=json.dumps(payload.options, ensure_ascii=False) if payload.options else None,
            answer=payload.correct_answer or "",
            solution=payload.solution or "简化模式题目：由用户或资料管线提供，系统记录真实作答并更新画像。",
            source="diagnostic" if payload.stem else "user_mistake",
            difficulty_elo=1200.0,
        )
        self.db.add(question)
        self.db.flush()
        return question, kp_ids

    def _resolve_kps(
        self,
        *,
        user_id: str,
        twin: LearningTwin,
        kp_ids: list[str],
        kp_names: list[str],
        allow_fallback: bool,
    ) -> list[str]:
        resolved = list(
            self.db.scalars(
                select(KnowledgePoint.id).where(
                    KnowledgePoint.user_id == user_id,
                    KnowledgePoint.twin_id == twin.id,
                    KnowledgePoint.id.in_(kp_ids),
                )
            )
        )
        for name in kp_names:
            kp = self.graph.get_or_create(
                user_id=user_id,
                twin_id=twin.id,
                name=name,
                subject=twin.subject,
                source="manual",
                description="由做题流手动补充的知识点。",
            )
            self.graph.ensure_mastery_state(user_id=user_id, twin_id=twin.id, kp_id=kp.id)
            resolved.append(kp.id)
        if not resolved and allow_fallback:
            kp = self.graph.get_or_create(
                user_id=user_id,
                twin_id=twin.id,
                name=f"{twin.subject} 启动诊断",
                subject=twin.subject,
                source="manual",
                description="证据不足时的启动知识点，完成更多题目后可细分。",
            )
            self.graph.ensure_mastery_state(user_id=user_id, twin_id=twin.id, kp_id=kp.id)
            resolved.append(kp.id)
        return list(dict.fromkeys(resolved))

    def _require_twin(self, *, user_id: str, twin_id: str) -> LearningTwin:
        twin = self.db.scalar(select(LearningTwin).where(LearningTwin.user_id == user_id, LearningTwin.id == twin_id))
        if not twin:
            raise ValueError("Learning twin not found")
        return twin

    def _question_read(self, question: Question) -> QuestionRead:
        try:
            kp_ids = json.loads(question.kp_ids_json or "[]")
        except json.JSONDecodeError:
            kp_ids = []
        try:
            options = json.loads(question.options_json) if question.options_json else None
        except json.JSONDecodeError:
            options = None
        return QuestionRead(
            id=question.id,
            twin_id=question.twin_id,
            kp_ids=[str(item) for item in kp_ids],
            stem=question.stem,
            options=options,
            answer=question.answer,
            solution=question.solution,
            source=question.source,
            difficulty_elo=question.difficulty_elo,
            created_at=question.created_at,
        )
