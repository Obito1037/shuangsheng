from __future__ import annotations

import json
import logging
import re
from hashlib import sha256
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ProviderError
from app.db.models.document_chunk import DocumentChunk
from app.db.models.learning_twin import LearningTwin
from app.db.models.twin_brain import Attempt, BlackboardLesson, KnowledgePoint, MasteryState, Mistake
from app.integrations.registry import ProviderRegistry, create_provider_registry
from app.schemas.llm import LlmMessage
from app.schemas.twin import BlackboardResponse, BlackboardStepRead

logger = logging.getLogger(__name__)


class BlackboardStepDraft(BaseModel):
    index: int = Field(ge=1, le=8)
    title: str = Field(min_length=2, max_length=80)
    explanation: str = Field(min_length=12, max_length=700)
    formula: str | None = Field(default=None, max_length=160)
    check_question: str | None = Field(default=None, max_length=160)

    @field_validator("title", "explanation", "formula", "check_question", mode="before")
    @classmethod
    def strip_text(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class BlackboardLessonDraft(BaseModel):
    steps: list[BlackboardStepDraft] = Field(min_length=3, max_length=6)


class BlackboardLessonService:
    def __init__(self, db: Session, *, registry: ProviderRegistry | None = None) -> None:
        self.db = db
        self.registry = registry or create_provider_registry()

    def get_lesson(self, *, user_id: str, twin_id: str, topic: str | None = None) -> BlackboardResponse:
        twin = self._require_twin(user_id=user_id, twin_id=twin_id)
        selected_topic = self._normalize_topic(topic) or self._topic(twin)
        profile_hash = self._profile_hash(user_id=user_id, twin_id=twin_id, twin=twin)
        cached = self._cached_lesson(twin_id=twin.id, topic=selected_topic, profile_hash=profile_hash)
        if cached:
            return self._response_from_lesson(cached, cached=True, user_id=user_id, twin_id=twin.id)

        kp = self._select_kp(user_id=user_id, twin_id=twin.id, topic=selected_topic)
        attempts_count = self._attempt_count(user_id=user_id, twin_id=twin.id)
        steps, model = self._generate_steps(
            user_id=user_id,
            twin=twin,
            topic=selected_topic,
            attempts_count=attempts_count,
            kp=kp,
        )
        lesson = BlackboardLesson(
            twin_id=twin.id,
            topic=selected_topic,
            profile_hash=profile_hash,
            kp_id=kp.id if kp else None,
            steps_json=json.dumps([step.model_dump() for step in steps], ensure_ascii=False),
            model=model,
        )
        self.db.add(lesson)
        self.db.commit()
        self.db.refresh(lesson)
        return self._response_from_lesson(lesson, cached=False, user_id=user_id, twin_id=twin.id)

    def _generate_steps(
        self,
        *,
        user_id: str,
        twin: LearningTwin,
        topic: str,
        attempts_count: int,
        kp: KnowledgePoint | None,
    ) -> tuple[list[BlackboardStepRead], str]:
        context = self._context(user_id=user_id, twin_id=twin.id, topic=topic)
        schema = json.dumps(BlackboardLessonDraft.model_json_schema(), ensure_ascii=False)
        system = (
            "你是双生学习分身的黑板课生成器。只生成教学叙事，不编造掌握度、收益、排名等数字。"
            "必须输出严格 JSON，符合给定 JSON Schema。"
        )
        user = (
            f"主题：{topic}\n"
            f"分身学科：{twin.subject}\n"
            f"分身目标：{twin.goal}\n"
            f"证据模式：{'启动方案/简化模式' if attempts_count < 10 else '真实画像'}\n"
            f"目标知识点：{kp.name if kp else '未定位到具体知识点'}\n"
            f"可用证据：\n{context}\n\n"
            f"JSON Schema:\n{schema}\n\n"
            "要求：生成 3-5 个 steps。每步包含 index/title/explanation/formula/check_question。"
            "证据不足时，在 explanation 中明确写“启动方案/简化模式”。不要输出 Markdown 代码块。"
        )
        try:
            provider = self.registry.get_llm_provider()
            result = provider.chat(
                [LlmMessage(role="system", content=system), LlmMessage(role="user", content=user)],
                temperature=0.2,
                max_tokens=1200,
            )
            try:
                return self._parse_llm_steps(result.content), result.model
            except (ValueError, ValidationError) as exc:
                repaired = provider.chat(
                    [
                        LlmMessage(role="system", content="把用户提供的内容修复成符合 JSON Schema 的严格 JSON，只输出 JSON。"),
                        LlmMessage(
                            role="user",
                            content=(
                                f"JSON Schema:\n{schema}\n\n"
                                f"校验错误：{exc}\n\n"
                                f"原始内容：\n{result.content}"
                            ),
                        ),
                    ],
                    temperature=0,
                    max_tokens=1200,
                )
                return self._parse_llm_steps(repaired.content), repaired.model
        except (ProviderError, ValueError, ValidationError) as exc:
            if isinstance(exc, ProviderError):
                logger.warning("Blackboard LLM failed; using fallback: %s", exc.to_safe_dict())
            else:
                logger.warning("Blackboard LLM output invalid; using fallback: %s", exc)
        except Exception:
            logger.exception("Unexpected blackboard generation failure; using fallback")
        return self._fallback_steps(topic=topic, twin=twin, attempts_count=attempts_count, kp=kp), "template-fallback"

    def _parse_llm_steps(self, content: str) -> list[BlackboardStepRead]:
        data = self._extract_json(content)
        draft = BlackboardLessonDraft.model_validate(data)
        return [
            BlackboardStepRead(
                index=index,
                title=step.title,
                explanation=step.explanation,
                formula=step.formula,
                check_question=step.check_question,
            )
            for index, step in enumerate(draft.steps, start=1)
        ]

    def _fallback_steps(
        self,
        *,
        topic: str,
        twin: LearningTwin,
        attempts_count: int,
        kp: KnowledgePoint | None,
    ) -> list[BlackboardStepRead]:
        evidence_prefix = "启动方案/简化模式：" if attempts_count < 10 else "简化模式："
        focus = kp.name if kp else topic
        return [
            BlackboardStepRead(
                index=1,
                title=f"定位 {focus} 的核心问题",
                explanation=(
                    f"{evidence_prefix}当前黑板课使用本地模板兜底生成。先把题目或资料拆成“已知条件、变化关系、要求目标”，"
                    "避免直接套答案。"
                ),
                formula="目标 = 已知条件 + 变化关系 + 验收标准",
                check_question=f"我现在要判断的是 {focus} 的定义、方法，还是易错边界？",
            ),
            BlackboardStepRead(
                index=2,
                title="把分身证据放到推导里",
                explanation=(
                    f"围绕“{twin.subject} / {twin.goal}”读取已有知识点、做题记录和错题。证据不足时，本步骤只给学习动作，"
                    "不声称已经发现稳定薄弱点。"
                ),
                formula="证据 = 资料片段 + attempt + mistake",
                check_question="这个结论有没有来自真实资料、真实做题或真实错题？",
            ),
            BlackboardStepRead(
                index=3,
                title="用一道自检题闭环",
                explanation=(
                    "讲解之后立刻安排复述或变式题，把结果写入 attempts。后续掌握度数字由 BKT/Elo/FSRS 更新，"
                    "黑板只负责把动作讲清楚。"
                ),
                formula="讲解 -> 复述 -> attempt -> BKT/Elo/FSRS",
                check_question="完成后，我能不能用自己的话复述，并提交一次可记录的答案？",
            ),
        ]

    def _cached_lesson(self, *, twin_id: str, topic: str, profile_hash: str) -> BlackboardLesson | None:
        return self.db.scalar(
            select(BlackboardLesson)
            .where(
                BlackboardLesson.twin_id == twin_id,
                BlackboardLesson.topic == topic,
                BlackboardLesson.profile_hash == profile_hash,
            )
            .order_by(BlackboardLesson.updated_at.desc())
        )

    def _response_from_lesson(self, lesson: BlackboardLesson, *, cached: bool, user_id: str, twin_id: str) -> BlackboardResponse:
        steps = self._steps_from_json(lesson.steps_json)
        attempts_count = self._attempt_count(user_id=user_id, twin_id=twin_id)
        return BlackboardResponse(
            twin_id=twin_id,
            topic=lesson.topic,
            steps=steps,
            lesson_id=lesson.id,
            source=lesson.model,
            cached=cached,
            evidence_mode="真实画像" if attempts_count >= 10 and lesson.model != "template-fallback" else "启动方案/简化模式",
        )

    def _steps_from_json(self, value: str) -> list[BlackboardStepRead]:
        try:
            data = json.loads(value or "[]")
        except json.JSONDecodeError:
            data = []
        steps: list[BlackboardStepRead] = []
        for item in data:
            if isinstance(item, dict):
                try:
                    steps.append(BlackboardStepRead.model_validate(item))
                except ValidationError:
                    continue
        return steps

    def _context(self, *, user_id: str, twin_id: str, topic: str) -> str:
        mastery_rows = list(
            self.db.execute(
                select(KnowledgePoint, MasteryState)
                .join(MasteryState, MasteryState.kp_id == KnowledgePoint.id, isouter=True)
                .where(KnowledgePoint.user_id == user_id, KnowledgePoint.twin_id == twin_id)
                .order_by(MasteryState.p_mastery.asc().nulls_first(), KnowledgePoint.created_at.asc())
                .limit(5)
            )
        )
        kps = [
            f"- {kp.name}: p_mastery={state.p_mastery:.2f}, attempts={state.attempt_count}"
            if state
            else f"- {kp.name}: 尚无 attempt"
            for kp, state in mastery_rows
        ]
        chunks = list(
            self.db.scalars(
                select(DocumentChunk)
                .where(DocumentChunk.user_id == user_id, DocumentChunk.twin_id == twin_id)
                .order_by(DocumentChunk.created_at.desc())
                .limit(3)
            )
        )
        snippets = [f"- {chunk.source}: {chunk.text[:180]}" for chunk in chunks]
        attempts = self._attempt_count(user_id=user_id, twin_id=twin_id)
        mistakes = int(
            self.db.scalar(select(func.count()).select_from(Mistake).where(Mistake.user_id == user_id, Mistake.twin_id == twin_id)) or 0
        )
        parts = [
            f"主题请求：{topic}",
            f"attempt_count={attempts}, mistake_count={mistakes}",
            "知识点画像：",
            "\n".join(kps) if kps else "- 暂无知识点画像",
            "资料片段：",
            "\n".join(snippets) if snippets else "- 暂无可引用资料片段",
        ]
        return "\n".join(parts)

    def _select_kp(self, *, user_id: str, twin_id: str, topic: str) -> KnowledgePoint | None:
        lowered = topic.lower()
        rows = list(
            self.db.execute(
                select(KnowledgePoint, MasteryState)
                .join(MasteryState, MasteryState.kp_id == KnowledgePoint.id, isouter=True)
                .where(KnowledgePoint.user_id == user_id, KnowledgePoint.twin_id == twin_id)
                .order_by(MasteryState.p_mastery.asc().nulls_first(), KnowledgePoint.created_at.asc())
                .limit(20)
            )
        )
        for kp, _ in rows:
            if kp.name.lower() in lowered or lowered in kp.name.lower():
                return kp
        return rows[0][0] if rows else None

    def _profile_hash(self, *, user_id: str, twin_id: str, twin: LearningTwin) -> str:
        states = list(self.db.scalars(select(MasteryState).where(MasteryState.user_id == user_id, MasteryState.twin_id == twin_id)))
        attempts = self._attempt_count(user_id=user_id, twin_id=twin_id)
        mistakes = int(
            self.db.scalar(select(func.count()).select_from(Mistake).where(Mistake.user_id == user_id, Mistake.twin_id == twin_id)) or 0
        )
        raw = "|".join(
            [
                twin.subject or "",
                twin.goal or "",
                str(attempts),
                str(mistakes),
                *[f"{state.kp_id}:{state.p_mastery:.4f}:{state.ability_elo:.1f}:{state.attempt_count}" for state in states],
            ]
        )
        return sha256(raw.encode("utf-8")).hexdigest()

    def _attempt_count(self, *, user_id: str, twin_id: str) -> int:
        return int(self.db.scalar(select(func.count()).select_from(Attempt).where(Attempt.user_id == user_id, Attempt.twin_id == twin_id)) or 0)

    def _require_twin(self, *, user_id: str, twin_id: str) -> LearningTwin:
        twin = self.db.scalar(select(LearningTwin).where(LearningTwin.user_id == user_id, LearningTwin.id == twin_id))
        if not twin:
            raise ValueError("Learning twin not found")
        return twin

    def _topic(self, twin: LearningTwin) -> str:
        subject = (twin.subject or "综合学习").strip()
        goal = (twin.goal or "").strip()
        return f"{subject}：{goal[:28]}" if goal else subject

    def _normalize_topic(self, topic: str | None) -> str | None:
        value = (topic or "").strip()
        return value[:120] if value else None

    def _extract_json(self, content: str) -> Any:
        text = (content or "").strip()
        fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.S | re.I)
        if fenced:
            text = fenced.group(1).strip()
        if not text.startswith("{"):
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                text = text[start : end + 1]
        if not text:
            raise ValueError("LLM returned empty JSON content")
        return json.loads(text)
