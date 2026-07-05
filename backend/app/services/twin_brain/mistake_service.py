from __future__ import annotations

import json
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.learning_twin import LearningTwin
from app.db.models.twin_brain import Attempt, KnowledgePoint, Mistake, Question
from app.schemas.twin_brain import MistakeCreateRequest, MistakeRead, MistakeUpdateRequest, QuestionRead, VariantQuestionsResponse
from app.services.twin_brain.knowledge_graph import KnowledgeGraphService


class MistakeService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.graph = KnowledgeGraphService(db)

    def list_mistakes(self, *, user_id: str, twin_id: str, status: str | None = None) -> list[MistakeRead]:
        self._require_twin(user_id=user_id, twin_id=twin_id)
        stmt = select(Mistake).where(Mistake.user_id == user_id, Mistake.twin_id == twin_id)
        if status:
            stmt = stmt.where(Mistake.status == status)
        mistakes = list(self.db.scalars(stmt.order_by(Mistake.created_at.desc())))
        return [self._read(item) for item in mistakes]

    def create_manual(self, *, user_id: str, payload: MistakeCreateRequest) -> MistakeRead:
        twin = self._require_twin(user_id=user_id, twin_id=payload.twin_id)
        kp_ids = self._resolve_kps(user_id=user_id, twin=twin, kp_ids=payload.kp_ids, kp_names=payload.kp_names)
        question_id = payload.question_id
        if not question_id:
            question = Question(
                user_id=user_id,
                twin_id=twin.id,
                kp_ids_json=json.dumps(kp_ids, ensure_ascii=False),
                stem=payload.source_text,
                answer="",
                solution="手动录入错题，答案和解析等待复盘补充。",
                source="user_mistake",
                difficulty_elo=1200.0,
            )
            self.db.add(question)
            self.db.flush()
            question_id = question.id
        mistake = Mistake(
            user_id=user_id,
            twin_id=twin.id,
            question_id=question_id,
            attempt_id=payload.attempt_id,
            source_text=payload.source_text,
            source_image_file_id=payload.source_image_file_id,
            error_type=payload.error_type or "待标注",
            error_analysis=payload.error_analysis
            or "简化模式：这是手动录入错题，尚未经过 LLM 错因 Schema 标注。请在复盘时补充错因或生成变式题。",
            status="open",
        )
        self.db.add(mistake)
        self._update_twin_error_profile(twin)
        self.db.commit()
        self.db.refresh(mistake)
        return self._read(mistake)

    def create_from_attempt(
        self,
        *,
        user_id: str,
        twin_id: str,
        attempt: Attempt,
        question: Question,
        error_type: str | None,
    ) -> Mistake:
        twin = self._require_twin(user_id=user_id, twin_id=twin_id)
        selected_error = error_type or self._infer_error_type(attempt)
        mistake = Mistake(
            user_id=user_id,
            twin_id=twin_id,
            question_id=question.id,
            attempt_id=attempt.id,
            source_text=question.stem,
            error_type=selected_error,
            error_analysis=(
                f"简化模式：本次错题来自真实做题记录。BKT 已下调相关知识点掌握概率，"
                f"Elo 已根据题目难度更新；当前错因暂标为「{selected_error}」。"
            ),
            status="open",
        )
        self.db.add(mistake)
        self._update_twin_error_profile(twin)
        return mistake

    def update_mistake(self, *, user_id: str, mistake_id: str, payload: MistakeUpdateRequest) -> MistakeRead:
        mistake = self._require_mistake(user_id=user_id, mistake_id=mistake_id)
        if payload.status is not None:
            mistake.status = payload.status
        if payload.error_type is not None:
            mistake.error_type = payload.error_type.strip() or mistake.error_type
        if payload.error_analysis is not None:
            mistake.error_analysis = payload.error_analysis.strip() or mistake.error_analysis
        twin = self._require_twin(user_id=user_id, twin_id=mistake.twin_id)
        self._update_twin_error_profile(twin)
        self.db.add(mistake)
        self.db.commit()
        self.db.refresh(mistake)
        return self._read(mistake)

    def generate_variants(self, *, user_id: str, mistake_id: str, count: int = 2) -> VariantQuestionsResponse:
        mistake = self._require_mistake(user_id=user_id, mistake_id=mistake_id)
        twin = self._require_twin(user_id=user_id, twin_id=mistake.twin_id)
        kp_ids = self._kp_ids_from_question(user_id=user_id, twin_id=twin.id, question_id=mistake.question_id)
        if not kp_ids:
            kp_ids = self._resolve_kps(user_id=user_id, twin=twin, kp_ids=[], kp_names=[])
        existing = self._variant_ids(mistake)
        questions: list[Question] = []
        if existing:
            questions.extend(
                self.db.scalars(
                    select(Question).where(
                        Question.user_id == user_id,
                        Question.twin_id == twin.id,
                        Question.id.in_(existing),
                    )
                )
            )
        needed = max(0, min(5, count) - len(questions))
        for idx in range(needed):
            question = Question(
                user_id=user_id,
                twin_id=twin.id,
                kp_ids_json=json.dumps(kp_ids, ensure_ascii=False),
                stem=(
                    f"变式题 {len(questions) + 1}：保留原错题的核心知识点，"
                    f"换一种条件或表述重新完成：{mistake.source_text[:160]}"
                ),
                answer="简化模式变式题：请提交作答并自评，系统会用真实结果更新 BKT/Elo。",
                solution=f"关注错因「{mistake.error_type}」；先写出条件、方法选择，再计算或论证。",
                source="variant",
                difficulty_elo=1220.0 + idx * 40,
            )
            self.db.add(question)
            self.db.flush()
            questions.append(question)
        mistake.variant_question_ids_json = json.dumps([q.id for q in questions], ensure_ascii=False)
        if mistake.status == "open":
            mistake.status = "reviewing"
        self.db.add(mistake)
        self.db.commit()
        for question in questions:
            self.db.refresh(question)
        self.db.refresh(mistake)
        return VariantQuestionsResponse(
            mistake_id=mistake.id,
            evidence_mode="简化模式",
            questions=[self._question_read(q) for q in questions],
        )

    def _resolve_kps(self, *, user_id: str, twin: LearningTwin, kp_ids: list[str], kp_names: list[str]) -> list[str]:
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
                description="由错题或做题流手动补充的知识点。",
            )
            self.graph.ensure_mastery_state(user_id=user_id, twin_id=twin.id, kp_id=kp.id)
            resolved.append(kp.id)
        if not resolved:
            kp = self.graph.get_or_create(
                user_id=user_id,
                twin_id=twin.id,
                name=f"{twin.subject} 未归类错题",
                subject=twin.subject,
                source="manual",
                description="证据不足时的临时归类，后续可通过复盘细分。",
            )
            self.graph.ensure_mastery_state(user_id=user_id, twin_id=twin.id, kp_id=kp.id)
            resolved.append(kp.id)
        return list(dict.fromkeys(resolved))

    def _infer_error_type(self, attempt: Attempt) -> str:
        if not attempt.answer_text.strip():
            return "表达不完整"
        if attempt.self_rating in {"again", "hard"}:
            return "概念不清"
        if any(ch.isdigit() for ch in attempt.answer_text):
            return "计算失误"
        return "方法选择错误"

    def _kp_ids_from_question(self, *, user_id: str, twin_id: str, question_id: str | None) -> list[str]:
        if not question_id:
            return []
        question = self.db.scalar(select(Question).where(Question.user_id == user_id, Question.twin_id == twin_id, Question.id == question_id))
        if not question:
            return []
        try:
            loaded = json.loads(question.kp_ids_json or "[]")
        except json.JSONDecodeError:
            return []
        return [str(item) for item in loaded if str(item).strip()]

    def _variant_ids(self, mistake: Mistake) -> list[str]:
        try:
            loaded = json.loads(mistake.variant_question_ids_json or "[]")
        except json.JSONDecodeError:
            return []
        return [str(item) for item in loaded if str(item).strip()]

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

    def _update_twin_error_profile(self, twin: LearningTwin) -> None:
        mistakes = list(self.db.scalars(select(Mistake).where(Mistake.user_id == twin.user_id, Mistake.twin_id == twin.id)))
        counts = Counter(item.error_type or "待标注" for item in mistakes)
        try:
            profile = json.loads(twin.profile_json or "{}")
        except json.JSONDecodeError:
            profile = {}
        profile["error_patterns"] = dict(counts)
        twin.profile_json = json.dumps(profile, ensure_ascii=False)
        self.db.add(twin)

    def _require_twin(self, *, user_id: str, twin_id: str) -> LearningTwin:
        twin = self.db.scalar(select(LearningTwin).where(LearningTwin.user_id == user_id, LearningTwin.id == twin_id))
        if not twin:
            raise ValueError("Learning twin not found")
        return twin

    def _require_mistake(self, *, user_id: str, mistake_id: str) -> Mistake:
        mistake = self.db.scalar(select(Mistake).where(Mistake.user_id == user_id, Mistake.id == mistake_id))
        if not mistake:
            raise ValueError("Mistake not found")
        return mistake

    def _read(self, item: Mistake) -> MistakeRead:
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
