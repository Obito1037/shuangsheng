from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.learning_twin import LearningTwin
from app.db.models.twin_brain import Attempt, KnowledgePoint, MasteryState, Question
from app.schemas.twin_brain import DiagnoseResponse, QuestionRead
from app.services.twin_brain.knowledge_graph import KnowledgeGraphService
from app.services.twin_brain.mastery_service import MasteryService

SUBJECT_SEEDS: dict[str, list[str]] = {
    "数学": ["定义与条件", "公式推导", "典型例题", "易错边界"],
    "数据库": ["关系模型", "SQL 聚合", "GROUP BY", "事务与索引"],
    "英语": ["词汇语义", "句型结构", "听说表达", "阅读推断"],
    "编程": ["核心语法", "数据结构", "调试方法", "边界条件"],
}


@dataclass(frozen=True, slots=True)
class ScoredQuestion:
    question: Question
    predicted_correct: float
    selection_score: float
    selection_reason: str


class QuestionSelectorService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.graph = KnowledgeGraphService(db)
        self.mastery = MasteryService(db)

    def diagnose(self, *, user_id: str, twin_id: str, limit: int = 8) -> DiagnoseResponse:
        twin = self._require_twin(user_id=user_id, twin_id=twin_id)
        self.ensure_diagnostic_seed(user_id=user_id, twin=twin)
        questions = self.list_questions(user_id=user_id, twin_id=twin_id, mode="diagnostic", limit=limit)
        attempt_count = int(
            self.db.scalar(select(func.count()).select_from(Attempt).where(Attempt.user_id == user_id, Attempt.twin_id == twin_id)) or 0
        )
        return DiagnoseResponse(
            twin_id=twin_id,
            evidence_mode="真实画像" if attempt_count >= 10 else "启动方案",
            reason="当前题组用于收集真实作答数据；完成后 BKT/Elo 会重新估计画像。" if attempt_count < 10 else "题组按当前薄弱点和 ZPD 打分排序。",
            questions=questions,
        )

    def list_questions(self, *, user_id: str, twin_id: str, mode: str = "practice", limit: int = 12) -> list[QuestionRead]:
        self._require_twin(user_id=user_id, twin_id=twin_id)
        questions = list(self.db.scalars(select(Question).where(Question.user_id == user_id, Question.twin_id == twin_id)))
        if not questions:
            twin = self._require_twin(user_id=user_id, twin_id=twin_id)
            self.ensure_diagnostic_seed(user_id=user_id, twin=twin)
            questions = list(self.db.scalars(select(Question).where(Question.user_id == user_id, Question.twin_id == twin_id)))
        scored = [self._score_question(user_id=user_id, twin_id=twin_id, question=q, mode=mode) for q in questions]
        scored.sort(key=lambda item: item.selection_score, reverse=True)
        return [self._question_read(item) for item in scored[: max(1, min(limit, 50))]]

    def ensure_diagnostic_seed(self, *, user_id: str, twin: LearningTwin) -> list[Question]:
        existing = list(self.db.scalars(select(Question).where(Question.user_id == user_id, Question.twin_id == twin.id).limit(1)))
        if existing:
            return existing
        seed_names = self._subject_seed_names(twin.subject)
        questions: list[Question] = []
        for name in seed_names:
            kp = self.graph.get_or_create(
                user_id=user_id,
                twin_id=twin.id,
                name=f"{twin.subject}：{name}",
                subject=twin.subject,
                source="seed",
                description="启动方案：在资料/错题不足时用于建立第一批诊断坐标。",
            )
            self.graph.ensure_mastery_state(user_id=user_id, twin_id=twin.id, kp_id=kp.id)
            q = Question(
                user_id=user_id,
                twin_id=twin.id,
                kp_ids_json=json.dumps([kp.id], ensure_ascii=False),
                stem=f"诊断题：请说明「{kp.name}」的核心含义，并举一个容易出错的例子。",
                answer="这是一道启动诊断题，需要用户自评作答结果来训练画像。",
                solution="启动方案：回答后提交“答对/答错”和自评，系统会用 BKT/Elo 更新分身画像。",
                source="diagnostic",
                difficulty_elo=1200.0,
            )
            self.db.add(q)
            questions.append(q)
        self.db.commit()
        for question in questions:
            self.db.refresh(question)
        return questions

    def _score_question(self, *, user_id: str, twin_id: str, question: Question, mode: str) -> ScoredQuestion:
        kp_ids = self._kp_ids(question)
        states = []
        if kp_ids:
            states = list(
                self.db.scalars(
                    select(MasteryState).where(
                        MasteryState.user_id == user_id,
                        MasteryState.twin_id == twin_id,
                        MasteryState.kp_id.in_(kp_ids),
                    )
                )
            )
        avg_ability = sum(s.ability_elo for s in states) / len(states) if states else 1200.0
        predicted = self.mastery.expected_correct(ability_elo=avg_ability, difficulty_elo=question.difficulty_elo)
        target = 0.55 if mode == "diagnostic" else 0.75
        zpd = max(0.0, 1.0 - abs(predicted - target) / 0.5)
        uncertainty = sum((s.p_mastery * (1 - s.p_mastery)) for s in states) / len(states) if states else 0.1875
        weak_cover = sum(1 for s in states if s.p_mastery < 0.6)
        recent_attempts = int(
            self.db.scalar(
                select(func.count())
                .select_from(Attempt)
                .where(
                    Attempt.user_id == user_id,
                    Attempt.twin_id == twin_id,
                    Attempt.question_id == question.id,
                    Attempt.created_at >= func.datetime("now", "-7 days"),
                )
            )
            or 0
        )
        repeat_penalty = min(0.6, recent_attempts * 0.3)
        score = zpd * 0.55 + uncertainty * 1.1 + min(0.3, weak_cover * 0.12) - repeat_penalty
        reason = f"ZPD={zpd:.2f}，预测正确率={predicted:.2f}，信息增益={uncertainty:.2f}"
        if repeat_penalty:
            reason += f"，近 7 天已做过，重复惩罚={repeat_penalty:.2f}"
        return ScoredQuestion(question=question, predicted_correct=predicted, selection_score=score, selection_reason=reason)

    def _question_read(self, scored: ScoredQuestion) -> QuestionRead:
        question = scored.question
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
            predicted_correct=round(scored.predicted_correct, 4),
            selection_score=round(scored.selection_score, 4),
            selection_reason=scored.selection_reason,
            created_at=question.created_at,
        )

    def _subject_seed_names(self, subject: str) -> list[str]:
        key = subject or "综合学习"
        for name, seeds in SUBJECT_SEEDS.items():
            if name.lower() in key.lower() or key.lower() in name.lower():
                return seeds
        return [f"{key} 基础概念", f"{key} 方法选择", f"{key} 易错边界", f"{key} 输出复述"]

    def _kp_ids(self, question: Question) -> list[str]:
        try:
            loaded = json.loads(question.kp_ids_json or "[]")
        except json.JSONDecodeError:
            return []
        return [str(item) for item in loaded if str(item).strip()]

    def _require_twin(self, *, user_id: str, twin_id: str) -> LearningTwin:
        twin = self.db.scalar(select(LearningTwin).where(LearningTwin.user_id == user_id, LearningTwin.id == twin_id))
        if not twin:
            raise ValueError("Learning twin not found")
        return twin
