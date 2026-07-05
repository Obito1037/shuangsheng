from __future__ import annotations

import re
from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.document import Document
from app.db.models.document_chunk import DocumentChunk
from app.db.models.learning_twin import LearningTwin
from app.db.models.twin_brain import ChunkKnowledgePoint, KnowledgePoint, MasteryState, Question

STOP_WORDS = {
    "the",
    "and",
    "with",
    "for",
    "that",
    "this",
    "from",
    "into",
    "your",
    "学习",
    "资料",
    "内容",
    "问题",
    "方法",
    "步骤",
}


class KnowledgeGraphService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def extract_from_document(self, *, user_id: str, twin_id: str | None, document_id: str) -> list[KnowledgePoint]:
        if not twin_id:
            return []
        twin = self.db.scalar(select(LearningTwin).where(LearningTwin.id == twin_id, LearningTwin.user_id == user_id))
        document = self.db.scalar(select(Document).where(Document.id == document_id, Document.user_id == user_id))
        if not twin or not document:
            return []
        chunks = list(
            self.db.scalars(
                select(DocumentChunk)
                .where(DocumentChunk.user_id == user_id, DocumentChunk.document_id == document_id)
                .order_by(DocumentChunk.chunk_index.asc())
            )
        )
        created_or_seen: dict[str, KnowledgePoint] = {}
        for chunk in chunks:
            candidates = self._candidate_names(chunk.text, fallback=document.title)
            for name, weight in candidates:
                kp = self.get_or_create(
                    user_id=user_id,
                    twin_id=twin.id,
                    name=name,
                    subject=twin.subject,
                    source="seed",
                    description="简化模式：由本地知识点抽取器根据真实资料片段生成，后续可由 LLM Schema 抽取校准。",
                )
                self._ensure_chunk_link(user_id=user_id, twin_id=twin.id, chunk_id=chunk.id, kp_id=kp.id, weight=weight)
                self.ensure_mastery_state(user_id=user_id, twin_id=twin.id, kp_id=kp.id)
                created_or_seen[kp.id] = kp
        self._seed_diagnostic_questions(user_id=user_id, twin_id=twin.id, document=document, points=list(created_or_seen.values()))
        self.db.commit()
        return list(created_or_seen.values())

    def get_or_create(
        self,
        *,
        user_id: str,
        twin_id: str,
        name: str,
        subject: str,
        source: str = "seed",
        description: str = "",
    ) -> KnowledgePoint:
        clean_name = self._clean_name(name)
        existing = self.db.scalar(
            select(KnowledgePoint).where(
                KnowledgePoint.user_id == user_id,
                KnowledgePoint.twin_id == twin_id,
                func.lower(KnowledgePoint.name) == clean_name.lower(),
            )
        )
        if existing:
            return existing
        kp = KnowledgePoint(
            user_id=user_id,
            twin_id=twin_id,
            name=clean_name,
            subject=subject or "综合学习",
            source=source,
            description=description,
        )
        self.db.add(kp)
        self.db.flush()
        return kp

    def ensure_mastery_state(self, *, user_id: str, twin_id: str, kp_id: str) -> MasteryState:
        existing = self.db.scalar(
            select(MasteryState).where(
                MasteryState.user_id == user_id,
                MasteryState.twin_id == twin_id,
                MasteryState.kp_id == kp_id,
            )
        )
        if existing:
            return existing
        state = MasteryState(user_id=user_id, twin_id=twin_id, kp_id=kp_id)
        self.db.add(state)
        self.db.flush()
        return state

    def _ensure_chunk_link(self, *, user_id: str, twin_id: str, chunk_id: str, kp_id: str, weight: float) -> None:
        existing = self.db.scalar(
            select(ChunkKnowledgePoint).where(
                ChunkKnowledgePoint.user_id == user_id,
                ChunkKnowledgePoint.twin_id == twin_id,
                ChunkKnowledgePoint.chunk_id == chunk_id,
                ChunkKnowledgePoint.kp_id == kp_id,
            )
        )
        if existing:
            existing.weight = max(existing.weight, weight)
            self.db.add(existing)
            return
        self.db.add(ChunkKnowledgePoint(user_id=user_id, twin_id=twin_id, chunk_id=chunk_id, kp_id=kp_id, weight=weight))

    def _seed_diagnostic_questions(self, *, user_id: str, twin_id: str, document: Document, points: list[KnowledgePoint]) -> None:
        for kp in points[:8]:
            exists = self.db.scalar(
                select(Question).where(
                    Question.user_id == user_id,
                    Question.twin_id == twin_id,
                    Question.stem.like(f"%{kp.name}%"),
                    Question.source == "diagnostic",
                )
            )
            if exists:
                continue
            question = Question(
                user_id=user_id,
                twin_id=twin_id,
                kp_ids_json=f'["{kp.id}"]',
                stem=f"请用自己的话说明「{kp.name}」的核心含义，并指出一个容易混淆的边界。",
                answer=f"参考资料《{document.title}》中与「{kp.name}」相关的片段，完成概念复述和边界说明。",
                solution="简化模式诊断题：用于收集真实作答数据，不自动判定内容对错，需要你提交自评结果。",
                source="diagnostic",
                difficulty_elo=1200.0,
            )
            self.db.add(question)

    def _candidate_names(self, text: str, *, fallback: str) -> list[tuple[str, float]]:
        names: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            heading = re.sub(r"^[#>\-\*\d\.\s]+", "", stripped).strip()
            if 2 <= len(heading) <= 28 and any(ch in stripped[:4] for ch in ("#", "第", "一", "1", "-", "*")):
                names.append(heading)
        names.extend(re.findall(r"[A-Za-z][A-Za-z0-9_\- ]{2,28}", text))
        names.extend(re.findall(r"[\u4e00-\u9fff]{2,12}(?:概念|公式|定理|方法|模型|函数|方程|语法|结构|原则|规律)", text))
        names.extend(re.findall(r"(?:[\u4e00-\u9fff]{2,8})(?:的)?(?:定义|性质|应用|推导|证明|用法)", text))
        if fallback:
            names.append(fallback.rsplit(".", 1)[0])
        counts = Counter(self._clean_name(name) for name in names)
        ranked: list[tuple[str, float]] = []
        for name, count in counts.most_common(6):
            if self._valid_name(name):
                ranked.append((name, min(1.0, 0.45 + count * 0.15)))
        return ranked[:4]

    def _clean_name(self, name: str) -> str:
        clean = re.sub(r"\s+", " ", name).strip(" ：:，,。.；;、\t\r\n")
        return clean[:80] or "未归类知识点"

    def _valid_name(self, name: str) -> bool:
        if len(name) < 2 or len(name) > 80:
            return False
        if name.lower() in STOP_WORDS:
            return False
        return any(ch.isalnum() or "\u4e00" <= ch <= "\u9fff" for ch in name)
