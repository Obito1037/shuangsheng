from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.conversation import Conversation
from app.db.models.file import FileObject
from app.db.models.learning_record import LearningRecord
from app.db.models.learning_twin import LearningTwin
from app.db.repositories.learning_twin_repository import LearningTwinRepository
from app.schemas.twin import (
    BlackboardResponse,
    BlackboardStepRead,
    LearningOutputRead,
    LearningTwinRead,
    RouteOptionRead,
    RouteSimulationResponse,
    SourceStats,
    StudyPathStepRead,
    TwinConversationSummary,
    TwinSyncResponse,
    TwinUpdateRequest,
    WeakPointRead,
    WorkStepRead,
)

DEFAULT_MEMORIES = [
    "HAVING 与 WHERE 容易混淆",
    "更适合先看例题再做变式题",
    "SQL 任务通常在晚上完成",
]


@dataclass(frozen=True, slots=True)
class AssetSnapshot:
    stats: SourceStats
    assets: list[str]


class TwinService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.twins = LearningTwinRepository(db)

    def list_twins(self, user_id: str) -> list[LearningTwinRead]:
        twins = self.twins.list(user_id)
        return [self._read(twin) for twin in twins]

    def create_twin(self, *, user_id: str, name: str, subject: str, goal: str, stage: str | None = None) -> LearningTwinRead:
        snapshot = self._asset_snapshot(user_id)
        twin = self.twins.create(
            user_id=user_id,
            name=name.strip() or f"{subject.strip() or '学习'}分身",
            subject=subject.strip() or "综合学习",
            goal=goal.strip() or "建立可持续同步的学习分身",
            stage=stage.strip() if stage else "同步资料中",
            status="同步 12% · 正在读取资料",
            sync_percent=12,
            memories_json=json.dumps(self._memory_candidates(snapshot), ensure_ascii=False),
        )
        return self._read(twin)

    def get_twin(self, *, user_id: str, twin_id: str) -> LearningTwinRead:
        return self._read(self._require_twin(user_id=user_id, twin_id=twin_id))

    def update_twin(self, *, user_id: str, twin_id: str, payload: TwinUpdateRequest) -> LearningTwinRead:
        twin = self._require_twin(user_id=user_id, twin_id=twin_id)
        if payload.name is not None:
            twin.name = payload.name.strip() or twin.name
        if payload.subject is not None:
            twin.subject = payload.subject.strip() or twin.subject
        if payload.goal is not None:
            twin.goal = payload.goal.strip() or twin.goal
        if payload.stage is not None:
            twin.stage = payload.stage.strip() or twin.stage
        return self._read(self.twins.save(twin))

    def delete_twin(self, *, user_id: str, twin_id: str) -> None:
        twin = self._require_twin(user_id=user_id, twin_id=twin_id)
        self.twins.delete(twin)

    def sync_twin(self, *, user_id: str, twin_id: str) -> TwinSyncResponse:
        twin = self._require_twin(user_id=user_id, twin_id=twin_id)
        snapshot = self._asset_snapshot(user_id)
        twin.sync_percent = min(100, max(twin.sync_percent, 68 if snapshot.assets else 24))
        twin.status = f"同步 {twin.sync_percent}% · 已更新认知模型"
        twin.memories_json = json.dumps(self._memory_candidates(snapshot), ensure_ascii=False)
        self.twins.save(twin)
        return TwinSyncResponse(twin=self._read(twin), learned_assets=snapshot.assets)

    def simulate_routes(self, *, user_id: str, twin_id: str) -> RouteSimulationResponse:
        twin = self._require_twin(user_id=user_id, twin_id=twin_id)
        snapshot = self._asset_snapshot(user_id)
        routes = self._routes(snapshot)
        optimal_path = self._optimal_path(twin.subject)
        evidence = self._evidence(snapshot)
        outputs = self._outputs(twin.subject, routes[0].score)
        payload = {
            "recommended_route": routes[0].model_dump(),
            "routes": [route.model_dump() for route in routes],
            "optimal_path": [step.model_dump() for step in optimal_path],
            "evidence": evidence,
        }
        twin.sync_percent = max(twin.sync_percent, 72)
        twin.status = f"同步 {twin.sync_percent}% · 路线模拟完成"
        twin.route_snapshot_json = json.dumps(payload, ensure_ascii=False)
        twin.outputs_json = json.dumps([output.model_dump() for output in outputs], ensure_ascii=False)
        self.twins.save(twin)
        return RouteSimulationResponse(
            twin_id=twin.id,
            recommended_route=routes[0],
            routes=routes,
            optimal_path=optimal_path,
            evidence=evidence,
            outputs=outputs,
        )

    def list_outputs(self, *, user_id: str, twin_id: str) -> list[LearningOutputRead]:
        twin = self._require_twin(user_id=user_id, twin_id=twin_id)
        outputs = self._parse_outputs(twin.outputs_json)
        if not outputs:
            outputs = self._outputs(twin.subject, score=88)
            twin.outputs_json = json.dumps([output.model_dump() for output in outputs], ensure_ascii=False)
            self.twins.save(twin)
        return outputs

    def generate_outputs(self, *, user_id: str, twin_id: str) -> list[LearningOutputRead]:
        twin = self._require_twin(user_id=user_id, twin_id=twin_id)
        score = 92
        try:
            snapshot = json.loads(twin.route_snapshot_json or "{}")
            score = int(snapshot.get("recommended_route", {}).get("score", score))
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
        outputs = self._outputs(twin.subject, score=score)
        twin.outputs_json = json.dumps([output.model_dump() for output in outputs], ensure_ascii=False)
        self.twins.save(twin)
        return outputs

    def weak_points(self, *, user_id: str, twin_id: str) -> list[WeakPointRead]:
        twin = self._require_twin(user_id=user_id, twin_id=twin_id)
        snapshot = self._asset_snapshot(user_id)
        topic = "GROUP BY / HAVING 边界" if "数据" in twin.subject or "SQL" in twin.subject.upper() else f"{twin.subject} 核心概念"
        weak_points = [
            WeakPointRead(
                topic=topic,
                severity="high" if snapshot.stats.mistakes else "medium",
                evidence=f"错题 {snapshot.stats.mistakes} 份，课件 {snapshot.stats.courseware} 份，对话 {snapshot.stats.conversations} 次",
                next_action="先做概念澄清，再用 2 道变式题验证是否真正掌握。",
            ),
            WeakPointRead(
                topic="输出复述完整度",
                severity="medium",
                evidence="历史对话和资料摘要尚未形成稳定复述记录",
                next_action="用自己的话复述解题路径，并让分身检查漏项。",
            ),
        ]
        return weak_points

    def blackboard(self, *, user_id: str, twin_id: str, topic: str | None = None) -> BlackboardResponse:
        twin = self._require_twin(user_id=user_id, twin_id=twin_id)
        selected_topic = topic or ("GROUP BY 和 HAVING" if "数据" in twin.subject or "SQL" in twin.subject.upper() else twin.subject)
        steps = [
            BlackboardStepRead(
                index=1,
                title="先确定问题要按什么分组",
                explanation="把题目中的统计对象圈出来，先找每组的边界，再决定 SELECT 里哪些字段可以出现。",
                formula="GROUP BY 分组字段",
                check_question="这道题的每一组代表什么？",
            ),
            BlackboardStepRead(
                index=2,
                title="WHERE 先过滤行，HAVING 后过滤组",
                explanation="WHERE 发生在聚合前，只能看原始行；HAVING 发生在聚合后，可以判断 COUNT、SUM 等聚合结果。",
                formula="WHERE row_condition -> GROUP BY -> HAVING aggregate_condition",
                check_question="这个条件是在分组前成立，还是分组后才知道？",
            ),
            BlackboardStepRead(
                index=3,
                title="用变式题验证边界",
                explanation="把同一道题改成不同阈值或不同分组字段，检查你是否只是记住答案，还是掌握了判断流程。",
                check_question="如果把 COUNT(*) > 2 改成 AVG(score) > 80，SQL 哪部分变化？",
            ),
        ]
        return BlackboardResponse(twin_id=twin.id, topic=selected_topic, steps=steps)

    def _create_default_twin(self, user_id: str) -> LearningTwin:
        snapshot = self._asset_snapshot(user_id)
        return self.twins.create(
            user_id=user_id,
            name="数据库考试分身",
            subject="数据库",
            goal="两周内补齐 SQL 聚合函数与查询逻辑",
            stage="期末冲刺",
            status="同步 68% · 正在模拟",
            sync_percent=68,
            memories_json=json.dumps(self._memory_candidates(snapshot), ensure_ascii=False),
            outputs_json=json.dumps([output.model_dump() for output in self._outputs("数据库", 92)], ensure_ascii=False),
        )

    def _require_twin(self, *, user_id: str, twin_id: str) -> LearningTwin:
        twin = self.twins.get(user_id=user_id, twin_id=twin_id)
        if not twin:
            raise ValueError("Learning twin not found")
        return twin

    def _read(self, twin: LearningTwin) -> LearningTwinRead:
        snapshot = self._asset_snapshot(twin.user_id)
        return LearningTwinRead(
            id=twin.id,
            name=twin.name,
            subject=twin.subject,
            goal=twin.goal,
            stage=twin.stage,
            status=twin.status,
            sync_percent=twin.sync_percent,
            source_stats=snapshot.stats,
            memories=self._parse_memories(twin.memories_json),
            recent_conversations=self._recent_conversations(twin.user_id),
            current_work=self._work_steps(snapshot),
            outputs=self._parse_outputs(twin.outputs_json),
            created_at=twin.created_at,
            updated_at=twin.updated_at,
        )

    def _asset_snapshot(self, user_id: str) -> AssetSnapshot:
        files = list(self.db.scalars(select(FileObject).where(FileObject.user_id == user_id)))
        conversations = self.db.scalar(select(func.count()).select_from(Conversation).where(Conversation.user_id == user_id)) or 0
        records = self.db.scalar(select(func.count()).select_from(LearningRecord).where(LearningRecord.user_id == user_id)) or 0
        stats = SourceStats(conversations=int(conversations))
        assets: list[str] = []
        for file in files:
            name = file.original_name.lower()
            suffix = Path(name).suffix
            if file.content_type.startswith("audio/") or suffix in {".wav", ".mp3", ".m4a"}:
                stats.audio += 1
                assets.append(f"口语语音：{file.original_name}")
            elif "错" in file.original_name or "mistake" in name or "error" in name:
                stats.mistakes += 1
                assets.append(f"错题：{file.original_name}")
            elif suffix in {".ppt", ".pptx", ".pdf"}:
                stats.courseware += 1
                assets.append(f"课件：{file.original_name}")
            elif suffix in {".md", ".txt", ".docx"}:
                stats.notes += 1
                assets.append(f"笔记：{file.original_name}")
            else:
                stats.assignments += 1
                assets.append(f"资料：{file.original_name}")
        if records:
            assets.append(f"学习行为记录：{records} 条")
        return AssetSnapshot(stats=stats, assets=assets)

    def _memory_candidates(self, snapshot: AssetSnapshot) -> list[str]:
        memories = list(DEFAULT_MEMORIES)
        if snapshot.stats.mistakes:
            memories.insert(0, f"错题重复出现 {snapshot.stats.mistakes} 次，需要变式验证")
        if snapshot.stats.audio:
            memories.append("口语表达会参与理解与表达能力判断")
        if snapshot.stats.conversations:
            memories.append(f"最近 {snapshot.stats.conversations} 次对话会参与路线模拟")
        return memories

    def _recent_conversations(self, user_id: str) -> list[TwinConversationSummary]:
        statement = select(Conversation).where(Conversation.user_id == user_id).order_by(Conversation.updated_at.desc()).limit(3)
        conversations = list(self.db.scalars(statement))
        if not conversations:
            return [
                TwinConversationSummary(title="SQL 聚合函数复习", status="正在模拟 · 刚刚"),
                TwinConversationSummary(title="HAVING 错因分析", status="已生成黑板讲解 · 昨天"),
            ]
        return [TwinConversationSummary(title=item.title, status="已同步到分身") for item in conversations]

    def _work_steps(self, snapshot: AssetSnapshot) -> list[WorkStepRead]:
        total_sources = (
            snapshot.stats.assignments
            + snapshot.stats.mistakes
            + snapshot.stats.notes
            + snapshot.stats.courseware
            + snapshot.stats.audio
        )
        return [
            WorkStepRead(title="检索资料", detail=f"资料 {total_sources} 份 · 对话 {snapshot.stats.conversations} 次", state="done"),
            WorkStepRead(title="更新认知模型", detail="记录高频错误、表达习惯和阶段目标", state="done"),
            WorkStepRead(title="并发模拟路线", detail="路线 A / B / C", state="active"),
            WorkStepRead(title="选择最优路径", detail="等待收益评分", state="pending"),
            WorkStepRead(title="生成学习方案", detail="黑板讲解、视频和文档可用", state="pending"),
        ]

    def _routes(self, snapshot: AssetSnapshot) -> list[RouteOptionRead]:
        evidence_bonus = min(10, snapshot.stats.mistakes * 2 + snapshot.stats.courseware + snapshot.stats.conversations)
        route_a_score = min(96, 84 + evidence_bonus)
        route_c_score = max(76, route_a_score - 13)
        route_b_score = max(68, route_a_score - 21)
        return [
            RouteOptionRead(
                name="路线 A",
                strategy="先补 GROUP BY / HAVING，再做变式验证",
                score=route_a_score,
                duration_minutes=25,
                cognitive_load="低",
                forgetting_risk="中",
                teachers=["规划老师", "概念老师", "训练老师", "表达老师"],
                rationale="先修复隐藏漏洞，再用输出验证是否真正掌握。",
            ),
            RouteOptionRead(
                name="路线 B",
                strategy="直接刷题，错因老师实时纠偏",
                score=route_b_score,
                duration_minutes=18,
                cognitive_load="高",
                forgetting_risk="高",
                teachers=["训练老师", "错因老师"],
                rationale="短期提速明显，但容易把概念漏洞带进下一轮题目。",
            ),
            RouteOptionRead(
                name="路线 C",
                strategy="先看黑板讲解，再复述总结",
                score=route_c_score,
                duration_minutes=30,
                cognitive_load="中",
                forgetting_risk="低",
                teachers=["概念老师", "推导老师", "表达老师"],
                rationale="理解更稳，但对临近任务的收益略低于先补漏洞。",
            ),
        ]

    def _optimal_path(self, subject: str) -> list[StudyPathStepRead]:
        topic = "GROUP BY 和 HAVING" if "数据" in subject or "SQL" in subject.upper() else "当前薄弱知识"
        return [
            StudyPathStepRead(
                index=1,
                title=f"补清 {topic} 的边界",
                teacher="概念老师",
                mode="分步讲解",
                verification="口头复述定义",
            ),
            StudyPathStepRead(index=2, title="做 3 道变式题验证", teacher="训练老师", mode="互动练习", verification="记录错因和耗时"),
            StudyPathStepRead(
                index=3,
                title="用自己的话总结解题路线",
                teacher="表达老师",
                mode="输出训练",
                verification="检查表达是否完整",
            ),
            StudyPathStepRead(
                index=4,
                title="24 小时后间隔复测",
                teacher="规划老师",
                mode="复习提醒",
                verification="区分短暂记住和真正掌握",
            ),
        ]

    def _evidence(self, snapshot: AssetSnapshot) -> list[str]:
        source_count = (
            snapshot.stats.assignments
            + snapshot.stats.mistakes
            + snapshot.stats.notes
            + snapshot.stats.courseware
            + snapshot.stats.audio
        )
        return [
            f"RAG 检索库：资料 {source_count} 份",
            f"错题模式：{snapshot.stats.mistakes} 个高频错误信号",
            f"历史对话：{snapshot.stats.conversations} 次学习阶段描述",
            "长期记忆：薄弱点、偏好和可执行时间参与评分",
        ]

    def _outputs(self, subject: str, score: int) -> list[LearningOutputRead]:
        topic = "SQL 聚合函数" if "数据" in subject or "SQL" in subject.upper() else subject
        return [
            LearningOutputRead(title=f"{topic} 查漏补缺路径", type="路径", detail=f"4 步 · 25 分钟 · 收益 {score}", status="已生成"),
            LearningOutputRead(title=f"{topic} 黑板讲解", type="黑板", detail="步骤 2/5 · 已生成", status="可播放"),
            LearningOutputRead(title=f"{topic} 2 分钟讲解", type="视频", detail="视频草稿 · 可编辑", status="草稿"),
            LearningOutputRead(title=f"{topic} 复述练习.pdf", type="PDF", detail="已导出 · 6 页", status="已导出"),
            LearningOutputRead(title=f"{topic} 错因分析.docx", type="Word", detail="文档 · 已完成", status="已完成"),
        ]

    def _parse_memories(self, value: str) -> list[str]:
        try:
            loaded = json.loads(value or "[]")
        except json.JSONDecodeError:
            return []
        return [str(item) for item in loaded if str(item).strip()]

    def _parse_outputs(self, value: str) -> list[LearningOutputRead]:
        try:
            loaded = json.loads(value or "[]")
        except json.JSONDecodeError:
            return []
        outputs: list[LearningOutputRead] = []
        for item in loaded:
            if isinstance(item, dict):
                outputs.append(LearningOutputRead.model_validate(item))
        return outputs
