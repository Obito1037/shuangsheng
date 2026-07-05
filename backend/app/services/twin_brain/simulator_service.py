from __future__ import annotations

import json
import logging
import random
from datetime import UTC, datetime
from hashlib import sha256

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.base import utc_now
from app.db.models.learning_twin import LearningTwin
from app.db.models.twin_brain import Attempt, KnowledgePoint, MasteryState, PlanTask, StudyPlan
from app.integrations.registry import ProviderRegistry, create_provider_registry
from app.schemas.llm import LlmMessage
from app.schemas.twin_brain import PlanCandidateRead, PlanTaskRead, PlanTaskUpdateRequest, StudyPlanResponse
from app.services.twin_brain.mastery_service import BKT_GUESS, BKT_SLIP, BKT_T, MasteryService
from app.services.twin_brain.scheduler_service import ReviewSchedulerService
from app.services.twin_brain.selector_service import QuestionSelectorService

logger = logging.getLogger(__name__)


class SimulatorService:
    def __init__(self, db: Session, *, registry: ProviderRegistry | None = None) -> None:
        self.db = db
        self.mastery = MasteryService(db)
        self.selector = QuestionSelectorService(db)
        self.scheduler = ReviewSchedulerService(db)
        self.registry = registry or create_provider_registry()

    def create_plan(self, *, user_id: str, twin_id: str) -> StudyPlanResponse:
        twin = self._require_twin(user_id=user_id, twin_id=twin_id)
        profile_hash = self._profile_hash(user_id=user_id, twin_id=twin_id)
        plan = StudyPlan(user_id=user_id, twin_id=twin_id, status="simulating", profile_hash=profile_hash)
        self.db.add(plan)
        self.db.flush()
        attempts_count = self._attempt_count(user_id=user_id, twin_id=twin_id)
        candidates = self._cold_start_candidates() if attempts_count < 10 else self._simulate_candidates(user_id=user_id, twin_id=twin_id, seed=plan.id)
        candidates.sort(key=lambda item: item.utility, reverse=True)
        chosen = candidates[0]
        for candidate in candidates[1:]:
            candidate.eliminated = True
        selected_questions = self.selector.diagnose(user_id=user_id, twin_id=twin_id, limit=4).questions if attempts_count < 10 else self.selector.list_questions(user_id=user_id, twin_id=twin_id, mode="practice", limit=4)
        tasks = self._tasks_for_candidate(plan_id=plan.id, chosen=chosen, questions=selected_questions, cold_start=attempts_count < 10)
        for task in tasks:
            self.db.add(task)
        self.db.flush()
        profile_summary = self._profile_summary(user_id=user_id, twin_id=twin_id, attempts_count=attempts_count)
        chosen_route = {
            "name": chosen.name,
            "strategy": chosen.strategy,
            "utility": chosen.utility,
            "tasks": [self._task_read(task).model_dump() for task in tasks],
        }
        plan.status = "ready"
        plan.candidates_json = json.dumps([candidate.model_dump() for candidate in candidates], ensure_ascii=False)
        plan.chosen_route_json = json.dumps(chosen_route, ensure_ascii=False)
        plan.narrative = self._narrative(chosen=chosen, candidates=candidates, twin=twin, attempts_count=attempts_count)
        plan.finished_at = utc_now()
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return self.get_plan(user_id=user_id, plan_id=plan.id)

    def get_plan(self, *, user_id: str, plan_id: str) -> StudyPlanResponse:
        plan = self._require_plan(user_id=user_id, plan_id=plan_id)
        tasks = list(self.db.scalars(select(PlanTask).where(PlanTask.plan_id == plan.id).order_by(PlanTask.index.asc())))
        try:
            candidates = [PlanCandidateRead.model_validate(item) for item in json.loads(plan.candidates_json or "[]")]
        except (json.JSONDecodeError, TypeError):
            candidates = []
        try:
            chosen_route = json.loads(plan.chosen_route_json or "{}")
        except json.JSONDecodeError:
            chosen_route = {}
        return StudyPlanResponse(
            plan_id=plan.id,
            twin_id=plan.twin_id,
            status=plan.status,
            profile_summary=self._profile_summary(user_id=user_id, twin_id=plan.twin_id, attempts_count=self._attempt_count(user_id=user_id, twin_id=plan.twin_id)),
            candidates=candidates,
            chosen_route=chosen_route,
            tasks=[self._task_read(task) for task in tasks],
            narrative=plan.narrative,
            created_at=plan.created_at,
            finished_at=plan.finished_at,
        )

    def update_task(self, *, user_id: str, plan_id: str, task_id: str, payload: PlanTaskUpdateRequest) -> StudyPlanResponse:
        plan = self._require_plan(user_id=user_id, plan_id=plan_id)
        task = self.db.scalar(select(PlanTask).where(PlanTask.plan_id == plan.id, PlanTask.id == task_id))
        if not task:
            raise ValueError("Plan task not found")
        if payload.status is not None:
            task.status = payload.status
            if payload.status == "done":
                task.completed_at = utc_now()
        if payload.outcome is not None:
            task.outcome_json = json.dumps(payload.outcome, ensure_ascii=False)
        self.db.add(task)
        self.db.commit()
        return self.get_plan(user_id=user_id, plan_id=plan.id)

    def _simulate_candidates(self, *, user_id: str, twin_id: str, seed: str) -> list[PlanCandidateRead]:
        rows = list(
            self.db.execute(
                select(MasteryState, KnowledgePoint)
                .join(KnowledgePoint, KnowledgePoint.id == MasteryState.kp_id)
                .where(MasteryState.user_id == user_id, MasteryState.twin_id == twin_id)
            )
        )
        states = [row[0] for row in rows]
        prototypes = [
            ("概念先行", "先补薄弱概念，再做靶向题验证", 26, 0.38, 2),
            ("做题反推", "先做题暴露错因，再回补方法", 20, 0.58, 3),
            ("黑板讲解 + 复述", "分步讲解后用复述检查缺口", 22, 0.34, 1),
            ("薄弱点集中训练", "集中处理 p_mastery < 0.6 的知识点", 30, 0.52, 4),
        ]
        return [self._simulate_candidate(states=states, proto=proto, seed=f"{seed}:{idx}") for idx, proto in enumerate(prototypes)]

    def _simulate_candidate(self, *, states: list[MasteryState], proto: tuple[str, str, int, float, int], seed: str) -> PlanCandidateRead:
        name, strategy, minutes, load, reps = proto
        if not states:
            return PlanCandidateRead(name=name, strategy=strategy, utility=0.0, expected_gain=0.0, minutes=minutes, cognitive_load=load, forgetting_risk=0.5, eliminated=True, reason="没有 mastery 状态，无法推演。")
        rng = random.Random(seed)
        gains: list[float] = []
        for _ in range(200):
            gain = 0.0
            for state in states:
                p0 = state.p_mastery
                p = p0
                weak_weight = 1.4 if p0 < 0.6 else 0.8
                difficulty = 1200.0 + load * 220.0
                prob = self.mastery.expected_correct(ability_elo=state.ability_elo, difficulty_elo=difficulty)
                for _ in range(reps):
                    p = self._bkt_roll(p, is_correct=rng.random() < prob)
                gain += max(0.0, p - p0) * weak_weight
            gains.append(gain / len(states))
        expected_gain = sum(gains) / len(gains)
        weak_coverage = sum(1 for s in states if s.p_mastery < 0.6) / max(1, len(states))
        forgetting_risk = sum(1.0 - self._retention(s) for s in states) / len(states)
        utility = expected_gain + 0.3 * weak_coverage - 0.2 * (minutes / 45.0) - 0.25 * load - 0.25 * forgetting_risk
        reason = (
            f"200 次 rollout 预期掌握提升 +{expected_gain:.2f}，"
            f"薄弱点覆盖 {weak_coverage:.0%}，认知负荷 {load:.2f}，遗忘风险 {forgetting_risk:.2f}。"
        )
        return PlanCandidateRead(
            name=name,
            strategy=strategy,
            utility=round(utility, 4),
            expected_gain=round(expected_gain, 4),
            minutes=minutes,
            cognitive_load=round(load, 4),
            forgetting_risk=round(forgetting_risk, 4),
            eliminated=False,
            reason=reason,
        )

    def _cold_start_candidates(self) -> list[PlanCandidateRead]:
        return [
            PlanCandidateRead(name="诊断先行", strategy="先做启动诊断题，再重新模拟路线", utility=0.42, expected_gain=0.08, minutes=18, cognitive_load=0.32, forgetting_risk=0.2, eliminated=False, reason="attempt_count < 10，证据不足；先收集真实做题数据。"),
            PlanCandidateRead(name="概念先行", strategy="直接讲概念再练习", utility=0.18, expected_gain=0.04, minutes=24, cognitive_load=0.4, forgetting_risk=0.35, eliminated=True, reason="缺少真实错因和掌握度，直接讲解容易错配。"),
            PlanCandidateRead(name="做题反推", strategy="直接刷题暴露问题", utility=0.12, expected_gain=0.03, minutes=20, cognitive_load=0.62, forgetting_risk=0.42, eliminated=True, reason="冷启动阶段题目难度无法可靠贴合当前能力带。"),
        ]

    def _tasks_for_candidate(self, *, plan_id: str, chosen: PlanCandidateRead, questions: list, cold_start: bool) -> list[PlanTask]:
        question_ids = [q.id for q in questions[:3]]
        if cold_start:
            return [
                PlanTask(plan_id=plan_id, index=1, type="practice", title="完成启动诊断题", detail="先做 3-4 道题，提交答对/答错和自评。", question_ids_json=json.dumps(question_ids, ensure_ascii=False), est_minutes=12, completion_criteria="至少提交 3 条 attempt。"),
                PlanTask(plan_id=plan_id, index=2, type="review", title="查看画像变化", detail="观察 p_mastery 与 Elo 的第一轮变化。", est_minutes=4, completion_criteria="能说出一个薄弱知识点。"),
                PlanTask(plan_id=plan_id, index=3, type="blackboard", title="黑板补一个最弱点", detail="选择最低掌握度知识点进行分步讲解。", est_minutes=8, completion_criteria="完成一次复述。"),
            ]
        return [
            PlanTask(plan_id=plan_id, index=1, type="concept", title=f"{chosen.name}：先校准概念边界", detail=chosen.reason, est_minutes=8, completion_criteria="能复述核心定义与一个反例。"),
            PlanTask(plan_id=plan_id, index=2, type="practice", title="靶向练习 3 题", detail="题目按 ZPD/信息增益/薄弱覆盖排序。", question_ids_json=json.dumps(question_ids, ensure_ascii=False), est_minutes=14, completion_criteria="至少 2 题独立做对。"),
            PlanTask(plan_id=plan_id, index=3, type="review", title="复盘错因并安排复习", detail="答错题进入错题本，FSRS 排入复习队列。", est_minutes=6, completion_criteria="所有新增错题都有错因标签。"),
        ]

    def _task_read(self, task: PlanTask) -> PlanTaskRead:
        def parse(value: str) -> list[str]:
            try:
                loaded = json.loads(value or "[]")
            except json.JSONDecodeError:
                return []
            return [str(item) for item in loaded]

        try:
            outcome = json.loads(task.outcome_json or "{}")
        except json.JSONDecodeError:
            outcome = {}
        return PlanTaskRead(
            id=task.id,
            index=task.index,
            type=task.type,
            title=task.title,
            detail=task.detail,
            kp_ids=parse(task.kp_ids_json),
            question_ids=parse(task.question_ids_json),
            est_minutes=task.est_minutes,
            completion_criteria=task.completion_criteria,
            status=task.status,
            outcome=outcome,
        )

    def _profile_summary(self, *, user_id: str, twin_id: str, attempts_count: int) -> dict:
        rows = list(
            self.db.execute(
                select(MasteryState, KnowledgePoint)
                .join(KnowledgePoint, KnowledgePoint.id == MasteryState.kp_id)
                .where(MasteryState.user_id == user_id, MasteryState.twin_id == twin_id)
                .order_by(MasteryState.p_mastery.asc())
                .limit(5)
            )
        )
        return {
            "weak_kps": [kp.name for _, kp in rows if _.p_mastery < 0.6],
            "attempts_used": attempts_count,
            "mode": "启动方案" if attempts_count < 10 else "真实画像",
        }

    def _narrative(self, *, chosen: PlanCandidateRead, candidates: list[PlanCandidateRead], twin: LearningTwin, attempts_count: int) -> str:
        template = (
            "当前为启动方案：分身还缺少足够做题证据，本轮先用诊断题收集真实 attempt，再重新模拟路线。"
            if attempts_count < 10
            else f"推荐「{chosen.name}」。数字由 BKT/Elo/FSRS 与 200 次 rollout 计算，LLM 叙事未改写这些分数。{chosen.reason}"
        )
        # ===================== 调用大模型 (LLM API) =====================
        # 让大模型把模拟器算出的效用/收益/负荷数字，解释成给用户看的推荐理由。
        # 数字仍以算法结果为准，LLM 只负责叙事，不允许编造新数字。失败时回退模板。
        try:
            payload = {
                "分身": {"名称": twin.name, "科目": twin.subject, "目标": twin.goal},
                "已做题数": attempts_count,
                "推荐路线": {"名称": chosen.name, "策略": chosen.strategy, "效用": chosen.utility, "预期掌握提升": chosen.expected_gain, "认知负荷": chosen.cognitive_load},
                "淘汰路线": [
                    {"名称": c.name, "效用": c.utility, "预期掌握提升": c.expected_gain, "认知负荷": c.cognitive_load}
                    for c in candidates
                    if c.eliminated
                ],
            }
            system = (
                "你是学习分身的路线解说员。基于给定的推荐路线与被淘汰路线的数字，"
                "用 60-110 字中文说明为什么推荐这条、为什么淘汰其它。"
                "只能引用给定数字，不得编造新数据，不要用 Markdown，直接输出一段话。"
            )
            result = self.registry.get_llm_provider().chat(
                [LlmMessage(role="system", content=system), LlmMessage(role="user", content=json.dumps(payload, ensure_ascii=False))]
            )
            text = (result.content or "").strip()
            if text and len(text) >= 12:
                return text
        except Exception as exc:  # noqa: BLE001 - LLM 不可用时回退模板，不影响出方案
            logger.warning("Plan narrative LLM failed; using template: %s", exc)
        return template

    def _bkt_roll(self, p: float, *, is_correct: bool) -> float:
        if is_correct:
            numerator = p * (1 - BKT_SLIP)
            denominator = numerator + (1 - p) * BKT_GUESS
        else:
            numerator = p * BKT_SLIP
            denominator = numerator + (1 - p) * (1 - BKT_GUESS)
        posterior = numerator / denominator if denominator else p
        return max(0.01, min(0.99, posterior + (1 - posterior) * BKT_T))

    def _retention(self, state: MasteryState) -> float:
        if not state.last_review_at:
            return 0.75
        now = datetime.now(UTC)
        last = state.last_review_at if state.last_review_at.tzinfo else state.last_review_at.replace(tzinfo=UTC)
        days = max(0.0, (now - last).total_seconds() / 86400.0)
        stability = max(0.1, state.stability)
        return max(0.0, min(1.0, (1.0 + days / (9.0 * stability)) ** -1))

    def _profile_hash(self, *, user_id: str, twin_id: str) -> str:
        rows = list(self.db.scalars(select(MasteryState).where(MasteryState.user_id == user_id, MasteryState.twin_id == twin_id)))
        raw = "|".join(f"{s.kp_id}:{s.p_mastery:.4f}:{s.ability_elo:.1f}:{s.attempt_count}" for s in rows)
        return sha256(raw.encode("utf-8")).hexdigest()

    def _attempt_count(self, *, user_id: str, twin_id: str) -> int:
        return int(self.db.scalar(select(func.count()).select_from(Attempt).where(Attempt.user_id == user_id, Attempt.twin_id == twin_id)) or 0)

    def _require_twin(self, *, user_id: str, twin_id: str) -> LearningTwin:
        twin = self.db.scalar(select(LearningTwin).where(LearningTwin.user_id == user_id, LearningTwin.id == twin_id))
        if not twin:
            raise ValueError("Learning twin not found")
        return twin

    def _require_plan(self, *, user_id: str, plan_id: str) -> StudyPlan:
        plan = self.db.scalar(select(StudyPlan).where(StudyPlan.user_id == user_id, StudyPlan.id == plan_id))
        if not plan:
            raise ValueError("Study plan not found")
        return plan
