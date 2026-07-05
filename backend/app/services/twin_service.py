from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.conversation import Conversation
from app.db.models.document import Document
from app.db.models.document_chunk import DocumentChunk
from app.db.models.file import FileObject
from app.db.models.learning_record import LearningRecord
from app.db.models.learning_twin import LearningTwin
from app.db.models.message import Message
from app.db.repositories.learning_twin_repository import LearningTwinRepository
from app.integrations.registry import ProviderRegistry
from app.schemas.twin import (
    BlackboardResponse,
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
from app.services.twin_brain.blackboard_service import BlackboardLessonService


@dataclass(frozen=True, slots=True)
class AssetSnapshot:
    stats: SourceStats
    assets: list[str]
    document_count: int
    parsed_document_count: int
    indexed_chunk_count: int
    message_count: int
    learning_event_count: int


class TwinService:
    def __init__(self, db: Session, *, registry: ProviderRegistry | None = None) -> None:
        self.db = db
        self.twins = LearningTwinRepository(db)
        self.registry = registry

    def list_twins(self, user_id: str) -> list[LearningTwinRead]:
        twins = self.twins.list(user_id)
        return [self._read(twin) for twin in twins]

    def create_twin(self, *, user_id: str, name: str, subject: str, goal: str, stage: str | None = None) -> LearningTwinRead:
        snapshot = self._asset_snapshot(user_id)
        sync_percent, status = self._training_status(snapshot)
        twin = self.twins.create(
            user_id=user_id,
            name=name.strip() or f"{subject.strip() or '学习'}分身",
            subject=subject.strip() or "综合学习",
            goal=goal.strip() or "建立可持续同步的学习分身",
            stage=stage.strip() if stage else "待训练",
            status=status,
            sync_percent=sync_percent,
            memories_json=json.dumps(self._memory_candidates(snapshot), ensure_ascii=False),
            outputs_json="[]",
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
        if payload.avatar_data_url is not None:
            twin.avatar_data_url = payload.avatar_data_url
        snapshot = self._asset_snapshot(user_id)
        twin.sync_percent, twin.status = self._training_status(snapshot)
        twin.memories_json = json.dumps(self._memory_candidates(snapshot), ensure_ascii=False)
        return self._read(self.twins.save(twin))

    def delete_twin(self, *, user_id: str, twin_id: str) -> None:
        twin = self._require_twin(user_id=user_id, twin_id=twin_id)
        self.twins.delete(twin)

    def sync_twin(self, *, user_id: str, twin_id: str) -> TwinSyncResponse:
        twin = self._require_twin(user_id=user_id, twin_id=twin_id)
        snapshot = self._asset_snapshot(user_id)
        twin.sync_percent, twin.status = self._training_status(snapshot)
        twin.memories_json = json.dumps(self._memory_candidates(snapshot), ensure_ascii=False)
        self.twins.save(twin)
        return TwinSyncResponse(twin=self._read(twin), learned_assets=snapshot.assets)

    def simulate_routes(self, *, user_id: str, twin_id: str) -> RouteSimulationResponse:
        twin = self._require_twin(user_id=user_id, twin_id=twin_id)
        snapshot = self._asset_snapshot(user_id)
        routes = self._routes(twin=twin, snapshot=snapshot)
        optimal_path = self._optimal_path(twin=twin, snapshot=snapshot)
        evidence = self._evidence(snapshot)
        outputs = self._outputs(twin=twin, snapshot=snapshot, score=routes[0].score)
        payload = {
            "recommended_route": routes[0].model_dump(),
            "routes": [route.model_dump() for route in routes],
            "optimal_path": [step.model_dump() for step in optimal_path],
            "evidence": evidence,
        }
        train_percent, _ = self._training_status(snapshot)
        twin.sync_percent = max(train_percent, 70 if snapshot.assets or snapshot.message_count else 15)
        twin.status = "学习路径已基于真实资料生成" if snapshot.assets or snapshot.message_count else "学习路径已生成 · 等待更多训练数据"
        twin.route_snapshot_json = json.dumps(payload, ensure_ascii=False)
        twin.outputs_json = json.dumps([output.model_dump() for output in outputs], ensure_ascii=False)
        twin.memories_json = json.dumps(self._memory_candidates(snapshot), ensure_ascii=False)
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
        return self._parse_outputs(twin.outputs_json)

    def generate_outputs(self, *, user_id: str, twin_id: str) -> list[LearningOutputRead]:
        twin = self._require_twin(user_id=user_id, twin_id=twin_id)
        snapshot = self._asset_snapshot(user_id)
        score = 80
        try:
            route_snapshot = json.loads(twin.route_snapshot_json or "{}")
            score = int(route_snapshot.get("recommended_route", {}).get("score", score))
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
        outputs = self._outputs(twin=twin, snapshot=snapshot, score=score)
        twin.outputs_json = json.dumps([output.model_dump() for output in outputs], ensure_ascii=False)
        self.twins.save(twin)
        return outputs

    def weak_points(self, *, user_id: str, twin_id: str) -> list[WeakPointRead]:
        twin = self._require_twin(user_id=user_id, twin_id=twin_id)
        snapshot = self._asset_snapshot(user_id)
        topic = self._topic(twin)
        evidence = self._evidence(snapshot)
        if not snapshot.assets and not snapshot.message_count:
            return [
                WeakPointRead(
                    topic="训练数据不足",
                    severity="low",
                    evidence="当前还没有可分析的资料、对话或学习事件。",
                    next_action="先上传一份资料，或用 3-5 轮对话描述当前学习目标和卡点。",
                )
            ]
        return [
            WeakPointRead(
                topic=f"{topic} 的知识边界",
                severity="high" if snapshot.stats.mistakes else "medium",
                evidence=evidence[0] if evidence else "已有学习行为可用于初步判断。",
                next_action="先做概念澄清，再完成 2 道变式题验证是否真正掌握。",
            ),
            WeakPointRead(
                topic="输出复述完整度",
                severity="medium",
                evidence=f"历史消息 {snapshot.message_count} 条，学习事件 {snapshot.learning_event_count} 条。",
                next_action="用自己的话复述解题路径，让分身检查漏项并生成复盘清单。",
            ),
        ]

    def blackboard(self, *, user_id: str, twin_id: str, topic: str | None = None) -> BlackboardResponse:
        return BlackboardLessonService(self.db, registry=self.registry).get_lesson(user_id=user_id, twin_id=twin_id, topic=topic)

    def _create_default_twin(self, user_id: str) -> LearningTwin:
        snapshot = self._asset_snapshot(user_id)
        sync_percent, status = self._training_status(snapshot)
        return self.twins.create(
            user_id=user_id,
            name="学习分身",
            subject="综合学习",
            goal="持续同步资料、对话和学习行为，生成下一步学习路径",
            stage="待训练",
            status=status,
            sync_percent=sync_percent,
            memories_json=json.dumps(self._memory_candidates(snapshot), ensure_ascii=False),
            outputs_json="[]",
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
            level=twin.level,
            xp=twin.xp,
            avatar_data_url=twin.avatar_data_url,
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
        messages = self.db.scalar(select(func.count()).select_from(Message).where(Message.user_id == user_id)) or 0
        records = self.db.scalar(select(func.count()).select_from(LearningRecord).where(LearningRecord.user_id == user_id)) or 0
        documents = self.db.scalar(select(func.count()).select_from(Document).where(Document.user_id == user_id)) or 0
        parsed_documents = self.db.scalar(
            select(func.count()).select_from(Document).where(Document.user_id == user_id, Document.status == "parsed")
        ) or 0
        indexed_chunks = self.db.scalar(
            select(func.count()).select_from(DocumentChunk).where(
                DocumentChunk.user_id == user_id,
                DocumentChunk.embedding_json.is_not(None),
            )
        ) or 0
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
        if documents:
            assets.append(f"文档记录：{int(documents)} 份")
        if parsed_documents:
            assets.append(f"已解析文档：{int(parsed_documents)} 份")
        if indexed_chunks:
            assets.append(f"已索引片段：{int(indexed_chunks)} 段")
        if records:
            assets.append(f"学习行为记录：{int(records)} 条")
        if messages:
            assets.append(f"历史消息：{int(messages)} 条")
        return AssetSnapshot(
            stats=stats,
            assets=assets,
            document_count=int(documents),
            parsed_document_count=int(parsed_documents),
            indexed_chunk_count=int(indexed_chunks),
            message_count=int(messages),
            learning_event_count=int(records),
        )

    def _training_status(self, snapshot: AssetSnapshot) -> tuple[int, str]:
        if not snapshot.assets and not snapshot.message_count:
            return 0, "待训练 · 上传资料或开始对话"
        percent = 20
        if snapshot.document_count:
            percent += 20
        if snapshot.parsed_document_count:
            percent += 25
        if snapshot.indexed_chunk_count:
            percent += 25
        if snapshot.message_count:
            percent += min(20, snapshot.message_count * 2)
        if snapshot.learning_event_count:
            percent += min(10, snapshot.learning_event_count)
        percent = min(100, percent)
        if snapshot.indexed_chunk_count:
            status = f"训练中 · 已索引 {snapshot.indexed_chunk_count} 段资料"
        elif snapshot.parsed_document_count:
            status = f"训练中 · 已解析 {snapshot.parsed_document_count} 份资料"
        elif snapshot.document_count:
            status = f"训练中 · 已登记 {snapshot.document_count} 份资料"
        else:
            status = f"训练中 · 已读取 {snapshot.message_count} 条对话"
        return percent, status

    def _memory_candidates(self, snapshot: AssetSnapshot) -> list[str]:
        memories: list[str] = []
        if snapshot.stats.mistakes:
            memories.append(f"错题资料出现 {snapshot.stats.mistakes} 份，需要优先做变式验证")
        if snapshot.stats.audio:
            memories.append(f"口语/音频资料 {snapshot.stats.audio} 份，可参与表达能力训练")
        if snapshot.parsed_document_count:
            memories.append(f"已解析 {snapshot.parsed_document_count} 份资料，可用于生成学习路径")
        if snapshot.indexed_chunk_count:
            memories.append(f"已索引 {snapshot.indexed_chunk_count} 段资料，可用于引用式回答")
        if snapshot.message_count:
            memories.append(f"最近 {snapshot.message_count} 条对话可参与阶段判断")
        return memories

    def _recent_conversations(self, user_id: str) -> list[TwinConversationSummary]:
        statement = select(Conversation).where(Conversation.user_id == user_id).order_by(Conversation.updated_at.desc()).limit(3)
        conversations = list(self.db.scalars(statement))
        return [TwinConversationSummary(title=item.title, status="已同步到分身") for item in conversations]

    def _work_steps(self, snapshot: AssetSnapshot) -> list[WorkStepRead]:
        total_sources = (
            snapshot.stats.assignments
            + snapshot.stats.mistakes
            + snapshot.stats.notes
            + snapshot.stats.courseware
            + snapshot.stats.audio
        )
        if total_sources == 0 and snapshot.message_count == 0:
            return [
                WorkStepRead(title="等待训练数据", detail="上传资料或开始对话后生成分身画像", state="pending"),
                WorkStepRead(title="生成学习路径", detail="需要至少一条资料、对话或学习事件", state="pending"),
            ]
        return [
            WorkStepRead(title="收集资料", detail=f"资料 {total_sources} 份 · 对话 {snapshot.stats.conversations} 次", state="done"),
            WorkStepRead(
                title="解析与分块",
                detail=f"已解析 {snapshot.parsed_document_count}/{snapshot.document_count} 份 · 索引 {snapshot.indexed_chunk_count} 段",
                state="done" if snapshot.parsed_document_count else "active",
            ),
            WorkStepRead(title="更新分身画像", detail=f"记忆候选 {len(self._memory_candidates(snapshot))} 条", state="active"),
            WorkStepRead(title="推荐学习路径", detail="基于资料、对话和目标生成下一步", state="pending"),
            WorkStepRead(title="交付学习方案", detail="路径、黑板提纲、练习清单和复盘任务", state="pending"),
        ]

    def _routes(self, *, twin: LearningTwin, snapshot: AssetSnapshot) -> list[RouteOptionRead]:
        evidence_bonus = min(
            18,
            snapshot.parsed_document_count * 3
            + snapshot.indexed_chunk_count // 4
            + snapshot.stats.mistakes * 2
            + snapshot.message_count // 2
            + snapshot.learning_event_count,
        )
        route_a_score = min(96, 80 + evidence_bonus)
        route_b_score = max(60, route_a_score - (8 if snapshot.stats.mistakes else 12))
        route_c_score = max(58, route_a_score - (5 if snapshot.message_count else 15))
        topic = self._topic(twin)
        return [
            RouteOptionRead(
                name="路线 A",
                strategy=f"先补清 {topic} 的关键概念，再做 2 道变式验证",
                score=route_a_score,
                duration_minutes=25,
                cognitive_load="中",
                forgetting_risk="低" if snapshot.parsed_document_count else "中",
                teachers=["规划老师", "概念老师", "训练老师", "复盘老师"],
                rationale="优先把分身已掌握的资料和最近对话转成可验证动作，收益稳定。",
            ),
            RouteOptionRead(
                name="路线 B",
                strategy="直接做题或输出任务，分身实时标记错因",
                score=route_b_score,
                duration_minutes=18,
                cognitive_load="高",
                forgetting_risk="高" if not snapshot.parsed_document_count else "中",
                teachers=["训练老师", "错因老师"],
                rationale="适合时间很少的情况，但证据不足时容易只记住题面。",
            ),
            RouteOptionRead(
                name="路线 C",
                strategy="先看黑板讲解，再复述总结并生成复盘清单",
                score=route_c_score,
                duration_minutes=30,
                cognitive_load="低",
                forgetting_risk="低",
                teachers=["推导老师", "表达老师", "复盘老师"],
                rationale="更适合概念不稳或需要长期记忆沉淀的任务。",
            ),
        ]

    def _optimal_path(self, *, twin: LearningTwin, snapshot: AssetSnapshot) -> list[StudyPathStepRead]:
        topic = self._topic(twin)
        first_title = "上传或补充一份核心资料" if not snapshot.assets else f"定位 {topic} 的核心薄弱点"
        return [
            StudyPathStepRead(index=1, title=first_title, teacher="规划老师", mode="资料诊断", verification="形成 1 条明确学习目标"),
            StudyPathStepRead(index=2, title=f"补清 {topic} 的定义、条件和易错边界", teacher="概念老师", mode="分步讲解", verification="能用自己的话复述"),
            StudyPathStepRead(index=3, title="完成 2 道变式题或 1 次输出复述", teacher="训练老师", mode="互动练习", verification="记录错因、耗时和卡点"),
            StudyPathStepRead(index=4, title="生成今日交付清单并安排 24 小时复测", teacher="复盘老师", mode="复盘计划", verification="形成下一次复习入口"),
        ]

    def _evidence(self, snapshot: AssetSnapshot) -> list[str]:
        source_count = (
            snapshot.stats.assignments
            + snapshot.stats.mistakes
            + snapshot.stats.notes
            + snapshot.stats.courseware
            + snapshot.stats.audio
        )
        evidence: list[str] = []
        evidence.append(f"资料来源：{source_count} 份文件，{snapshot.parsed_document_count} 份已解析，{snapshot.indexed_chunk_count} 段已索引")
        evidence.append(f"学习行为：{snapshot.stats.conversations} 次会话，{snapshot.message_count} 条消息，{snapshot.learning_event_count} 条事件")
        if snapshot.stats.mistakes:
            evidence.append(f"错题信号：{snapshot.stats.mistakes} 份错题资料，需要优先验证边界")
        if not snapshot.assets and not snapshot.message_count:
            evidence.append("证据不足：当前路径只作为启动建议，上传资料后会重新计算")
        return evidence

    def _outputs(self, *, twin: LearningTwin, snapshot: AssetSnapshot, score: int) -> list[LearningOutputRead]:
        topic = self._topic(twin)
        source_note = f"基于 {snapshot.parsed_document_count} 份已解析资料和 {snapshot.message_count} 条消息"
        if not snapshot.assets and not snapshot.message_count:
            source_note = "基于分身目标生成的启动方案，等待资料训练后更新"
        return [
            LearningOutputRead(title=f"{topic} 推荐学习路径", type="路径", detail=f"4 步 · 约 25 分钟 · 收益评分 {score} · {source_note}", status="已生成方案"),
            LearningOutputRead(title=f"{topic} 黑板讲解提纲", type="黑板", detail="3 步：问题拆解、证据提取、训练验证", status="可在黑板页查看"),
            LearningOutputRead(title=f"{topic} 练习任务清单", type="练习", detail="2 道变式题或 1 次输出复述，完成后写入学习事件", status="待完成"),
            LearningOutputRead(title=f"{topic} 复盘交付清单", type="复盘", detail="错因、证据、下一次复测时间，不伪造 PDF/Word 文件", status="待复盘"),
            LearningOutputRead(title=f"{topic} 视频讲解", type="视频", detail="当前未生成视频文件；M4 接入 TTS/视频能力后再开放导出。", status="未生成"),
            LearningOutputRead(title=f"{topic} PDF 报告", type="PDF", detail="当前未生成 PDF 文件；仅保留交付占位，避免假文件成功。", status="未生成"),
            LearningOutputRead(title=f"{topic} Word 复盘", type="Word", detail="当前未生成 Word 文件；后续接入文档导出后再开放。", status="未生成"),
        ]

    def _topic(self, twin: LearningTwin) -> str:
        subject = (twin.subject or "综合学习").strip()
        goal = (twin.goal or "").strip()
        if goal:
            return f"{subject}：{goal[:28]}"
        return subject

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
