from __future__ import annotations

import json
import math
import random

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.document import Document
from app.db.models.document_chunk import DocumentChunk
from app.db.models.learning_twin import LearningTwin
from app.db.models.twin_brain import ChunkKnowledgePoint, KnowledgePoint, KpEdge, MasteryState
from app.schemas.memory_map import (
    DocLegend,
    KpLink,
    KpNode,
    MemoryMapResponse,
    MemorySummary,
    VectorPoint,
)

SCAN_LIMIT = 80


class MemoryMapService:
    """把分身的 RAG 记忆变成可视化数据：文本向量的 2D 投影 + 知识点图谱。

    文本向量来自 vivo m3e-base embedding（在文档解析时写入 document_chunks.embedding_json）。
    这里用纯 Python PCA 把高维向量降到 2D 供前端散点展示，不引入 numpy 依赖。
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_map(self, *, user_id: str, twin_id: str) -> MemoryMapResponse:
        twin = self.db.scalar(
            select(LearningTwin).where(LearningTwin.id == twin_id, LearningTwin.user_id == user_id)
        )
        if not twin:
            raise ValueError("Learning twin not found")

        chunks = list(
            self.db.scalars(
                select(DocumentChunk)
                .where(DocumentChunk.user_id == user_id, DocumentChunk.twin_id == twin_id)
                .order_by(DocumentChunk.created_at.asc())
                .limit(SCAN_LIMIT)
            )
        )
        documents = list(
            self.db.scalars(
                select(Document).where(Document.user_id == user_id, Document.twin_id == twin_id)
            )
        )
        doc_index: dict[str, int] = {}
        doc_titles: list[str] = []
        for chunk in chunks:
            if chunk.source not in doc_index:
                doc_index[chunk.source] = len(doc_titles)
                doc_titles.append(chunk.source)

        embedded_vectors: list[tuple[DocumentChunk, list[float]]] = []
        for chunk in chunks:
            vector = self._parse_vector(chunk.embedding_json)
            if vector:
                embedded_vectors.append((chunk, vector))

        dim = len(embedded_vectors[0][1]) if embedded_vectors else 0
        coords = self._pca_2d([vec for _, vec in embedded_vectors]) if len(embedded_vectors) >= 2 else []

        vectors: list[VectorPoint] = []
        embedded_ids = {chunk.id for chunk, _ in embedded_vectors}
        for offset, (chunk, _) in enumerate(embedded_vectors):
            x, y = coords[offset] if offset < len(coords) else (0.0, 0.0)
            vectors.append(
                VectorPoint(
                    id=chunk.id,
                    source=chunk.source,
                    doc_index=doc_index.get(chunk.source, 0),
                    text_preview=chunk.text.strip().replace("\n", " ")[:90],
                    x=round(x, 4),
                    y=round(y, 4),
                    embedded=True,
                )
            )
        # 未 embedding 的分块也列出（云端 embedding 完成后会带向量），用确定性布局占位
        pending = [chunk for chunk in chunks if chunk.id not in embedded_ids]
        for offset, chunk in enumerate(pending):
            angle = offset * 2.399963  # 黄金角，均匀铺开
            radius = 0.35 + 0.5 * ((offset % 5) / 5)
            vectors.append(
                VectorPoint(
                    id=chunk.id,
                    source=chunk.source,
                    doc_index=doc_index.get(chunk.source, 0),
                    text_preview=chunk.text.strip().replace("\n", " ")[:90],
                    x=round(math.cos(angle) * radius, 4),
                    y=round(math.sin(angle) * radius, 4),
                    embedded=False,
                )
            )

        kp_nodes, edges = self._knowledge_graph(user_id=user_id, twin_id=twin_id)

        summary = MemorySummary(
            documents=len(documents),
            chunks=len(chunks),
            embedded=len(embedded_vectors),
            knowledge_points=len(kp_nodes),
            edges=len(edges),
            dim=dim,
            projection="pca" if coords else "pending",
        )
        legends = [DocLegend(index=i, title=title, chunks=sum(1 for c in chunks if c.source == title)) for i, title in enumerate(doc_titles)]
        return MemoryMapResponse(
            twin_id=twin_id,
            summary=summary,
            documents=legends,
            vectors=vectors,
            knowledge_points=kp_nodes,
            edges=edges,
        )

    def _knowledge_graph(self, *, user_id: str, twin_id: str) -> tuple[list[KpNode], list[KpLink]]:
        rows = list(
            self.db.execute(
                select(KnowledgePoint, MasteryState)
                .outerjoin(
                    MasteryState,
                    (MasteryState.kp_id == KnowledgePoint.id) & (MasteryState.twin_id == KnowledgePoint.twin_id),
                )
                .where(KnowledgePoint.user_id == user_id, KnowledgePoint.twin_id == twin_id)
            )
        )
        chunk_counts = dict(
            self.db.execute(
                select(ChunkKnowledgePoint.kp_id, func.count())
                .where(ChunkKnowledgePoint.twin_id == twin_id)
                .group_by(ChunkKnowledgePoint.kp_id)
            ).all()
        )
        nodes: list[KpNode] = []
        valid_ids: set[str] = set()
        for kp, state in rows:
            valid_ids.add(kp.id)
            nodes.append(
                KpNode(
                    id=kp.id,
                    name=kp.name,
                    p_mastery=round(state.p_mastery, 3) if state else 0.25,
                    attempt_count=state.attempt_count if state else 0,
                    source=kp.source,
                    chunk_count=int(chunk_counts.get(kp.id, 0)),
                )
            )
        edges: list[KpLink] = []
        for edge in self.db.scalars(select(KpEdge).where(KpEdge.twin_id == twin_id)):
            if edge.from_kp_id in valid_ids and edge.to_kp_id in valid_ids:
                edges.append(KpLink(source=edge.from_kp_id, target=edge.to_kp_id, relation=edge.relation))
        return nodes, edges

    @staticmethod
    def _parse_vector(raw: str | None) -> list[float] | None:
        if not raw:
            return None
        try:
            parsed = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return None
        if isinstance(parsed, list) and parsed and all(isinstance(v, (int, float)) for v in parsed):
            return [float(v) for v in parsed]
        return None

    @staticmethod
    def _pca_2d(vectors: list[list[float]]) -> list[tuple[float, float]]:
        n = len(vectors)
        d = len(vectors[0])
        mean = [sum(v[j] for v in vectors) / n for j in range(d)]
        centered = [[v[j] - mean[j] for j in range(d)] for v in vectors]

        def mat_vec(x: list[float]) -> list[float]:
            # 计算 (Xᵀ X) x = Σ_i (row_i · x) row_i，避免显式构造 d×d 协方差矩阵
            out = [0.0] * d
            for row in centered:
                dot = 0.0
                for j in range(d):
                    dot += row[j] * x[j]
                for j in range(d):
                    out[j] += dot * row[j]
            return out

        def power_iteration(deflate: list[float] | None) -> list[float]:
            rnd = random.Random(42)
            x = [rnd.gauss(0.0, 1.0) for _ in range(d)]
            for _ in range(60):
                y = mat_vec(x)
                if deflate is not None:
                    dot = sum(y[j] * deflate[j] for j in range(d))
                    for j in range(d):
                        y[j] -= dot * deflate[j]
                norm = math.sqrt(sum(v * v for v in y)) or 1.0
                x = [v / norm for v in y]
            return x

        v1 = power_iteration(None)
        v2 = power_iteration(v1)
        raw_points = []
        for row in centered:
            a = sum(row[j] * v1[j] for j in range(d))
            b = sum(row[j] * v2[j] for j in range(d))
            raw_points.append((a, b))
        return MemoryMapService._normalize(raw_points)

    @staticmethod
    def _normalize(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        lo_x, hi_x = min(xs), max(xs)
        lo_y, hi_y = min(ys), max(ys)
        rng_x = (hi_x - lo_x) or 1.0
        rng_y = (hi_y - lo_y) or 1.0
        return [(((p[0] - lo_x) / rng_x) * 1.7 - 0.85, ((p[1] - lo_y) / rng_y) * 1.7 - 0.85) for p in points]
